import io
path = 'kayanos/hooks.py'
with open(path, 'rb') as f:
    content = f.read()

# find where "doc_events =" is if it's garbled, just strip from 'scheduler_events = {' down and rewrite
text = content.decode('utf-8', errors='ignore')
idx = text.find('d\x00o\x00c\x00_\x00e\x00v')
if idx != -1:
    text = text[:idx]

text += """
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

scheduler_events.setdefault("hourly", []).append("kayanos.kayanos_core.erpnext_collection_service.sync_all_collections")
"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
