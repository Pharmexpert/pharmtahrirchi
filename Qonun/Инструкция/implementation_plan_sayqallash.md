# Enhancing 'Sayqallash' Accuracy & AI-Local Integration

The goal is to ensure the **Sayqallash** tool captures all errors by first applying local learned rules and then using AI (Claude) as a meticulous "gap-filler" for missed morphological, phonetic, and contextual errors (e.g., "синаладган" -> "синаладиган").

## User Review Required

> [!IMPORTANT]
> **Multiple Occurrences**: I will update the logic to handle the same error appearing multiple times in a single sentence. Currently, it only flags the first occurrence.
> **AI Strictness**: I will increase the AI's strictness regarding Uzbek suffix harmony (синаладган vs синаладиган).

## Proposed Changes

### Backend: Database & API Logic

#### [MODIFY] [db.py](file:///c:/Users/Администратор/Desktop/2/backend/db.py)
- Update `get_rules_for_text` to use a `while` loop with `find()` to identify **all** occurrences of a known wrong word, not just the first one.

#### [MODIFY] [main.py](file:///c:/Users/Администратор/Desktop/2/backend/main.py)
- **Prompt Optimization**: Enrich `SAYQALLASH_PROMPT` with specific instructions for pharmaceutical terminology and common phonetic slips (omitted vowels).
- **Safe Indexing**: Implement a better index resolution for AI-suggested errors to prevent "phantom" highlights if the same word appears correctly elsewhere.
- **Hybrid Merge**: Ensure AI suggestions are only suppressed if they *exactly* overlap with a higher-priority local rule.

## Open Questions

- Should the AI also suggest stylistic improvements (e.g., more "academic" sounding words) or strictly stick to grammar/spelling?
- Do you want a "One-click" button to apply all AI suggestions at once?

## Verification Plan

### Automated Tests
1. Create a test script that calls the `/sayqallash` endpoint with the sentence containing "синаладган".
2. Verify that the response contains an annotation for "синаладган" with the correct `from_index` and `to_index`.

### Manual Verification
1. Open the Table Editor.
2. Enter the text from your screenshot.
3. Click "Sayqallash" and confirm that "синаладган" is now correctly identified and highlighted.
