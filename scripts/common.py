"""Local implementation helpers; secrets stay in ignored .env/runtime files."""
from pathlib import Path
import json, os, time, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import pymysql, requests

ROOT = Path(__file__).resolve().parents[1]
ENV = {}
for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
    if line and not line.startswith('#'):
        k, v = line.split('=', 1)
        ENV[k] = v

def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def write_json(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def db(database=None, root=False):
    return pymysql.connect(host='127.0.0.1', port=int(ENV['MYSQL_PORT']),
        user='root' if root else ENV['MYSQL_USER'],
        password=ENV['MYSQL_ROOT_PASSWORD'] if root else ENV['MYSQL_PASSWORD'],
        database=database or ENV['MYSQL_DATABASE'], charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor, autocommit=True)

def query(sql, args=None, database=None):
    with db(database) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

class API:
    def __init__(self):
        self.base = 'http://127.0.0.1:' + ENV['HTTP_PORT'] + '/jshERP-boot'
        self.session = requests.Session()
        self.records = []
        self.last_mutation=0
    def call(self, method, path, throttle=True, **kwargs):
        if method.upper() not in ('GET','HEAD') and throttle:
            # MySQL DATETIME(0) rounds milliseconds whereas LogService floors
            # its comparison time. 1.7 s avoids adjacent calls sharing that second.
            time.sleep(max(0,1.7-(time.monotonic()-self.last_mutation)))
        from native import redis_cmd
        token=self.session.headers.get('X-Access-Token')
        auth_before=redis_cmd('HGET',token,'userId') if token else None
        response = self.session.request(method, self.base + path, timeout=60, **kwargs)
        if method.upper() not in ('GET','HEAD'): self.last_mutation=time.monotonic()
        try:
            body = response.json()
        except ValueError:
            body = response.text[:1000]
        # Tokens, credentials and cookies are intentionally excluded from evidence.
        safe = json.loads(json.dumps(body, ensure_ascii=False)) if isinstance(body, (dict,list)) else body
        def redact(value):
            if isinstance(value, dict):
                return {k: ('[REDACTED]' if k.lower() in ('token','password','uuid','codeimg') else redact(v)) for k,v in value.items()}
            if isinstance(value, list): return [redact(v) for v in value]
            return value
        request = {k:v for k,v in kwargs.items() if k in ('json','params')}
        if path == '/user/login': request = {'json': {'loginName': kwargs.get('json',{}).get('loginName'), 'password':'[MD5 REDACTED]', 'code':'[REDACTED]', 'uuid':'[REDACTED]'}}
        self.records.append({'time':now(), 'method':method, 'path':path, 'request':request,
            'http_status':response.status_code, 'response':redact(safe), 'authenticated_user_before':auth_before})
        return body
    def login(self, name='jsh', password=None):
        import hashlib
        # Native captcha stays enabled. Read this local test instance's generated
        # captcha via Redis for automation; no ERP authentication code is changed.
        cap = self.session.get(self.base + '/user/randomImage', timeout=30).json()
        write_json('runtime/captcha-response.private.json', cap)
        from native import redis_get
        data = cap.get('data', cap)
        uuid = data.get('uuid')
        if uuid is None:
            raise RuntimeError('Inspect native captcha response contract before login')
        code = redis_get('captcha_codes:' + uuid)
        password = password or ENV['ERP_TENANT_PASSWORD']
        res = self.call('POST', '/user/login', json={'loginName':name, 'password':hashlib.md5(password.encode()).hexdigest(), 'code':code, 'uuid':uuid})
        if res.get('data',{}).get('msgTip') != 'user can login':
            raise RuntimeError('Native login failed: ' + str(res))
        self.session.headers['X-Access-Token'] = res['data']['token']
        return res
