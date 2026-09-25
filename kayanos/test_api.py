import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from kayanos.api import get_projects_list, get_project_workspace, create_project_workspace
import json

class IntegrationTestProjectsAPI(IntegrationTestCase):
    def setUp(self):
        frappe.db.sql("DELETE FROM `tabProject` WHERE project_name LIKE 'Test API Project%'")
        frappe.db.sql("DELETE FROM `tabRE Project Profile` WHERE project LIKE 'Test API Project%'")
        
        if not frappe.db.exists('Company', 'Test API Company'):
            doc = frappe.get_doc({
                'doctype': 'Company',
                'company_name': 'Test API Company',
                'default_currency': 'EGP',
                'eta_default_activity_code': '0111'
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            self.company = doc.name
        else:
            self.company = 'Test API Company'
            
        self.project_name = 'Test API Project 1'
        self.project = frappe.get_doc({
            'doctype': 'Project',
            'project_name': self.project_name,
            'company': self.company
        }).insert(ignore_permissions=True)
        
        self.profile = frappe.get_doc({
            'doctype': 'RE Project Profile',
            'project': self.project.name,
            'operating_company': self.company,
            'ownership_type': 'Internal'
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_get_projects_list(self):
        frappe.set_user("Administrator")
        res = get_projects_list(search="Test API Project")
        self.assertTrue(len(res['projects']) >= 1)
        
        project = [p for p in res['projects'] if p['name'] == self.project.name][0]
        self.assertEqual(project['ownership_type'], 'Internal')
        self.assertEqual(project['developer'], self.company)
        
    def test_get_projects_list_filters(self):
        frappe.set_user("Administrator")
        res = get_projects_list(company=self.company, ownership_type="Internal")
        self.assertTrue(len(res['projects']) >= 1)
        
        res = get_projects_list(ownership_type="External")
        # Should not match Test API Project 1 since it is Internal
        matches = [p for p in res['projects'] if p['name'] == self.project.name]
        self.assertEqual(len(matches), 0)

    def test_get_project_workspace(self):
        frappe.set_user("Administrator")
        res = get_project_workspace(self.project.name)
        self.assertIsNotNone(res['project'])
        self.assertEqual(res['project']['name'], self.project.name)
        self.assertIsNotNone(res['profile'])
        self.assertEqual(res['profile']['ownership_type'], 'Internal')
        
    def test_get_project_workspace_no_profile(self):
        p2 = frappe.get_doc({
            'doctype': 'Project',
            'project_name': 'Test API Project 2 No Profile',
            'company': self.company
        }).insert(ignore_permissions=True)
        
        frappe.set_user("Administrator")
        res = get_project_workspace(p2.name)
        self.assertIsNotNone(res['project'])
        self.assertIsNone(res['profile'])

    def test_create_project_workspace(self):
        frappe.set_user("Administrator")
        project_data = {
            "project_name": "Test API Project 3 Created",
            "company": self.company
        }
        profile_data = {
            "operating_company": self.company,
            "ownership_type": "Internal"
        }
        
        res = create_project_workspace(project=project_data, profile=profile_data)
        
        self.assertIsNotNone(res['project'])
        self.assertEqual(res['project']['project_name'], "Test API Project 3 Created")
        self.assertIsNotNone(res['profile'])
        self.assertEqual(res['profile']['ownership_type'], "Internal")
        
    def test_create_project_workspace_missing_data(self):
        frappe.set_user("Administrator")
        project_data = {
            "project_name": "Test API Project 4 Fail",
        }
        
        with self.assertRaises(frappe.ValidationError) as context:
            create_project_workspace(project=project_data)

