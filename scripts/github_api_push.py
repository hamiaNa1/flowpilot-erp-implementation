"""Fallback: transfer identical Git objects through GitHub's Git Database API.

Creates a new main ref, or advances it only from a local ancestor. Never force
updates a ref. Secret authentication remains in memory via Git Credential Manager.
"""
import base64, concurrent.futures, datetime, json, re, subprocess
from github_publish import auth, BASE, git
from common import ROOT

def output(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def store(kind,data,expected):
    p=subprocess.run(['git','hash-object','-t',kind,'-w','--stdin'],cwd=ROOT,input=data,capture_output=True,check=True)
    if p.stdout.decode().strip()!=expected: raise RuntimeError('Imported '+kind+' object SHA mismatch')
def bootstrap(session):
    """Git DB API rejects empty repositories; initialize once through Contents API.

    Import this own bootstrap commit and merge it as a second parent, preserving
    both already-created local and remote histories. Neither branch is rewritten.
    """
    content=output('show','HEAD:README.md')
    date=datetime.datetime.now(datetime.timezone.utc).isoformat()
    person={'name':git('config','user.name'),'email':git('config','user.email'),'date':date}
    result=call(session,'PUT','/contents/README.md',json={'message':'Initialize reviewed FlowPilot delivery repository','content':base64.b64encode(content).decode('ascii'),'branch':'main','author':person,'committer':person})
    sha=result['commit']['sha']
    return import_bootstrap(session,sha)

def import_bootstrap(session,sha):
    c=call(session,'GET','/git/commits/'+sha)
    if c['message'].rstrip('\n')!='Initialize reviewed FlowPilot delivery repository': raise RuntimeError('Unknown remote bootstrap; manual review required')
    if c['parents']: raise RuntimeError('Unexpected bootstrap history; refusing alteration')
    t=call(session,'GET','/git/trees/'+c['tree']['sha'])['tree']
    if len(t)!=1 or t[0]['path']!='README.md': raise RuntimeError('Bootstrap contains unexpected files')
    content=output('show','HEAD:README.md'); blob=t[0]['sha']; store('blob',content,blob)
    treedata=b'100644 README.md\0'+bytes.fromhex(blob); store('tree',treedata,c['tree']['sha'])
    def line(kind,obj,offset):
        dt=datetime.datetime.fromisoformat(obj['date'].replace('Z','+00:00'))
        return f"{kind} {obj['name']} <{obj['email']}> {int(dt.timestamp())} {offset}"
    # GitHub's API normalizes signature dates to UTC and strips message newlines.
    # Recover the exact stored representation by hash, without changing history.
    matched=None
    for minutes in range(-720,841,15):
        sign='-' if minutes<0 else '+'; absolute=abs(minutes); offset=f'{sign}{absolute//60:02d}{absolute%60:02d}'
        head='\n'.join(['tree '+c['tree']['sha'],line('author',c['author'],offset),line('committer',c['committer'],offset)])+'\n\n'
        for n in range(3):
            raw=(head+c['message'].rstrip('\n')+'\n'*n).encode()
            value=subprocess.check_output(['git','hash-object','-t','commit','--stdin'],cwd=ROOT,input=raw).decode().strip()
            if value==sha: matched=raw; break
        if matched is not None: break
    if matched is None: raise RuntimeError('Cannot recover exact bootstrap commit; no branch altered')
    store('commit',matched,sha)
    previous=git('rev-parse','HEAD')
    merged=subprocess.check_output(['git','commit-tree',previous+'^{tree}','-p',previous,'-p',sha],cwd=ROOT,input=b'Merge GitHub API bootstrap while preserving verified delivery history\n').decode().strip()
    subprocess.run(['git','update-ref','refs/heads/main',merged,previous],cwd=ROOT,check=True)
    print('Initialized GitHub repository and preserved both histories with local merge '+merged[:12],flush=True)
    return sha
def call(session,method,path,**kwargs):
    response=session.request(method,BASE+path,timeout=90,**kwargs)
    if response.status_code>=400:
        raise RuntimeError(f'Git Database API {path}: HTTP {response.status_code}; '+str(response.json().get('message','')))
    return response.json()
def tree(session,commit):
    entries=[]; binary=[]
    for raw in output('ls-tree','-r','-z',commit).split(b'\0'):
        if not raw: continue
        left,path=raw.split(b'\t',1); mode,kind,sha=left.decode().split(); path=path.decode('utf-8')
        data=output('cat-file','blob',sha)
        entry={'path':path,'mode':mode,'type':'blob'}
        try:
            if b'\0' in data: raise UnicodeError()
            entry['content']=data.decode('utf-8')
        except UnicodeError:
            entry['sha']=sha; binary.append((sha,data))
        entries.append(entry)
    # Binary objects are independent; one authenticated request per local blob.
    headers=dict(session.headers)
    def upload(pair):
        import requests
        sha,data=pair
        r=requests.post(BASE+'/git/blobs',headers=headers,json={'content':base64.b64encode(data).decode('ascii'),'encoding':'base64'},timeout=90)
        r.raise_for_status()
        if r.json()['sha']!=sha: raise RuntimeError('Binary blob SHA mismatch')
        return sha
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        uploaded=list(pool.map(upload,binary))
    result=call(session,'POST','/git/trees',json={'tree':entries})
    expected=git('rev-parse',commit+'^{tree}')
    if result['sha']!=expected: raise RuntimeError('Tree SHA mismatch; refusing ref update')
    print(f'Transferred tree {expected[:12]} ({len(entries)} files, {len(uploaded)} binary blobs).',flush=True)
    return expected
def signature(line):
    match=re.match(r'(?:author|committer) (.*) <([^>]+)> (\d+) ([+-]\d{4})',line)
    name,email,seconds,offset=match.groups()
    minutes=int(offset[1:3])*60+int(offset[3:]); minutes=-minutes if offset[0]=='-' else minutes
    date=datetime.datetime.fromtimestamp(int(seconds),datetime.timezone(datetime.timedelta(minutes=minutes))).isoformat()
    return {'name':name,'email':email,'date':date}

def main():
    session,_=auth()
    existing=session.get(BASE+'/git/ref/heads/main',timeout=30)
    if existing.status_code in [404,409]:
        branches=session.get(BASE+'/branches',timeout=30); branches.raise_for_status()
        if branches.json(): raise RuntimeError('Repository has existing branches but main is unavailable; refusing replacement')
        remote=bootstrap(session)
    else:
        existing.raise_for_status(); remote=existing.json()['object']['sha']
        if remote not in git('rev-list','HEAD').splitlines():
            prepared=json.loads((ROOT/'evidence/github-repository-preparation.json').read_text(encoding='utf-8'))
            if not prepared['created']: raise RuntimeError('Remote main is not a local ancestor; refuse overwrite')
            import_bootstrap(session,remote)
    local=git('rev-parse','HEAD')
    pending=git('rev-list','--reverse',(remote+'..HEAD') if remote else 'HEAD').splitlines()
    for commit in pending:
        raw=output('cat-file','commit',commit).decode('utf-8'); head,message=raw.split('\n\n',1)
        lines=head.splitlines(); parents=[x.split()[1] for x in lines if x.startswith('parent ')]
        payload={'message':message,'tree':tree(session,commit),'parents':parents,
            'author':signature(next(x for x in lines if x.startswith('author '))),
            'committer':signature(next(x for x in lines if x.startswith('committer ')))}
        created=call(session,'POST','/git/commits',json=payload)
        if created['sha']!=commit:
            raise RuntimeError('Commit metadata SHA differs; no branch updated. Expected '+commit+' actual '+created['sha'])
        print('Transferred identical commit '+commit[:12],flush=True)
    if remote:
        call(session,'PATCH','/git/refs/heads/main',json={'sha':local,'force':False})
    else:
        call(session,'POST','/git/refs',json={'ref':'refs/heads/main','sha':local})
    current=call(session,'GET','/git/ref/heads/main')['object']['sha']
    if current!=local: raise RuntimeError('Remote ref mismatch')
    print('Published identical main commit via Git Database API: '+local,flush=True)
if __name__=='__main__': main()
