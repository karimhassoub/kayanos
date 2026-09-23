import os, ast, re, json

TARGET_DIR = r'E:\kayan OS\kayanOS\kayanos'
REPORT_DATA = []

def add_finding(file_path, severity, category, message, line, fix_direction):
    REPORT_DATA.append({
        'file': file_path.replace(TARGET_DIR, '').lstrip('\\\\/'),
        'severity': severity,
        'category': category,
        'message': message,
        'line': line,
        'fix_direction': fix_direction
    })

for root, _, files in os.walk(TARGET_DIR):
    for file in files:
        if not file.endswith('.py'):
            continue
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            line_no = i + 1
            if 'frappe.db.sql' in line and ('%' in line or '.format(' in line or line.strip().startswith('f"')):
                add_finding(filepath, 'Critical', 'Security', 'Potential SQL injection: string formatting in frappe.db.sql', line_no, 'Use parameterized queries (%s) and pass variables as a tuple/dict.')
            if '1970-01-01' in line or '1900-01-01' in line:
                add_finding(filepath, 'Medium', 'Clean Code', 'Hardcoded fallback date used', line_no, 'Remove hardcoded fallback and handle None/empty cases explicitly or log the fallback.')
            if 'frappe.db.commit()' in line and not file.startswith('test_'):
                add_finding(filepath, 'Critical', 'Architectural Contracts', 'frappe.db.commit() called directly in code', line_no, 'Remove explicit commit; rely on frappe framework request lifecycle to handle commits.')
            if 'flt(' in line and ('amount' in line.lower() or 'total' in line.lower() or 'balance' in line.lower()):
                if ',' not in line.split('flt(')[1].split(')')[0]:
                    add_finding(filepath, 'Low', 'Business Logic', 'Monetary calculation using flt() without explicit precision', line_no, 'Pass precision argument to flt() or use currency rounding functions.')
            if ('"Payment Entry"' in line or "'Payment Entry'" in line) and ('frappe.get_doc' in line or 'frappe.new_doc' in line) and not file.startswith('test_') and 'erpnext_bridge' not in filepath:
                add_finding(filepath, 'High', 'Architectural Contracts', 'Direct manipulation of Payment Entry from KayanOS', line_no, 'Use the ERPNext Bridge/Service layer to interact with financial doctypes.')
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    is_whitelisted = False
                    for d in node.decorator_list:
                        if isinstance(d, ast.Call) and getattr(d.func, 'attr', '') == 'whitelist':
                            is_whitelisted = True
                        elif isinstance(d, ast.Name) and getattr(d, 'id', '') == 'whitelist':
                            is_whitelisted = True
                        elif isinstance(d, ast.Attribute) and getattr(d, 'attr', '') == 'whitelist':
                            is_whitelisted = True
                    if is_whitelisted:
                        func_code = ast.unparse(node)
                        if 'has_permission' not in func_code and 'allow_guest=True' not in func_code:
                            add_finding(filepath, 'High', 'Security', 'Whitelisted function missing explicit frappe.has_permission() check', node.lineno, 'Add frappe.has_permission() check or role-based validation before returning data.')
        except Exception:
            pass

with open('audit_report_data.json', 'w', encoding='utf-8') as f:
    json.dump(REPORT_DATA, f, indent=2)
print(f'Found {len(REPORT_DATA)} issues.')
