"""Create random local credentials without overwriting an existing .env."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    raise SystemExit('Existing .env preserved. Inspect it locally; never overwrite credentials automatically.')
values={'MYSQL_ROOT_PASSWORD':secrets.token_hex(18),'MYSQL_DATABASE':'jsh_erp',
    'MYSQL_USER':'flowpilot','MYSQL_PASSWORD':secrets.token_hex(18),'MYSQL_PORT':'3308',
    'REDIS_PASSWORD':secrets.token_hex(18),'REDIS_PORT':'6388','BACKEND_PORT':'9999','HTTP_PORT':'8088',
    'ERP_ADMIN_PASSWORD':secrets.token_urlsafe(18),'ERP_TENANT_PASSWORD':secrets.token_urlsafe(18),
    'ERP_DEMO_PASSWORD':secrets.token_urlsafe(18)}
with path.open('x',encoding='utf-8') as f:
    f.write('\n'.join(f'{k}={v}' for k,v in values.items())+'\n')
try: path.chmod(0o600)
except OSError: pass
print('Generated .env with random credentials. No credentials printed.')
