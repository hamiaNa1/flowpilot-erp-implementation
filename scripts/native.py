"""Portable Windows deployment, limited to this project's own processes/data."""
from pathlib import Path
import argparse, hashlib, json, os, secrets, shutil, socket, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[1]

def setup_env():
    if not (ROOT/'.env').exists():
        values = {'MYSQL_ROOT_PASSWORD':secrets.token_hex(18), 'MYSQL_DATABASE':'jsh_erp',
            'MYSQL_USER':'flowpilot', 'MYSQL_PASSWORD':secrets.token_hex(18), 'MYSQL_PORT':'3308',
            'REDIS_PASSWORD':secrets.token_hex(18), 'REDIS_PORT':'6388', 'BACKEND_PORT':'9999',
            'HTTP_PORT':'8088', 'ERP_ADMIN_PASSWORD':secrets.token_urlsafe(18),
            'ERP_TENANT_PASSWORD':secrets.token_urlsafe(18), 'ERP_DEMO_PASSWORD':secrets.token_urlsafe(18)}
        (ROOT/'.env').write_text('\n'.join(f'{k}={v}' for k,v in values.items())+'\n',encoding='utf-8')
setup_env()
from common import ENV, now, write_json

MYSQL = ROOT/'tools/mysql-8.0.44-winx64/bin'
JAVA = ROOT/'tools/zulu8.96.0.205-ca-jdk8.0.504-win_x64/bin/java.exe'
NGINX = ROOT/'tools/nginx-1.28.0/nginx.exe'
RUNTIME = ROOT/'runtime'
STATE = RUNTIME/'processes.json'
for d in ('mysql','redis','logs','exports','nginx','nginx/logs','nginx/temp','upload','tomcat','plugins','pluginConfig'):
    (RUNTIME/d).mkdir(parents=True,exist_ok=True)

def port_open(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1',int(port)))==0

def wait_port(port, seconds=60):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if port_open(port): return
        time.sleep(.5)
    raise RuntimeError(f'Port {port} did not become ready; inspect runtime/logs')

def launch(name, args, cwd=ROOT):
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    out=open(RUNTIME/'logs'/f'{name}.log','ab')
    err=open(RUNTIME/'logs'/f'{name}-stderr.log','ab')
    flags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    proc=subprocess.Popen([str(a) for a in args],cwd=cwd,stdout=out,stderr=err,creationflags=flags)
    state[name]={'pid':proc.pid,'executable':str(args[0]),'started':now()}
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
    return proc

def redis_cmd(*parts):
    # RESP protocol avoids passwords in process command lines.
    with socket.create_connection(('127.0.0.1',int(ENV['REDIS_PORT'])),timeout=5) as s:
        f=s.makefile('rb')
        def send(items):
            data=b'*'+str(len(items)).encode()+b'\r\n'
            for item in items:
                b=str(item).encode(); data+=b'$'+str(len(b)).encode()+b'\r\n'+b+b'\r\n'
            s.sendall(data)
            line=f.readline()
            if line.startswith(b'$'):
                n=int(line[1:]); return None if n<0 else f.read(n+2)[:-2].decode()
            if line.startswith(b'-'): raise RuntimeError(line.decode())
            return line[1:].decode().strip()
        send(['AUTH',ENV['REDIS_PASSWORD']])
        return send(parts)

def redis_get(key): return redis_cmd('GET',key)

def configure():
    base=(ROOT/'upstream/jshERP-boot/src/main/resources/application.properties').read_text(encoding='utf-8')
    overrides={
        'server.address':'127.0.0.1','server.port':ENV['BACKEND_PORT'],
        'spring.datasource.url':f"jdbc:mysql://127.0.0.1:{ENV['MYSQL_PORT']}/{ENV['MYSQL_DATABASE']}?useUnicode=true&characterEncoding=utf8&useCursorFetch=true&defaultFetchSize=500&allowMultiQueries=true&rewriteBatchedStatements=true&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai",
        'spring.datasource.username':ENV['MYSQL_USER'],'spring.datasource.password':ENV['MYSQL_PASSWORD'],
        'spring.redis.host':'127.0.0.1','spring.redis.port':ENV['REDIS_PORT'],'spring.redis.password':ENV['REDIS_PASSWORD'],
        'file.path':(RUNTIME/'upload').as_posix(),'server.tomcat.basedir':(RUNTIME/'tomcat').as_posix(),
        'plugin.pluginPath':(RUNTIME/'plugins').as_posix(),'plugin.pluginConfigFilePath':(RUNTIME/'pluginConfig').as_posix(),
        'logging.level.com.jsh':'INFO'}
    # Extra properties override bundled defaults without modifying upstream sources.
    text=base+'\n'+'\n'.join(f'{k}={v}' for k,v in overrides.items())+'\n'
    (RUNTIME/'application.properties').write_text(text,encoding='utf-8')
    (RUNTIME/'redis.conf').write_text(f"bind 127.0.0.1\nport {ENV['REDIS_PORT']}\nrequirepass {ENV['REDIS_PASSWORD']}\nappendonly yes\ndir {str(RUNTIME/'redis').replace(chr(92),'/')}\nmaxmemory 128mb\nmaxmemory-policy noeviction\n",encoding='utf-8')
    (RUNTIME/'my.ini').write_text(f"[mysqld]\nbasedir={MYSQL.parent.as_posix()}\ndatadir={(RUNTIME/'mysql').as_posix()}\nport={ENV['MYSQL_PORT']}\nbind-address=127.0.0.1\nskip-mysqlx\ncharacter-set-server=utf8mb4\ncollation-server=utf8mb4_unicode_ci\ndefault-time-zone=+08:00\nlog-error={(RUNTIME/'logs/mysql-server.log').as_posix()}\n[client]\ndefault-character-set=utf8mb4\n",encoding='utf-8')
    (RUNTIME/'mysql-client.cnf').write_text(f"[client]\nhost=127.0.0.1\nport={ENV['MYSQL_PORT']}\nuser=root\npassword={ENV['MYSQL_ROOT_PASSWORD']}\ndefault-character-set=utf8mb4\n",encoding='utf-8')
    conf='''worker_processes 1;
pid nginx.pid;
error_log ../logs/nginx-error.log;
events { worker_connections 512; }
http {
  include ../../tools/nginx-1.28.0/conf/mime.types;
  default_type application/octet-stream;
  access_log ../logs/nginx-access.log;
  sendfile on;
  server_tokens off;
  client_max_body_size 12m;
  server {
    listen 127.0.0.1:HTTPPORT;
    server_name localhost;
    root FRONTROOT;
    index index.html;
    add_header X-Content-Type-Options nosniff;
    location / { try_files $uri $uri/ /index.html; }
    location /healthz { return 200 'ok'; add_header Content-Type text/plain; }
    location /jshERP-boot/ {
      proxy_pass http://127.0.0.1:BACKPORT/jshERP-boot/;
      proxy_set_header Host $host:$server_port;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_read_timeout 60s;
    }
  }
}
'''.replace('HTTPPORT',ENV['HTTP_PORT']).replace('BACKPORT',ENV['BACKEND_PORT']).replace('FRONTROOT',(ROOT/'upstream/jshERP-web/dist').as_posix())
    (RUNTIME/'nginx/nginx.conf').write_text(conf,encoding='utf-8')

def initialize():
    import pymysql
    configure()
    if (RUNTIME/'mysql/auto.cnf').exists():
        raise RuntimeError('MySQL already initialized; use start. Never reinitialize existing data.')
    with open(ROOT/'evidence/mysql-initialize.log','wb') as log:
        subprocess.run([str(MYSQL/'mysqld.exe'),f'--defaults-file={RUNTIME / "my.ini"}','--initialize-insecure'],stdout=log,stderr=log,check=True)
    launch('mysql',[MYSQL/'mysqld.exe',f'--defaults-file={RUNTIME / "my.ini"}'])
    wait_port(ENV['MYSQL_PORT'])
    conn=pymysql.connect(host='127.0.0.1',port=int(ENV['MYSQL_PORT']),user='root',password='',charset='utf8mb4',autocommit=True,client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS)
    with conn.cursor() as cur:
        cur.execute(f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{ENV['MYSQL_ROOT_PASSWORD']}'")
        cur.execute(f"CREATE DATABASE `{ENV['MYSQL_DATABASE']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"CREATE USER '{ENV['MYSQL_USER']}'@'127.0.0.1' IDENTIFIED BY '{ENV['MYSQL_PASSWORD']}'")
        cur.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON `{ENV['MYSQL_DATABASE']}`.* TO '{ENV['MYSQL_USER']}'@'127.0.0.1'")
        cur.execute(f"USE `{ENV['MYSQL_DATABASE']}`")
        cur.execute('SHOW TABLES')
        if cur.fetchall(): raise RuntimeError('Refusing SQL import into nonempty database')
        cur.execute((ROOT/'upstream/jshERP-boot/docs/jsh_erp.sql').read_text(encoding='utf-8'))
        while cur.nextset(): pass
        for name,key in [('admin','ERP_ADMIN_PASSWORD'),('jsh','ERP_TENANT_PASSWORD')]:
            cur.execute('UPDATE jsh_user SET password=%s WHERE login_name=%s',(hashlib.md5(ENV[key].encode()).hexdigest(),name))
        cur.execute("UPDATE jsh_user SET status=1 WHERE login_name='test123'")
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s",(ENV['MYSQL_DATABASE'],))
        count=cur.fetchone()[0]
    conn.close()
    write_json('evidence/database-initialization.json',{'time':now(),'schema':ENV['MYSQL_DATABASE'],'tables':count,'source_sql':'upstream/jshERP-boot/docs/jsh_erp.sql','default_passwords_rotated':True,'sample_user_disabled':True,'port':ENV['MYSQL_PORT']})
    print(f'Initialized isolated database: {count} tables. Passwords stored only in .env.')

def start():
    configure()
    if not (RUNTIME/'mysql/auto.cnf').exists(): raise RuntimeError('Run init first')
    if not port_open(ENV['MYSQL_PORT']): launch('mysql',[MYSQL/'mysqld.exe',f'--defaults-file={RUNTIME / "my.ini"}'])
    wait_port(ENV['MYSQL_PORT'])
    if not port_open(ENV['REDIS_PORT']): launch('redis',[ROOT/'tools/redis/redis-server.exe',RUNTIME/'redis.conf'])
    wait_port(ENV['REDIS_PORT'])
    if not port_open(ENV['BACKEND_PORT']):
        shutil.copy2(ROOT/'upstream/jshERP-boot/target/jshERP.jar', RUNTIME/'jshERP.jar')
        launch('backend',[JAVA,'-Xms128m','-Xmx768m','-Dfile.encoding=UTF-8',f'-Dlogs.home={(RUNTIME/"logs").as_posix()}',f'-Dflowpilot.export.dir={(RUNTIME/"exports").as_posix()}','-jar',RUNTIME/'jshERP.jar',f'--spring.config.location={(RUNTIME/"application.properties").as_posix()}'],RUNTIME)
    wait_port(ENV['BACKEND_PORT'],90)
    prefix=(RUNTIME/'nginx').as_posix()+'/'
    check=subprocess.run([str(NGINX),'-p',prefix,'-c','nginx.conf','-t'],capture_output=True)
    (ROOT/'evidence/nginx-config-check.log').write_bytes(check.stdout+check.stderr)
    check.check_returncode()
    if not port_open(ENV['HTTP_PORT']): launch('nginx',[NGINX,'-p',prefix,'-c','nginx.conf'],RUNTIME/'nginx')
    wait_port(ENV['HTTP_PORT'])
    import requests
    response=requests.get(f"http://127.0.0.1:{ENV['HTTP_PORT']}/jshERP-boot/platformConfig/getPlatform/name",timeout=30)
    write_json('evidence/deployment-health.json',{'time':now(),'url':f"http://127.0.0.1:{ENV['HTTP_PORT']}", 'mysql_port':ENV['MYSQL_PORT'],'redis_ping':redis_cmd('PING'),'proxy_http_status':response.status_code,'platform_response':response.text,'all_loopback':True})
    print(f"ERP started: http://127.0.0.1:{ENV['HTTP_PORT']}")

def stop():
    import ctypes
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    # Validate executable against recorded project-owned path before terminating.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    def kill_owned(name):
        p=state.get(name)
        if not p: return
        handle=kernel.OpenProcess(0x1000|0x0001,False,p['pid'])
        if not handle: return
        try:
            buf=ctypes.create_unicode_buffer(32768); size=ctypes.c_ulong(len(buf))
            if not kernel.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)): raise RuntimeError('Unable to validate PID ownership')
            if Path(buf.value).resolve()!=Path(p['executable']).resolve(): raise RuntimeError('PID executable mismatch; refusing termination')
            kernel.TerminateProcess(handle,0)
        finally: kernel.CloseHandle(handle)
    if port_open(ENV['HTTP_PORT']): subprocess.run([str(NGINX),'-p',(RUNTIME/'nginx').as_posix()+'/', '-c','nginx.conf','-s','quit'],check=True)
    kill_owned('backend')
    if port_open(ENV['REDIS_PORT']):
        try: redis_cmd('SHUTDOWN','SAVE')
        except Exception: pass
    if port_open(ENV['MYSQL_PORT']): subprocess.run([str(MYSQL/'mysqladmin.exe'),f'--defaults-extra-file={RUNTIME / "mysql-client.cnf"}','shutdown'],check=True)
    time.sleep(2)
    print('Project services stopped; all persisted data retained.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['init','start','stop','restart','status'])
    args=parser.parse_args()
    if args.action=='init': initialize()
    elif args.action=='start': start()
    elif args.action=='stop': stop()
    elif args.action=='restart': stop(); start()
    else: print(json.dumps({k:port_open(ENV[k]) for k in ['MYSQL_PORT','REDIS_PORT','BACKEND_PORT','HTTP_PORT']}))
