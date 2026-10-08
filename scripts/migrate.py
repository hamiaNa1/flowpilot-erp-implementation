"""Validate legacy ledgers, then migrate through jshERP's native APIs/XLS import."""
import argparse, csv, hashlib, io, json, re
from decimal import Decimal, InvalidOperation
from datetime import datetime
import xlwt, xlrd
from common import ROOT, ENV, API, db, query, now, write_json

DATA=ROOT/'data'
HEADERS=['名称*','规格','型号','颜色','品牌','类别','基础重量(kg)','保质期(天)','基本单位*','副单位','基本条码*','副条码','比例','多属性','采购价','零售价','销售价','最低售价','状态*','序列号','批号','仓位货架','制造商','扩展1','扩展2','扩展3','备注']

def xls(path, rows, native=False):
    book=xlwt.Workbook(encoding='utf-8'); sheet=book.add_sheet('商品信息' if native else '旧台账')
    sheet.show_grid=False
    style=xlwt.easyxf('font: name Microsoft YaHei, bold on, colour white; pattern: pattern solid, fore_colour dark_blue; align: vert centre, wrap on;')
    normal=xlwt.easyxf('font: name Microsoft YaHei; align: vert centre;')
    for r,row in enumerate(rows):
        for c,value in enumerate(row):
            sheet.write(r,c,value,style if r==(1 if native else 0) else normal)
            sheet.col(c).width=max(sheet.col(c).width,min(42,max(14,len(str(value))+4))*256)
        sheet.row(r).height_mismatch=True; sheet.row(r).height=460
    sheet.panes_frozen=True; sheet.horz_split_pos=2 if native else 1
    book.save(str(path))
    reread=xlrd.open_workbook(str(path)).sheet_by_index(0)
    assert reread.nrows==len(rows) and reread.ncols==max(map(len,rows))

def create_templates():
    DATA.mkdir(exist_ok=True)
    partners={
      'suppliers':[['SUP-FP-001','FlowPilot精密钢材供应商（虚构）','供应商','供应联系人甲','苏州演示工业园','2026-10-01'],
                   ['SUP-FP-002','FlowPilot标准件供应商（虚构）','供应商','供应联系人乙','无锡演示工业园','2026-10-01'],
                   ['SUP-FP-003','FlowPilot包装材料供应商（虚构）','供应商','供应联系人丙','常州演示工业园','2026-10-01']],
      'customers':[['CUS-FP-001','FlowPilot汽车总装客户（虚构）','客户','客户联系人甲','上海演示工业园','2026-10-01'],
                   ['CUS-FP-002','FlowPilot售后配件客户（虚构）','客户','客户联系人乙','南京演示工业园','2026-10-01'],
                   ['CUS-FP-003','FlowPilot底盘系统客户（虚构）','客户','客户联系人丙','合肥演示工业园','2026-10-01']]}
    headers=['code','name','type','contact','address','effective_date']
    for name,rows in partners.items():
        p=DATA/f'{name}.csv'
        if not p.exists():
            with p.open('w',encoding='utf-8-sig',newline='') as f: csv.writer(f).writerows([headers]+rows)
            xls(DATA/f'{name}.xls',[headers]+rows)
    materials=[['FP-MAT-001','FlowPilot制动支架','BRK-01','件','68','95','50','10','2026-10-01'],
      ['FP-MAT-002','FlowPilot轮毂轴套','HUB-02','件','35','52','80','0','2026-10-01'],
      ['FP-MAT-003','FlowPilot紧固螺栓M10','M10x30','个','1.2','2','1000','0','2026-10-01'],
      ['FP-MAT-004','FlowPilot密封垫圈','SEAL-04','个','2.5','4','200','0','2026-10-01'],
      ['FP-MAT-005','FlowPilot冷轧钢板','SPCC-2mm','千克','6','8','500','0','2026-10-01'],
      ['FP-MAT-006','FlowPilot成品包装箱','BOX-06','个','3','5','100','0','2026-10-01']]
    p=DATA/'materials.csv'
    if not p.exists():
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            csv.writer(f).writerows([['barcode','name','specification','unit','purchase_price','sale_price','raw_stock','finished_stock','effective_date']]+materials)
    p=DATA/'initial-stock.csv'
    if not p.exists():
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            csv.writer(f).writerows([['barcode','warehouse','quantity','effective_date']]+[[r[0],w,r[c],r[8]] for r in materials for w,c in [('FlowPilot原料仓',6),('FlowPilot成品仓',7)]])
        xls(DATA/'initial-stock.xls',[['barcode','warehouse','quantity','effective_date']]+[[r[0],w,int(r[c]),r[8]] for r in materials for w,c in [('FlowPilot原料仓',6),('FlowPilot成品仓',7)]])
    print('Created UTF-8 BOM CSV and legacy XLS templates.')

def read_csv(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def validate(loaded=None, save=True):
    errors=[]; loaded=loaded if loaded is not None else {name:read_csv(name+'.csv') for name in ['suppliers','customers','materials','initial-stock']}
    for kind,rows in loaded.items():
        seen=set()
        for i,row in enumerate(rows,2):
            try:
                required=['barcode','warehouse','quantity'] if kind=='initial-stock' else (['barcode','name','unit'] if kind=='materials' else ['code','name','type'])
                for field in required:
                    if not row.get(field,'').strip(): raise ValueError('missing '+field)
                key=(row['barcode'],row['warehouse']) if kind=='initial-stock' else row.get('barcode',row.get('code'))
                if key in seen: raise ValueError('duplicate code '+str(key))
                seen.add(key)
                datetime.strptime(row['effective_date'],'%Y-%m-%d')
                for field in (['quantity'] if kind=='initial-stock' else ['purchase_price','sale_price','raw_stock','finished_stock'] if kind=='materials' else []):
                    n=Decimal(row[field])
                    if not n.is_finite() or n<0: raise ValueError('illegal nonnegative quantity/price '+field)
                if kind=='materials' and (len(row['barcode'])>30 or len(row['name'])>100): raise ValueError('field length exceeded')
                if kind in ('suppliers','customers') and row['type']!=('供应商' if kind=='suppliers' else '客户'): raise ValueError('incorrect partner type')
            except (ValueError,InvalidOperation,KeyError) as e: errors.append({'file':kind+'.csv','row':i,'error':str(e)})
    by_code={r['barcode']:r for r in loaded['materials']}
    for row in loaded['initial-stock']:
        if row['barcode'] not in by_code: errors.append({'file':'initial-stock.csv','error':'unknown material '+row['barcode']})
        elif row['warehouse'] in ('FlowPilot原料仓','FlowPilot成品仓'):
            field='raw_stock' if row['warehouse']=='FlowPilot原料仓' else 'finished_stock'
            try:
                if Decimal(row['quantity'])!=Decimal(by_code[row['barcode']][field]): errors.append({'file':'initial-stock.csv','error':'initial quantity mismatch'})
            except (InvalidOperation,KeyError): errors.append({'file':'initial-stock.csv','error':'invalid quantity in cross-check'})
        else: errors.append({'file':'initial-stock.csv','error':'unknown warehouse '+row['warehouse']})
    if save: write_json('evidence/migration-precheck.json',{'time':now(),'records':{k:len(v) for k,v in loaded.items()},'errors':errors,'encoding':'UTF-8 BOM','valid':not errors})
    if errors: raise ValueError('Source validation failed before mutation: '+str(errors))
    return loaded

def import_partners(api, loaded):
    """Native two-header XLS contract; verify every imported field and stable IDs."""
    results=[]
    for kind,endpoint in [('suppliers','importVendor'),('customers','importCustomer')]:
        rows=loaded[kind]; typ='供应商' if kind=='suppliers' else '客户'
        before=query("SELECT id,supplier,description FROM jsh_supplier WHERE tenant_id=63 AND type=%s AND description LIKE %s AND delete_flag='0' ORDER BY id",(typ,'legacy-code:%'))
        # Native importer updates by name, so refuse a collision with another legacy code.
        for r in rows:
            matches=query("SELECT id,description FROM jsh_supplier WHERE tenant_id=63 AND type=%s AND supplier=%s AND delete_flag='0'",(typ,r['name']))
            assert len(matches)<=1 and all(m['description']=='legacy-code:'+r['code'] for m in matches),'Partner name collision; manual review required'
        heads=['名称*','联系人','手机号码','联系电话','电子邮箱','传真','期初应付' if kind=='suppliers' else '期初应收','纳税人识别号','税率(%)','开户行','账号','地址','备注','排序','状态*']
        content=[['*导入时本行内容请勿删除，切记！']+['']*14,heads]
        content += [[r['name'],r['contact'],'','','','',0,'',13,'','',r['address'],'legacy-code:'+r['code'],'10','1'] for r in rows]
        path=DATA/(kind+'-native.xls'); xls(path,content,True)
        with path.open('rb') as f:
            response=api.call('POST','/supplier/'+endpoint,files={'file':(path.name,f,'application/vnd.ms-excel')})
        assert response.get('code')==200,response
        after=query("SELECT id,supplier,contacts,address,description,enabled FROM jsh_supplier WHERE tenant_id=63 AND type=%s AND description LIKE %s AND delete_flag='0' ORDER BY id",(typ,'legacy-code:%'))
        assert len(after)==len(rows)
        bycode={r['description']:r for r in after}
        for r in rows:
            a=bycode['legacy-code:'+r['code']]
            assert (a['supplier'],a['contacts'],a['address'],bool(a['enabled']))==(r['name'],r['contact'],r['address'],True)
        assert not before or [(r['id'],r['description']) for r in before]==[(r['id'],r['description']) for r in after]
        results.append({'kind':kind,'endpoint':'/supplier/'+endpoint,'before':before,'after':after,'response':response,'stable_ids':bool(before),'verified':True})
    return results

def ensure_relation(api, kind, key, ids, btn=None):
    current=query('SELECT id,value,btn_str FROM jsh_user_business WHERE type=%s AND key_id=%s AND delete_flag=\'0\' AND (tenant_id=63 OR tenant_id IS NULL)',(kind,str(key)))
    body={'type':kind,'keyId':str(key),'value':''.join(f'[{v}]' for v in ids)}
    if btn is not None:
        body['btnStr']=json.dumps(btn,ensure_ascii=False,separators=(',',':'))
        if len(body['btnStr'])>2000: raise ValueError('Button permissions exceed native varchar(2000) limit')
    if current:
        body['id']=current[0]['id']; res=api.call('PUT','/userBusiness/update',json=body)
    else: res=api.call('POST','/userBusiness/add',json=body)
    assert res.get('code')==200, res

def migrate():
    loaded=validate(); api=API(); api.login()
    try:
        config=query('SELECT * FROM jsh_system_config WHERE tenant_id=63 AND delete_flag=\'0\'')[0]
        # Read existing configuration and only adjust demonstration business parameters.
        body={'id':config['id'],'companyName':'FlowPilot汽车零部件有限公司（虚构演示企业）','minusStockFlag':'0','inOutManageFlag':'0','forceApprovalFlag':'1'}
        assert api.call('PUT','/systemConfig/update',json=body).get('code')==200
        for name in ['FlowPilot原料仓','FlowPilot成品仓']:
            if not query('SELECT id FROM jsh_depot WHERE name=%s AND tenant_id=63 AND delete_flag=\'0\'',(name,)):
                assert api.call('POST','/depot/add',json={'name':name,'address':'虚构演示仓库','description':'FlowPilot实施实验','sort':'10','isDefault':name.endswith('原料仓')}).get('code')==200
        depots=query('SELECT id,name FROM jsh_depot WHERE tenant_id=63 AND delete_flag=\'0\' ORDER BY id')
        fpdepots=[d['id'] for d in depots if d['name'].startswith('FlowPilot')]
        existing_depots=query("SELECT value FROM jsh_user_business WHERE type='UserDepot' AND key_id='63' AND delete_flag='0'")
        old=[int(x) for x in re.findall(r'\[(\d+)\]',existing_depots[0]['value'])] if existing_depots else []
        ensure_relation(api,'UserDepot',63,sorted(set(old+fpdepots)))
        write_json('evidence/partner-native-import.json',{'time':now(),'results':import_partners(api,loaded)})
        if not query('SELECT id FROM jsh_account WHERE tenant_id=63 AND serial_no=\'FP-ACC-001\' AND delete_flag=\'0\''):
            assert api.call('POST','/account/add',json={'name':'FlowPilot演示结算账户','serialNo':'FP-ACC-001','initialAmount':100000,'currentAmount':100000,'isDefault':False,'remark':'虚构账户，不对应银行','sort':'10'}).get('code')==200
        codes=[r['barcode'] for r in loaded['materials']]
        existing=query("SELECT me.bar_code FROM jsh_material_extend me WHERE me.tenant_id=63 AND me.delete_flag='0' AND me.bar_code LIKE 'FP-MAT-%'")
        if not existing:
            rows=[['*导入时本行内容请勿删除，切记！']+['']*(26+len(depots)),HEADERS+[d['name'] for d in depots]]
            for r in loaded['materials']:
                values=[r['name'],r['specification'],'','','FlowPilot','','','',''+r['unit'],'',r['barcode'],'','','',float(r['purchase_price']),float(r['sale_price']),float(r['sale_price']),0,'1','0','0','','FlowPilot虚构制造商','','','','旧Excel台账迁移 '+r['barcode']]
                values += [float(r['raw_stock']) if d['name']=='FlowPilot原料仓' else float(r['finished_stock']) if d['name']=='FlowPilot成品仓' else 0 for d in depots]
                rows.append(values)
            xls(DATA/'materials-native.xls',rows,True)
            # Capture the actual native export template to verify positional headers.
            resp=api.session.get(api.base+'/material/exportExcel',timeout=60)
            resp.raise_for_status(); (DATA/'native-export-template.xls').write_bytes(resp.content)
            if not resp.content: raise RuntimeError('Native export returned empty body; inspect backend error log')
            exported=xlrd.open_workbook(str(DATA/'native-export-template.xls')).sheet_by_index(0)
            assert exported.row_values(1)[:27]==HEADERS, 'Native header contract mismatch'
            with (DATA/'materials-native.xls').open('rb') as f:
                res=api.call('POST','/material/importExcel',files={'file':('materials-native.xls',f,'application/vnd.ms-excel')})
            assert res.get('code')==200,res
        else:
            assert {r['bar_code'] for r in existing}==set(codes),'partial import detected; reconcile before retry'
        functions=query("SELECT id,name,url,number,parent_number FROM jsh_function WHERE delete_flag='0'")
        byname={f['name']:f['id'] for f in functions}
        roles={
          'fp_manager':('FlowPilot实施管理员',['商品信息','供应商信息','客户信息','仓库','结算账户','用户管理','角色管理','系统参数','采购订单','采购入库','销售订单','销售出库','商品库存'], '全部数据'),
          'fp_purchase':('FlowPilot采购员',['采购订单','采购入库','供应商信息','商品信息','商品库存'],'个人数据'),
          'fp_warehouse':('FlowPilot仓库员',['商品库存','入库明细','出库明细','其它入库','其它出库','商品信息'],'全部数据'),
          'fp_sales':('FlowPilot销售员',['销售订单','销售出库','客户信息','商品信息','商品库存'],'个人数据')}
        # Find actual menu labels by contained keywords, without inventing native IDs.
        role_results=[]
        for login,(role_name,names,description) in roles.items():
            found=query('SELECT id FROM jsh_role WHERE tenant_id=63 AND name=%s AND delete_flag=\'0\'',(role_name,))
            if not found:
                assert api.call('POST','/role/add',json={'name':role_name,'description':description,'type':'私有','remark':'虚构演示岗位','sort':'10'}).get('code')==200
                found=query('SELECT id FROM jsh_role WHERE tenant_id=63 AND name=%s AND delete_flag=\'0\'',(role_name,))
            rid=found[0]['id']
            ids=[f['id'] for f in functions if f['name'] in names]
            if login=='fp_manager':
                ids=[int(x) for x in re.findall(r'\[(\d+)\]',query("SELECT value FROM jsh_user_business WHERE type='RoleFunctions' AND key_id='10'")[0]['value'])]
            ensure_relation(api,'RoleFunctions',rid,ids,[{'funId':i,'btnStr':'1,2,3,7'} for i in ids])
            found=query('SELECT id FROM jsh_user WHERE tenant_id=63 AND login_name=%s AND delete_flag=\'0\'',(login,))
            if not found:
                res=api.call('POST','/user/addUser',json={'username':role_name,'loginName':login,'position':role_name,'roleId':rid,'leaderFlag':'0'})
                assert isinstance(res,dict) and res.get('code')==200,res
                found=query('SELECT id FROM jsh_user WHERE tenant_id=63 AND login_name=%s AND delete_flag=\'0\'',(login,))
                # Native add always sets 123456, so immediately rotate via native updatePwd.
                res=api.call('PUT','/user/updatePwd',json={'userId':found[0]['id'],'oldpassword':hashlib.md5(b'123456').hexdigest(),'password':hashlib.md5(ENV['ERP_DEMO_PASSWORD'].encode()).hexdigest()})
                assert res.get('code')==200,res
                api.records[-1]['request']={'json':{'userId':found[0]['id'],'oldpassword':'[REDACTED]','password':'[REDACTED]'}}
            uid=found[0]['id']; ensure_relation(api,'UserRole',uid,[rid]); ensure_relation(api,'UserDepot',uid,fpdepots)
            customers=query("SELECT id FROM jsh_supplier WHERE tenant_id=63 AND type='客户' AND description LIKE 'legacy-code:CUS-FP-%'")
            ensure_relation(api,'UserCustomer',uid,[r['id'] for r in customers])
            role_results.append({'login':login,'user_id':uid,'role_id':rid,'role_name':role_name,'menus':[f['name'] for f in functions if f['id'] in ids],'data_scope':description})
        report={'time':now(),'partners':query("SELECT id,supplier,type,description FROM jsh_supplier WHERE tenant_id=63 AND description LIKE 'legacy-code:%'"),
          'materials':query("SELECT m.id,m.name,m.unit,me.bar_code FROM jsh_material m JOIN jsh_material_extend me ON me.material_id=m.id WHERE me.bar_code LIKE 'FP-MAT-%' AND me.delete_flag='0'"),
          'stocks':query("SELECT me.bar_code,d.name,s.number,c.current_number FROM jsh_material_initial_stock s JOIN jsh_material m ON m.id=s.material_id JOIN jsh_material_extend me ON me.material_id=m.id JOIN jsh_depot d ON d.id=s.depot_id LEFT JOIN jsh_material_current_stock c ON c.material_id=m.id AND c.depot_id=d.id WHERE me.bar_code LIKE 'FP-MAT-%' ORDER BY me.bar_code,d.id"),'roles':role_results}
        assert len(report['partners'])==6 and len(report['materials'])==6
        write_json('evidence/migration-result.json',report)
        print('Native migration verified: 6 partners, 6 materials, 4 role/user profiles.')
    finally: write_json('evidence/migration-api.json',api.records)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['templates','validate','import']); args=p.parse_args()
    if args.action=='templates': create_templates()
    elif args.action=='validate': validate(); print('Precheck passed')
    else: migrate()
