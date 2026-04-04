# [Implementation Plan: Unified Feature Set - Single Language & Specialist Tracking]

This plan addresses the requirement to handle single-language documents, update UI labels, and implement a mandatory specialist tracking system with a self-learning autocomplete list.

## User Review Required

> [!IMPORTANT]
> **Database Migration**: I will automatically add a `specialist_name` column to your existing `pharma_editor.db`. No data will be lost.
> **Language Detection**: I will use the `langdetect` library. For short fragments, it may occasionally misidentify (e.g., short technical terms), but for full documents, it is highly accurate.

## Proposed Changes

### 1. Database & API (Backend)

#### [MODIFY] [db.py](file:///c:/Users/Администратор/Desktop/2/backend/db.py)
- Update `init_db` to add `specialist_name` column to the `alignments` table.
- Add `get_unique_specialists()` function to return a sorted list of unique names from the database.
- Update saving functions to store the specialist name.

#### [MODIFY] [main.py](file:///c:/Users/Администратор/Desktop/2/backend/main.py)
- Create `@app.get("/specialists")` endpoint.
- Update `/upload` to accept `specialist_name` and pass it to the alignment data.
- Update `/save` and `/save-row` to persist the specialist name.

### 2. Document Processing (Backend)

#### [MODIFY] [processor.py](file:///c:/Users/Администратор/Desktop/2/backend/processor.py)
- Import `langdetect`.
- Implement `detect_and_split_single_language(text)`:
  - Detects if text is EN, RU, or UZ.
  - Splits text into meaningful rows.
  - Maps rows to the specific column while leaving translations and original `v1` empty as requested.
- Update `ParagraphAligner` to use this logic if a 3-column table isn't found.

### 3. User Interface (Frontend)

#### [MODIFY] [page.tsx](file:///c:/Users/Администратор/Desktop/2/frontend/app/page.tsx)
- **Rename Item**: Change label to "шу ҳолатида юклаш".
- **Specialist Input**: Add a mandatory text input for "Мутахассис исми ва шарифи".
- **Autocomplete**:
  - Fetch list from `/specialists` on component load.
  - Use a `<datalist>` for the input field to show the "previously entered" list.
- **Validation**: Ensure the "Ишлов бериш ва очиш" button is only enabled if a Specialist Name is provided.
- **State**: Include `specialistName` in the `handleUpload` request.

## Open Questions

- Should the Specialist Name be editable later in the `TableEditor`, or is it only set at upload time for the entire file? (I will assume it is set for the whole file during upload).

## Verification Plan

### Automated Tests
1. Test `/upload` with a 1-column DOCX and verify it maps to correctly detected language column.
2. Verify `/specialists` returns unique names after several uploads.

### Manual Verification
1. Open the landing page.
2. Verify the toggle label is renamed.
3. Check if the specialist field is mandatory.
4. Upload a single-language file and verify the column alignment.
