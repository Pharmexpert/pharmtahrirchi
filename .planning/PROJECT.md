# PROJECT: Pharma Expert v4

## Overview
Pharma Expert — трёхъязычная веб-платформа для профессионального перевода, научного редактирования и лингвистического контроля фармацевтической документации (UZ/RU/EN).

## Owner
Акмалхожа Зайнидинов (texnopharm@gmail.com)

## Tech Stack
- **Frontend**: Next.js 14 + React 18 + TypeScript (Vercel: pharmtech.info)
- **Backend**: Python 3.11 + FastAPI (Railway: api.pharmtech.info)
- **Database**: SQLite (28 таблиц) + FAISS (BERT 768-dim embeddings)
- **AI**: Claude Haiku 4.5, Gemini 2.0 Flash, Mistral-7B, BERT, BERTbek, NLLB-200
- **Spellcheck**: Hunspell (spylls) + 5,600+ rules + AI (3-tier pipeline)

## Repository
- **Repo**: github.com/Pharmexpert/pharmtahrirchi
- **Monorepo**: `backend/` (Python) + `frontend/` (Next.js)
- **Data**: Railway Persistent Volume `/app/data/`

## Key Metrics
| Metric | Value |
|--------|-------|
| DB Tables | 28 |
| API Endpoints | ~146 |
| Frontend Pages | 23 |
| AI Engines | 12 |
| Sayqallash Rules | 5,600+ |
| Annotated Terms | 9,923 |
| Drug Registry | 8,265 |
| Translation Memory | 184 (auto-grows) |
| Abbreviations | 3,775 |
| Transliteration Rules | 81 |
| Code Lines | ~24,600 |

## Current Milestone
v4.1 — Platform Enhancement (14 phases)

## Deploy
- **Backend**: `git push origin main` → Railway auto-build (~3-5 min)
- **Frontend**: `git push` → Vercel auto-deploy (~1-2 min)
- **Health**: `curl https://api.pharmtech.info/api/version`

## Critical Paths
- `backend/db.py` — all DB operations + FAISS (2,543 lines)
- `backend/routes/` — 18 route modules
- `backend/tm_search.py` — Translation Memory (search + learn)
- `frontend/components/AnnotatedTextView.tsx` — inline error display
- `frontend/components/TableEditor.tsx` — trilingual table editor
- `frontend/services/api.ts` — all API calls (802 lines)
