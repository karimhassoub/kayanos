import frappe
from frappe.model.document import Document

class REProperty(Document):
    def before_validate(self):
        if self.phase:
            # Derive project strictly from the parent Phase
            self.project = frappe.db.get_value('RE Phase', self.phase, 'project')

