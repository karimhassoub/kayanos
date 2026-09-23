import frappe
def execute():
    deals = frappe.get_all("DocType", filters={"name": ("like", "%Deal%")}, pluck="name")
    print("Found Deal DocTypes:", deals)
    
    for d in deals:
        meta = frappe.get_meta(d)
        print(f"\n{d} Fields:")
        for f in meta.fields:
            if f.fieldtype == "Link":
                print(f" - {f.fieldname} -> {f.options}")

