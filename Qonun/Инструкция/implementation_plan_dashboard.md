# Scientific Rules Management Dashboard

This feature will allow users to manage the "Sayqallash" (Grammatical/Terminology) rules that the system learns during the editing process. Users can view, add, edit, or delete rules to ensure the AI's future suggestions are accurate and contextually appropriate.

## User Review Required

> [!NOTE]
> This dashboard will directly affect the AI's "Sayqallash" suggestions. Deleting a rule will stop the editor from suggesting that specific correction in the future.

## Proposed Changes

### Backend: API for Rules Management

#### [MODIFY] [db.py](file:///c:/Users/Администратор/Desktop/2/backend/db.py)
- Add `delete_sayqallash_rule(rule_id: int)` function.
- Add `update_sayqallash_rule(rule_id: int, data: Dict)` function.

#### [MODIFY] [main.py](file:///c:/Users/Администратор/Desktop/2/backend/main.py)
- Add `GET /api/rules` endpoint to fetch rules with pagination/filters.
- Add `POST /api/rules` endpoint to manually create new rules.
- Add `PUT /api/rules/{id}` endpoint to update existing rules.
- Add `DELETE /api/rules/{id}` endpoint to remove rules.

### Frontend: Dashboard UI

#### [NEW] [RulesPage.tsx](file:///c:/Users/Администратор/Desktop/2/frontend/app/rules/page.tsx)
- Create a modern, searchable table showing:
  - Wrong Form vs Correct Form
  - Type (Spelling, Grammar, Terminology, etc.)
  - Frequency (How many times it was used)
  - Last Updated timestamp.
- Add a modal for Adding/Editing rules.

#### [MODIFY] [Sidebar.tsx](file:///c:/Users/Администратор/Desktop/2/frontend/components/Sidebar.tsx) (or equivalent)
- Add a navigation link to the "Rules Management" dashboard.

## Open Questions

- Should we support "Bulk Delete" for rules?
- Should we allow users to "Export/Import" rules as CSV/Excel for collaborative sharing?

## Verification Plan

### Automated Tests
- Test API endpoints using `curl` to ensure CRUDS operations on the database are successful.
- Verify that adding a rule via the dashboard correctly influences the "Sayqallash" suggestions in the main editor.

### Manual Verification
- Open the new Rules page, add a test rule, and verify it appears in the list.
- Edit the rule and verify the changes are saved.
- Delete the rule and verify it is removed from the database.
