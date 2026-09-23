import json

with open('kayanos/kayanos_core/doctype/re_billing_event/re_billing_event.json', 'r') as f:
    data = json.load(f)

targets = ('gross_invoiced_amount', 'returned_amount', 'cash_allocated', 'adjustment_allocated', 'projected_balance', 'erpnext_outstanding', 'collection_status')

for field in data['fields']:
    if field['fieldname'] in targets:
        print(f"Field: {field['fieldname']}, Type: {field['fieldtype']}, Options: {field.get('options')}")
