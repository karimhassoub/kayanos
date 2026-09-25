import frappe
from frappe import _
import json

@frappe.whitelist()
def get_projects_list(page=1, page_length=20, search=None, status=None, company=None, ownership_type=None):
    frappe.has_permission("Project", "read", throw=True)
    
    page = frappe.utils.cint(page) or 1
    page_length = min(frappe.utils.cint(page_length) or 20, 100)
    
    filters = {}
    if status:
        filters['status'] = status
    if company:
        filters['company'] = company
        
    or_filters = {}
    if search:
        or_filters = {
            "name": ["like", f"%{search}%"],
            "project_name": ["like", f"%{search}%"]
        }
        
    if ownership_type:
        matching_profiles = frappe.get_all("RE Project Profile", 
            filters={"ownership_type": ownership_type},
            fields=["project"]
        )
        project_names = [p.project for p in matching_profiles]
        if not project_names:
            return {"projects": [], "total": 0, "page": page, "page_length": page_length}
        filters['name'] = ["in", project_names]
        
    projects = frappe.get_list("Project",
        fields=["name", "project_name", "status", "company", "project_type"],
        filters=filters,
        or_filters=or_filters,
        limit_start=(page - 1) * page_length,
        limit_page_length=page_length,
        order_by="modified desc"
    )
    
    total = frappe.db.count("Project", filters=filters, or_filters=or_filters)
    
    if projects:
        project_names = [p.name for p in projects]
        profiles = frappe.get_all("RE Project Profile",
            filters={"project": ["in", project_names]},
            fields=["project", "ownership_type", "developer_type", "external_developer", "sales_authorized"]
        )
        profile_map = {p.project: p for p in profiles}
        
        for p in projects:
            profile = profile_map.get(p.name, {})
            p.ownership_type = profile.get("ownership_type")
            p.developer_type = profile.get("developer_type")
            p.external_developer = profile.get("external_developer")
            p.sales_authorized = profile.get("sales_authorized")
            
            if p.ownership_type == "External" and p.external_developer:
                p.developer = p.external_developer
            elif p.ownership_type == "Internal" and p.company:
                p.developer = p.company
            else:
                p.developer = None
                
    return {
        "projects": projects,
        "total": total,
        "page": page,
        "page_length": page_length
    }

@frappe.whitelist()
def get_project_workspace(name):
    frappe.has_permission("Project", "read", throw=True)
    
    if not frappe.db.exists("Project", name):
        frappe.throw(_("Project {0} not found").format(name), frappe.DoesNotExistError)
        
    project = frappe.get_doc("Project", name)
    project.check_permission("read")
    
    project_dict = {
        "name": project.name,
        "project_name": project.project_name,
        "status": project.status,
        "company": project.company,
        "project_type": project.project_type,
        "expected_start_date": project.expected_start_date,
        "expected_end_date": project.expected_end_date,
        "actual_start_date": project.actual_start_date,
        "actual_end_date": project.actual_end_date
    }
    
    profile_name = frappe.db.get_value("RE Project Profile", {"project": name}, "name")
    if profile_name:
        profile = frappe.get_doc("RE Project Profile", profile_name)
        profile.check_permission("read")
        profile_dict = {
            "name": profile.name,
            "project": profile.project,
            "operating_company": profile.operating_company,
            "ownership_type": profile.ownership_type,
            "developer_type": profile.developer_type,
            "external_developer": profile.external_developer,
            "sales_authorized": profile.sales_authorized,
            "construction_responsible": profile.construction_responsible
        }
    else:
        profile_dict = None
        
    return {
        "project": project_dict,
        "profile": profile_dict
    }

@frappe.whitelist()
def create_project_workspace(project, profile=None):
    frappe.has_permission("Project", "create", throw=True)
    
    if isinstance(project, str):
        project = json.loads(project)
    if isinstance(profile, str):
        profile = json.loads(profile)
        
    if profile:
        frappe.has_permission("RE Project Profile", "create", throw=True)
        
    if not project.get("project_name"):
        frappe.throw(_("project_name is required"))
    if not project.get("company"):
        frappe.throw(_("company is required"))
        
    if profile:
        if not profile.get("ownership_type"):
            frappe.throw(_("ownership_type is required in profile"))
        if not profile.get("operating_company"):
            frappe.throw(_("operating_company is required in profile"))
            
    try:
        project_doc = frappe.new_doc("Project")
        project_doc.update(project)
        project_doc.insert()
        
        if profile:
            profile_doc = frappe.new_doc("RE Project Profile")
            profile_doc.update(profile)
            profile_doc.project = project_doc.name
            profile_doc.insert()
            
        frappe.db.commit()
        return get_project_workspace(project_doc.name)
    except Exception as e:
        frappe.db.rollback()
        raise e
