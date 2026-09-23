import frappe

def execute():
    frappe.conf.developer_mode = 1
    create_settings()
    create_reservation()
    frappe.db.commit()

def create_settings():
    if not frappe.db.exists("DocType", "RE Reservation Settings"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "RE Reservation Settings",
            "module": "Kayanos Core",
            "custom": 0,
            "issingle": 1,
            "fields": [
                {
                    "fieldname": "default_reservation_duration_hours",
                    "fieldtype": "Float",
                    "label": "Default Reservation Duration (Hours)",
                    "default": "48.0",
                    "reqd": 1
                }
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1}]
        })
        doc.insert(ignore_permissions=True)

def create_reservation():
    if not frappe.db.exists("DocType", "RE Unit Reservation"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "RE Unit Reservation",
            "module": "Kayanos Core",
            "custom": 0,
            "autoname": "naming_series:",
            "track_changes": 1,
            "fields": [
                {"fieldname": "naming_series", "fieldtype": "Select", "options": "RES-.YYYY.-.####", "label": "Series"},
                {"fieldname": "crm_deal", "fieldtype": "Link", "options": "CRM Deal", "label": "CRM Deal", "reqd": 1, "in_list_view": 1},
                {"fieldname": "unit", "fieldtype": "Link", "options": "RE Unit", "label": "Unit", "reqd": 1, "in_list_view": 1},
                {"fieldname": "lead", "fieldtype": "Link", "options": "CRM Lead", "label": "Lead", "read_only": 1},
                {"fieldname": "organization", "fieldtype": "Link", "options": "CRM Organization", "label": "Organization", "read_only": 1},
                {"fieldname": "status", "fieldtype": "Select", "options": "Draft\nActive\nCancelled\nExpired", "default": "Draft", "label": "Status", "in_list_view": 1},
                {"fieldname": "expiry_time", "fieldtype": "Datetime", "label": "Expiry Time", "read_only": 1},
                {"fieldname": "cancellation_reason", "fieldtype": "Small Text", "label": "Cancellation Reason", "depends_on": "eval:doc.status=='Cancelled'"}
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
        })
        doc.insert(ignore_permissions=True)
