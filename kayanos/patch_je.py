import sys

path = 'kayanos_core/erpnext_collection_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_je_logic = """    if je_accounts:
        # We need the voucher_type from the parent JEs
        je_names = list(set(r.parent for r in je_accounts))
        jes = frappe.get_all("Journal Entry", filters={"name": ("in", je_names)}, fields=["name", "voucher_type"])
        je_type_map = {je.name: je.voucher_type for je in jes}

        for r in je_accounts:
            v_type = je_type_map.get(r.parent)
            amt = flt(r.credit_in_account_currency)
            if v_type in ("Bank Entry", "Cash Entry", "Credit Card Entry"):
                raw_cash += amt
            else:
                raw_adj += amt"""

new_je_logic = """    if je_accounts:
        for r in je_accounts:
            raw_adj += flt(r.credit_in_account_currency)"""

content = content.replace(old_je_logic, new_je_logic)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
