import json
try:
    path = '/home/karim/frappe-bench/apps/erpnext/erpnext/accounts/doctype/payment_reconciliation/payment_reconciliation.json'
    with open(path) as f:
        d = json.load(f)
    print("issingle:", d.get('issingle', 0))
    print("is_submittable:", d.get('is_submittable', 0))
except Exception as e:
    print(e)
