"""Publish this reviewed implementation repository using existing Git credentials.

No token is printed, stored in source, or embedded in remote URLs. User has
explicitly authorized the named public repository and normal commits/pushes.
"""
import argparse, os, subprocess, json
from pathlib import Path
import requests
from common import ROOT, now, write_json

OWNER='hamiaNa1'; NAME='flowpilot-erp-implementation'
REMOTE=f'https://github.com/{OWNER}/{NAME}.git'
BASE=f'https://api.github.com/repos/{OWNER}/{NAME}'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8',stderr=subprocess.PIPE).strip()
def auth():
    env=os.environ.copy(); env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
    p=subprocess.run(['git','credential','fill'],cwd=ROOT,input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=env,timeout=90)
    values=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    if not values.get('password'): raise RuntimeError('GitHub credential unavailable; sign in using Git Credential Manager. No credentials logged.')
    s=requests.Session(); s.headers.update({'Authorization':'Bearer '+values['password'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    r=s.get('https://api.github.com/user',timeout=30); r.raise_for_status(); user=r.json()
    if user['login'].lower()!=OWNER.lower(): raise RuntimeError('Authenticated account differs from explicitly requested owner')
    return s,user

def prepare():
    audit=json.loads((ROOT/'evidence/release-audit.json').read_text(encoding='utf-8'))
    verified=json.loads((ROOT/'evidence/delivery-verification.json').read_text(encoding='utf-8'))
    if audit['findings'] or not verified['all_passed']: raise RuntimeError('Review blockers remain; refusing publication')
    s,user=auth(); r=s.get(BASE,timeout=30)
    if r.status_code==404:
        r=s.post('https://api.github.com/user/repos',json={'name':NAME,'private':False,'auto_init':False,'description':'个人ERP实施实战：jshERP部署、Excel迁移、采购库存销售UAT、SQL核对与备份隔离恢复；真实证据与验收限制。'},timeout=30)
        r.raise_for_status(); repo=r.json(); created=True
    else:
        r.raise_for_status(); repo=r.json(); created=False
        if repo.get('private'): raise RuntimeError('Existing repository is private; refusing to change its visibility')
        branches=s.get(BASE+'/branches',timeout=30); branches.raise_for_status()
        if branches.json(): raise RuntimeError('Existing repository contains branches; refusing to overwrite prior work')
    assert repo['owner']['login'].lower()==OWNER.lower()
    subprocess.run(['git','config','user.name',OWNER],cwd=ROOT,check=True)
    subprocess.run(['git','config','user.email',f"{user['id']}+{OWNER}@users.noreply.github.com"],cwd=ROOT,check=True)
    origins=git('remote').splitlines()
    if 'origin' in origins:
        if git('remote','get-url','origin')!=REMOTE: raise RuntimeError('Existing origin differs; refusing remote replacement')
    else: subprocess.run(['git','remote','add','origin',REMOTE],cwd=ROOT,check=True)
    write_json('evidence/github-repository-preparation.json',{'time':now(),'authenticated_owner':OWNER,'repository':repo['html_url'],'public':not repo['private'],'created':created,'existing_nonempty_repo_overwritten':False,'credentials_published':False})
    print('Prepared public repository '+repo['html_url']+'; code not pushed by prepare.')

def verify(record=False):
    local=git('rev-parse','HEAD')
    ref=requests.get(BASE+'/git/ref/heads/main',timeout=30); ref.raise_for_status()
    remote=ref.json()['object']['sha']
    if local!=remote: raise RuntimeError('Remote main does not match local commit')
    repo=requests.get(BASE,timeout=30); repo.raise_for_status()
    if repo.json()['private']: raise RuntimeError('Repository not public')
    readme=requests.get(BASE+'/readme',timeout=30); readme.raise_for_status()
    readme_match=readme.json()['sha']==git('rev-parse','HEAD:README.md')
    try:
        page=requests.get(f'https://github.com/{OWNER}/{NAME}',timeout=15)
        page_status=page.status_code
    except requests.RequestException: page_status='unavailable from this network; public repository/readme verified using anonymous GitHub API'
    tree=requests.get(BASE+'/git/trees/'+local,params={'recursive':'1'},timeout=30); tree.raise_for_status()
    paths=[r['path'] for r in tree.json()['tree'] if r['type']=='blob']
    forbidden=['.env','runtime/','backups/','tools/','upstream/','.venv/']
    excluded=not any(p==f or (f.endswith('/') and p.startswith(f)) for p in paths for f in forbidden)
    docs=[p for p in paths if p.startswith('docs/') and p.split('/')[-1][:2].isdigit() and p.endswith('.md')]
    okay=readme_match and excluded and len(docs)==13
    if not okay: raise RuntimeError('Public repository content verification failed')
    report={'time':now(),'repository':f'https://github.com/{OWNER}/{NAME}','verified_delivery_commit':local,
        'remote_main_matches_local':True,'anonymous_repository_http_status':repo.status_code,'anonymous_page_http_status':page_status,
        'public':True,'readme_blob_matches_local':readme_match,'delivery_documents':len(docs),'published_files':len(paths),
        'private_runtime_paths_absent':excluded,'force_push_used':False,'credential_in_remote_url':False,
        'transport':'Git Database API: identical local blobs/tree/commit; ref advanced without force. Git HTTPS pushes failed twice with connection reset.',
        'note':'This records the verified delivery commit before the follow-up evidence commit; final branch equality is rechecked after the follow-up ref advance.'}
    if record: write_json('evidence/github-publication.json',report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['prepare','verify','record']); a=p.parse_args()
    if a.action=='prepare': prepare()
    else: verify(record=a.action=='record')
