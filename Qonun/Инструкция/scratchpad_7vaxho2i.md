# Verification Tasks Checklist

- [x] Verify 'Таҳрир' (Edit) button on `http://localhost:3001/linguistic/paragraphs` shows filled fields.
    - **Result**: Success. Fields are populated correctly.
- [ ] Verify file upload on `http://localhost:3001/files` (no 'Not Found' error).
    - **Result**: **FAILED**. Network log shows 404 for `POST http://localhost:8000/api/upload`.
- [ ] Verify 'XLSX Юклаб олиш' (Download XLSX) on `http://localhost:3001/rules`.
    - **Result**: **FAILED**. Network log shows 405 Method Not Allowed for `GET http://localhost:8000/api/admin/rules/export?lang=uz`.
- [ ] Report findings.

