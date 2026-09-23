# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class REBillingPolicy(Document):
    def validate(self):
        self.validate_uniqueness()

    def validate_uniqueness(self):
        if not self.enabled:
            return

        # Check for existing active policy with same scope and trigger type
        filters = {
            "company": self.company,
            "trigger_type": self.trigger_type,
            "enabled": 1,
            "name": ["!=", self.name]
        }
        
        if self.project:
            filters["project"] = self.project
        else:
            filters["project"] = ["in", ["", None]]
            
        existing = frappe.db.exists("RE Billing Policy", filters)
        if existing:
            scope = f"Project {self.project}" if self.project else f"Company {self.company}"
            frappe.throw(_("An active Billing Policy already exists for {0} with Trigger Type '{1}' (Policy: {2})").format(
                scope, self.trigger_type, existing
            ))
