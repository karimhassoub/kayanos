import frappe
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.accounts.party import get_party_account
import traceback

@frappe.whitelist()
def execute_cancellation(cancellation_name, refund_account=None):
    if not frappe.has_permission('Payment Entry', 'create'):
        frappe.throw(_('No permission to execute financials.'))
        
    doc = frappe.get_doc('RE Agreement Cancellation', cancellation_name)
    if doc.execution_status not in ['Pending', 'Failed', 'Partially Executed']:
        frappe.throw(_('Only Pending, Failed, or Partially Executed cancellations can be executed.'))
        
    doc.db_set('execution_status', 'In Progress')
    
    policy = frappe.get_doc('RE Cancellation Policy', doc.cancellation_policy)
    events = frappe.get_all('RE Billing Event', filters={'sales_agreement': doc.sales_agreement, 'docstatus': 1}, fields=['name', 'erpnext_invoice_ref', 'status'])
    company = frappe.defaults.get_user_default('Company') or frappe.db.get_all('Company')[0].name
    
    returns_created = []
    total_cn_outstanding = 0.0
    total_si_outstanding = 0.0
    fee_outstanding = 0.0
    
    try:
        # 1. Handle Advance Payments
        # Advance payments not linked to billing events are not supported in V1
        # If the agreement has unallocated advance payments, block it.
        advances = frappe.get_all('Payment Entry Reference', 
            filters={'reference_doctype': 'RE Sales Agreement', 'reference_name': doc.sales_agreement},
            fields=['parent'])
        if advances:
            frappe.throw(_('Advance Payments detected. Not supported in automatic V1 cancellation. Manual Finance Exception required.'))

        # 2. Invoices & Credit Notes
        for ev in events:
            if not ev.erpnext_invoice_ref:
                continue
                
            si = frappe.get_doc('Sales Invoice', ev.erpnext_invoice_ref)
            if si.docstatus != 1:
                continue
                
            paid = flt(si.grand_total) - flt(si.outstanding_amount)
            
            # IDEMPOTENCY: Check if return already exists
            existing_return = frappe.db.get_value('Sales Invoice', 
                {'is_return': 1, 'return_against': si.name, 'docstatus': ['<', 2]}, 'name')
            
            if paid == 0 and policy.void_unpaid_invoices:
                if not existing_return:
                    frappe.get_doc('RE Billing Event', ev.name).void_unpaid_billing_event()
            elif paid > 0 and policy.refund_paid_amounts:
                ret_doc_name = existing_return
                if not ret_doc_name:
                    ret_doc = make_return_doc('Sales Invoice', si.name)
                    ret_doc.insert(ignore_permissions=True)
                    ret_doc.submit()
                    ret_doc_name = ret_doc.name
                    frappe.get_doc('RE Billing Event', ev.name).register_return_invoice(ret_doc_name)
                    
                returns_created.append(ret_doc_name)
                total_si_outstanding += flt(si.outstanding_amount)
                
        # 3. Create Fee Invoice
        fee_si_name = doc.cancellation_fee_invoice_ref
        fee_amount = flt(doc.calculated_cancellation_fee) + flt(doc.calculated_reservation_forfeiture)
        
        if not fee_si_name and fee_amount > 0 and policy.cancellation_fee_item:
            fee_si = frappe.new_doc('Sales Invoice')
            fee_si.customer = doc.customer
            fee_si.company = company
            fee_si.append('items', {
                'item_code': policy.cancellation_fee_item,
                'qty': 1,
                'rate': fee_amount
            })
            fee_si.insert(ignore_permissions=True)
            fee_si.submit()
            fee_si_name = fee_si.name
            doc.db_set('cancellation_fee_invoice_ref', fee_si_name)
            
        if fee_si_name:
            fee_outstanding = flt(frappe.db.get_value('Sales Invoice', fee_si_name, 'outstanding_amount'))
            
        # Recalculate CN outstanding
        for ret_name in returns_created:
            total_cn_outstanding += abs(flt(frappe.db.get_value('Sales Invoice', ret_name, 'outstanding_amount')))
            
        # 4. Cash Refund (Payment Entry)
        pe_name = doc.refund_payment_entry_ref
        net_refund = flt(doc.net_approved_refund)
        
        if net_refund < 0:
            frappe.throw(_('Negative refund calculated. Finance Exception required.'))
            
        if net_refund > 0 and not pe_name:
            pe = frappe.new_doc('Payment Entry')
            pe.payment_type = 'Pay'
            pe.party_type = 'Customer'
            pe.party = doc.customer
            pe.company = company
            pe.paid_from = refund_account if refund_account else frappe.db.get_value('Account', {'account_type': ['in', ['Cash', 'Bank']], 'company': company, 'is_group': 0})
            pe.paid_to = get_party_account('Customer', doc.customer, company)
            pe.paid_amount = net_refund
            pe.received_amount = net_refund
            pe.reference_no = 'REFUND-' + doc.name
            pe.reference_date = nowdate()
            
            # Allocate to Credit Notes until exhausted
            remaining_refund = net_refund
            for ret_name in returns_created:
                if remaining_refund <= 0: break
                out = abs(flt(frappe.db.get_value('Sales Invoice', ret_name, 'outstanding_amount')))
                alloc = min(out, remaining_refund)
                if alloc > 0:
                    pe.append('references', {
                        'reference_doctype': 'Sales Invoice',
                        'reference_name': ret_name,
                        'allocated_amount': -alloc # negative
                    })
                    remaining_refund -= alloc
                    
            pe.insert(ignore_permissions=True)
            pe.submit()
            pe_name = pe.name
            doc.db_set('refund_payment_entry_ref', pe_name)
            
        # 5. Reconciliation (Journal Entry)
        # IDEMPOTENCY: Check if JE already exists
        je_exists = frappe.db.exists('Journal Entry Account', {
            'reference_type': 'Sales Invoice', 
            'reference_name': ('in', returns_created),
            'docstatus': 1
        })
        
        if returns_created and not je_exists:
            je = frappe.new_doc('Journal Entry')
            je.voucher_type = 'Journal Entry'
            je.company = company
            je.posting_date = nowdate()
            acc = get_party_account('Customer', doc.customer, company)
            
            has_allocations = False
            for ret_name in returns_created:
                out = abs(flt(frappe.db.get_value('Sales Invoice', ret_name, 'outstanding_amount')))
                if out > 0:
                    orig_inv = frappe.db.get_value('Sales Invoice', ret_name, 'return_against')
                    cc = frappe.db.get_value('Sales Invoice Item', {'parent': orig_inv}, 'cost_center')
                    je.append('accounts', {
                        'account': acc, 'party_type': 'Customer', 'party': doc.customer,
                        'debit_in_account_currency': out,
                        'reference_type': 'Sales Invoice', 'reference_name': ret_name,
                        'cost_center': cc
                    })
                    has_allocations = True
                    
            if has_allocations:
                for ev in events:
                    if ev.erpnext_invoice_ref:
                        out = flt(frappe.db.get_value('Sales Invoice', ev.erpnext_invoice_ref, 'outstanding_amount'))
                        if out > 0:
                            cc = frappe.db.get_value('Sales Invoice Item', {'parent': ev.erpnext_invoice_ref}, 'cost_center')
                            je.append('accounts', {
                                'account': acc, 'party_type': 'Customer', 'party': doc.customer,
                                'credit_in_account_currency': out,
                                'reference_type': 'Sales Invoice', 'reference_name': ev.erpnext_invoice_ref,
                                'cost_center': cc
                            })
                            
                if fee_si_name:
                    out = flt(frappe.db.get_value('Sales Invoice', fee_si_name, 'outstanding_amount'))
                    if out > 0:
                        cc = frappe.db.get_value('Sales Invoice Item', {'parent': fee_si_name}, 'cost_center')
                        je.append('accounts', {
                            'account': acc, 'party_type': 'Customer', 'party': doc.customer,
                            'credit_in_account_currency': out,
                            'reference_type': 'Sales Invoice', 'reference_name': fee_si_name,
                            'cost_center': cc
                        })
                je.insert(ignore_permissions=True)
                je.submit()

        doc.db_set('execution_status', 'Completed')
        return 
    except Exception as e:
        frappe.db.rollback()
        doc.db_set('execution_status', 'Failed')
        doc.db_set('error_log', traceback.format_exc()[:140])
        raise e

@frappe.whitelist()
def submit_for_approval(cancellation_name):
    doc = frappe.get_doc('RE Agreement Cancellation', cancellation_name)
    if doc.status != 'Draft':
        frappe.throw('Only Draft can be submitted for commercial approval.')
    doc.status = 'Pending Commercial Approval'
    doc.save(ignore_permissions=True)
    return doc.status

@frappe.whitelist()
def approve_commercial(cancellation_name):
    if not frappe.has_permission('RE Agreement Cancellation', 'submit'):
        frappe.throw('No permission')
    doc = frappe.get_doc('RE Agreement Cancellation', cancellation_name)
    if doc.status != 'Pending Commercial Approval':
        frappe.throw('Invalid state.')
    doc.status = 'Pending Financial Execution'
    doc.save(ignore_permissions=True)
    return doc.status

@frappe.whitelist()
def reject_cancellation(cancellation_name):
    doc = frappe.get_doc('RE Agreement Cancellation', cancellation_name)
    doc.status = 'Rejected'
    doc.save(ignore_permissions=True)
    return doc.status
