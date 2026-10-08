"""Final read-only ERP checks and local delivery/artifact validation."""
import ast, hashlib, json, re, subprocess
from pathlib import Path
from decimal import Decimal
import requests, yaml
from common import ROOT, ENV, query, now, write_json
from native import redis_cmd

def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({'check':name,'passed':bool(ok),'detail':detail})
    required=[f'{n:02d}-' for n in range(1,14)]
    docs=list((ROOT/'docs').glob('*.md'))
    check('13 delivery documents',all(sum(p.name.startswith(n) for p in docs)==1 for n in required))
    python_errors=[]
    for path in (ROOT/'scripts').glob('*.py'):
        try: ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        except SyntaxError as e: python_errors.append({'file':str(path.relative_to(ROOT)),'error':str(e)})
    check('Python syntax',not python_errors,python_errors)
    broken=[]
    for path in docs+[ROOT/'README.md',ROOT/'UPSTREAM.md']:
        for dest in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if dest.startswith(('http:','https:','#')): continue
            target=(path.parent/dest.split('#')[0]).resolve()
            if not target.exists(): broken.append({'file':str(path.relative_to(ROOT)),'target':dest})
    check('Local Markdown links',not broken,broken)
    config=yaml.safe_load((ROOT/'compose.yaml').read_text(encoding='utf-8'))
    services=config['services']; violations=[]
    for name,s in services.items():
        if not s.get('healthcheck'): violations.append(name+' lacks healthcheck')
        for port in s.get('ports',[]):
            if not str(port).startswith('127.0.0.1:'): violations.append(name+' exposed outside loopback')
    check('Compose YAML/static safety only (Docker runtime NOT executed)',set(services)=={'mysql','redis','backend','nginx'} and not violations,violations)
    env=json.loads((ROOT/'postman/FlowPilot.local.postman_environment.json').read_text(encoding='utf-8'))
    values={v['key']:v['value'] for v in env['values']}
    check('Postman secret placeholders blank, writes disabled',all(values[k]=='' for k in ['password_md5','token','captcha_code','captcha_uuid']) and values['allow_mutation']=='false')
    coll=json.loads((ROOT/'postman/FlowPilot.postman_collection.json').read_text(encoding='utf-8'))
    check('Postman v2.1 schema declaration',coll['info']['schema']=='https://schema.getpostman.com/json/collection/v2.1.0/collection.json')
    for name in ['resume-pdf-verification.json','xls-template-verification.json']:
        d=json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))
        check(name+' visual review',d['visual_review'].startswith('passed'))
    uat=[]
    for name in ['uat-results.json','permissions-uat.json','gui-operation-uat.json']:
        uat+=json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))
    check('UAT truthful count and two failures preserved',len(uat)==19 and sum(r['status']=='通过' for r in uat)==17 and {r['id'] for r in uat if r['status']=='失败'}=={'UAT-08','UAT-12'})
    # Check current state, not the frozen earlier snapshots.
    headers=query("SELECT number,status,creator FROM jsh_depot_head WHERE tenant_id=63 AND number LIKE 'FP-%' AND delete_flag='0' ORDER BY id")
    check('Only four valid core bills; all disposable drafts cleaned',len(headers)==4 and {r['number'] for r in headers}=={f'FP-UAT-20261008-{s}' for s in ['PO','PI','SO','SI']},headers)
    current=query("SELECT c.current_number FROM jsh_material_current_stock c JOIN jsh_material_extend me ON me.material_id=c.material_id JOIN jsh_depot d ON d.id=c.depot_id WHERE me.bar_code='FP-MAT-001' AND me.tenant_id=63 AND d.name='FlowPilot原料仓' AND c.delete_flag='0'")
    check('Final raw warehouse stock 140',len(current)==1 and current[0]['current_number']==Decimal(140),current)
    chars=query('SELECT VERSION() AS version, @@character_set_server AS charset, @@collation_server AS collation')
    check('MySQL charset utf8mb4',chars[0]['charset']=='utf8mb4',chars)
    check('Redis authenticated PONG',redis_cmd('PING')=='PONG')
    for path in ['/healthz','/','/jshERP-boot/platformConfig/getPlatform/name']:
        r=requests.get(f"http://127.0.0.1:{ENV['HTTP_PORT']}"+path,timeout=20)
        check('HTTP '+path,r.status_code==200,{'status':r.status_code,'bytes':len(r.content)})
    accounts=query("SELECT login_name,status,password FROM jsh_user WHERE login_name IN ('admin','jsh','test123')")
    safe=[]
    for a in accounts:
        changed=a['password'] not in {hashlib.md5(v.encode()).hexdigest() for v in ['123456','admin','jsh']}
        safe.append({'login_name':a['login_name'],'status':a['status'],'default_password_changed':changed if a['login_name']!='test123' else None})
    check('Native default accounts rotated; sample disabled',all(a['default_password_changed'] for a in safe if a['login_name'] in ['admin','jsh']) and all(a['status']==1 for a in safe if a['login_name']=='test123'),safe)
    restored=json.loads((ROOT/'evidence/backup-restore-verification.json').read_text(encoding='utf-8'))
    check('Recorded isolated restore: all 30 tables equal',restored['all_equal'] and len(restored['table_results'])==30)
    persisted=json.loads((ROOT/'evidence/persistence-restart.json').read_text(encoding='utf-8'))
    check('Recorded four-service restart data persisted',persisted['data_equal'] and all(persisted['all_ports_stopped'].values()))
    ps=json.loads((ROOT/'evidence/powershell-syntax.json').read_text(encoding='utf-8-sig'))
    check('PowerShell syntax',not any(p['errors'] for p in ps),ps)
    report={'time':now(),'checks':checks,'all_passed':all(c['passed'] for c in checks),
        'meaning':'Delivery consistency checks passed does NOT mean all UAT passed; two business/security failures remain',
        'not_executed':['Docker runtime/compose config CLI','Linux VM','Clean-machine complete setup','Upstream unit-test compilation/execution']}
    write_json('evidence/delivery-verification.json',report)
    print(json.dumps({'all_passed':report['all_passed'],'checks':len(checks),'failed':[c for c in checks if not c['passed']]},ensure_ascii=False))
    if not report['all_passed']: raise SystemExit(1)
if __name__=='__main__': main()
