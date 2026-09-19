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
