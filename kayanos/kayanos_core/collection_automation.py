import frappe
from frappe.utils import add_days, today

def send_collection_reminders():
    # Only run for unpaid or partially settled events that are overdue
    overdue_events = frappe.db.sql("""
        SELECT be.name, be.customer, be.sales_agreement, be.projected_balance, sch.due_date, be.company
        FROM `tabRE Billing Event` be
        JOIN `tabRE Payment Schedule` sch ON be.payment_schedule = sch.name
        WHERE be.collection_status IN ('Unpaid', 'Partially Settled')
          AND be.status = 'Invoiced'
          AND sch.due_date < %s
    """, (today(),), as_dict=True)

    for ev in overdue_events:
        # Check if we already sent a reminder today to prevent duplicates
        sent_today = frappe.db.exists("Communication", {
            "reference_doctype": "RE Billing Event",
            "reference_name": ev["name"],
            "communication_type": "Communication",
            "subject": ["like", "Overdue Payment Reminder%"],
            "communication_date": ["like", f"{today()}%"]
        })
        
        if not sent_today:
            try:
                # Determine email address (mock implementation, should ideally fetch from Customer contacts)
                customer = frappe.get_cached_doc("Customer", ev["customer"])
                if not customer.email_id:
                    frappe.log_error(f"Cannot send reminder: Customer {ev['customer']} has no email", "Collection Automation")
                    continue
                    
                subject = f"Overdue Payment Reminder for Agreement {ev['sales_agreement']}"
                message = f"""
                Dear Customer,
                
                This is a friendly reminder that a payment of {ev['projected_balance']} is currently overdue for Billing Event {ev['name']} (Due: {ev['due_date']}).
                Please arrange for payment at your earliest convenience.
                
                Regards,
                Collections Team
                """
                
                # In a real environment, we'd enqueue the email, but for testing we can just log a communication
                frappe.get_doc({
                    "doctype": "Communication",
                    "communication_type": "Communication",
                    "communication_medium": "Email",
                    "sent_or_received": "Sent",
                    "subject": subject,
                    "content": message,
                    "sender": frappe.session.user,
                    "recipients": customer.email_id,
                    "reference_doctype": "RE Billing Event",
                    "reference_name": ev["name"],
                    "status": "Linked"
                }).insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(title=f"Failed to send collection reminder for {ev['name']}", message=frappe.get_traceback())

