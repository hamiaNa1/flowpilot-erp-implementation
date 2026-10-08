"""Redact local credentials from publishable evidence; private originals remain ignored."""
import hashlib, json, re
from common import ROOT, ENV, now, write_json

secrets=[v for k,v in ENV.items() if 'PASSWORD' in k]
secrets+= [hashlib.md5(v.encode()).hexdigest() for v in secrets]
def redact(text):
    for s in secrets: text=text.replace(s,'[REDACTED]')
    text=re.sub(r'(?i)((?:password|x-access-token|token|authorization)\s*[:=]\s*)[A-Za-z0-9_./+\-]{12,}',r'\1[REDACTED]',text)
    text=re.sub(r'(?i)([?&](?:token|password|uuid|code)=)[^&\s"<>]+',r'\1[REDACTED]',text)
    return text

changed=[]
for path in (ROOT/'evidence').iterdir():
    if path.suffix not in ['.json','.log','.md','.txt']: continue
    original=path.read_text(encoding='utf-8-sig',errors='replace'); safe=redact(original)
    if safe!=original:
        # Preserve untouched private original outside publishable evidence.
        private=ROOT/'runtime/private-evidence'/path.name; private.parent.mkdir(exist_ok=True)
        if not private.exists(): private.write_bytes(path.read_bytes())
        path.write_text(safe,encoding='utf-8'); changed.append(path.name)
chunks=[]
for name in ['backend.log','jshERP.log','mysql-server.log','redis.log']:
    path=ROOT/'runtime/logs'/name
    if path.exists():
        text=path.read_text(encoding='utf-8',errors='replace')
        chunks.append('### '+name+' (last 65 lines, redacted)\n'+redact('\n'.join(text.splitlines()[-65:])))
(ROOT/'evidence/service-logs-redacted.txt').write_text('\n\n'.join(chunks)+'\n',encoding='utf-8')
write_json('evidence/evidence-redaction.json',{'time':now(),'files_with_exact_local_secret_redactions':changed,'runtime_logs':'Only redacted excerpts published; raw logs ignored','credentials_printed':False})
print('Evidence credentials scrubbed; redacted service-log excerpts exported. Values not printed.')
