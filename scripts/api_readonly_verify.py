"""Verify native query contracts for exported Postman requests."""
import json
from common import API, ENV, query, now, write_json
api=API(); api.login('fp_manager',ENV['ERP_DEMO_PASSWORD'])
scenes=[('/supplier/list',{'currentPage':1,'pageSize':100,'search':json.dumps({'type':'供应商','supplier':'FlowPilot'},ensure_ascii=False)}),
        ('/supplier/list',{'currentPage':1,'pageSize':100,'search':json.dumps({'type':'客户','supplier':'FlowPilot'},ensure_ascii=False)}),
        ('/depotHead/getDetailByNumber',{'number':'FP-UAT-20261008-PI'}),
        ('/depotHead/getDetailByNumber',{'number':'FP-UAT-20261008-SI'}),
        ('/material/getListWithStock',{'currentPage':1,'pageSize':10,'depotIds':'19','materialParam':'FP-MAT-001','zeroStock':0})]
for path,params in scenes:
    result=api.call('GET',path,params=params)
    assert result.get('code')==200,result
    if path=='/supplier/list': assert len(result['data']['rows'])==3,result
for number in ['FP-UAT-20261008-PO','FP-UAT-20261008-SO']:
    head=query("SELECT id FROM jsh_depot_head WHERE number=%s AND tenant_id=63 AND delete_flag='0'",(number,))[0]
    result=api.call('GET','/depotItem/getDetailList',params={'headerId':head['id'],'mpList':''})
    assert result.get('code')==200,result
write_json('evidence/api-readonly-verification.json',{'time':now(),'requests':api.records,'sql_partners':query("SELECT id,supplier,type FROM jsh_supplier WHERE description LIKE 'legacy-code:%' AND tenant_id=63 AND delete_flag='0'"),'all_verified':True})
print('Native base-data, purchase/sales detail and stock query contracts verified.')
