"""Operate real ERP dialogs and status buttons; confirm resulting SQL."""
import re, time, json
from playwright.sync_api import sync_playwright
from common import ROOT, ENV, query, now, write_json
from gui_probe import browser_login
from business_uat import stock, get_bill, RUN

def main():
    results=json.loads((ROOT/'evidence/gui-operation-uat.json').read_text(encoding='utf-8')) if (ROOT/'evidence/gui-operation-uat.json').exists() else []
    calls=json.loads((ROOT/'evidence/gui-operation-api.json').read_text(encoding='utf-8')) if (ROOT/'evidence/gui-operation-api.json').exists() else []
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        context=browser.new_context(viewport={'width':1600,'height':1000},locale='zh-CN')
        context.route('**/hm.baidu.com/**',lambda r:r.abort())
        page=context.new_page(); browser_login(page,'fp_manager')
        def capture(response):
            if any(p in response.url for p in ['/supplier/update','/depotHead/batchSetStatus']):
                calls.append({'time':now(),'url':response.url,'request':response.request.post_data,'http_status':response.status,'response':response.json()})
                write_json('evidence/gui-operation-api.json',calls)
        page.on('response',capture)
        name='FlowPilot精密钢材供应商（虚构）'
        before=query("SELECT id,supplier,contacts,description FROM jsh_supplier WHERE description='legacy-code:SUP-FP-001' AND tenant_id=63 AND delete_flag='0'")[0]
        page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}/system/vendor",wait_until='domcontentloaded')
        page.get_by_placeholder('请输入名称查询',exact=True).fill(name)
        page.get_by_role('button',name=re.compile(r'查\s*询')).click()
        row=page.locator('.ant-table-row').filter(has_text=name).first; row.wait_for()
        row.get_by_text('编辑',exact=True).click()
        modal=page.locator('.ant-modal-content').filter(has=page.get_by_placeholder('请输入联系人',exact=True))
        modal.get_by_placeholder('请输入联系人',exact=True).fill('供应联系人甲（页面验收）')
        page.screenshot(path=str(ROOT/'evidence/gui-vendor-edit-dialog.png'),full_page=True)
        modal.get_by_role('button',name=re.compile(r'保\s*存')).click()
        page.wait_for_timeout(1700)
        after=query("SELECT id,supplier,contacts,description FROM jsh_supplier WHERE id=%s",(before['id'],))[0]
        assert after['contacts']=='供应联系人甲（页面验收）' and after['description']==before['description']
        page.screenshot(path=str(ROOT/'evidence/gui-vendor-edited.png'),full_page=True)
        if not any(r['id']=='UAT-14' for r in results): results.append({'id':'UAT-14','scene':'真实页面编辑中文供应商联系人','precondition':'fp_manager真实登录且拥有基础资料编辑按钮','steps':'供应商页面查询旧编码对应名称，点击编辑，修改联系人并保存，SQL核对','expected':'原记录联系人更新，ID和旧编码保留','actual':{'before':before,'after':after},'status':'通过','evidence':['gui-vendor-edit-dialog.png','gui-vendor-edited.png','gui-operation-api.json'],'time':now()})
        write_json('evidence/gui-operation-uat.json',results)
        number=RUN+'-SI'; original=get_bill(number)[0]
        assert (original['status']=='1' and stock()==140) or (original['status']=='0' and stock()==170)
        stages=[('0','反审核',170),('1','审核',140)] if original['status']=='1' else [('1','审核',140)]
        for status,label,quantity in stages:
            page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}/bill/sale_out",wait_until='domcontentloaded')
            page.get_by_placeholder('请输入单据编号',exact=True).fill(number)
            page.get_by_role('button',name=re.compile(r'查\s*询')).click()
            row=page.locator('.ant-table-row').filter(has_text=number).first; row.wait_for()
            row.get_by_role('checkbox').check()
            page.locator('button').filter(has_text=re.compile('^'+r'\s*'.join(label)+'$')).click()
            page.locator('.ant-modal-confirm').get_by_role('button',name=re.compile(r'确\s*定')).click()
            deadline=time.monotonic()+10
            while time.monotonic()<deadline and get_bill(number)[0]['status']!=status: page.wait_for_timeout(300)
            assert get_bill(number)[0]['status']==status and stock()==quantity
            page.screenshot(path=str(ROOT/'evidence'/f'gui-sale-status-{status}.png'),full_page=True)
            results=[r for r in results if r['id']!='UAT-15-'+status]
            results.append({'id':'UAT-15-'+status,'scene':'页面销售出库'+label,'precondition':'已保存真实销售出库30件','steps':'销售出库页面按单号查询，勾选，点击'+label+'并确认，SQL核对','expected':f'状态{status}，原料仓{quantity}件','actual':{'document':get_bill(number),'stock':stock()},'status':'通过','evidence':[f'gui-sale-status-{status}.png','gui-operation-api.json'],'time':now()})
            write_json('evidence/gui-operation-uat.json',results)
            page.wait_for_timeout(1700)
        write_json('evidence/gui-operation-api.json',calls)
        browser.close()
    print('Real browser operations verified: Chinese partner edit; reverse approval 170 and approval 140.')

if __name__=='__main__': main()
