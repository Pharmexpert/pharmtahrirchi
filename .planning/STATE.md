# STATE — Pharma Expert v4.1

## Current Milestone
v4.1 Platform Enhancement — **ALL 14 PHASES COMPLETE** ✅

## Phase Status
| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ Done | AnnotatedTextView → LangCell, Assistant, Paragraphs |
| 1 | ✅ Done | Style Guide tooltip (rule_id, category, source) |
| 2 | ✅ Done | Transliteration buttons in translate mode |
| 3 | ✅ Done | NER whitelist + placeholder + 3 API endpoints |
| 4 | ✅ Done | BERTbek POS discover-terms + approve-term |
| 5 | ✅ Done | /workbench — 3-language parallel editor |
| 6 | ✅ Done | OCR engine + endpoint (Tesseract needs Railway config) |
| 7 | ✅ Done | QA Lab — qa_engine + /qa page + /api/qa/check |
| 8 | ✅ Done | Mistral — local_gguf mode active on Railway |
| 9 | ✅ Done | Test suite — test_sayqallash.py (8 tests) |
| 10 | ✅ Done | Pharmacopoeia whitelist (9,923+ terms) |
| 11 | ✅ Done | PROMT seed — TM=11,000 abbrs=864 |
| 12 | ✅ Done | Dual-script style regex auto-conversion |
| 13 | ✅ Done | improve-row returns style+syntax layers |
| 14 | ✅ Done | AI batch — 9,757/9,757 terms translated (100%) |

## Production Deploys
| Commit | Date | Description |
|--------|------|-------------|
| 384046a | 2026-04-10 | feat: v4.1 — 14 phases (code) |
| f970587 | 2026-04-10 | fix: PROMT import schema alignment |
| 1c477bb | 2026-04-10 | deps: pytesseract + Tesseract nixpacks |

## Session 3 Summary
- Date: 2026-04-10
- Enhanced docs: SPECIFICATION + TZ (SQL, API examples, Props, Env, Lessons)
- GSD integration: .planning/ (PROJECT, ROADMAP, STATE, REQUIREMENTS)
- 14 phases implemented, deployed, and verified on production
- 9,757 annotated_words translated UZ→EN+RU via Claude Haiku
- 7 AI engines active: Claude, Gemini, Llama, Mistral, NLLB, Sage, Auto
- TM: 11,000 segments
- New pages: /workbench, /qa
- New endpoints: /api/analyze/ner, /protect-entities, /restore-entities, /api/nlp/discover-terms, /api/nlp/approve-term, /api/ocr/extract, /api/qa/check

## Session 5 Summary
- Date: 2026-04-12
- B-9 syntax templates: 1,490 templates + 456 word order rules (7 types: sodda, qoshma_bog, qoshma_bogsiz, qoshma_ergash, pharma, ilmiy, rasmiy)
- OCR: nixpacks.toml + tessdata auto-download script for Railway (tesseract + eng/rus/uzb)
- pdfplumber dependency added
- Document Processing: DOCX preview + translate verified on production
- Debug logging added to 5 translation engine fallbacks
- Production verified: Railway 9 AI engines, Vercel frontend, 4-layer analysis working
- Commits: a4db47e (B-9 syntax), ee5fdf3 (pdfplumber+logging), 767c94b (OCR tessdata)
