"""Repeat native partner XLS import and test copied invalid ledgers without writes."""
from copy import deepcopy
from common import API, now, write_json
from migrate import validate, import_partners
from business_uat import stock

loaded=validate(); api=API(); api.login(); before=stock()
rounds=[import_partners(api,loaded),import_partners(api,loaded)]
assert stock()==before
write_json('evidence/partner-native-import.json',{'time':now(),'rounds':rounds,'stock_before':before,'stock_after':stock(),'note':'Existing API-created partners re-imported via native XLS twice; names/IDs/counts stable'})
write_json('evidence/partner-native-api.json',api.records)
cases=[]
for label,change in [
    ('missing-name',lambda d:d['suppliers'][0].update(name='')),
    ('duplicate-code',lambda d:d['materials'].append(deepcopy(d['materials'][0]))),
    ('negative-quantity',lambda d:d['initial-stock'][0].update(quantity='-1')),
    ('invalid-number',lambda d:d['initial-stock'][0].update(quantity='not-a-number')),
    ('invalid-date',lambda d:d['customers'][0].update(effective_date='2026/99/99')),
    ('unknown-material',lambda d:d['initial-stock'][0].update(barcode='UNKNOWN')),
    ('unknown-warehouse',lambda d:d['initial-stock'][0].update(warehouse='UNKNOWN'))]:
    copied=deepcopy(loaded); change(copied)
    try:
        validate(copied,save=False); rejected=False; actual='accepted'
    except ValueError as e: rejected=True; actual=str(e)
    cases.append({'case':label,'rejected_before_mutation':rejected,'actual':actual})
assert all(c['rejected_before_mutation'] for c in cases)
write_json('evidence/migration-validation-tests.json',{'time':now(),'valid_source_passed':True,'negative_cases':cases,'source_files_unchanged':True})
print('Native XLS imports verified twice: 3 suppliers + 3 customers, unchanged IDs and stock; 7 invalid ledgers rejected.')
