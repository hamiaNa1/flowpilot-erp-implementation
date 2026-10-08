"""Execute native procurement/sales chain with SQL and actual browser evidence."""
import argparse, json, re, time, traceback
from decimal import Decimal
from playwright.sync_api import sync_playwright
from common import ROOT, ENV, API, query, now, write_json
from gui_probe import browser_login

BARCODE='FP-MAT-001'
RUN='FP-UAT-20261008'
CASES=[]; SNAPSHOTS=[]

def case(cid, scene, expected, actual, passed, steps, evidence, precondition='基础数据已迁移；启用强制审核，关闭负库存'):
    CASES.append({'id':cid,'scene':scene,'precondition':precondition,'steps':steps,'expected':expected,'actual':actual,'status':'通过' if passed else '失败','evidence':evidence,'time':now()})
    write_json('evidence/uat-results.json',CASES)

def ids():
    return {
      'material':query("SELECT me.material_id,me.id extend_id,m.unit FROM jsh_material_extend me JOIN jsh_material m ON m.id=me.material_id WHERE me.bar_code=%s AND me.tenant_id=63 AND me.delete_flag='0'",(BARCODE,))[0],
      'depot':query("SELECT id,name FROM jsh_depot WHERE name='FlowPilot原料仓' AND tenant_id=63 AND delete_flag='0'")[0],
      'supplier':query("SELECT id FROM jsh_supplier WHERE description='legacy-code:SUP-FP-001' AND tenant_id=63 AND delete_flag='0'")[0]['id'],
      'customer':query("SELECT id FROM jsh_supplier WHERE description='legacy-code:CUS-FP-001' AND tenant_id=63 AND delete_flag='0'")[0]['id'],
      'account':query("SELECT id FROM jsh_account WHERE serial_no='FP-ACC-001' AND tenant_id=63 AND delete_flag='0'")[0]['id']}

def stock():
    k=ids()
    rows=query('SELECT current_number FROM jsh_material_current_stock WHERE material_id=%s AND depot_id=%s AND delete_flag=\'0\'',(k['material']['material_id'],k['depot']['id']))
    return Decimal(rows[0]['current_number']) if rows else Decimal(0)

def bill(api, suffix, kind, quantity, link=None, overrides=None):
    k=ids(); purchase=kind.startswith('采购'); order=kind.endswith('订单'); price=68 if purchase else 95
    total=quantity*price; sign=-1 if purchase else 1
    header={'number':RUN+'-'+suffix,'defaultNumber':RUN+'-'+suffix,'type':'其它' if order else '入库' if purchase else '出库','subType':kind,
      'organId':k['supplier'] if purchase else k['customer'],'accountId':k['account'],'operTime':now()[:19].replace('T',' '),
      'totalPrice':sign*total,'changeAmount':0 if order else sign*total,'discount':0,'discountMoney':0,'discountLastMoney':total,
      'otherMoney':0,'deposit':0,'payType':'现付','status':'0','remark':'FlowPilot虚构企业实施UAT，非生产业务','linkNumber':link or ''}
    row={'barCode':BARCODE,'unit':k['material']['unit'],'operNumber':quantity,'unitPrice':price,'allPrice':total,'taxRate':0,'taxMoney':0,'taxLastMoney':total,'depotId':None if order else k['depot']['id'],'remark':'实施验收'}
    if link:
        items=query("SELECT di.id,di.oper_number FROM jsh_depot_item di JOIN jsh_depot_head dh ON dh.id=di.header_id WHERE dh.number=%s AND di.material_id=%s AND di.delete_flag='0'",(link,k['material']['material_id']))
        row.update({'linkId':items[0]['id'],'preNumber':float(items[0]['oper_number']),'finishNumber':0})
    if overrides:
        header.update(overrides.get('header',{})); row.update(overrides.get('row',{}))
    payload={'info':json.dumps(header,ensure_ascii=False),'rows':json.dumps([row],ensure_ascii=False)}
    res=api.call('POST','/depotHead/addDepotHeadAndDetail',json=payload)
    return res, header['number'], payload

def get_bill(number): return query("SELECT id,number,type,sub_type,status,purchase_status,creator,link_number,total_price FROM jsh_depot_head WHERE number=%s AND tenant_id=63 AND delete_flag='0'",(number,))
def approve(api, number, status='1'):
    return api.call('POST','/depotHead/batchSetStatus',json={'ids':str(get_bill(number)[0]['id']),'status':status})

def inventory(page, stage, api):
    k=ids(); dbstock=stock()
    result=api.call('GET','/material/getListWithStock',params={'currentPage':1,'pageSize':10,'depotIds':str(k['depot']['id']),'materialParam':BARCODE,'zeroStock':0})
    page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}/report/material_stock",wait_until='domcontentloaded')
    page.get_by_placeholder('请输入条码、名称、助记码、规格、型号等信息').fill(BARCODE)
    # Select the same warehouse that the SQL checks, using native visible options.
    page.locator('.table-page-search-wrapper .ant-select').first.click()
    page.get_by_role('option',name=re.compile(re.escape(k['depot']['name']))).click()
    page.locator('body').click(position={'x':700,'y':80})
    page.get_by_role('button',name=re.compile(r'查\s*询')).click()
    page.wait_for_timeout(800)
    row=page.locator('.ant-table-row').filter(has_text=BARCODE).first
    row.wait_for(); cells=row.locator('td').all_inner_texts()
    page.screenshot(path=str(ROOT/'evidence'/f'stock-{stage}.png'),full_page=True)
    SNAPSHOTS.append({'time':now(),'stage':stage,'warehouse':k['depot'],'sql_quantity':dbstock,'browser_row':cells,'stock_api':result})
    write_json('evidence/business-stock-snapshots.json',SNAPSHOTS)
    assert Decimal(cells[12])==dbstock and Decimal(str(result['data']['currentStock']))==dbstock, 'Browser/API/SQL inventory mismatch'
    # Inventory row includes both initial and current quantities; native source
    # defines current stock at column 13 (index 12 incl selection column).
    return dbstock, cells

def run():
    if get_bill(RUN+'-PO'):
        raise RuntimeError('This UAT run already exists. Inspect evidence; use a fresh RUN instead of duplicating business data.')
    purchase=API(); sales=API(); purchase.login('fp_purchase',ENV['ERP_DEMO_PASSWORD']); sales.login('fp_sales',ENV['ERP_DEMO_PASSWORD'])
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        context=browser.new_context(viewport={'width':1600,'height':1000},locale='zh-CN')
        context.route('**/hm.baidu.com/**',lambda r:r.abort())
        page=context.new_page(); browser_login(page,'fp_manager')
        before,cells=inventory(page,'01-initial',purchase)
        case('UAT-01','基础资料和期初库存','6个往来单位、6个物料；原料仓支架50件',{'partners':len(query("SELECT id FROM jsh_supplier WHERE tenant_id=63 AND description LIKE 'legacy-code:%'")),'materials':len(query("SELECT id FROM jsh_material_extend WHERE tenant_id=63 AND bar_code LIKE 'FP-MAT-%' AND delete_flag='0'")),'raw_stock':before},before==50,'读取真实基础资料接口、查询SQL、在库存页面筛选仓库与物料',['migration-result.json','stock-01-initial.png'])
        res,po,_=bill(purchase,'PO','采购订单',120); assert res.get('code')==200,res
        assert approve(purchase,po).get('code')==200
        case('UAT-02','采购订单','订单审核后不改变库存',{'order':get_bill(po),'stock':stock()},stock()==before,'采购账号保存采购订单120件并审核',['business-api.json'])
        res,pin,duplicate= bill(purchase,'PI','采购',120,po); assert res.get('code')==200,res
        pending=stock()
        assert approve(purchase,pin).get('code')==200
        after,cells=inventory(page,'02-purchase-approved',purchase)
        case('UAT-03','采购入库与审核','草稿不计库存；审核后50+120=170',{'pending_stock':pending,'approved_stock':after,'document':get_bill(pin),'browser_cells':cells},pending==before and after==170,'按采购订单关联保存采购入库，审核，在页面和SQL核实',['stock-02-purchase-approved.png','business-stock-snapshots.json'])
        res,so,_=bill(sales,'SO','销售订单',30); assert res.get('code')==200,res
        assert approve(sales,so).get('code')==200
        res,sout,_=bill(sales,'SI','销售',30,so); assert res.get('code')==200,res
        assert approve(sales,sout).get('code')==200
        aftersale,cells=inventory(page,'03-sales-approved',sales)
        case('UAT-04','销售订单与出库','170-30=140件；单据关联完整',{'stock':aftersale,'order':get_bill(so),'outbound':get_bill(sout),'browser_cells':cells},aftersale==140,'销售账号保存销售订单30件并审核，关联出库并审核，页面和SQL核实',['stock-03-sales-approved.png','business-api.json'])
        res,no,_=bill(sales,'SHORT','销售',141)
        count=len(get_bill(no)); unchanged=stock()
        case('UAT-05','库存不足','141件出库被拒绝；整单事务回滚，库存仍140',{'response':res,'bill_count':count,'stock':unchanged},res.get('code')!=200 and count==0 and unchanged==140,'销售账号尝试141件出库，SQL查询头表和库存',['business-api.json'])
        # Duplicate an existing successful number after the Redis 2s TTL.
        time.sleep(2.1)
        dup=purchase.call('POST','/depotHead/addDepotHeadAndDetail',json=duplicate)
        case('UAT-06','同号重复提交','拒绝同号单据，仅1个采购入库头、库存保持140',{'response':dup,'count':len(get_bill(pin)),'stock':stock()},dup.get('code')!=200 and len(get_bill(pin))==1 and stock()==140,'重放已成功采购入库的相同请求',['business-api.json'])
        missing,no,_=bill(sales,'MISSING','销售',1,overrides={'row':{'depotId':None}})
        case('UAT-07','必填仓库校验','缺少仓库被拒绝，头表回滚',{'response':missing,'bill_count':len(get_bill(no))},missing.get('code')!=200 and not get_bill(no),'用原生接口提交缺少仓库的销售出库',['business-api.json'])
        # Negative quantities are tested in a draft. They never become effective
        # inventory, and native deletion cleans up only this newly created test bill.
        invalid,no,_=bill(sales,'NEGATIVE','销售',-1)
        accepted=invalid.get('code')==200
        neg_record=get_bill(no)
        if accepted:
            time.sleep(1.7)
            cleanup=sales.call('DELETE','/depotHead/delete',params={'id':neg_record[0]['id']})
        else: cleanup=None
        case('UAT-08','接口负数量校验','出库数量必须大于0；服务端拒绝负数',{'response':invalid,'created_draft':neg_record,'cleanup':cleanup,'stock':stock()},not accepted,'提交-1件的未审核测试单；如果原生接口接受，保留证据并仅清理该测试草稿',['business-api.json'])
        res=approve(sales,sout,'0'); unapproved=stock()
        rere=approve(sales,sout,'1'); reappr=stock()
        case('UAT-09','反审核与重新审核','销售反审核库存恢复170，再审核回到140',{'unapprove':res,'stock_unapproved':unapproved,'reapprove':rere,'stock_reapproved':reappr},res.get('code')==200 and rere.get('code')==200 and unapproved==170 and reappr==140,'通过原生batchSetStatus反审核销售出库，再审核',['business-api.json'])
        ledger=query("SELECT dh.number,dh.type,dh.sub_type,dh.status,dh.creator,dh.link_number,di.oper_number,di.basic_number,di.depot_id,di.link_id FROM jsh_depot_head dh JOIN jsh_depot_item di ON di.header_id=dh.id WHERE dh.number LIKE %s AND dh.delete_flag='0' AND di.delete_flag='0' ORDER BY dh.id",(RUN+'%',))
        write_json('evidence/business-ledger.json',ledger)
        case('UAT-10','单据和库存一致性','4张有效主业务单据，订单完成，采购120销售30，原料仓140',{'ledger':ledger,'final_stock':stock()},len(ledger)==4 and stock()==140,'SQL核对头表、行表、状态、关联单号、库存',['business-ledger.json'])
        browser.close()
    finally:
        write_json('evidence/business-api.json',purchase.records+sales.records)
        write_json('evidence/uat-results.json',CASES)
    print('Executed business UAT: '+str([(c['id'],c['status']) for c in CASES]))

if __name__=='__main__': run()
