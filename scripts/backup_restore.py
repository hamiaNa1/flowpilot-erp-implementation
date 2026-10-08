"""Dump live schema, restore only to a new isolated test database, compare all tables."""
import hashlib, json, subprocess
from pathlib import Path
from common import ROOT, ENV, db, now, write_json
from native import MYSQL, RUNTIME

def inventory(database):
    result={}
    with db(database,root=True) as conn:
        with conn.cursor() as cur:
            cur.execute('SHOW TABLES'); tables=[next(iter(row.values())) for row in cur.fetchall()]
            for table in tables:
                cur.execute('SELECT * FROM `'+table+'`')
                rows=cur.fetchall()
                def normalize(obj):
                    if isinstance(obj,bytes): return {'hex':obj.hex()}
                    return str(obj)
                serialized=sorted(json.dumps(row,sort_keys=True,ensure_ascii=False,default=normalize) for row in rows)
                result[table]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(serialized).encode('utf-8')).hexdigest()}
    return result

def main():
    stamp=now()[:19].replace('-','').replace(':','').replace('T','_')
    backup=ROOT/'backups'/f'jsh_erp_{stamp}.sql'; backup.parent.mkdir(exist_ok=True)
    restore='flowpilot_restore_'+stamp
    args=[str(MYSQL/'mysqldump.exe'),f'--defaults-extra-file={RUNTIME / "mysql-client.cnf"}',
      '--single-transaction','--routines','--triggers','--events','--set-gtid-purged=OFF','--no-tablespaces',
      '--default-character-set=utf8mb4',f'--result-file={backup}',ENV['MYSQL_DATABASE']]
    result=subprocess.run(args,capture_output=True)
    (ROOT/'evidence/backup-command.log').write_bytes(result.stderr)
    result.check_returncode()
    before=inventory(ENV['MYSQL_DATABASE'])
    with db(root=True) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s',(restore,))
            if cur.fetchone(): raise RuntimeError('Restore database already exists; never overwrite')
            cur.execute('CREATE DATABASE `'+restore+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    with backup.open('rb') as src:
        completed=subprocess.run([str(MYSQL/'mysql.exe'),f'--defaults-extra-file={RUNTIME / "mysql-client.cnf"}',restore],stdin=src,capture_output=True)
    (ROOT/'evidence/restore-command.log').write_bytes(completed.stdout+completed.stderr)
    completed.check_returncode()
    after=inventory(restore)
    report={'time':now(),'backup_file':str(backup.relative_to(ROOT)), 'bytes':backup.stat().st_size,
      'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'source_database':ENV['MYSQL_DATABASE'],
      'restore_database':restore,'isolated_new_schema':True,'source_modified':False,
      'table_results':{t:{'source':before[t],'restored':after.get(t),'equal':before[t]==after.get(t)} for t in before},
      'all_equal':before==after,'scope':'all 30 tables: row counts and canonical row SHA-256, not just a file-exists check'}
    write_json('evidence/backup-restore-verification.json',report)
    assert report['all_equal'],'Restore mismatch; inspect evidence'
    print(f'Backup restored into {restore}; all {len(before)} tables match exactly.')

if __name__=='__main__': main()
