import frappe
from frappe.utils import nowdate, flt
import traceback

try:
    import erpnext_egypt_compliance.erpnext_eta.pre_validation
    erpnext_egypt_compliance.erpnext_eta.pre_validation.validate_eta_before_submit = lambda *args, **kwargs: None
except:
    pass

frappe.init(site='kayanos.localhost', sites_path='./sites')
frappe.connect()

print('Frappe Version:', frappe.__version__)
try:
    import erpnext
    print('ERPNext Version:', erpnext.__version__)
except:
    pass
try:
    import kayanos
    print('KayanOS Version:', kayanos.__version__)
except:
    pass

def log(msg):
    print('-- ' + msg)

try:
    customer = frappe.new_doc('Customer')
    customer.customer_name = 'Test Refund Customer Proof - ffc52658'
    customer.customer_type = 'Company'
    customer.customer_group = 'Commercial'
    customer.territory = 'All Territories'
    customer.insert(ignore_permissions=True)
    frappe.db.commit()
    log('Created Customer: ' + customer.name)

    item = frappe.new_doc('Item')
    item.item_code = 'Test Refund Item Proof - ffc52658'
    item.item_group = 'Products'
    item.is_stock_item = 0
    item.insert(ignore_permissions=True)
    frappe.db.commit()

    si = frappe.new_doc('Sales Invoice')
    si.customer = customer.name
    si.append('items', {
        'item_code': item.item_code,
        'qty': 1,
        'rate': 100000
    })
    si.insert(ignore_permissions=True)
    si.submit()
    frappe.db.commit()
    log('Created Sales Invoice: ' + si.name + ' (100000)')

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    pe1 = get_payment_entry('Sales Invoice', si.name)
    pe1.paid_amount = 60000
    pe1.received_amount = 60000
    pe1.reference_no = 'TEST-REC-1'
    pe1.reference_date = nowdate()
    pe1.references[0].allocated_amount = 60000
    pe1.insert(ignore_permissions=True)
    pe1.submit()
    frappe.db.commit()
    log('Created Payment Entry (Receive): ' + pe1.name + ' (60000)')

    si.reload()
    log('Original Invoice Outstanding: ' + str(si.outstanding_amount))

    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    cn = make_return_doc('Sales Invoice', si.name)
    cn.insert(ignore_permissions=True)
    cn.submit()
    frappe.db.commit()
    log('Created Return Invoice (Credit Note): ' + cn.name)

    si.reload()
    cn.reload()
    log('Original Invoice Outstanding after CN: ' + str(si.outstanding_amount))
    log('Credit Note Outstanding: ' + str(cn.outstanding_amount))

    fee_si = frappe.new_doc('Sales Invoice')
    fee_si.customer = customer.name
    fee_si.append('items', {
        'item_code': item.item_code,
        'qty': 1,
        'rate': 10000
    })
    fee_si.insert(ignore_permissions=True)
    fee_si.submit()
    frappe.db.commit()
    log('Created Fee Invoice: ' + fee_si.name + ' (10000)')

    gl_entries = frappe.get_all('GL Entry', filters={'party': customer.name}, fields=['debit', 'credit'])
    total_debit = sum([flt(e.debit) for e in gl_entries])
    total_credit = sum([flt(e.credit) for e in gl_entries])
    log('Customer Balance (GL): ' + str(total_debit - total_credit))

    pe2 = frappe.new_doc('Payment Entry')
    pe2.payment_type = 'Pay'
    pe2.party_type = 'Customer'
    pe2.party = customer.name
    pe2.paid_from = pe1.paid_to
    pe2.paid_to = si.debit_to
    pe2.paid_amount = 50000
    pe2.received_amount = 50000
    pe2.reference_no = 'TEST-REF-1'
    pe2.reference_date = nowdate()
    
    pe2.append('references', {
        'reference_doctype': 'Sales Invoice',
        'reference_name': cn.name,
        'allocated_amount': 60000
    })
    pe2.append('references', {
        'reference_doctype': 'Sales Invoice',
        'reference_name': fee_si.name,
        'allocated_amount': -10000
    })
    
    pe2.insert(ignore_permissions=True)
    pe2.submit()
    frappe.db.commit()
    log('Created Refund Payment Entry: ' + pe2.name + ' (50000)')
    
    cn.reload()
    fee_si.reload()
    log('Credit Note Outstanding after Refund: ' + str(cn.outstanding_amount))
    log('Fee Invoice Outstanding after Refund: ' + str(fee_si.outstanding_amount))
    
    gl_entries2 = frappe.get_all('GL Entry', filters={'party': customer.name}, fields=['debit', 'credit'])
    t_d = sum([flt(e.debit) for e in gl_entries2])
    t_c = sum([flt(e.credit) for e in gl_entries2])
    log('Final Customer Balance (GL): ' + str(t_d - t_c))

except Exception as e:
    log('Error occurred:')
    traceback.print_exc()

finally:
    log('Cleaning up...')
    frappe.db.rollback()
    for doctype, name in [
        ('Payment Entry', pe2.name if 'pe2' in locals() else None),
        ('Sales Invoice', fee_si.name if 'fee_si' in locals() else None),
        ('Sales Invoice', cn.name if 'cn' in locals() else None),
        ('Payment Entry', pe1.name if 'pe1' in locals() else None),
        ('Sales Invoice', si.name if 'si' in locals() else None),
        ('Item', item.name if 'item' in locals() else None),
        ('Customer', customer.name if 'customer' in locals() else None),
    ]:
        if name:
            try:
                doc = frappe.get_doc(doctype, name)
                if doc.docstatus == 1:
                    doc.cancel()
                doc.delete()
            except Exception as ex:
                pass
    frappe.db.commit()
