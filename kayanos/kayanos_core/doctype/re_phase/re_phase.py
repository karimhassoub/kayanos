import frappe
from frappe.model.document import Document

class REPhase(Document):
    def validate(self):
        if self.developer_type == 'Internal':
            self.external_developer_type = None
            self.external_developer = None
            
        # Validate sales_authorized against RE Project Profile
        if self.sales_authorized:
            profile_auth = frappe.db.get_value('RE Project Profile', {'project': self.project}, 'sales_authorized')
            if not profile_auth:
                frappe.throw("Cannot authorize sales for Phase because the Project Profile disallows it.")
                
    def on_update(self):
        # Auto-withhold available units if sales authorization is revoked
        if self.has_value_changed('sales_authorized') and not self.sales_authorized:
            # Find all units in this phase that are 'Available'
            # Note: Unit links to Property, Property links to Phase.
            properties = frappe.get_all('RE Property', filters={'phase': self.name}, pluck='name')
            if properties:
                units = frappe.get_all('RE Unit', filters={'property': ['in', properties], 'availability_status': 'Available'})
                for u in units:
                    unit_doc = frappe.get_doc('RE Unit', u.name)
                    unit_doc.db_set('availability_status', 'Withheld')
                    # Sync shadow item disabled state
                    if unit_doc.shadow_item:
                        frappe.db.set_value('Item', unit_doc.shadow_item, 'disabled', 1)

