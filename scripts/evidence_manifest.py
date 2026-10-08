"""Freeze checksums of published evidence, excluding the self-referencing manifest."""
import hashlib, json, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT=Path(__file__).resolve().parents[1]
names=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True).stdout.split(b'\0')
items=[]
for raw in sorted(set(names)):
    if not raw: continue
    name=raw.decode('utf-8')
    if not name.startswith('evidence/') or name=='evidence/manifest.json': continue
    path=ROOT/name
    items.append({'file':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
out={'generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'algorithm':'SHA-256','scope':'Published redacted evidence only; manifest excludes itself, runtime and backups','files':items}
(ROOT/'evidence/manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Frozen '+str(len(items))+' evidence file hashes.')
