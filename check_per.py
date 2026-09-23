import json
path = '/home/karim/frappe-bench/apps/erpnext/erpnext/accounts/doctype/payment_entry_reference/payment_entry_reference.json'
with open(path) as f:
    d = json.load(f)
for f in d['fields']:
    print(f['fieldname'], f['fieldtype'])
