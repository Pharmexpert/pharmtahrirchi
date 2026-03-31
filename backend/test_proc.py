import os, glob
from processor import ParagraphAligner

f = "temp_files/1243 WETTING PROPERTIES OF PHARMACEUTICAL SYSTEMS 27.01.26.docx"
print(f"=== Testing: {f} ===")
a = ParagraphAligner(f)

# Test process() (auto mode)
print("\n--- AUTO MODE (process()) ---")
result = a.process()
print(f"Result: {len(result)} rows")
for i, r in enumerate(result[:10]):
    en = r.get('en', '')[:50]
    ru = r.get('ru_v1', '')[:50]
    uz = r.get('uz_v1', '')[:50]
    print(f"  [{i}] type={r['type']} en='{en}' ru='{ru}' uz='{uz}'")

# Test process_ready_form()
print("\n--- READY MODE (process_ready_form()) ---")
result2 = a.process_ready_form()
print(f"Result: {len(result2)} rows")
for i, r in enumerate(result2[:10]):
    en = r.get('en', '')[:50]
    ru = r.get('ru_v1', '')[:50]
    uz = r.get('uz_v1', '')[:50]
    print(f"  [{i}] type={r['type']} en='{en}' ru='{ru}' uz='{uz}'")
