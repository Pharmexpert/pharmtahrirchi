# REQUIREMENTS — Pharma Expert v4.1

## Functional Requirements

### FR-ATV: AnnotatedTextView Integration (Phase 0)
- FR-ATV-001: AnnotatedTextView LangCell (TableEditor) ичида ишлаши керак
- FR-ATV-002: /assistant саҳифасида AI javoblari AnnotatedTextView орқали кўринади
- FR-ATV-003: /paragraphs саҳифасида AnnotatedTextView интеграция
- FR-ATV-004: Tooltip 4 слой (sayqallash, syntax, style, morph) учун бирхил

### FR-STY: Style Guide Inline (Phase 1)
- FR-STY-001: 126 стилистик қоида розовая линия (#DB2777) билан
- FR-STY-002: USP/ICH/WHO/SI манба tooltip'да кўрсатилиши

### FR-TRL: Транслитерация (Phase 2)
- FR-TRL-001: 🔄 Кирилл↔Latin тугмаси edit/translate режимларда
- FR-TRL-002: dual_script_rules (81 қоида) ишлатилиши

### FR-NER: NER (Phase 3)
- FR-NER-001: drug_registry + annotated_words → whitelist
- FR-NER-002: Placeholder механизм таржима вақтида

### FR-POS: BERTbek POS (Phase 4)
- FR-POS-001: Янги NOUN/ADJ терминларни автомат аниқлаш
- FR-POS-002: Админ тасдиқи → DB қўшиш

### FR-WB: Workbench (Phase 5)
- FR-WB-001: 3 Monaco editor (UZ/RU/EN) + синхрон скролл
- FR-WB-002: TM% ҳар сатр ёнида

### FR-OCR: OCR (Phase 6)
- FR-OCR-001: Tesseract eng/rus/uzb → текст чиқариш
- FR-OCR-002: Авто-sayqallash OCR натижасига

### FR-QA: QA Lab (Phase 7)
- FR-QA-001: Back-translation текшируви
- FR-QA-002: Сегмент сони + рақам сақланиши

### FR-MIS: Mistral (Phase 8)
- FR-MIS-001: HF Inference API орқали Mistral-7B

### FR-TST: Функционал тест (Phase 9)
- FR-TST-001: Барча тугмалар ишлаши

### FR-WHL: Pharmacopoeia Whitelist (Phase 10)
- FR-WHL-001: 9,923 термин → sayqallash whitelist

### FR-PRM: PROMT Seed (Phase 11)
- FR-PRM-001: Production'да seed ишлаши

### FR-DSC: Dual-script (Phase 12)
- FR-DSC-001: Барча поиск dual-script

### FR-MIG: improve-row миграция (Phase 13)
- FR-MIG-001: Единый /api/analyze/full эндпоинт

### FR-BAT: AI батч таржима (Phase 14)
- FR-BAT-001: 9,698 термин UZ→EN+RU

## Non-Functional Requirements
- NFR-PERF-001: API < 500ms (кроме AI)
- NFR-PERF-002: AI таймаут 180с
- NFR-PERF-003: FAISS < 5ms
- NFR-SEC-001: JWT HS256 env var орқали
- NFR-SEC-002: CORS whitelist
- NFR-REL-001: Ежедневный бэкап 02:00
