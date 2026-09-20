import frappe
from frappe.model.document import Document

class REProjectProfile(Document):
    def validate(self):
        if self.get('ownership_type') == 'Internal':
            self.developer_type = None
            self.external_developer = None
            
        elif self.get('ownership_type') == 'External':
            if not self.get('developer_type') or not self.get('external_developer'):
                frappe.throw('Developer Type and External Developer are mandatory for External ownership.')
            
            if self.get('developer_type') == 'Company' and self.get('external_developer') == self.get('operating_company'):
                frappe.throw('External Developer cannot be the same as the Operating Company.')

        existing = frappe.db.get_value(
            'RE Project Profile',
            {'project': self.get('project'), 'name': ('!=', self.get('name', ''))}
        )
        if existing:
            frappe.throw('A Profile already exists for this Project: ' + str(existing))
