import os, glob
from processor import ParagraphAligner

# Find a docx file in temp_files
files = glob.glob("temp_files/*.docx")
print("Files:", files)

if files:
    f = files[0]
    print(f"\n=== Testing: {f} ===")
    a = ParagraphAligner(f)
    print(f"Table exists: {a.table is not None}")
    if a.table:
        print(f"Table rows: {len(a.table.rows)}")
        for i, row in enumerate(a.table.rows[:3]):
            print(f"  Row {i}: {len(row.cells)} cells")
            for j, cell in enumerate(row.cells[:4]):
                txt = cell.text[:60].replace('\n', ' ')
                print(f"    Cell {j}: '{txt}'")
        print(f"Has 3-col table: {a.has_three_column_table()}")
    
    try:
        result = a.process()
        print(f"\nResult: {len(result)} rows")
        for i, r in enumerate(result[:5]):
            print(f"  [{i}] type={r['type']} en='{r['en'][:40]}' ru='{r.get('ru_v1','')[:40]}' uz='{r.get('uz_v1','')[:40]}'")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
