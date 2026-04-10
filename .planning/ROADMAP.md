# ROADMAP — Pharma Expert v4.1

## Milestone: v4.1 Platform Enhancement
**Goal**: Барча саҳифаларда лингвистик анализ, янги AI интеграциялар, OCR, QA, ва маълумотлар тўлдириш
**Phases**: 15 (0-14)
**Status**: In Progress

---

## Phase 0: AnnotatedTextView + Tooltip барча саҳифаларга
**Goal**: Inline ошибки + tooltip + синонимлар — AnnotatedTextView компонентини барча саҳифаларга интеграция
**Status**: Not Started
**Priority**: 🔴 Critical
**Depends on**: —
**Key tasks**:
- LangCell (TableEditor) ичига AnnotatedTextView қўшиш → /projects/:id жадвалда inline ошибки
- /assistant саҳифасида chat UI ичига AnnotatedTextView интеграция
- /paragraphs саҳифасида AnnotatedTextView қўшиш
- Единообразный tooltip: ❌ old → ✅ new + тип + доверие%
**Success criteria**: Барча саҳифаларда 4-слойный inline ошибки кўринади

## Phase 1: Style Guide inline ошибки
**Goal**: 126 та стилистик қоида учун розовая волнистая линия AnnotatedTextView ичида
**Status**: Not Started
**Priority**: 🔴 Critical
**Depends on**: Phase 0
**Key tasks**:
- _run_style() функциясини AnnotatedTextView-ga интеграция
- Розовый (#DB2777) волнистый подчёркивание стил ошибки учун
- USP/ICH/WHO/SI қоидалари tooltip-да кўрсатиш
**Success criteria**: Стил ошибки розовая линия билан белгиланади

## Phase 2: Тилшунос транслитерация тугмаси
**Goal**: 🔄 Кирилл↔Latin тугмаси Тилшунос edit + translate режимларида
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: —
**Key tasks**:
- Тилшунос UI'да 🔄 тугма қўшиш (edit ва translate режимлар)
- dual_script_rules (81 правило, Закон 2019 г.) орқали конвертация
- Toolbar'да тугма + keyboard shortcut (Ctrl+Shift+T)
**Success criteria**: Бир тугма билан Кирилл→Latin ёки Latin→Кирилл ўтказиш мумкин

## Phase 3: NER исм ҳимояси
**Goal**: Дори номлари ва терминларни таржимадан ҳимоя қилиш (whitelist + NER)
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: —
**Key tasks**:
- drug_registry (8,265) + annotated_words (9,923) → whitelist массив
- spaCy xx_ent_wiki_sm (100+ тил, 50MB) интеграция
- Placeholder механизм: "__NE_0__" таржима вақтида
- NER endpoint: POST /api/ner/extract
**Success criteria**: Дори номлари таржима вақтида ўзгармайди

## Phase 4: BERTbek POS → авто-луғат бойитиш
**Goal**: Янги терминларни автомат аниқлаш ва луғатга қўшиш
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: Phase 3
**Key tasks**:
- BERTBEK_ENABLED=1 Railway'да ёқиш
- POS-тегирование → NOUN/ADJ фильтр → "Янги термин" уведомление
- Админ тасдиқи → annotated_words/drugs жадвалга қўшиш
**Success criteria**: Янги терминлар автомат аниқланиб, админга кўрсатилади

## Phase 5: /workbench — 3-тилли таржима станцияси
**Goal**: Профессионал 3-тилли Monaco editor саҳифаси
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: Phase 0, Phase 2
**Key tasks**:
- /workbench саҳифаси яратиш (3 та Monaco editor: UZ/RU/EN)
- Синхронный скролл + alignment
- TM% ҳар сатр ёнида кўрсатиш
- NER подсветка ҳимояланган исмлар
**Success criteria**: 3 тилда параллель таҳрирлаш + TM интеграция ишлайди

## Phase 6: OCR пайплайн
**Goal**: PDF/расм → текст → авто-sayqallash
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: —
**Key tasks**:
- Tesseract 5 + eng/rus/uzb traineddata интеграция
- POST /api/ocr/extract endpoint
- OCR натижасини автоматик sayqallash'дан ўтказиш
- Frontend: файл юклаш → OCR → натижа
**Success criteria**: PDF/расм текстга айлантирилади ва текширилади

## Phase 7: QA Lab (сифат назорати)
**Goal**: Таржима сифатини автоматик текшириш
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: Phase 5
**Key tasks**:
- Back-translation текшируви (UZ→EN→UZ, солиштириш)
- Сегмент сони текшируви (source vs target)
- Рақам/бирлик сақланишини текшириш
- QA ҳисобот яратиш
**Success criteria**: Таржима сифати автоматик баҳоланади

## Phase 8: Mistral HF Inference API
**Goal**: Mistral-7B-Instruct-Uz узбек тили учун AI ёқиш
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: —
**Key tasks**:
- HF_TOKEN Railway env'га қўшиш
- mistral_engine.py HF Inference режимини тестлаш
- /api/assistant endpoints'да Mistral тугма қўшиш
**Success criteria**: Mistral AI endpoint ишлайди ва жавоб қайтаради

## Phase 9: Сайқаллаш функционал тест
**Goal**: Барча тугмалар, барча саҳифалар тест + learn-batch тасдиқлаш
**Status**: Not Started
**Priority**: 🔴 Critical
**Depends on**: All prior phases
**Key tasks**:
- Ҳар саҳифадаги Сайқаллаш тугмасини текшириш
- learn-batch эндпоинтни тестлаш (ўрганиш циклини тасдиқлаш)
- Ўлик (мёртвый) тугмаларни аниқлаш ва тузатиш
- E2E тест сценарийлар
**Success criteria**: Барча тугмалар ишлайди; ўрганиш цикли тасдиқланди

## Phase 10: Pharmacopoeia whitelist
**Goal**: 9,923 термин → Sayqallash "тўғри сўзлар" рўйхати (false-positive камайтириш)
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: —
**Key tasks**:
- annotated_words'дан term_uz чиқариш → sayqallash whitelist
- Hunspell кастом луғатга қўшиш
- False-positive тестлаш (фарм. терминлар хатолик сифатида кўрсатилмаслиги)
**Success criteria**: Фарм. терминлар Sayqallash'да хатолик сифатида кўринмайди

## Phase 11: PROMT ресурсларни Railway'да seed
**Goal**: Админ панелдаги "🔤 PROMT ресурслар" тугмаси production'да ишлаши
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: —
**Key tasks**:
- import_promt_resources.py production'да тестлаш
- TMX (184) + Abbrs (3,018) + Rules (36) + Translit (81) seed
- Идемпотентлик тасдиқлаш
**Success criteria**: PROMT ресурслар production'да муваффақиятли импорт

## Phase 12: Dual-script қолдиқлар
**Goal**: Дуал-скрипт қолдиқларни тузатиш (стиль regex, синонимлар, фронтенд)
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: Phase 2
**Key tasks**:
- style_rules regex'да дуал-скрипт pattern қўшиш
- Синонимлар дуал-скрипт сақлаш
- Фронтенд транслитерация тугмаси (глобал)
**Success criteria**: Барча поиск/фильтр Кирилл ва Latin'да ишлайди

## Phase 13: improve-row → analyze/full миграция
**Goal**: improve-row'ни analyze/full бирлаштириш (единый эндпоинт)
**Status**: Not Started
**Priority**: 🟢 Low
**Depends on**: Phase 0, Phase 1
**Key tasks**:
- /api/improve-row логикасини /api/analyze/full'га кўчириш
- TableEditor'да analyze/full чақириш
- Эски endpoint'ни deprecated қилиш
**Success criteria**: Барча текшириш бир эндпоинт орқали

## Phase 14: AI таржима батч (EN+RU тўлдириш)
**Goal**: 9,698 та annotated_words учун EN ва RU таржималарни AI билан тўлдириш
**Status**: Not Started
**Priority**: 🟡 Medium
**Depends on**: Phase 10
**Key tasks**:
- translate_annotated.py скриптини ишга тушириш
- Claude Haiku 4.5 батч таржима (UZ→EN, UZ→RU)
- Натижаларни annotated_words жадвалга сақлаш
- Сифат текшируви (рандом 100 та)
**Success criteria**: annotated_words'да term_en ва term_ru тўлдирилган (≥90%)
