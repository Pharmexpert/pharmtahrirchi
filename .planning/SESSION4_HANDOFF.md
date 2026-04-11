# SESSION 4 HANDOFF — Миссия Б давоми + Document Processing

## БАЖАРИЛГАН (Session 3-4):
- Миссия А: PROMT morph (184K POS) + syntax (гап бўлаклари) + 10K REP
- Миссия Б-1: Луғат 88K → whitelist ✅
- Миссия Б-2: Word freq 30K → suggest приоритет ✅
- Миссия Б-3: Affix tooltip (текшириш = текшир + иш) ✅
- Миссия Б-7: TM порог 0.95→0.80 ✅
- Она тилини бойитиш админ ойнаси ✅
- Vercel .vercelignore fix ✅

## ҚОЛГАН ВАЗИФАЛАР:

### Миссия Б (6 та):
- Б-4: Prefixes 32K → morph (бе-тартиб, но-тўғри)
- Б-5: Collocation 4,969 → бирикма текшируви
- Б-6: FAISS lexicon 8.7M индекс яратиш
- Б-8: Morphology engine preload (degraded→ready)
- Б-9: Syntax шаблонлар 1,490 + сўз тартиби 446
- Б-10: Word IDs 182K + NER 30 тур

### Document Processing (КРИТИК):
Word/Excel/PowerPoint дизайн сақлаб таржима — ҳозир ИШЛАМАЙДИ:
- mammoth DOCX → HTML конвертация бор лекин форматлаш тўлиқ сақланмайди
- Excel жадвал render ишлайди лекин формулалар йўқолади
- PowerPoint умуман қўллаб-қувватланмайди
- Қонун/1/ папкасида PROMT ресурслар бор:
  - PREPROC/ — preprocessing скриптлар
  - DIaLOGIKa.b2xtranslator.* — Word/Excel/PPT конвертер (.NET DLL)
  - TransIF.dll — ҳужжат ички тузилиш бошқариш
  - Лекин булар .NET/Windows DLL — Railway Linux'да ишламайди
- ЕЧИМ: mammoth (DOCX) + xlsx (Excel) + pptx-parser (PPT) JS/Python кутубхоналари

### UI муаммолар:
- Morph хатолари кўк ранг билан кўринмайди (Vercel кэш)
- Tooltip дизайн яхшилаш + drag
- Дубликат матн ойнаси пастда

## DEPLOY:
- Railway: `38d31b3` ✅
- Vercel: CLI deploy керак (`npx vercel --prod --yes`)
- GitHub webhook ишламайди — `.vercelignore` fix бор

## КРИТИК ФАЙЛЛАР:
- backend/routes/unified_analyze_routes.py — 4-қатлам анализ
- backend/promt_morph.py — PROMT морфология (184K POS)
- backend/uzbek_fdi_data.json — 250K луғат + pos_map
- frontend/components/AnnotatedTextView.tsx — хато кўрсатиш
- frontend/components/LinguisticAnalysisBar.tsx — 4 тугма
- frontend/app/tilshunos/page.tsx — Тилшунос саҳифа
