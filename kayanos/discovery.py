import frappe
def execute():
    for term in ['%build%', '%estate%', '%zone%', '%phase%', '%asset%', '%item%']:
        docs = frappe.get_all('DocType', filters={'name': ['like', term], 'custom': 0}, pluck='name')
        print(f'Term {term}: {docs}')
