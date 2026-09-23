import frappe
import os

def execute():
    app_path = frappe.get_app_path("kayanos")
    hooks_path = os.path.join(app_path, "hooks.py")
    
    with open(hooks_path, "r") as f:
        content = f.read()
        
    if "expire_reservations" not in content:
        scheduler_code = """
scheduler_events = {
    "cron": {
        "*/1 * * * *": [
            "kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation.expire_reservations"
        ]
    }
}
"""
        if "scheduler_events = {" in content:
            # Safely replace if it already has something else
            pass
        else:
            with open(hooks_path, "a") as f:
                f.write(scheduler_code)
        print("hooks.py updated.")
    else:
        print("hooks.py already updated.")
