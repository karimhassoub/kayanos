import json
path = '/home/karim/frappe-bench/apps/erpnext/erpnext/accounts/doctype/journal_entry/journal_entry.json'
with open(path) as f:
    d = json.load(f)
for f in d['fields']:
    if f['fieldname'] == 'voucher_type':
        print(f['options'])
