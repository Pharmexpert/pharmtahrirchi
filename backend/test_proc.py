from processor import ParagraphAligner
a = ParagraphAligner("temp_files/1243 WETTING PROPERTIES OF PHARMACEUTICAL SYSTEMS 27.01.26.docx")
r = a.process()
print(f"ROWS: {len(r)}")
for i,x in enumerate(r[:8]):
    print(f"[{i}] en={x['en'][:40]} | ru={x.get('ru_v1','')[:40]} | uz={x.get('uz_v1','')[:40]}")
