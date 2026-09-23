import json
path = '/home/karim/frappe-bench/apps/frappe/frappe/geo/doctype/currency/currency.json'
with open(path) as f:
    d = json.load(f)
print([f['fieldname'] for f in d['fields']])
