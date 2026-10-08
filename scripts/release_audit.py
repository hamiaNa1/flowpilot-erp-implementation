"""Audit the actual Git publication set, without printing any credential values."""
import hashlib, json, re, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT=Path(__file__).resolve().parents[1]
def tracked():
    p=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True)
    return sorted(set(x.decode('utf-8') for x in p.stdout.split(b'\0') if x))

def main():
    values=[]
    for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        if '=' in line:
            key,value=line.split('=',1)
            if 'PASSWORD' in key:
                values += [value,hashlib.md5(value.encode()).hexdigest()]
    findings=[]; files=tracked(); large=[]
    forbidden={'.env','runtime','backups','tools','upstream','.venv','node_modules'}
    token_patterns=[r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{30,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'AKIA[0-9A-Z]{16}']
    for name in files:
        path=ROOT/name
        if any(p in forbidden for p in path.relative_to(ROOT).parts): findings.append({'file':name,'category':'private/generated path'})
        size=path.stat().st_size
        if size>10*1024*1024: large.append({'file':name,'bytes':size})
        if size>50*1024*1024: findings.append({'file':name,'category':'oversized file'})
        data=path.read_bytes()
        if any(v.encode('utf-8') in data for v in values): findings.append({'file':name,'category':'actual local password or password MD5'})
        text=data.decode('utf-8',errors='replace')
        if any(re.search(p,text) for p in token_patterns): findings.append({'file':name,'category':'token/private-key pattern'})
        if path.suffix=='.json':
            try: json.loads(path.read_text(encoding='utf-8-sig'))
            except (ValueError,UnicodeError): findings.append({'file':name,'category':'invalid JSON'})
    for name in ['.env','runtime/application.properties','runtime/mysql-client.cnf','backups/jsh_erp_20261008_165458.sql','upstream/jshERP-boot/pom.xml','tools/mysql.zip']:
        r=subprocess.run(['git','check-ignore','--quiet',name],cwd=ROOT)
        if r.returncode: findings.append({'file':name,'category':'expected private path not ignored'})
    # Exact existing ERP/Git publication boundaries.
    diff=subprocess.run(['git','-C','upstream','diff','--name-only'],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    expected=['jshERP-boot/src/main/java/com/jsh/erp/utils/ExcelUtils.java']
    if diff!=expected: findings.append({'file':'upstream','category':'unexpected ERP source modification'})
    listed=subprocess.run(['git','rev-list','--all'],cwd=ROOT,capture_output=True)
    commits=listed.stdout.decode().splitlines() if listed.returncode==0 else []
    history_blobs=set()
    for commit in commits:
        tree=subprocess.check_output(['git','ls-tree','-r','-z',commit],cwd=ROOT)
        for raw in tree.split(b'\0'):
            if not raw: continue
            metadata,path=raw.split(b'\t',1); name=path.decode('utf-8'); sha=metadata.decode().split()[2]
            if any(part in forbidden for part in Path(name).parts): findings.append({'file':name,'category':'private path in Git history'})
            if sha in history_blobs: continue
            history_blobs.add(sha); data=subprocess.check_output(['git','cat-file','blob',sha],cwd=ROOT)
            if any(v.encode('utf-8') in data for v in values): findings.append({'file':name,'category':'actual credential in Git history'})
            if any(re.search(p,data.decode('utf-8',errors='replace')) for p in token_patterns): findings.append({'file':name,'category':'token/private-key pattern in Git history'})
    history_count=len(commits)
    report={'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'verdict':'可以上传' if not findings else '暂时不要上传',
        'findings':findings,'candidate_files':len(files),'total_bytes':sum((ROOT/f).stat().st_size for f in files),
        'large_files_over_10mb':large,'ignored_private_paths_verified':True,'upstream_modified_files':diff,
        'history_commits':history_count,'history_unique_blobs_scanned':len(history_blobs),'history_scope':'All locally reachable implementation and own GitHub bootstrap commits scanned. No upstream or private runtime history imported.',
        'limitations':['Docker/Linux and clean-machine full deployment unverified','Two UAT failures remain','No claim of exhaustive security or production-readiness audit']}
    (ROOT/'evidence/release-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':report['verdict'],'files':len(files),'bytes':report['total_bytes'],'findings':findings},ensure_ascii=False))
    if findings: raise SystemExit(1)
if __name__=='__main__': main()
