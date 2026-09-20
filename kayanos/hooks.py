app_name = "kayanos"
app_title = "KayanOS"
app_publisher = "Kayan"
app_description = "Business orchestration layer for real-estate developers."
app_email = "hello@kayan.com"
app_license = "mit"

# include js, css files in header of desk.html
# app_include_css = "/assets/kayanos/css/kayanos.css"
# app_include_js = "/assets/kayanos/js/kayanos.js"

website_route_rules = [
	{"from_route": "/kayanos/<path:app_path>", "to_route": "kayanos"},
]

# Fixtures for exporting standard settings/roles
fixtures = [
	{"dt": "Workspace", "filters": [["module", "=", "KayanOS Core"]]}
]

# Upgrade-safe Custom Fields injection
custom_fields = {
	"CRM Lead": [
		{"fieldname": "kayanos_project", "fieldtype": "Link", "label": "KayanOS Project", "options": "Project", "insert_after": "status"},
	],
	"CRM Deal": [
		{"fieldname": "kayanos_project", "fieldtype": "Link", "label": "KayanOS Project", "options": "Project", "insert_after": "status"},
	]
}
