# ТЕХНИЧЕСКОЕ ЗАДАНИЕ И СПЕЦИФИКАЦИЯ
# Pharma Aligner — Трёхъязычный редактор фармацевтических документов

> **Версия:** 2.0
> **Дата:** 2026-04-05
> **Проект:** `C:\Users\Администратор\Desktop\2`
> **Статус:** Действующий продукт, требуется усовершенствование

---

## ЧАСТЬ I. ТЕХНИЧЕСКОЕ ЗАДАНИЕ (ТЗ)

---

### 1. ОБЩИЕ СВЕДЕНИЯ

| Параметр | Значение |
|----------|----------|
| **Название продукта** | Pharma Aligner (Фарма-редактор) |
| **Тип** | Веб-приложение (SPA + REST API) |
| **Назначение** | Автоматизация выравнивания, редактирования и контроля качества трёхъязычных (EN/RU/UZ) фармацевтических документов |
| **Целевая аудитория** | Специалисты-переводчики, редакторы фармацевтической документации, администраторы качества |
| **Домен** | Фармацевтическая промышленность, стандарты ГФ, USP, Ph. Eur. |

---

### 2. ТЕКУЩАЯ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────────────┐
│                        КЛИЕНТ (БРАУЗЕР)                        │
│  Next.js 14 (App Router) · React 18 · TypeScript · Lucide     │
│  Vercel: frontend-dun-nine-30.vercel.app                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST
┌──────────────────────────▼──────────────────────────────────────┐
│                     БЭКЕНД (PYTHON)                            │
│  FastAPI 0.135 · Uvicorn · JWT Auth · CORS                     │
│  Railway: pharma-backend-production-38bb.up.railway.app        │
├────────────────────────────────────────────────────────────────-┤
│  МОДУЛИ:                                                       │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ processor.py│ │ bert_engine  │ │ sayqallash (3-tier)     │  │
│  │ DOCX/PDF    │ │ tahrirchi-   │ │ Rules DB → AI → BERT    │  │
│  │ alignment   │ │ bert-base    │ │ Gemini + Claude fallback│  │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘  │
├────────────────────────────────────────────────────────────────-┤
│  ХРАНИЛИЩЕ:                                                    │
│  ┌──────────────────┐  ┌───────────────────────────────────┐   │
│  │ pharma_editor.db │  │ tahrirchi.db (8.7M слов)          │   │
│  │ SQLite            │  │ Словарь узбекского языка           │   │
│  └──────────────────┘  └───────────────────────────────────┘   │
│  FAISS Index (in-memory) · AI Cache (TTL) · Rules Cache (5m)  │
└────────────────────────────────────────────────────────────────┘
          │                    │                    │
   ┌──────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
   │ Google AI   │    │ Anthropic    │    │ HuggingFace  │
   │ Gemini 2.0  │    │ Claude 3.5   │    │ BERT Model   │
   │ (primary)   │    │ (fallback)   │    │ tahrirchi-   │
   │             │    │ Haiku        │    │ bert-base    │
   └─────────────┘    └──────────────┘    └──────────────┘
```

---

### 3. СТЕК ТЕХНОЛОГИЙ

#### 3.1 Фронтенд
| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Фреймворк | Next.js (App Router, CSR) | 14.1.0 |
| UI-библиотека | React | ^18.2.0 |
| Язык | TypeScript (strict) | ES5 target |
| Иконки | Lucide React | ^0.344.0 |
| Excel-экспорт | xlsx | ^0.18.5 |
| Стилизация | CSS Variables + inline styles | - |
| i18n | Object maps (UZ/EN/RU) | Кастомный |
| Хостинг | Vercel | - |

#### 3.2 Бэкенд
| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Фреймворк | FastAPI | 0.135.1 |
| Сервер | Uvicorn | 0.41.0 |
| Аутентификация | PyJWT (HS256, 7 дней) | 2.9.0 |
| AI (primary) | Google Generative AI (Gemini 2.0 Flash) | 0.8.6 |
| AI (fallback) | Anthropic (Claude 3.5 Haiku) | >=0.25.0 |
| NLP | Transformers (BERT fill-mask) | 5.4.0 |
| Векторный поиск | FAISS CPU | 1.13.2 |
| DOCX | python-docx | 1.2.0 |
| PDF→DOCX | pdf2docx | 0.5.12 |
| База данных | SQLite | Встроенная |
| Хостинг | Railway | - |

#### 3.3 CI/CD и деплой
| Компонент | Технология |
|-----------|-----------|
| Фронтенд деплой | Vercel CLI (`npx vercel --prod`) |
| Бэкенд деплой | Git push → Railway |
| CI/CD | GitHub Actions (Node 20) |
| Оркестрация | `deploy.bat` (Windows batch) |
| VCS | Git (monorepo) |

---

### 4. БАЗА ДАННЫХ — СХЕМА

#### 4.1 pharma_editor.db (основная)

```
┌─────────────────────┐     ┌──────────────────────────┐
│       users          │     │        projects           │
├─────────────────────┤     ├──────────────────────────┤
│ id TEXT PK           │◄───┤ user_id TEXT FK           │
│ email TEXT UNIQUE    │     │ id TEXT PK               │
│ name TEXT            │     │ name TEXT                │
│ role TEXT            │     │ specialist_name TEXT      │
│ status TEXT          │     │ status TEXT              │
│ password_hash TEXT   │     │ original_filename TEXT    │
│ salt TEXT            │     │ file_path TEXT           │
│ avatar_url TEXT      │     │ source_lang TEXT         │
│ department TEXT      │     │ created_at TIMESTAMP     │
│ last_login TIMESTAMP │     │ updated_at TIMESTAMP     │
│ created_at TIMESTAMP │     └──────────┬───────────────┘
└─────────────────────┘                 │
                                        │ 1:N
┌───────────────────────────────────────▼───────────────┐
│                    alignments                          │
├────────────────────────────────────────────────────────┤
│ id INTEGER PK AUTO                                     │
│ sentence_no INTEGER · display_no TEXT                   │
│ row_type TEXT ('marker'|'content')                      │
│ text_id TEXT · specialist_name TEXT · user_id TEXT       │
│ en_text TEXT · confirmed_ru_text TEXT · confirmed_uz_text│
│ ru_proposed TEXT · uz_proposed TEXT                      │
│ ru_annotations TEXT (JSON) · uz_annotations TEXT (JSON)  │
│ ru_confidence REAL · uz_confidence REAL                  │
│ is_pre_polished INTEGER · notes TEXT                    │
│ created_at TIMESTAMP                                    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────┐  ┌──────────────────────────┐
│     sayqallash_rules       │  │     paragraphs_dashboard  │
├────────────────────────────┤  ├──────────────────────────┤
│ id INTEGER PK              │  │ id INTEGER PK            │
│ wrong_form TEXT             │  │ text_id TEXT             │
│ correct_form TEXT           │  │ sentence_no INTEGER      │
│ error_type TEXT             │  │ en TEXT · ru TEXT · uz TEXT│
│ context TEXT                │  │ specialist_name TEXT      │
│ lang TEXT (uz/ru)           │  │ action_type TEXT          │
│ frequency INTEGER           │  │ notes TEXT               │
│ source TEXT                 │  │ created_at TIMESTAMP     │
│ vector BLOB (BERT embed)    │  └──────────────────────────┘
│ modified_by TEXT            │
│ created_at · updated_at    │  ┌──────────────────────────┐
└────────────────────────────┘  │       synonyms            │
                                 ├──────────────────────────┤
┌────────────────────────────┐  │ id INTEGER PK            │
│    annotated_words         │  │ word TEXT · synonym TEXT  │
├────────────────────────────┤  │ lang TEXT                │
│ id · word · definition     │  │ frequency INTEGER        │
│ en/ru/uz translations      │  │ source TEXT (ai/user)    │
│ source_lang · user_id      │  │ created_by TEXT          │
│ text_id · status           │  │ created_at TIMESTAMP     │
│ modified_by_id             │  └──────────────────────────┘
└────────────────────────────┘
                                 ┌──────────────────────────┐
┌────────────────────────────┐  │      ai_cache             │
│    disputed_words          │  ├──────────────────────────┤
├────────────────────────────┤  │ key TEXT PK              │
│ (same schema as annotated) │  │ result TEXT (JSON)       │
│ + context-heavy meanings   │  │ created_at TIMESTAMP     │
└────────────────────────────┘  │ ttl INTEGER              │
                                 └──────────────────────────┘
┌────────────────────────────┐
│     abbreviations          │  ┌──────────────────────────┐
├────────────────────────────┤  │    password_resets        │
│ (same schema as annotated) │  ├──────────────────────────┤
│ + acronym expansions       │  │ email · code · expires_at│
└────────────────────────────┘  └──────────────────────────┘
```

#### 4.2 tahrirchi.db (лингвистическая)
| Таблица | Записей | Назначение |
|---------|---------|-----------|
| dictionary | ~8,700,000 | Узбекские слова с частотой |
| terms | - | Термины |
| corrections | - | Исправления |
| sessions | - | Сессии проверки |
| confirmed_words | - | Подтверждённые слова |

---

### 5. API — ПОЛНАЯ КАРТА ЭНДПОИНТОВ

#### 5.1 Аутентификация
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/api/auth/register` | - | Регистрация (статус pending) |
| POST | `/api/auth/login` | - | Вход по email/пароль |
| POST | `/api/auth/google` | - | Google OAuth |
| GET | `/api/auth/me` | Bearer | Текущий пользователь |
| POST | `/api/auth/forgot-password` | - | Запрос кода сброса |
| POST | `/api/auth/reset-password` | - | Сброс пароля |

#### 5.2 Проекты и файлы
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/api/upload` `/api/upload-docx` | Bearer | Загрузка DOCX/PDF |
| GET | `/api/projects` | Bearer | Список проектов |
| DELETE | `/api/projects/{id}` | Bearer | Удаление проекта |
| POST | `/api/projects/{id}/finish` | Bearer | Завершение проекта |
| GET | `/api/projects/{id}/export` | Bearer | Экспорт в DOCX |
| GET | `/api/projects/{id}/preview` | Bearer | Превью (top 50) |
| GET | `/api/projects/{id}/polishing-summary` | Bearer | Сводка полировки |

#### 5.3 Редактирование контента
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/api/save` | Bearer | Сохранить все строки |
| POST | `/api/save-row` | Bearer | Сохранить одну строку |
| DELETE | `/api/delete-row/{text_id}/{no}` | Bearer | Удалить строку |
| POST | `/api/split-row` | - | AI-разделение строки |
| GET | `/api/history/{text_id}` | - | История проекта |
| GET | `/api/alignments/{text_id}` | - | Данные выравнивания |
| GET | `/api/specialists` | - | Список специалистов |

#### 5.4 AI-функции (Sayqallash)
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/sayqallash` | - | 3-tier коррекция текста |
| POST | `/api/sayqallash/batch` | - | Пакетная коррекция |
| POST | `/api/sayqallash/learn-batch` | - | Самообучение из правок |
| POST | `/api/align-document` | - | AI-выравнивание документа |
| POST | `/api/improve-row` | - | Улучшение одной строки |
| POST | `/api/auto-notes` | - | Генерация diff-заметок |
| POST | `/suggest-edits` | - | AI-предложения правок |
| POST | `/synonyms` | - | AI-синонимы |

#### 5.5 NLP и словарь
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/api/bert/synonyms` | - | BERT fill-mask синонимы |
| POST | `/api/dictionary/autocomplete` | - | Автодополнение (8.7M слов) |
| POST | `/api/dictionary/suggest` | - | Орфографические подсказки |
| POST | `/api/transliterate-batch` | - | Кириллица ↔ Латиница |

#### 5.6 Лингвистика
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| POST | `/api/linguistic/analyze` | Bearer | Анализ терминов, спорных слов, аббревиатур |

#### 5.7 Dashboard и профиль
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| GET | `/api/dashboard/all` | Bearer | Все записи дашборда |
| POST | `/api/dashboard/record` | Bearer | Записать событие |
| GET | `/api/user/me` | Bearer | Профиль пользователя |
| PUT | `/api/user/me` | Bearer | Обновить профиль |

#### 5.8 Администрирование
| Метод | Эндпоинт | Авторизация | Описание |
|-------|----------|-------------|----------|
| GET | `/api/admin/rules` | Admin | Список правил |
| POST | `/api/admin/rules` | Admin | Добавить правило |
| DELETE | `/api/admin/rules/{id}` | Admin | Удалить правило |
| GET | `/api/admin/rules/export` | Admin | Экспорт правил в XLSX |
| POST | `/api/admin/rules/batch` | Secret | Массовый посев правил |
| GET | `/api/admin/db-stats` | Admin | Статистика БД |
| GET | `/api/admin/stats` | Admin | Legacy статистика |

---

### 6. ФРОНТЕНД — КАРТА СТРАНИЦ

| Маршрут | Компонент | Назначение |
|---------|----------|-----------|
| `/` | page.tsx + TableEditor | Загрузка документа + главный редактор |
| `/dashboard` | dashboard/page.tsx | Обзор: статистика, быстрая загрузка, недавние проекты |
| `/projects` | projects/page.tsx | Список всех проектов с поиском и фильтрами |
| `/files` | files/page.tsx | Файловый менеджер: просмотр, скачивание, удаление |
| `/paragraphs` | paragraphs/page.tsx | База параграфов: поиск, инлайн-редактирование, экспорт |
| `/history` | history/page.tsx | Хронология проектов |
| `/linguistic/[category]` | linguistic/[category]/page.tsx | Энциклопедия: annotated / disputed / abbreviations |
| `/synonyms` | synonyms/page.tsx | База синонимов (UZ/RU/EN) |
| `/rules` | rules/page.tsx | База правил Sayqallash |
| `/profile` | profile/page.tsx | Настройки пользователя |
| `/admin` | admin/page.tsx | Управление пользователями, статистика |
| `/admin/activity` | admin/activity/page.tsx | Журнал активности системы |

---

### 7. КЛЮЧЕВЫЕ БИЗНЕС-ПРОЦЕССЫ

#### 7.1 Загрузка и обработка документа
```
DOCX/PDF ──► processor.py ──► Определение формата
                                 ├─► 3-колоночная таблица → process_ready_form()
                                 ├─► Один языковой блок → process_single_language()
                                 └─► Мультиблок → process() + align_paragraphs()
                                          │
                                          ▼
                                 Трёхъязычные строки (EN/RU/UZ)
                                          │
                                          ▼
                                 AI Pre-polishing (фоновая задача)
                                          │
                                          ▼
                                 TableEditor ← Пользователь редактирует
```

#### 7.2 Sayqallash — 3-уровневая коррекция
```
Входной текст
     │
     ▼
[Tier 1] База правил sayqallash_rules
     │   ├─ Точное совпадение (wrong_form)
     │   └─ Семантический поиск (FAISS + BERT embeddings)
     │
     ▼ (если не найдено)
[Tier 2] AI-коррекция
     │   ├─ Gemini 2.0 Flash (primary)
     │   └─ Claude 3.5 Haiku (fallback)
     │
     ▼ (если AI недоступен)
[Tier 3] BERT fill-mask предложения
     │
     ▼
Результат: annotations[] + corrected_text + confidence
```

#### 7.3 Самообучение
```
Пользователь принимает правку ──► /api/sayqallash/learn-batch
                                        │
                                        ▼
                                 sayqallash_rules += новое правило
                                 frequency++ (если существует)
                                 FAISS index обновляется
```

---

### 8. АУТЕНТИФИКАЦИЯ И АВТОРИЗАЦИЯ

| Аспект | Реализация |
|--------|-----------|
| Метод | JWT (HS256) |
| Время жизни токена | 7 дней |
| Хранение (клиент) | localStorage (`pharma_token`) |
| Google OAuth | GSI (client_id: `1069007349621-...`) |
| Роли | `admin`, `foydalanuvchi` (обычный) |
| Статусы пользователей | pending → approved / rejected |
| Сброс пароля | Код по email (выводится в console) |
| Dev-режим | token="dev-token" → автоматический admin |

---

### 9. ДИЗАЙН-СИСТЕМА

| Параметр | Значение |
|----------|----------|
| Палитра | Warm Milky/Cream (#FFF8F0 основной фон) |
| Акцент | #B48C64 (золотисто-коричневый) |
| Текст | #3D2B1F (тёмно-коричневый) |
| Стилизация | CSS Variables + inline styles |
| Эффекты | Glass-morphism (backdrop-filter: blur) |
| Скругления | 8–24px |
| Иконки | Lucide React |
| Адаптивность | CSS media queries (inline) |
| Sidebar | 280px (развёрнут) / 80px (свёрнут) |
| Header | 72px |

---

## ЧАСТЬ II. СПЕЦИФИКАЦИЯ ДЛЯ УСОВЕРШЕНСТВОВАНИЯ

---

### 10. ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ И ТЕХНИЧЕСКИЙ ДОЛГ

#### 10.1 Критические

| # | Проблема | Файл | Влияние |
|---|---------|------|---------|
| C1 | JWT secret захардкожен (`pharma_secret_key_2026`) | auth.py | Безопасность |
| C2 | Dev-token bypass (`token == "dev-token"` → admin) | auth.py | Безопасность |
| C3 | CORS `allow_origins=["*"]` в продакшене | main.py | Безопасность |
| C4 | SQLite в продакшене (нет конкурентной записи) | db.py | Масштабируемость |
| C5 | Нет rate limiting на AI-эндпоинтах | main.py | Затраты AI API |
| C6 | Нет валидации загружаемых файлов (размер, тип) | main.py | Безопасность |
| C7 | Password reset код в console.log (не email) | main.py | Функциональность |

#### 10.2 Архитектурные

| # | Проблема | Файл | Влияние |
|---|---------|------|---------|
| A1 | main.py — 18,000+ строк, монолитный | main.py | Поддерживаемость |
| A2 | db.py — 19,500+ строк, всё в одном | db.py | Поддерживаемость |
| A3 | Нет слоя абстракции API на фронте (fetch везде инлайн) | components/*.tsx | Дублирование кода |
| A4 | Нет state management (только useState) | все страницы | Сложность роста |
| A5 | Все страницы CSR (`'use client'`) — нет SSR/SSG | app/**/*.tsx | SEO, производительность |
| A6 | Нет тестов (ни unit, ни integration, ни e2e) | - | Качество |
| A7 | Нет TypeScript типов для API responses | components/ | Надёжность |
| A8 | TableEditor.tsx — один огромный компонент | TableEditor.tsx | Поддерживаемость |

#### 10.3 UX/UI

| # | Проблема | Влияние |
|---|---------|---------|
| U1 | Inline styles вместо CSS modules/Tailwind | Поддерживаемость стилей |
| U2 | Нет skeleton/loading states на страницах | UX |
| U3 | Нет оффлайн-поддержки | UX |
| U4 | Нет keyboard shortcuts в редакторе | Продуктивность |
| U5 | Нет dark mode | UX |
| U6 | Нет breadcrumbs / навигационных цепочек | Навигация |

---

### 11. ПЛАН УСОВЕРШЕНСТВОВАНИЯ — ФАЗЫ

#### ФАЗА 1: Безопасность и стабильность (Приоритет: КРИТИЧЕСКИЙ)

```
Задачи:
├── 1.1 Убрать dev-token bypass из auth.py
├── 1.2 JWT secret → переменная окружения (не хардкод)
├── 1.3 CORS → whitelist конкретных доменов
├── 1.4 Rate limiting (slowapi) на AI-эндпоинты
├── 1.5 Валидация загрузки: размер ≤50MB, типы .docx/.pdf
├── 1.6 Реальная отправка email для password reset (SMTP)
├── 1.7 Аудит SQL-инъекций в db.py
└── 1.8 HTTPS-only cookies / httpOnly для токенов
```

#### ФАЗА 2: Рефакторинг бэкенда (Приоритет: ВЫСОКИЙ)

```
Задачи:
├── 2.1 Разбить main.py на модули:
│   ├── routes/auth.py
│   ├── routes/projects.py
│   ├── routes/editor.py
│   ├── routes/sayqallash.py
│   ├── routes/dictionary.py
│   └── routes/export.py
├── 2.2 Разбить db.py на:
│   ├── models/user.py
│   ├── models/project.py
│   ├── models/alignment.py
│   ├── models/rule.py
│   └── models/linguistic.py
├── 2.3 Внедрить Pydantic models для всех запросов/ответов
├── 2.4 Миграция SQLite → PostgreSQL (Railway addon)
├── 2.5 Alembic для миграций БД
└── 2.6 Структурированное логирование (structlog)
```

#### ФАЗА 3: Рефакторинг фронтенда (Приоритет: ВЫСОКИЙ)

```
Задачи:
├── 3.1 Создать API-клиент (services/api.ts) с типами
├── 3.2 Разбить TableEditor на подкомпоненты:
│   ├── TableRow.tsx
│   ├── SynonymPopup.tsx
│   ├── ToolbarActions.tsx
│   ├── ColumnResizer.tsx
│   └── LinguisticModal.tsx
├── 3.3 Внедрить Tailwind CSS (убрать inline styles)
├── 3.4 TypeScript интерфейсы для всех API-моделей
├── 3.5 React Query (TanStack Query) для кэширования API
├── 3.6 Zustand для глобального состояния
└── 3.7 Error Boundary компоненты
```

#### ФАЗА 4: Тестирование (Приоритет: СРЕДНИЙ)

```
Задачи:
├── 4.1 pytest для бэкенда (unit + integration)
├── 4.2 Jest + React Testing Library для фронтенда
├── 4.3 Playwright для e2e тестов
├── 4.4 CI pipeline: тесты на каждый PR
└── 4.5 Минимум 70% coverage для критических модулей
```

#### ФАЗА 5: Новые фичи (Приоритет: НОРМАЛЬНЫЙ)

```
Задачи:
├── 5.1 WebSocket для real-time collaboration
├── 5.2 Версионирование документов (git-like diff)
├── 5.3 Keyboard shortcuts в TableEditor
├── 5.4 Оффлайн-режим (Service Worker + IndexedDB)
├── 5.5 Dark mode
├── 5.6 Экспорт в PDF (помимо DOCX)
├── 5.7 Bulk import из Excel
├── 5.8 Уведомления (in-app + email)
└── 5.9 Роли: reviewer, translator, admin, super_admin
```

#### ФАЗА 6: DevOps и мониторинг (Приоритет: НОРМАЛЬНЫЙ)

```
Задачи:
├── 6.1 Docker-compose для локальной разработки
├── 6.2 Sentry для error tracking
├── 6.3 Prometheus + Grafana метрики
├── 6.4 Автоматический backup БД
├── 6.5 Staging-окружение
└── 6.6 Feature flags (unleash/flagsmith)
```

---

### 12. СУБАГЕНТНАЯ СТРАТЕГИЯ ВЫПОЛНЕНИЯ

При загрузке этой спецификации, Claude Code может параллельно запускать субагентов:

```
Координатор (основной агент)
│
├── [Agent 1: Security] Фаза 1 — безопасность
│   └── Файлы: auth.py, main.py (CORS, rate limit)
│
├── [Agent 2: Backend Refactor] Фаза 2 — рефакторинг бэкенда
│   └── Файлы: main.py → routes/, db.py → models/
│
├── [Agent 3: Frontend Refactor] Фаза 3 — рефакторинг фронтенда
│   └── Файлы: components/, services/, app/
│
├── [Agent 4: Testing] Фаза 4 — тесты
│   └── Файлы: tests/, __tests__/, playwright/
│
├── [Agent 5: Features] Фаза 5 — новые фичи
│   └── Файлы: зависит от фичи
│
└── [Agent 6: DevOps] Фаза 6 — инфраструктура
    └── Файлы: docker-compose.yml, .github/workflows/
```

**Правила координации:**
- Фазы 1–3 выполняются последовательно (зависимости)
- Фаза 4 может начинаться параллельно с Фазой 3
- Фазы 5–6 выполняются параллельно после завершения 1–3
- Каждый агент работает в своём worktree (изоляция)
- PR создаётся на каждую подзадачу

---

### 13. МЕТРИКИ УСПЕХА

| Метрика | Текущее | Цель |
|---------|---------|------|
| Покрытие тестами | 0% | ≥70% |
| Время загрузки страницы | ~3s | <1.5s |
| Размер main.py | 18,000 строк | <500 строк (точка входа) |
| Размер db.py | 19,500 строк | <300 строк (ORM models) |
| Безопасность (OWASP) | Критические уязвимости | 0 критических |
| Доступность API | Нет мониторинга | 99.5% uptime |
| AI Response time | ~2-5s | <2s (с кэшем <100ms) |

---

### 14. ГЛОССАРИЙ

| Термин | Определение |
|--------|-----------|
| **Sayqallash** | Система коррекции текста (узб. "полировка") — 3-уровневая: правила → AI → BERT |
| **Tahrirchi** | Редактор (узб.) — кастомная BERT-модель для узбекского языка |
| **Alignment** | Выравнивание — сопоставление параграфов EN ↔ RU ↔ UZ |
| **Pre-polishing** | Автоматическая AI-коррекция сразу после загрузки документа |
| **Marker row** | Служебная строка-разделитель в таблице (заголовок секции) |
| **FAISS** | Facebook AI Similarity Search — индекс для семантического поиска правил |
| **ГФ** | Государственная Фармакопея |
| **USP** | United States Pharmacopeia |
| **Ph. Eur.** | European Pharmacopoeia |

---

### 15. КОНТАКТЫ И РЕСУРСЫ

| Ресурс | URL |
|--------|-----|
| Frontend (prod) | `https://frontend-dun-nine-30.vercel.app` |
| Backend (prod) | `https://pharma-backend-production-38bb.up.railway.app` |
| Backend API docs | `https://pharma-backend-production-38bb.up.railway.app/docs` |
| Repository | `C:\Users\Администратор\Desktop\2` |
| BERT Model | `tahrirchi/tahrirchi-bert-base` (HuggingFace) |

---

> **Использование:** Загрузите этот файл в начале сессии Claude Code командой:
> ```
> Прочитай SPEC.md и начни работу по Фазе [N]
> ```
> Claude Code автоматически разобьёт задачи на подзадачи и запустит субагентов для параллельного выполнения.
