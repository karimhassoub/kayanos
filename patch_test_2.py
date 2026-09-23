import sys

path = 'kayanos/kayanos_core/test_erpnext_collections.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'si.submit()', 
    'si.flags.ignore_validate = True\n        frappe.db.set_value("Sales Invoice", si.name, "docstatus", 1)'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
