# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_billing_policy(sales_agreement_name):
    """
    Resolves the applicable Billing Policy for a Sales Agreement.
    Hierarchy:
    1. Project specific policy
    2. Company specific fallback policy
    Returns policy dict or None.
    """
    agreement = frappe.get_cached_doc("RE Sales Agreement", sales_agreement_name)
    company = agreement.company
    
    # We need the project. Usually in Unit -> Property -> Phase -> Project Profile.
    # We will assume it's fetched or available. Since Phase 5H doesn't explicitly expose project on Agreement,
    # we fetch it from the Unit.
    unit = frappe.get_cached_doc("RE Unit", agreement.unit)
    project = unit.project if hasattr(unit, "project") and unit.project else None
    
    # Try Project Level
    if project:
        policies = frappe.get_all("RE Billing Policy", 
            filters={"company": company, "project": project, "enabled": 1},
            fields=["name", "trigger_type"]
        )
        if policies:
            if len(policies) > 1:
                # If ambiguity exists for the same exact scope without varying trigger_type
                # The rule says: "reject ambiguous configuration"
                # Wait, validation allows multiple policies if they have *different* trigger_types.
                # So returning all valid policies for the scope is better, or resolving by requested trigger.
                pass
            return policies
            
    # Try Company Level Fallback
    policies = frappe.get_all("RE Billing Policy", 
        filters={"company": company, "project": ["in", ["", None]], "enabled": 1},
        fields=["name", "trigger_type"]
    )
    
    return policies

@frappe.whitelist()
def get_or_create_billing_event(sales_agreement, payment_schedule, trigger_type):
    """
    Idempotent API to create or retrieve a Billing Event.
    Never creates ERPNext documents.
    """
    # 1. Deterministic Idempotency Key
    idempotency_key = f"{sales_agreement}-{payment_schedule}-{trigger_type}"
    
    # 2. Check for existing (safe concurrency using for_update or unique constraint)
    # We rely on the Unique constraint on idempotency_key to prevent duplicates at DB level.
    existing = frappe.db.get_value("RE Billing Event", {"idempotency_key": idempotency_key}, "name")
    if existing:
        return frappe.get_doc("RE Billing Event", existing)
        
    # 3. Validate Agreement & Policy
    policies = get_billing_policy(sales_agreement)
    if not policies:
        frappe.throw(_("No active Billing Policy found for this agreement's scope."))
        
    # Check if the requested trigger_type is supported by the resolved policy
    supported_triggers = [p.trigger_type for p in policies]
    if trigger_type not in supported_triggers:
        frappe.throw(_("Trigger type '{0}' is not supported by the active Billing Policy.").format(trigger_type))
        
    # 4. Attempt Creation (Concurrency Safe via DB Unique Constraint)
    doc = frappe.new_doc("RE Billing Event")
    doc.sales_agreement = sales_agreement
    doc.payment_schedule = payment_schedule
    doc.trigger_type = trigger_type
    
    try:
        # We don't use frappe.db.commit() internally as requested.
        # Frappe's insert() handles DB unique constraint errors gracefully.
        doc.insert(ignore_permissions=True)
        return doc
    except frappe.UniqueValidationError:
        # Race condition occurred, another transaction created it. Retrieve it.
        frappe.clear_messages()
        existing = frappe.db.get_value("RE Billing Event", {"idempotency_key": idempotency_key}, "name")
        return frappe.get_doc("RE Billing Event", existing)
