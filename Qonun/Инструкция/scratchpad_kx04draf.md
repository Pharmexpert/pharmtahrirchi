# Task: Test Login and Registration Functionality

## Checklist
- [x] Navigate to http://localhost:3001
- [x] Observe LoginGuard UI
- [x] Switch to 'Рўйхат' (Register) tab
- [x] Register with: Name='Test User', Email='test@example.com', Password='password123'
- [x] Click 'РЎЙХАТДАН ЎТИШ'
- [x] Verify success message
- [x] Switch back to 'Кириш' (Login) tab
- [x] Try to log in with new credentials
- [x] Verify 'Ҳисобингиз ҳали тасдиқланмаган' error message
- [x] Test 'DEVELOPER BYPASS (ADMIN)' button
- [x] Report Findings:
    - Registration works correctly.
    - Login with unapproved account correctly shows 'Ҳисобингиз ҳали тасдиқланмаган'.
    - 'DEVELOPER BYPASS (ADMIN)' button works and redirects to the dashboard.
    - **CRITICAL BUG**: The dashboard (app/page.tsx) crashes with `ReferenceError: Loader2 is not defined`.
- [ ] Report Findings
