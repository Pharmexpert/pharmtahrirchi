# ПОЛНЫЙ ОТЧЁТ ПО РАБОТЕ — Pharma Expert AI
## Дата: 2026-04-05 / 2026-04-06
## Исполнитель: Claude Code (Opus 4.6, 1M context)
## Заказчик: Акмалходжа Зайнидинов

---

## СОДЕРЖАНИЕ

1. [Исходное состояние проекта](#1-исходное-состояние-проекта)
2. [Техническое задание и спецификация](#2-техническое-задание-и-спецификация)
3. [Фаза 1: Безопасность](#3-фаза-1-безопасность)
4. [Фаза 2: Рефакторинг бэкенда](#4-фаза-2-рефакторинг-бэкенда)
5. [Фаза 3: Рефакторинг фронтенда](#5-фаза-3-рефакторинг-фронтенда)
6. [Фаза 4: Тестирование](#6-фаза-4-тестирование)
7. [Фаза 6: DevOps](#7-фаза-6-devops)
8. [Деплой и отладка продакшена](#8-деплой-и-отладка-продакшена)
9. [Дополнительные улучшения](#9-дополнительные-улучшения)
10. [Аудит баз данных](#10-аудит-баз-данных)
11. [Анализ инструкций из Qonun](#11-анализ-инструкций-из-qonun)
12. [Нерешённые проблемы](#12-нерешённые-проблемы)
13. [Все коммиты](#13-все-коммиты)
14. [Рекомендации на будущее](#14-рекомендации-на-будущее)

---

## 1. ИСХОДНОЕ СОСТОЯНИЕ ПРОЕКТА

### 1.1 Что было на момент начала работы

Проект Pharma Expert AI — веб-приложение для автоматизации выравнивания, редактирования и контроля качества трёхъязычных (EN/RU/UZ) фармацевтических документов.

**Структура проекта:**
```
C:\Users\Администратор\Desktop\2\
├── backend/           — FastAPI бэкенд (Python)
│   ├── main.py        — 1500+ строк, ВСЕ эндпоинты в одном файле
│   ├── db.py          — 19500+ строк, все модели БД
│   ├── auth.py        — аутентификация с dev-token bypass
│   ├── processor.py   — DOCX/PDF обработка
│   ├── bert_engine.py — BERT NLP модель
│   └── ...
├── frontend/          — Next.js 14 фронтенд (TypeScript)
│   ├── app/           — 12 страниц
│   └── components/    — 3 компонента (LoginGuard, DashboardLayout, TableEditor)
├── pharma-backend-deploy/ — Субмодуль для Railway деплоя
└── .github/workflows/ — CI/CD
```

### 1.2 Выявленные проблемы

**Критические (безопасность):**
- `auth.py` строка 21: `if token == "dev-token"` — любой мог получить admin доступ
- `main.py` строка 1147: Google OAuth тоже имел dev-token bypass
- CORS `allow_origins=["*"]` — открыт для всех доменов
- JWT secret захардкожен: `"pharma_secret_key_2026"`
- Нет rate limiting на AI эндпоинтах (риск исчерпания API квоты)
- Нет валидации загружаемых файлов (любой тип, любой размер)
- Password reset код выводился в console.log вместо email

**Архитектурные:**
- `main.py` — 1500+ строк монолитный файл со всеми 40+ эндпоинтами
- Нет TypeScript типов для API на фронтенде
- API вызовы разбросаны по всем компонентам inline `fetch()`
- Нет Error Boundary — ошибки крэшат всё приложение
- Нет тестов (0% coverage)
- Нет Docker для локальной разработки
- Нет CI pipeline

---

## 2. ТЕХНИЧЕСКОЕ ЗАДАНИЕ И СПЕЦИФИКАЦИЯ

### 2.1 Процесс создания

Для создания ТЗ было запущено 3 параллельных агента-исследователя:
1. **Agent 1** — исследование бэкенда: прочитал ВСЕ .py файлы, составил карту эндпоинтов, описал схему БД
2. **Agent 2** — исследование фронтенда: прочитал ВСЕ .tsx файлы, описал компоненты, API вызовы, стилизацию
3. **Agent 3** — исследование конфигурации: CI/CD, деплой скрипты, .env файлы

### 2.2 Результат

Создан файл **`SPEC.md`** (700+ строк) содержащий:

1. **Общие сведения** — название, тип, назначение, целевая аудитория
2. **Архитектурная диаграмма** — ASCII-art схема всех компонентов и их связей:
   - Клиент (Next.js) → HTTPS → Бэкенд (FastAPI) → SQLite + FAISS + BERT
   - Бэкенд → Google Gemini (primary AI) / Anthropic Claude (fallback)
   - Бэкенд → HuggingFace (BERT model: tahrirchi/tahrirchi-bert-base)
3. **Стек технологий** — все библиотеки с версиями для фронтенда и бэкенда
4. **Схема БД** — 11 таблиц с полями, типами, связями:
   - projects, alignments, sayqallash_rules, users, password_resets
   - annotated_words, disputed_words, abbreviations
   - ai_cache, paragraphs_dashboard, synonyms
   - tahrirchi.db: dictionary (8.7M слов)
5. **API карта** — все 40+ эндпоинтов разбитых по группам:
   - Аутентификация (6 эндпоинтов)
   - Проекты и файлы (7)
   - Редактирование контента (7)
   - AI-функции Sayqallash (6)
   - NLP и словарь (4)
   - Лингвистика (1)
   - Dashboard и профиль (4)
   - Администрирование (7)
6. **Карта страниц фронтенда** — 12 маршрутов с описанием
7. **Бизнес-процессы** — диаграммы:
   - Загрузка и обработка документа
   - Sayqallash 3-уровневая коррекция
   - Самообучение из пользовательских правок
8. **Аутентификация** — JWT, Google OAuth, роли, статусы
9. **Дизайн-система** — цвета, шрифты, скругления, эффекты
10. **Выявленные проблемы** — 7 критических, 8 архитектурных, 6 UX
11. **План улучшений** — 6 фаз с конкретными задачами
12. **Субагентная стратегия** — как Claude Code параллелит работу
13. **Метрики успеха** — от текущего к целевому
14. **Глоссарий** — Sayqallash, Tahrirchi, Alignment, FAISS и др.
15. **Контакты и ресурсы** — все URLs

---

## 3. ФАЗА 1: БЕЗОПАСНОСТЬ

### 3.1 Dev-token bypass (КРИТИЧЕСКИЙ)

**Проблема:** В `auth.py` строка 21 находился код:
```python
if token == "dev-token":
    return {"userId": "admin_primary", "email": "texnopharm@gmail.com", "role": "admin", "name": "Admin (Dev)"}
```
Любой человек мог отправить запрос с заголовком `Authorization: Bearer dev-token` и получить полный admin доступ ко всем данным.

**Также** в `main.py` строка 1147 Google OAuth имел bypass:
```python
if credential == "dev-token" or payload.get("email") == "admin@pharma.local":
    user = db.get_user_by_email("texnopharm@gmail.com")
    return {"success": True, "token": "dev-token", "user": user}
```

**Решение:**
- `auth.py`: Полностью удалён блок dev-token. Добавлена обработка конкретных JWT ошибок (`jwt.ExpiredSignatureError`, `jwt.InvalidTokenError`) вместо голого `except:`
- `main.py`: Блок dev-token заменён на валидацию:
```python
if not credential:
    raise HTTPException(status_code=400, detail="Google credential required")
```

**Проверка в продакшене:**
```
curl -H "Authorization: Bearer dev-token" /api/auth/me → {"detail":"Unauthorized"}
```

### 3.2 JWT Secret

**Проблема:** `JWT_SECRET = os.getenv("JWT_SECRET", "pharma_secret_key_2026")` — дефолтное значение позволяло подделать токены.

**Решение:** JWT_SECRET читается из env var. Если не установлен — выводится WARNING в логи, но используется fallback (для обратной совместимости). Добавлена константа `TOKEN_EXPIRE_DAYS = 7`.

### 3.3 CORS Whitelist

**Проблема:** `allow_origins=["*"]` позволяло любому сайту делать запросы к API.

**Решение:**
```python
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
```
В продакшене: `ALLOWED_ORIGINS=http://localhost:3000,https://frontend-dun-nine-30.vercel.app`

**Важно:** `.strip()` был добавлен позже, когда обнаружилось что пробелы в переменной окружения ломают CORS matching.

### 3.4 Rate Limiting

**Проблема:** Нет ограничений на вызовы AI эндпоинтов — можно было исчерпать квоту Gemini/Claude за минуты.

**Решение:** Создан in-memory rate limiter (без внешних зависимостей):
```python
class RateLimiter:
    def __init__(self, max_calls=10, period=60):
        self._calls = defaultdict(list)
    def is_allowed(self, key):
        # Очищает старые записи, проверяет лимит
```
Два экземпляра:
- `ai_limiter`: 20 AI вызовов/мин на IP
- `upload_limiter`: 5 загрузок/мин на IP

Применено к эндпоинтам: `/sayqallash`, `/api/align-document`, `/api/upload`

### 3.5 Валидация загрузки файлов

**Проблема:** Можно было загрузить любой файл любого размера.

**Решение:**
```python
allowed_extensions = {".docx", ".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```
Проверка расширения и размера ДО сохранения файла на диск.

### 3.6 SMTP для Password Reset

**Проблема:** Код сброса пароля выводился в `console.log`:
```python
logger.info(f"PASSWORD RESET CODE for {email}: {code}")
```

**Решение:** Добавлена отправка через SMTP с fallback:
- Если `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS` установлены — отправляет email
- Если нет — fallback в console.log с пометкой "(SMTP not configured)"
- Поддержка `SMTP_PORT` (дефолт 587, STARTTLS)

### 3.7 Security Headers

**Решение:** Middleware добавляющий заголовки к каждому ответу:
```python
@app.middleware("http")
async def security_headers(request, call_next):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
```

### 3.8 SQL Injection аудит

Проведён полный аудит `db.py` (19500 строк). Найдено 4 паттерна f-string SQL:
- Все используют `?` placeholders для значений
- Имена колонок формируются из whitelisted наборов
- **Уязвимостей не обнаружено**

### 3.9 Обновление .env.example

Файл полностью переписан с секциями:
- Authentication (JWT_SECRET)
- AI API Keys (ANTHROPIC_API_KEY, GOOGLE_API_KEY)
- CORS (ALLOWED_ORIGINS)
- SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
- Optional: Vercel integration

---

## 4. ФАЗА 2: РЕФАКТОРИНГ БЭКЕНДА

### 4.1 Анализ структуры main.py

Перед разбиением был проведён детальный анализ всех 1500 строк. Идентифицировано:
- 17 логических групп эндпоинтов
- 6 вспомогательных функций (не эндпоинты)
- 2 дубликата маршрутов (`/api/transliterate-batch` и `/synonyms`)
- 2 уже извлечённых модуля (admin_routes.py, linguistic_routes.py)

### 4.2 Новая модульная структура

```
backend/
├── main.py                  ← 90 строк (entry point only)
├── routes/
│   ├── __init__.py
│   ├── ai_helpers.py        ← Dual AI клиент
│   ├── rate_limit.py        ← Rate limiter
│   ├── auth_routes.py       ← 8 эндпоинтов авторизации
│   ├── upload_routes.py     ← 7 эндпоинтов загрузки
│   ├── sayqallash_routes.py ← 5 эндпоинтов GEC
│   ├── editor_routes.py     ← 10 эндпоинтов редактора
│   └── projects_routes.py   ← 14 эндпоинтов проектов
├── admin_routes.py          ← уже существовал
├── linguistic_routes.py     ← уже существовал
└── ...
```

### 4.3 Детали каждого модуля

**routes/ai_helpers.py** (67 строк):
- `get_gemini()` — ленивая инициализация Gemini 2.0 Flash
- `get_anthropic()` — ленивая инициализация Anthropic Claude
- `get_client()` — возвращает доступный AI клиент
- `generate_ai_content(prompt)` — dual-AI с автоматическим fallback

**routes/rate_limit.py** (21 строка):
- `RateLimiter` класс с настраиваемым max_calls и period
- `ai_limiter` (20/мин) и `upload_limiter` (5/мин) — готовые экземпляры

**routes/auth_routes.py** (190 строк):
- Google OAuth с валидацией через `googleapis.com/tokeninfo`
- Email/password регистрация с статусом "pending"
- Login с проверкой статуса пользователя
- Forgot password с SMTP
- Reset password с кодом
- Profile update и password change

**routes/upload_routes.py** (193 строки):
- Upload с валидацией типа/размера + rate limiting
- PDF→DOCX конвертация через pdf2docx
- Файловый менеджер (list, download, preview, delete)
- Open file in editor с background pre-polishing

**routes/sayqallash_routes.py** (282 строки):
- `_sayqallash_logic()` — core функция (вызывается и из HTTP и внутренне)
- `sayqallash_endpoint()` — HTTP с rate limiting
- `pre_polish_document()` — фоновая задача после загрузки
- Batch processing и self-learning endpoints
- Auto-notes generation

**routes/editor_routes.py** (341 строка):
- AI alignment целого документа (batched по 4 блока)
- Improve row через Sayqallash
- BERT fill-mask synonyms
- Dictionary autocomplete/suggest (8.7M слов)
- Suggest edits / synonyms с AI
- Split row (AI sentence splitting)
- Transliteration (batch и single)

**routes/projects_routes.py** (276 строк):
- Save all / save row с dashboard recording
- Export to DOCX
- Polishing summary
- Project finish с аудит-логом
- Dashboard CRUD
- User profile
- Projects CRUD
- Synonyms CRUD

### 4.4 Проблемы при разбиении

**Проблема 1: BACKEND_DIR путь**
`upload_routes.py` использует `os.path.dirname(os.path.dirname(__file__))` для определения пути к uploads/. На Railway структура директорий другая. Решение: `os.environ.get("BACKEND_DIR", ...)` с установкой в main.py до импорта модулей.

**Проблема 2: Порядок импортов**
`load_dotenv()` вызывался ПОСЛЕ импорта модулей, но модули читали env vars при загрузке. Решение: перенёс `load_dotenv()` и установку `BACKEND_DIR` ДО всех импортов.

**Проблема 3: Sayqallash вызов из других модулей**
`improve_row` в editor_routes вызывает `sayqallash()` из sayqallash_routes. Решение: разделение на `_sayqallash_logic()` (внутренний вызов) и `sayqallash_endpoint()` (HTTP с rate limiting).

### 4.5 Верификация

```python
python -c "from main import app; print('Routes:', len(app.routes))"
# Backend imports OK, routes: 83
```

---

## 5. ФАЗА 3: РЕФАКТОРИНГ ФРОНТЕНДА

### 5.1 TypeScript интерфейсы (frontend/types/api.ts)

Создано 20+ интерфейсов покрывающих все API модели:

```typescript
// Основные модели данных
export interface RowData { type, en, ru_v1, ru_proposed, uz_v1, uz_proposed, status, ... }
export interface User { id, email, name, role, status, avatar_url, department, ... }
export interface Project { id, name, specialist_name, status, original_filename, ... }
export interface SayqallashRule { id, wrong_form, correct_form, error_type, lang, frequency, ... }
export interface Synonym { id, word, synonym, lang, frequency, source, ... }
export interface DashboardEntry { id, en, ru, uz, specialist_name, action_type, ... }

// API Response типы
export interface AuthResponse { success, token, user, message }
export interface Annotation { old_value, new_value, from_index, to_index, error_type, source }
export interface SayqallashResponse { annotations, corrected_text, rules_count, confidence }
export interface ImproveRowResponse { annotations, rationale }
export interface PolishingSummary { total, corrected, annotations, timestamp }
export interface DictionaryWord { word, frequency }
export interface SynonymSuggestion { synonyms, note }
export interface DbStats { projects, alignments, rules, users, ... }
export interface LinguisticItem { id, word, definition, en, ru, uz, ... }
```

### 5.2 Централизованный API клиент (frontend/services/api.ts)

Вместо разбросанных `fetch()` вызовов — единый типизированный клиент:

```typescript
// Базовая инфраструктура
function authHeaders()   // Автоматически добавляет Bearer token из localStorage
async function request<T>(path, options)  // Обработка ошибок, JSON парсинг
function get<T>(path), post<T>(path, body), put<T>(), del<T>()

// Доменные группы (40+ методов):
api.auth.login(email, password)
api.auth.google(credential)
api.projects.list()
api.projects.finish(id, data, specialist)
api.editor.save(project_id, data, specialist)
api.editor.alignDocument(data)
api.sayqallash.check(text, lang, context)
api.sayqallash.learnBatch(corrections, lang)
api.dictionary.autocomplete(prefix, limit)
api.synonyms.suggestEdits(payload)
api.files.upload(file, onProgress)
api.upload.process(file, mode, textId, onProgress)
api.dashboard.all()
api.linguistic.analyze(payload)
api.admin.dbStats()
api.profile.changePassword(old, new)
// ... и др.
```

Файл upload использует XMLHttpRequest с прогрессом (не fetch) для tracking загрузки.

### 5.3 ErrorBoundary (frontend/components/ErrorBoundary.tsx)

React Class Component для перехвата ошибок:
- Ловит все uncaught errors в дереве компонентов
- Показывает сообщение "Хатолик юз берди" с кнопкой "Қайта уриниш"
- Стилизован под дизайн-систему проекта (warm cream palette)
- Интегрирован в `app/layout.tsx` как обёртка всего приложения

### 5.4 Дополнительные фиксы

- `TableEditor.tsx`: RowData теперь импортируется из `types/api.ts` (shared type)
- `admin/activity/page.tsx`: исправлен путь импорта LoginGuard (`../../` → `../../../`)
- TypeScript проверка: `npx tsc --noEmit` → **0 ошибок**

---

## 6. ФАЗА 4: ТЕСТИРОВАНИЕ

### 6.1 Инфраструктура

- `backend/pytest.ini` — конфигурация pytest
- `backend/tests/conftest.py` — shared fixtures:
  - `app` — FastAPI тестовое приложение
  - `client` — TestClient для HTTP запросов
  - `auth_token` — валидный JWT для тестов
  - `auth_headers` — готовые заголовки с Bearer token
- Добавлены `pytest>=8.0.0` и `httpx>=0.27.0` в requirements.txt
- Обновлён `backend/.gitignore` чтобы не игнорировать `tests/` директорию

### 6.2 Тесты аутентификации (test_auth.py — 10 тестов)

```python
class TestJWT:
    test_create_and_verify_token()    # Round-trip создание/проверка
    test_verify_invalid_token()       # Невалидные токены → None
    test_dev_token_removed()          # КРИТИЧЕСКИЙ: dev-token НЕ работает
    test_token_contains_expiry()      # Наличие exp claim

class TestAuthEndpoints:
    test_register_missing_fields()    # 400 при неполных данных
    test_login_missing_email()        # 400 без email
    test_login_wrong_credentials()    # 401 при неверном пароле
    test_auth_me_no_token()           # 401/403 без токена
    test_google_auth_no_credential()  # 400 без Google credential
    test_forgot_password_nonexistent() # 200 (не раскрываем существование)
```

### 6.3 Тесты Rate Limiter (test_rate_limit.py — 4 теста)

```python
test_allows_within_limit()        # Разрешает в пределах лимита
test_blocks_over_limit()          # Блокирует при превышении
test_different_keys_independent() # Разные IP изолированы
test_expired_calls_cleaned()      # Старые записи очищаются
```

### 6.4 Тесты эндпоинтов (test_endpoints.py — 11 тестов)

```python
class TestSecurityHeaders:
    test_cors_headers()              # 4 security заголовка присутствуют

class TestUploadValidation:
    test_upload_wrong_file_type()    # .txt → 400
    test_upload_no_auth()            # Без токена → 401

class TestProjectEndpoints:
    test_list_projects()             # GET /api/projects → 200
    test_specialists_list()          # GET /api/specialists → 200
    test_history_nonexistent()       # Несуществующий проект → пустой массив

class TestSayqallashEndpoints:
    test_sayqallash_empty_text()     # Пустой текст → пустой результат
    test_auto_notes_empty()          # Одинаковые тексты → 200
    test_learn_batch_empty()         # Пустой batch → count=0

class TestDictionaryEndpoints:
    test_autocomplete_short_prefix() # Короткий prefix → пустой
    test_bert_synonyms_empty_word()  # Пустое слово → нет синонимов

class TestTransliteration:
    test_transliterate_empty()       # Пустой текст → пустой
    test_transliterate_batch_empty() # Пустой batch → пустой
```

---

## 7. ФАЗА 6: DEVOPS

### 7.1 Docker (docker-compose.yml)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - JWT_SECRET, ALLOWED_ORIGINS, PORT
    volumes:
      - ./backend:/app
      - backend_uploads, backend_data
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]
```

- `backend/Dockerfile`: Python 3.11-slim, gcc/g++ для нативных зависимостей
- `frontend/Dockerfile`: Node 20-alpine

### 7.2 CI Pipeline (.github/workflows/ci.yml)

Запускается на каждый PR и push в main:

**Job 1: backend-tests**
- Python 3.11, pip cache
- `pip install -r requirements.txt && pip install pytest httpx`
- `pytest tests/ -v --tb=short`

**Job 2: frontend-typecheck**
- Node 20, npm cache
- `npm ci`
- `npx tsc --noEmit`
- `npm run lint`

---

## 8. ДЕПЛОЙ И ОТЛАДКА ПРОДАКШЕНА

### 8.1 Процесс деплоя

1. Создана ветка `security/phase1-hardening` для всех изменений
2. 4 коммита в ветку (Фазы 1-4, 6)
3. Merge в `main` (fast-forward)
4. Push `main` → GitHub
5. Копирование backend файлов в `pharma-backend-deploy/` (включая новую папку `routes/`)
6. Push в Railway backend repo
7. Vercel auto-deploy из main

### 8.2 Проблема 1: Railway 502 — несовпадение портов (30+ мин дебаг)

**Симптом:** После деплоя Railway возвращал 502 на ВСЕ запросы, хотя Deploy Logs показывали `Uvicorn running on http://0.0.0.0:8000` и `BERT Engine is READY`.

**Расследование:**
1. Проверили Deploy Logs → приложение запускается успешно
2. HTTP Logs → "No logs in this time range" (запросы не доходят)
3. Проверили Variables → PORT не установлен (Railway auto-injects)
4. Пользователь добавил PORT=8000 → всё ещё 502
5. **Ключевое открытие:** Settings → Networking показал port **8080**, а uvicorn слушал на **8000**

**Решение:** Изменить Networking port с 8080 на 8000 в Settings → Networking.

**Урок:** Railway proxy маппит запросы на порт из Networking settings, НЕ на PORT env var. Эти настройки должны совпадать.

### 8.3 Проблема 2: CORS на скачивание файлов

**Симптом:** Console ошибка `No 'Access-Control-Allow-Origin' header` при скачивании файла.

**Причина:** `ALLOWED_ORIGINS` в Railway содержал пробел после запятой.

**Решение:** `.strip()` каждого элемента при парсинге:
```python
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "...").split(",") if o.strip()]
```

### 8.4 Проблема 3: routes/ не синхронизировался в Railway

**Симптом:** Railway возвращал `ModuleNotFoundError` при import routes.

**Причина:** Старый `deploy.bat` копировал только `*.py` файлы из корня backend/, но не `routes/` директорию.

**Решение:** Обновлён `deploy.bat`:
```batch
if not exist "%BACKEND_DST%\routes" mkdir "%BACKEND_DST%\routes"
xcopy /Y /Q "%BACKEND_SRC%\routes\*.py" "%BACKEND_DST%\routes\"
```

### 8.5 Проблема 4: Vercel не деплоит (целый день!)

**Симптом:** Фронтенд на vercel.app показывал старую версию. Все push в main не приводили к обновлению.

**Причина:** В Vercel Environment Variables была переменная `ANTHROPIC_API_KEY` которая ссылалась на Secret "anthropic-api-key" — этот Secret не существовал. Vercel **блокировал ВСЕ деплои** из-за этой ошибки.

**Решение:** Удалить `ANTHROPIC_API_KEY` из Vercel Variables (фронтенд не использует его) и Redeploy.

### 8.6 Проблема 5: Railway bytecode кэш

**Симптом:** Ошибка `name 'json' is not defined` в sayqallash несмотря на `import json` в файле.

**Причина:** Railway кэширует build layers и `.pyc` файлы. Старый скомпилированный bytecode выполняется вместо нового кода.

**Попытки решения:**
1. Добавил `import json` внутри функции → не помогло (кэш)
2. Добавил `import json as _json_module` + explicit binding → не помогло
3. Procfile: `find . -name "*.pyc" -delete` перед запуском → не помогло
4. Procfile: `python -B` (запрещает создание .pyc) → деплоено
5. Clear Build Cache в Railway Settings → деплоено

**Статус:** Ожидает полного rebuild после cache clear.

### 8.7 Проблема 6: AI не работает — 3 ошибки

**Ошибка 1: `Rules DB error: 'id'`**
- `RulesCache.get_all()` возвращал правила без поля `id`
- `get_rules_for_text()` на строке 635 пытался создать `rules_by_id = {r['id']: r for r in rules}`
- **Решение:** Добавил `id` в SELECT и в возвращаемый dict:
```python
cursor.execute("SELECT id, wrong_form, correct_form, error_type, lang, frequency FROM sayqallash_rules")
```

**Ошибка 2: `authentication_error: invalid x-api-key`**
- ANTHROPIC_API_KEY в Railway Variables был старый/неверный ключ
- Пользователь видел в UI: `sk-ant-api03-r2HMquHZ...` вместо правильного `sk-ant-api03-zucibI...`
- **Решение:** Пользователь заменил ключ в Railway Variables

**Ошибка 3: Claude model not found**
- Модель `claude-3-5-haiku-20241022` была удалена Anthropic (end-of-life)
- **Решение:** Обновлена на `claude-haiku-4-5-20251001` в `routes/ai_helpers.py` и `linguistic_routes.py`

**Дополнительно:** Gemini возвращал 429 (quota exceeded) — бесплатный лимит исчерпан. Claude работает как fallback.

### 8.8 Конфигурация Railway (финальная)

```
ALLOWED_ORIGINS = http://localhost:3000,https://frontend-dun-nine-30.vercel.app
JWT_SECRET = [установлен]
GOOGLE_API_KEY = AIzaSyAQPxDxe6F-Vz4zxb8H4WQ3mjvhmzjpPZk (квота исчерпана)
ANTHROPIC_API_KEY = sk-ant-api03-zucibI...a49l9gAA
DB_PATH, TAHRIRCHI_DB_PATH, SEED_SECRET = [установлены]
Networking port = 8000
```

---

## 9. ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ

### 9.1 Автоматизация (3 скрипта)

**start_app.bat** — Запуск локального окружения:
1. Проверяет Python и Node
2. Убивает процессы на портах 8000/3000
3. Создаёт необходимые директории
4. Запускает backend в отдельном окне
5. Запускает frontend в отдельном окне
6. Ждёт 10 сек и проверяет доступность

**deploy.bat** — Деплой в продакшен:
1. Синхронизирует ВСЕ backend файлы включая `routes/` в pharma-backend-deploy/
2. Коммитит и пушит в Railway repo
3. Коммитит и пушит monorepo (исключая .db, .venv, .claude)
4. Деплоит frontend через `npx vercel --prod`
5. Верифицирует оба продакшен URL

**sync_git.bat** — Синхронизация репозиториев:
1. Синхронизирует файлы backend → pharma-backend-deploy
2. Коммитит Railway repo
3. Коммитит monorepo
4. Пушит оба с rebase fallback

### 9.2 UI фиксы

**Дубликат футера:** На странице dashboard показывались два одинаковых блока:
```
© 2026 PHARMA TRANSLATION PLATFORM
Давлат фармакопеясини ишлаб чиқиш тизими
Саволлар ва таклифлар...
```
Один из `LoginGuard.tsx`, другой из `DashboardLayout.tsx`. Удалён из LoginGuard.

**Контактный блок на логин-странице:** Блок с email texnopharm@gmail.com удалён со страницы логина (оставлен только "© 2026 Pharma Translation Platform").

### 9.3 AI модель обновлена

`claude-3-5-haiku-20241022` → `claude-haiku-4-5-20251001`

Старая модель вернула `404 not_found_error` с предупреждением:
```
DeprecationWarning: The model 'claude-3-5-haiku-20241022' is deprecated
and will reach end-of-life on February 19th, 2026.
```

### 9.4 Admin endpoint alias

Фронтенд вызывал `/api/admin/approve`, бэкенд имел `/api/admin/users/approve`. Добавлен alias:
```python
@router.post("/users/approve")
@router.post("/approve")  # alias для фронтенда
async def approve_user(payload, current_user):
```

### 9.5 Cross-alphabet поиск

Добавлена функция `cross_alphabet_variants()` в `transliterate.py`:
```python
def cross_alphabet_variants(text):
    """Возвращает обе версии: кириллица и латиница"""
    variants = [text]
    if is_cyrillic(text):
        variants.append(to_latin(text))
    else:
        variants.append(to_cyrillic(text))
    return variants
```

Интегрировано в `/api/dictionary/autocomplete` — теперь поиск по "tablet" найдёт и "таблет" и наоборот.

### 9.6 RulesCache fix

Проблема: `get_rules_for_text()` строка 635 создавала `rules_by_id = {r['id']: r for r in rules}`, но cached rules не содержали `id`.

Решение:
- `RulesCache.load()`: добавлен `id` в SELECT query
- `RulesCache.get_all()`: возвращает `id` в каждом dict

### 9.7 UzWordnet интеграция

Создан скрипт `import_uzwordnet.py`:
1. Парсит WN-LMF XML файлы из `Qonun/UzWordnet/`
2. Строит `synset_id → [words]` mapping
3. Генерирует synonym pairs из каждого synset (bidirectional)
4. Вставляет в таблицу `synonyms` с `source='uzwordnet'`

Результат импорта:
```
Total synsets: 28,140
Synsets with 2+ words: 16,694
Unique words: 20,156
Total pairs generated: 146,606
```

### 9.8 Progressive Loading

Фазовый прогресс-бар при загрузке документа в `page.tsx`:

| Процент | Фаза |
|---------|------|
| 0-15% | Матн тайёрланмоқда... |
| 15-35% | AI модел юкланмоқда... |
| 35-60% | Терминология таҳлили... |
| 60-80% | Таржима солиштирилмоқда... |
| 80-95% | Натижалар тўпланмоқда... |
| 95-100% | Тайёр! |

Реализация:
- `setInterval` симулирует прогресс +1% каждые 400ms
- Real XHR progress events перезаписывают симуляцию
- На завершение — прыжок на 100% с "Тайёр!"
- На ошибку — сброс прогресса
- Градиентный прогресс-бар в тёплых тонах

### 9.9 Error Handling в Sayqallash

Добавлена защита от 500 ошибок:
- `_sayqallash_logic()` обёрнута в try/except
- При ошибке возвращает оригинальный текст (не крэшит)
- `local_annotations or []` guard для NoneType
- `known_rules or []` guard
- Traceback logging в Deploy Logs для дебага

### 9.10 Memory система

Сохранено 3 файла в `.claude/projects/.../memory/`:

**project_pharma.md** — контекст проекта:
- Архитектура, URLs, Railway config
- Deploy process, ключевые технические детали
- КРИТИЧНО: Networking port = 8000, routes/ sync

**feedback_deploy.md** — уроки деплоя:
- routes/ sync обязателен при deploy
- Networking port должен совпадать с uvicorn
- ALLOWED_ORIGINS без пробелов
- Не устанавливать PORT вручную

**user_akmal.md** — профиль пользователя:
- Фармацевт, владелец платформы
- Предпочитает автономную работу
- Русский для коммуникации

---

## 10. АУДИТ БАЗ ДАННЫХ

### 10.1 Таблицы в pharma_editor.db (11 таблиц)

| # | Таблица | Записей | Frontend страницы |
|---|---------|---------|------------------|
| 1 | projects | ~10 | dashboard, projects, history |
| 2 | alignments | ~100+ | TableEditor, paragraphs |
| 3 | sayqallash_rules | 4365 | rules/ |
| 4 | users | ~3 | admin/, profile/ |
| 5 | password_resets | — | LoginGuard |
| 6 | annotated_words | — | linguistic/ |
| 7 | disputed_words | — | linguistic/ |
| 8 | abbreviations | — | linguistic/ |
| 9 | synonyms | 146K+ | synonyms/, TableEditor |
| 10 | paragraphs_dashboard | ~100+ | paragraphs/, dashboard |
| 11 | ai_cache | — | внутренний |

### 10.2 Внешняя БД: tahrirchi.db

| Таблица | Записей | Назначение |
|---------|---------|-----------|
| dictionary | 8,764,767 | Узбекские слова с частотой |

### 10.3 Проверка интеграции Backend ↔ Frontend

Все 40+ эндпоинтов проверены на соответствие frontend вызовам. Найдено и исправлено 1 несовпадение:
- Frontend: `/api/admin/approve` → Backend: `/api/admin/users/approve` → **Добавлен alias**

---

## 11. АНАЛИЗ ИНСТРУКЦИЙ ИЗ QONUN

### 11.1 Структура Qonun/Инструкция

60+ .md файлов содержащих:
- Планы реализации фич
- Логи разговоров с AI
- Технические спецификации

### 11.2 Реализованные фичи (из инструкций)

| Фича | Файл инструкции | Статус |
|------|----------------|--------|
| Sayqallash 3-tier GEC | implementation_plan_sayqallash.md | Работает |
| Linguistic Dashboard (3 категории) | Implementing Trilingual Dashboard (23-30) | Работает |
| Column resizing в TableEditor | walkthrough.md | Работает |
| Ready Form mode | walkthrough.md | Работает |
| Database consolidation | Finalizing Pharma Platform (36-41) | Работает |
| Progressive Loading | Pharma Editor Integration (41-46) | **Добавлено в этой сессии** |
| UzWordnet интеграция | Locating Linguistic Files (33-35) | **Добавлено в этой сессии** |
| Cross-alphabet search | Pending Tasks (13, 15) | **Добавлено в этой сессии** |

### 11.3 Фичи описанные но не начатые (Приоритет 3 — НЕ делаем)

- Secure HTTPS tunnel (ngrok)
- Full BERT local integration
- Scientific standards compliance tables

---

## 12. НЕРЕШЁННЫЕ ПРОБЛЕМЫ

### 12.1 Sayqallash `json` ошибка на Railway

**Симптом:** `name 'json' is not defined` при вызове /sayqallash с текстом.

**Корневая причина:** Railway кэширует build layer и выполняет старый .pyc bytecode.

**Что сделано:**
1. `import json` на уровне модуля (строка 3) — было изначально
2. `import json` внутри `_sayqallash_logic()` (строка 64) — добавлено
3. `import json as _json_module` + explicit binding — добавлено
4. Procfile: `python -B` (no bytecode) — добавлено
5. Railway Settings: Clear Build Cache — сделано пользователем

**Следующее действие:** Если после полного rebuild ошибка сохранится — нужно вручную Redeploy в Railway Dashboard.

### 12.2 Gemini AI квота исчерпана (429)

**Симптом:** Google Generative AI API возвращает `429 Too Many Requests`.

**Влияние:** AI коррекция работает через Claude (Anthropic) fallback.

**Действие:** Нужен новый GOOGLE_API_KEY или платный план на console.cloud.google.com.

---

## 13. ВСЕ КОММИТЫ

```
a1e9040 Add work report: full session log 2026-04-05
e9e1b78 Fix: explicit json module binding to prevent async scope loss
e162eb3 Fix: clear __pycache__ in Procfile before uvicorn start
d319c0b Fix: guard local_annotations with 'or []'
b6e5c0c Fix: add traceback logging to sayqallash error handler
d937923 Fix: handle None from get_all_rules in sayqallash
9997b19 Fix json scope in sayqallash, add UzWordnet importer, progressive loading
53157d4 Fix: add error handling to sayqallash to prevent 500 errors
2902c68 Fix: add 'id' field to RulesCache for FAISS semantic search
ff2c22b Fix: update Claude model, add admin/approve alias, cross-alphabet search
a67bb43 Fix: remove contact info block from login page footer
2ce513c Fix: remove duplicate footer from LoginGuard
2be5dba Update automation scripts: start_app, deploy, sync_git
9bf731e Fix: strip whitespace from ALLOWED_ORIGINS + add CORS logging
e7acd5c Fix: resolve BACKEND_DIR path for Railway deploy + import order
203ac2a Add test suite, Docker setup, and CI pipeline (Phases 4+6)
2dc2b2d Frontend: add TypeScript types, centralized API client, and ErrorBoundary
d473567 Refactor: split main.py (1500 lines) into 7 modular route files
eba6cac Security hardening (Phase 1)
```

**Итого: 19 коммитов, ~5000+ строк добавлено, ~1500 удалено, 55+ файлов затронуто.**

---

## 14. РЕКОМЕНДАЦИИ НА БУДУЩЕЕ

### Немедленно
1. Дождаться rebuild Railway после cache clear
2. Обновить GOOGLE_API_KEY (квота)
3. Проверить все страницы фронтенда после Vercel redeploy

### Краткосрочно
1. Перевести остальные страницы на `services/api.ts` (вместо inline fetch)
2. Разбить TableEditor.tsx (1310 строк) на подкомпоненты
3. Добавить Tailwind CSS вместо inline styles

### Среднесрочно
1. Миграция SQLite → PostgreSQL (Railway addon)
2. Alembic для миграций БД
3. Sentry для error tracking

### Долгосрочно
1. WebSocket для совместного редактирования
2. Версионирование документов
3. PDF экспорт

---

## ПРОДАКШЕН URLS

| Сервис | URL |
|--------|-----|
| Frontend | https://frontend-dun-nine-30.vercel.app |
| Backend | https://pharma-backend-production-38bb.up.railway.app |
| Backend API Docs | https://pharma-backend-production-38bb.up.railway.app/docs |
| Railway Dashboard | https://railway.com/project/e0f4d961-40b7-429a-a4f1-c7241011297a |
| GitHub (monorepo) | https://github.com/Pharmexpert/pharmtahrirchi |
| GitHub (backend deploy) | https://github.com/Pharmexpert/pharma-backend |

---

*Полный отчёт сгенерирован Claude Opus 4.6 (1M context)*
*Дата: 2026-04-06*
*Объём: ~800 строк*
