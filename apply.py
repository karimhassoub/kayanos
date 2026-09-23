with open(r'kayanos/discovery.py', 'w', encoding='utf-8') as f:
    f.write('''import frappe
def execute():
    for term in ['%build%', '%estate%', '%zone%', '%phase%', '%asset%', '%item%']:
        docs = frappe.get_all('DocType', filters={'name': ['like', term], 'custom': 0}, pluck='name')
        print(f'Term {term}: {docs}')
''')

with open(r'kayanos/kayanos_core/doctype/re_unit_reservation/re_unit_reservation.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        # 5. Update Unit Status
        frappe.db.set_value("RE Unit", self.unit, "availability_status", "Reserved")'''
replacement = '''        # 5. Update Unit Status
        frappe.db.set_value("RE Unit", self.unit, "availability_status", "Reserved")
        
        # 6. Queue Email Notification (Model A)
        frappe.enqueue(
            "kayanos.kayanos_core.notifications.send_reservation_confirmation",
            reservation_name=self.name,
            enqueue_after_commit=True
        )'''

if target in content:
    content = content.replace(target, replacement)
    with open(r'kayanos/kayanos_core/doctype/re_unit_reservation/re_unit_reservation.py', 'w', encoding='utf-8') as f:
        f.write(content)
