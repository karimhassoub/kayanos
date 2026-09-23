import json
import os

with open('audit_report_data.json', 'r') as f:
    data = json.load(f)

# Group by file
files = {}
for d in data:
    f = d['file']
    if f not in files:
        files[f] = []
    files[f].append(d)

md_content = "# KayanOS General Code Review Audit Report\n\n"
md_content += "## Summary Table\n\n"
md_content += "| File | Critical | High | Medium | Low | Total |\n"
md_content += "|---|---|---|---|---|---|\n"

for f, findings in files.items():
    counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    for d in findings:
        counts[d['severity']] += 1
    total = len(findings)
    md_content += f"| {f} | {counts['Critical']} | {counts['High']} | {counts['Medium']} | {counts['Low']} | {total} |\n"

md_content += "\n## Detailed Findings\n\n"

for f, findings in files.items():
    if f == 'audit_script.py':
        continue
    md_content += f"### File: {f}\n\n"
    
    # Group by category
    cats = {}
    for d in findings:
        c = d['category']
        if c not in cats:
            cats[c] = []
        cats[c].append(d)
        
    for c, items in cats.items():
        md_content += f"#### {c}\n\n"
        for i, item in enumerate(items, 1):
            md_content += f"{i}. **Severity**: {item['severity']}\n"
            md_content += f"   - **Line**: {item['line']}\n"
            md_content += f"   - **Issue**: {item['message']}\n"
            md_content += f"   - **Recommendation**: {item['fix_direction']}\n\n"

artifact_path = r"C:\Users\Khass\.gemini\antigravity\brain\3ed3c7bf-e4ec-4040-8495-b6aca0b7f715\audit_report.md"
with open(artifact_path, 'w', encoding='utf-8') as f:
    f.write(md_content)
print("Report generated.")
