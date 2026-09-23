import json
path = '/home/karim/frappe-bench/apps/erpnext/erpnext/accounts/doctype/sales_invoice/sales_invoice.json'
with open(path) as f:
    d = json.load(f)
for f in d['fields']:
    if f['fieldname'] in ['outstanding_amount', 'status', 'grand_total', 'total_advance', 'base_grand_total']:
        print(f['fieldname'], f['fieldtype'])
