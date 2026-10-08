"""Export native API contracts and redacted captured responses as Postman v2.1."""
import json, uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'postman'; out.mkdir(exist_ok=True)
def read(name): return json.loads((root/'evidence'/name).read_text(encoding='utf-8-sig'))
business=read('business-api.json'); readonly=read('api-readonly-verification.json')['requests']
permission=read('permissions-api.json')

def item(name,method,path,body=None,params=None,description='',captured=None,tests=None,pre=None,file=None):
    url={'raw':'{{base_url}}'+path,'host':['{{base_url}}'],'path':path.strip('/').split('/')}
    if params:
        url['query']=[{'key':k,'value':str(v)} for k,v in params.items()]
        from urllib.parse import urlencode
        url['raw']+='?'+urlencode(params)
    headers=[{'key':'X-Access-Token','value':'{{token}}','type':'text'}] if path not in ['/user/randomImage','/user/login'] else []
    req={'method':method,'header':headers,'url':url,'description':description}
    if body is not None:
        req['header'].append({'key':'Content-Type','value':'application/json'})
        req['body']={'mode':'raw','raw':json.dumps(body,ensure_ascii=False,indent=2),'options':{'raw':{'language':'json'}}}
    if file: req['body']={'mode':'formdata','formdata':[{'key':'file','type':'file','src':file}]}
    res={'name':name,'request':req,'event':[],'response':[]}
    test=['pm.test("HTTP 200", () => pm.response.to.have.status(200));']
    if path!='/user/randomImage': test+=['pm.test("native code 200", () => pm.expect(pm.response.json().code).to.eql(200));']
    if tests: test+=tests
    res['event'].append({'listen':'test','script':{'type':'text/javascript','exec':test}})
    if pre: res['event'].append({'listen':'prerequest','script':{'type':'text/javascript','exec':pre}})
    if captured:
        res['response'].append({'name':'2026-10-08 actual captured baseline (redacted)','originalRequest':req,
            'status':'OK','code':captured['http_status'],'header':[{'key':'Content-Type','value':'application/json'}],
            'body':json.dumps(captured['response'],ensure_ascii=False,indent=2)})
    return res

auth=[item('01 生成真实图形验证码','GET','/user/randomImage',description='原生验证码保留。设置uuid后从base64图像识别并手填captcha_code。',tests=[
    'const d = pm.response.json().data; pm.environment.set("captcha_uuid", d.uuid);',
    'pm.visualizer.set("<img src=\"{{image}}\" alt=\"captcha\" />", {image:d.base64 || ""});']),
    item('02 登录并保存本地会话','POST','/user/login',{'loginName':'{{login_name}}','password':'{{password_md5}}','code':'{{captcha_code}}','uuid':'{{captcha_uuid}}'},
         captured=next(r for r in readonly if r['path']=='/user/login'),tests=[
            'const d=pm.response.json().data; pm.test("login",()=>pm.expect(d.msgTip).to.eql("user can login"));',
            'if(d.msgTip === "user can login") {pm.environment.set("token",d.token); pm.environment.set("user_id",String(d.user.id));}'],
         pre=['if(!pm.environment.get("password_md5") || !pm.environment.get("captcha_code")) throw new Error("Set local MD5 password and captcha first");'])]
queries=[]
for i,r in enumerate(readonly[1:]):
    params=r['request']['params']; label=['供应商3条','客户3条','已验证采购入库详情','已验证销售出库详情','原料仓支架库存140','已验证采购订单明细','已验证销售订单明细'][i]
    queries.append(item(label,r['method'],r['path'],params=params,captured=r,description='只读查询已存在的演示资料或单据；SQL对应evidence/api-readonly-verification.json。'))
menu=next(r for r in permission if r['path']=='/function/findMenuByPNumber')
queries.append(item('当前岗位菜单','POST',menu['path'],{'pNumber':'0','userId':'{{user_id}}'},captured=menu))

guard=['if(pm.environment.get("allow_mutation") !== "true") throw new Error("Writes disabled. Use isolated test DB and explicitly set allow_mutation=true");',
       'if(!pm.environment.get("new_run")) pm.environment.set("new_run", "FP-POSTMAN-"+Date.now());',
       'if(!/^FP-POSTMAN-/.test(pm.environment.get("new_run"))) throw new Error("Use a fresh FP-POSTMAN run prefix, never the accepted UAT run");',
       'pm.environment.set("oper_time", new Date().toISOString().slice(0,19).replace("T"," "));',
       'setTimeout(()=>{},1700);']
write=[]
for suffix,label in [('PO','新采购订单120件'),('PI','新采购入库120件'),('SO','新销售订单30件'),('SI','新销售出库30件')]:
    r=next(r for r in business if r['path']=='/depotHead/addDepotHeadAndDetail' and json.loads(r['request']['json']['info'])['number'].endswith('-'+suffix))
    h=json.loads(r['request']['json']['info']); rows=json.loads(r['request']['json']['rows'])
    h.update(number='{{new_run}}-'+suffix,defaultNumber='{{new_run}}-'+suffix,operTime='{{oper_time}}',accountId='{{account_id}}')
    h['organId']='{{supplier_id}}' if suffix in ['PO','PI'] else '{{customer_id}}'
    if suffix in ['PI','SI']:
        h['linkNumber']='{{new_run}}-'+('PO' if suffix=='PI' else 'SO')
        rows[0]['depotId']='{{depot_id}}'
        rows[0]['linkId']='{{purchase_order_item_id}}' if suffix=='PI' else '{{sale_order_item_id}}'
    payload={'info':json.dumps(h,ensure_ascii=False),'rows':json.dumps(rows,ensure_ascii=False)}
    pre=guard[:]
    if suffix in ['PI','SI']:
        key='purchase_order_item_id' if suffix=='PI' else 'sale_order_item_id'
        pre.append(f'if(!pm.environment.get("{key}")) throw new Error("Query the NEW order detail and set {key}; never reuse baseline IDs");')
    write.append(item(label,'POST','/depotHead/addDepotHeadAndDetail',payload,description='根据真实请求生成。先查询本轮订单头/行ID；保存后需显式审核，不能沿用现有UAT ID。',captured=r,pre=pre))
    write.append(item(label+'：查询本轮单据','GET','/depotHead/getDetailByNumber',params={'number':'{{new_run}}-'+suffix},description='保存本轮头ID供审核/明细查询。查询模板来自原生合同，尚未在新Postman业务轮次执行。',tests=[
        'const d=pm.response.json().data; if(d && String(d.number).startsWith(pm.environment.get("new_run"))) pm.environment.set("document_id",String(d.id));']))
    if suffix in ['PO','SO']:
        write.append(item(label+'：查询本轮关联行ID','GET','/depotItem/getDetailList',params={'headerId':'{{document_id}}','mpList':''},description='从真实原生明细响应提取本轮订单行ID，手动填写purchase_order_item_id或sale_order_item_id；不要沿用现有UAT行ID。'))
    write.append(item(label+'：审核本轮单据','POST','/depotHead/batchSetStatus',{'ids':'{{document_id}}','status':'1'},pre=guard+['if(!pm.environment.get("document_id")) throw new Error("Set the NEW document_id first");'],description='只对当前隔离测试轮次新单审核，不使用固定验收单ID。'))
for path,filename in [('/supplier/importVendor','suppliers-native.xls'),('/supplier/importCustomer','customers-native.xls'),('/material/importExcel','materials-native.xls')]:
    write.append(item('原生XLS '+filename,'POST',path,file='../data/'+filename,pre=guard,description='在Postman本地选择文件。商品原生模板包括期初库存，只在新演示库导入；业务开展后不要覆盖期初。'))
collection={'info':{'_postman_id':str(uuid.uuid4()),'name':'FlowPilot ERP native implementation verification','schema':'https://schema.getpostman.com/json/collection/v2.1.0/collection.json','description':'Actual native contracts from jshERP v3.6. Baseline requests executed via requests/Edge, not Postman GUI. Writes guarded and require fresh isolated run.'},'item':[{'name':'认证（手填验证码）','item':auth},{'name':'只读实测查询','item':queries},{'name':'隔离实验写入（默认阻止）','item':write}]}
env={'id':str(uuid.uuid4()),'name':'FlowPilot localhost (no credentials)','values':[{'key':k,'value':v,'type':'secret' if k in ['password_md5','token','captcha_code'] else 'default','enabled':True} for k,v in {
    'base_url':'http://127.0.0.1:8088/jshERP-boot','login_name':'fp_manager','password_md5':'','captcha_uuid':'','captcha_code':'','token':'','user_id':'',
    'allow_mutation':'false','new_run':'','oper_time':'','document_id':'','purchase_order_item_id':'','sale_order_item_id':'','supplier_id':'90','customer_id':'93','account_id':'','depot_id':'19'}.items()], '_postman_variable_scope':'environment'}
for name,d in [('FlowPilot.postman_collection.json',collection),('FlowPilot.local.postman_environment.json',env)]: (out/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Exported Postman collection and blank secret environment; write requests protected.')
