app_name = "kayanos"
app_title = "KayanOS"
app_publisher = "Kayan"
app_description = "Business orchestration layer for real-estate developers."
app_email = "hello@kayan.com"
app_license = "mit"

website_route_rules = [
	{"from_route": "/kayanos/<path:app_path>", "to_route": "kayanos"},
]

fixtures = [
	{"dt": "Workspace", "filters": [["module", "=", "KayanOS Core"]]}
]

custom_fields = {
	"CRM Lead": [
		{"fieldname": "kayanos_project", "fieldtype": "Link", "label": "KayanOS Project", "options": "Project", "insert_after": "status"},
	],
	"CRM Deal": [
		{"fieldname": "kayanos_project", "fieldtype": "Link", "label": "KayanOS Project", "options": "Project", "insert_after": "status"},
	]
}

scheduler_events = {
    "cron": {
        "*/1 * * * *": [
            "kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation.expire_reservations"
        ]
    },
    "hourly": [
        "kayanos.kayanos_core.erpnext_collection_service.sync_all_collections"
    ],
    "daily": [
        "kayanos.kayanos_core.financial_reconciliation.run_daily_integrity_audit",
        "kayanos.kayanos_core.collection_automation.send_collection_reminders"
    ]
}

doc_events = {
    "Payment Entry": {
        "on_submit": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update",
        "on_cancel": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update",
        "on_update_after_submit": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update"
    },
    "Journal Entry": {
        "on_submit": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update",
        "on_cancel": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update",
        "on_update_after_submit": "kayanos.kayanos_core.erpnext_collection_service.on_payment_voucher_update"
    }
}
