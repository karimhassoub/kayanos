frappe.query_reports["RE Receivables Worklist"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname": "sales_agreement",
            "label": __("Sales Agreement"),
            "fieldtype": "Link",
            "options": "RE Sales Agreement"
        },
        {
            "fieldname": "collection_status",
            "label": __("Collection Status"),
            "fieldtype": "Select",
            "options": "\nUnpaid\nPartially Settled\nFully Settled\nFully Returned\nOver-Settled (Credit)"
        }
    ]
};
