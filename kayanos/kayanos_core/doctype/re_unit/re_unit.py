import frappe
from frappe.model.document import Document

class REUnit(Document):
    def before_validate(self):
        if self.property:
            # Derive project strictly from the parent Property
            self.project = frappe.db.get_value('RE Property', self.property, 'project')
            
    def validate(self):
        # 1. Uniqueness of unit_number within property
        if self.property and self.unit_number:
            filters = {'property': self.property, 'unit_number': self.unit_number}
            if not self.is_new():
                filters['name'] = ['!=', self.name]
            if frappe.db.exists('RE Unit', filters):
                frappe.throw("Unit number must be unique within its Property")
        
        # 2. Lifecycle and Availability status validation
        if self.availability_status == 'Available':
            if self.lifecycle_status != 'Active':
                frappe.throw("An Available unit must have an Active lifecycle status.")
                
            # Validate Phase sales_authorized
            phase = frappe.db.get_value('RE Property', self.property, 'phase')
            phase_auth = frappe.db.get_value('RE Phase', phase, 'sales_authorized')
            if not phase_auth:
                frappe.throw("Cannot mark unit as Available: Sales are not authorized for this Phase.")
                
            # Validate Project sales_authorized
            project_auth = frappe.db.get_value('RE Project Profile', {'project': self.project}, 'sales_authorized')
            if not project_auth:
                frappe.throw("Cannot mark unit as Available: Sales are not authorized for the Project.")
                
    def after_insert(self):
        # Generate exactly one Shadow Item deterministically.
        if not self.shadow_item:
            item_code = self.name
            
            # Using an Item Group that is guaranteed to exist.
            item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
            
            item = frappe.new_doc('Item')
            item.item_code = item_code
            item.item_name = item_code
            item.item_group = item_group
            item.is_stock_item = 0
            item.is_sales_item = 1
            
            if self.lifecycle_status == 'Draft' or self.availability_status == 'Withheld':
                item.disabled = 1
                
            item.insert(ignore_permissions=True)
            self.db_set('shadow_item', item.name)

    def on_update(self):
        # Sync disabled status based on Unit state
        if self.shadow_item:
            disabled = 1 if (self.lifecycle_status == 'Draft' or self.availability_status == 'Withheld') else 0
            current_disabled = frappe.db.get_value('Item', self.shadow_item, 'disabled')
            if current_disabled != disabled:
                frappe.db.set_value('Item', self.shadow_item, 'disabled', disabled)

    def on_trash(self):
        # Prevent deletion if shadow item is linked
        if self.shadow_item:
            frappe.throw("Cannot delete RE Unit once a Shadow Item is linked. Use Inactive/archival behavior instead.")

