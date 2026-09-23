import frappe
from frappe.model.document import Document
import json

def execute():
    # Setup global flags that might prevent versioning
    frappe.flags.in_test = False
    frappe.flags.in_import = False
    
    # 1. Fetch
    phase = frappe.get_all('RE Phase', limit=1)
    if not phase:
        print("No phase found")
        return
    doc = frappe.get_doc('RE Phase', phase[0].name)
    
    # Enable track_changes
    meta = frappe.get_meta('RE Phase')
    meta.track_changes = 1
    
    doc_before = doc.get_doc_before_save()
    print("Doc before save exists?", doc_before is not None)
    
    print("Old dev type:", doc.developer_type)
    doc.developer_type = 'External' if doc.developer_type == 'Internal' else 'Internal'
    print("New dev type:", doc.developer_type)
    
    doc.flags.ignore_version = False
    
    doc.save()
    
    versions = frappe.get_all('Version', filters={'ref_doctype': 'RE Phase', 'docname': doc.name})
    print("Versions count:", len(versions))
    if versions:
        v = frappe.get_doc('Version', versions[0].name)
        print("Version data:", v.data)
