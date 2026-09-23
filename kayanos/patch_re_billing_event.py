import json
path = 'kayanos_core/doctype/re_billing_event/re_billing_event.json'
with open(path, 'r') as f:
    d = json.load(f)

# The section is to be inserted right after "returns_section" stuff? Or after integration?
# Let's add it right before "returns_section" or after it. 
# Let's insert after returns child table.
idx = d['field_order'].index('returns')
d['field_order'] = d['field_order'][:idx+1] + [
    "collection_section",
    "gross_invoiced_amount",
    "cash_allocated",
    "adjustment_allocated",
    "projected_balance",
    "erpnext_outstanding",
    "collection_status"
] + d['field_order'][idx+1:]

new_fields = [
    {
        "fieldname": "collection_section",
        "fieldtype": "Section Break",
        "label": "Collections & Adjustments"
    },
    {
        "fieldname": "gross_invoiced_amount",
        "fieldtype": "Currency",
        "label": "Gross Invoiced Amount",
        "options": "currency",
        "read_only": 1,
        "default": "0"
    },
    {
        "fieldname": "cash_allocated",
        "fieldtype": "Currency",
        "label": "Cash Allocated",
        "options": "currency",
        "read_only": 1,
        "default": "0"
    },
    {
        "fieldname": "adjustment_allocated",
        "fieldtype": "Currency",
        "label": "Adjustment Allocated",
        "options": "currency",
        "read_only": 1,
        "default": "0"
    },
    {
        "fieldname": "projected_balance",
        "fieldtype": "Currency",
        "label": "Projected Balance",
        "options": "currency",
        "read_only": 1,
        "default": "0"
    },
    {
        "fieldname": "erpnext_outstanding",
        "fieldtype": "Currency",
        "label": "ERPNext Outstanding",
        "options": "currency",
        "read_only": 1,
        "default": "0"
    },
    {
        "default": "Unpaid",
        "fieldname": "collection_status",
        "fieldtype": "Select",
        "label": "Collection Status",
        "options": "Unpaid\nPartially Settled\nFully Settled\nFully Returned\nOver-Settled (Credit)",
        "read_only": 1
    }
]

# Insert into fields array
fields = d['fields']
insert_idx = next(i for i, f in enumerate(fields) if f['fieldname'] == 'returns')
d['fields'] = fields[:insert_idx+1] + new_fields + fields[insert_idx+1:]

with open(path, 'w') as f:
    json.dump(d, f, indent=1)
