import re
import sys

try:
    with open("kayanos/kayanos_core/doctype/re_unit_reservation/test_re_unit_reservation.py", "r") as f:
        content = f.read()

    setup_fix = """        # Setup settings
        frappe.db.set_single_value("RE Reservation Settings", "default_reservation_duration_hours", 48.0)
        
        deal1_name = frappe.db.get_value("CRM Deal", {"title": "TEST-DEAL-01"})
        if not deal1_name:
            doc = frappe.get_doc({
                "doctype": "CRM Deal",
                "title": "TEST-DEAL-01",
                "status": "Open"
            })
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True, ignore_links=True)
            deal1_name = doc.name
        cls.deal1 = deal1_name
            
        deal2_name = frappe.db.get_value("CRM Deal", {"title": "TEST-DEAL-02"})
        if not deal2_name:
            doc = frappe.get_doc({
                "doctype": "CRM Deal",
                "title": "TEST-DEAL-02",
                "status": "Open"
            })
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True, ignore_links=True)
            deal2_name = doc.name
        cls.deal2 = deal2_name
        
        # Create Project/Phase/Property/Unit"""

    content = re.sub(r'        # Setup settings.*# Create Project/Phase/Property/Unit', setup_fix, content, flags=re.DOTALL)
    content = content.replace('"TEST-DEAL-01"', 'self.deal1')
    content = content.replace('"TEST-DEAL-02"', 'self.deal2')
    content = content.replace('self.deal1,\n                "unit": "ANY"', 'frappe.db.get_value("CRM Deal", {}),\n                "unit": "ANY"')

    with open("kayanos/kayanos_core/doctype/re_unit_reservation/test_re_unit_reservation.py", "w") as f:
        f.write(content)
        
    print("Test file patched successfully.")
except Exception as e:
    print("Error:", e)
    sys.exit(1)
