import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.exceptions import LinkExistsError, ValidationError

class UnitTestREProjectProfile(UnitTestCase):
    pass

class IntegrationTestREProjectProfile(IntegrationTestCase):
    def setUp(self):
        frappe.db.sql("DELETE FROM `tabProject` WHERE project_name LIKE 'Test Canonical Project%' OR project_name LIKE 'Proj %'")
        
        # Create test company safely bypassing regional mandatory fields if possible, or supplying them
        if not frappe.db.exists('Company', 'Test RE Company'):
            doc = frappe.get_doc({
                'doctype': 'Company',
                'company_name': 'Test RE Company',
                'default_currency': 'EGP',
                'eta_default_activity_code': '0111' # Stub value for Egyptian compliance
            })
            doc.flags.ignore_mandatory = True # Bypass other potential mandatory fields
            doc.insert(ignore_permissions=True)
            self.company = doc.name
        else:
            self.company = 'Test RE Company'
            
        if not frappe.db.exists('Customer', 'Test External Developer'):
            doc = frappe.get_doc({
                'doctype': 'Customer',
                'customer_name': 'Test External Developer',
                'customer_group': 'Commercial'
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            self.customer = doc.name
        else:
            self.customer = 'Test External Developer'
            
        self.project_name = 'Test Canonical Project'
        self.project = frappe.get_doc({
            'doctype': 'Project',
            'project_name': self.project_name,
            'company': self.company
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_01_valid_internal_profile(self):
        doc = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': self.project.name,
            'operating_company': self.company,
            'ownership_type': 'Internal'
        }).insert()
        self.assertEqual(doc.ownership_type, 'Internal')
        self.assertFalse(doc.developer_type)

    def test_02_valid_external_profile(self):
        project2_name = 'Test Canonical Project 2'
        frappe.get_doc({'doctype': 'Project', 'project_name': project2_name, 'company': self.company}).insert(ignore_permissions=True)
            
        doc = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': project2_name,
            'operating_company': self.company,
            'ownership_type': 'External',
            'developer_type': 'Customer',
            'external_developer': self.customer
        }).insert()
        self.assertEqual(doc.external_developer, self.customer)

    def test_03_missing_project(self):
        doc = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'operating_company': self.company,
            'ownership_type': 'Internal'
        })
        self.assertRaises(ValidationError, doc.insert)

    def test_04_duplicate_profile(self):
        frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': self.project.name,
            'operating_company': self.company,
            'ownership_type': 'Internal'
        }).insert()
        
        doc2 = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': self.project.name,
            'operating_company': self.company,
            'ownership_type': 'Internal'
        })
        with self.assertRaises(Exception):
            doc2.insert()

    def test_06_internal_with_external_values_cleared(self):
        project3 = frappe.get_doc({'doctype': 'Project', 'project_name': 'Proj 3', 'company': self.company}).insert(ignore_permissions=True)
        doc = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': project3.name,
            'operating_company': self.company,
            'ownership_type': 'Internal',
            'developer_type': 'Customer',
            'external_developer': self.customer
        }).insert()
        self.assertEqual(doc.developer_type, None)

    def test_07_08_external_missing_developer(self):
        project4 = frappe.get_doc({'doctype': 'Project', 'project_name': 'Proj 4', 'company': self.company}).insert(ignore_permissions=True)
        doc = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': project4.name,
            'operating_company': self.company,
            'ownership_type': 'External'
        })
        self.assertRaises(ValidationError, doc.insert)

    def test_10_project_deletion_blocked(self):
        frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': self.project.name,
            'operating_company': self.company,
            'ownership_type': 'Internal'
        }).insert()
        self.assertRaises(LinkExistsError, frappe.delete_doc, 'Project', self.project.name)

    def test_12_crm_lead_deal_expose_field(self):
        meta_lead = frappe.get_meta('CRM Lead')
        meta_deal = frappe.get_meta('CRM Deal')
        self.assertTrue(meta_lead.has_field('kayanos_project'))
        self.assertTrue(meta_deal.has_field('kayanos_project'))

    def test_14_lead_to_deal_conversion(self):
        lead = frappe.get_doc({
            'doctype': 'CRM Lead',
            'first_name': 'Test Lead',
            'kayanos_project': self.project.name
        }).insert(ignore_permissions=True)
        
        from crm.crm.doctype.crm_lead.crm_lead import convert_to_deal
        deal = convert_to_deal(lead.name)
        self.assertEqual(deal.kayanos_project, self.project.name)

