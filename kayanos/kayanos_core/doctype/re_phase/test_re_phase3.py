import frappe
import unittest
from frappe.exceptions import ValidationError

class IntegrationTestREPhase3(unittest.TestCase):
    def setUp(self):
        # Create test company safely bypassing regional mandatory fields if possible
        if not frappe.db.exists('Company', 'Test RE Company'):
            doc = frappe.get_doc({
                'doctype': 'Company',
                'company_name': 'Test RE Company',
                'default_currency': 'EGP',
                'eta_default_activity_code': '0111' 
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            self.company = doc.name
        else:
            self.company = 'Test RE Company'
            
        # Create Canonical Project and Profile
        self.project_name = 'PH3-PROJ'
        if not frappe.db.exists('Project', self.project_name):
            self.project = frappe.get_doc({
                'doctype': 'Project',
                'project_name': self.project_name,
                'company': self.company
            }).insert(ignore_permissions=True)
        else:
            self.project = frappe.get_doc('Project', self.project_name)
            
        if not frappe.db.exists('RE Project Profile', {'project': self.project.name}):
            self.profile = frappe.get_doc({
                'doctype': 'RE Project Profile',
                'project': self.project.name,
                'operating_company': self.company,
                'ownership_type': 'Internal',
                'sales_authorized': 1
            }).insert(ignore_permissions=True)
        else:
            self.profile = frappe.get_doc('RE Project Profile', {'project': self.project.name})
            self.profile.db_set('sales_authorized', 1)

    def test_01_hierarchy_creation(self):
        # Configurable Setup Types
        phase_type = frappe.get_doc({'doctype': 'RE Phase Type', 'type_name': 'Test Phase Type'}).insert(ignore_permissions=True, ignore_if_duplicate=True)
        prop_type = frappe.get_doc({'doctype': 'RE Property Type', 'type_name': 'Test Prop Type'}).insert(ignore_permissions=True, ignore_if_duplicate=True)
        unit_type = frappe.get_doc({'doctype': 'RE Unit Type', 'type_name': 'Test Unit Type', 'category': 'Residential'}).insert(ignore_permissions=True, ignore_if_duplicate=True)
        
        # Valid Project -> Phase -> Property -> Unit
        phase = frappe.get_doc({
            'doctype': 'RE Phase',
            'project': self.project.name,
            'phase_name': 'Phase 1',
            'phase_type': phase_type.name,
            'sales_authorized': 1
        }).insert(ignore_permissions=True)
        
        property_doc = frappe.get_doc({
            'doctype': 'RE Property',
            'phase': phase.name,
            'property_name': 'Bldg A',
            'property_type': prop_type.name
        }).insert(ignore_permissions=True)
        
        self.assertEqual(property_doc.project, self.project.name)
        
        unit = frappe.get_doc({
            'doctype': 'RE Unit',
            'property': property_doc.name,
            'unit_number': '101',
            'unit_type': unit_type.name,
            'lifecycle_status': 'Active',
            'availability_status': 'Available',
            'included_components': [
                {'component_type': 'Parking', 'component_number': 'P-1'}
            ]
        }).insert(ignore_permissions=True)
        
        self.assertEqual(unit.project, self.project.name)
        self.assertTrue(unit.shadow_item)
        self.assertEqual(unit.shadow_item, unit.name)

        item = frappe.get_doc('Item', unit.shadow_item)
        self.assertEqual(item.disabled, 0)

        return unit

    def test_02_unit_uniqueness(self):
        unit = self.test_01_hierarchy_creation()
        # Duplicate unit number in same property
        dup = frappe.get_doc({
            'doctype': 'RE Unit',
            'property': unit.property,
            'unit_number': unit.unit_number
        })
        self.assertRaises(ValidationError, dup.insert)
        
    def test_03_shadow_item_block_delete(self):
        unit = self.test_01_hierarchy_creation()
        # Try to delete unit
        self.assertRaises(ValidationError, frappe.delete_doc, 'RE Unit', unit.name)
        
    def test_04_sales_auth_revocation(self):
        unit = self.test_01_hierarchy_creation()
        phase = frappe.get_doc('RE Phase', frappe.db.get_value('RE Property', unit.property, 'phase'))
        
        # Revoke Phase auth
        phase.sales_authorized = 0
        phase.save()
        
        # Unit should auto-withhold
        unit.reload()
        self.assertEqual(unit.availability_status, 'Withheld')
        item = frappe.get_doc('Item', unit.shadow_item)
        self.assertEqual(item.disabled, 1)

    def test_05_reserved_sold_unchanged(self):
        unit = self.test_01_hierarchy_creation()
        unit.db_set('availability_status', 'Sold')
        
        phase = frappe.get_doc('RE Phase', frappe.db.get_value('RE Property', unit.property, 'phase'))
        phase.sales_authorized = 0
        phase.save()
        
        unit.reload()
        self.assertEqual(unit.availability_status, 'Sold')
        
    def test_06_project_auth_override(self):
        self.profile.db_set('sales_authorized', 0)
        
        phase = frappe.get_doc({
            'doctype': 'RE Phase',
            'project': self.project.name,
            'phase_name': 'Phase Fail',
            'sales_authorized': 1
        })
        self.assertRaises(ValidationError, phase.insert)

    def test_07_developer_change_allowed(self):
        unit = self.test_01_hierarchy_creation()
        phase = frappe.get_doc('RE Phase', frappe.db.get_value('RE Property', unit.property, 'phase'))
        
        phase.developer_type = 'External'
        
        if not frappe.db.exists('Customer', 'Test Ext Dev'):
            doc = frappe.get_doc({'doctype': 'Customer', 'customer_name': 'Test Ext Dev'})
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            
        phase.external_developer_type = 'Customer'
        phase.external_developer = 'Test Ext Dev'
        phase.save()
        self.assertEqual(phase.developer_type, 'External')

    def test_08_lifecycle_validation(self):
        property_name = frappe.get_all('RE Property', limit=1)[0].name
        unit = frappe.get_doc({
            'doctype': 'RE Unit',
            'property': property_name,
            'unit_number': 'TEST-LIFECYCLE',
            'lifecycle_status': 'Draft',
            'availability_status': 'Available'
        })
        self.assertRaises(ValidationError, unit.insert)

    def test_09_rollback_on_item_fail(self):
        # We simulate item creation failure
        property_name = frappe.get_all('RE Property', limit=1)[0].name
        unit = frappe.get_doc({
            'doctype': 'RE Unit',
            'property': property_name,
            'unit_number': 'TEST-ROLLBACK'
        })
        
        # Monkey patch frappe.new_doc for Item to raise Exception
        original_new_doc = frappe.new_doc
        def mock_new_doc(doctype, *args, **kwargs):
            if doctype == 'Item':
                raise ValueError("Item creation simulated failure")
            return original_new_doc(doctype, *args, **kwargs)
            
        frappe.new_doc = mock_new_doc
        
        try:
            self.assertRaises(ValueError, unit.insert)
            # Ensure unit is NOT in DB (rollback)
            self.assertFalse(frappe.db.exists('RE Unit', {'unit_number': 'TEST-ROLLBACK'}))
        finally:
            frappe.new_doc = original_new_doc

    def test_10_guest_access_denied(self):
        frappe.set_user('Guest')
        try:
            property_name = frappe.db.get_value('RE Property', {})
            unit = frappe.get_doc({
                'doctype': 'RE Unit',
                'property': property_name,
                'unit_number': 'GUEST-TEST'
            })
            self.assertRaises(frappe.PermissionError, unit.insert)
        finally:
            frappe.set_user('Administrator')

