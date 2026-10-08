from common import ROOT, query, write_json, now
text=(ROOT/'sql/reconciliation.sql').read_text(encoding='utf-8')
clean='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('--'))
results=[]
for sql in clean.split(';'):
    if sql.strip(): results.append({'sql':sql.strip(),'rows':query(sql)})
write_json('evidence/sql-reconciliation.json',{'time':now(),'results':results})
assert all(row['difference']==0 for row in results[3]['rows']), 'Stock ledger mismatch'
assert not results[-1]['rows'] and not results[-2]['rows'] and not results[-3]['rows'], 'Duplicate business data'
print('SQL stock reconciliation passed; no duplicate migrated codes or bill numbers.')
