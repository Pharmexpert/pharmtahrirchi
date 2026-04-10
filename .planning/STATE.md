# STATE — Pharma Expert v4.1

## Current Milestone
v4.1 Platform Enhancement — ALL PHASES IMPLEMENTED

## Phase Status
| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ Done | AnnotatedTextView → LangCell, Assistant, Paragraphs |
| 1 | ✅ Done | Style Guide tooltip (rule_id, category, source) |
| 2 | ✅ Done | Transliteration buttons in translate mode |
| 3 | ✅ Done | NER whitelist + placeholder + 3 API endpoints |
| 4 | ✅ Done | BERTbek POS discover-terms + approve-term endpoints |
| 5 | ✅ Done | /workbench page (3-lang parallel editor) |
| 6 | ✅ Done | OCR engine + /api/ocr/extract endpoint |
| 7 | ✅ Done | QA Lab engine + /qa page + /api/qa/check |
| 8 | ✅ Ready | Mistral HF — code ready, needs HF_TOKEN env |
| 9 | ✅ Done | Test files: test_sayqallash.py (8 tests) |
| 10 | ✅ Done | Pharmacopoeia whitelist in sayqallash |
| 11 | ✅ Ready | PROMT seed — call /api/admin/promt-resources/import |
| 12 | ✅ Done | Dual-script style regex auto-convert |
| 13 | ✅ Done | improve-row returns style+syntax layers |
| 14 | ✅ Ready | AI batch — call /api/admin/annotated/translate-batch |

## Deployment Actions Needed
1. `HF_TOKEN=hf_xxx` → Railway env (Phase 8)
2. `pytesseract` + Tesseract → Railway nixpacks (Phase 6)
3. Call `/api/admin/promt-resources/import` on production (Phase 11)
4. Call `/api/admin/annotated/translate-batch` repeatedly (Phase 14, ~$10-50)

## Last Session
- Date: 2026-04-10 (Session 3)
- All 14 phases implemented in code
- 4 phases need production deployment actions
