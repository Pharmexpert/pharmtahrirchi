"""
Pharma Aligner Backend — FastAPI Application Entry Point
Modular architecture: all endpoints are in routes/ directory.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["BACKEND_DIR"] = BACKEND_DIR  # Share with route modules

import db
import bert_engine
import admin_routes
import linguistic_routes
from routes import auth_routes, upload_routes, sayqallash_routes, editor_routes, projects_routes
from routes.websocket_routes import router as websocket_router
from routes.morph_routes import router as morph_router
from routes.grammar_routes import router as grammar_router
from routes.learn_routes import router as learn_router
from routes.nlp_admin_routes import router as nlp_admin_router
from routes.tilshunos_routes import router as tilshunos_router
from routes.assistant_routes import router as assistant_router
TEMP_DIR = os.path.join(BACKEND_DIR, "temp_files")
# Use persistent volume for uploads on Railway
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
DATA_DIR = os.getenv("DATA_DIR", "/app/data" if IS_RAILWAY else BACKEND_DIR)
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(os.path.join(TEMP_DIR, "imgs"), exist_ok=True)

app = FastAPI()


@app.get("/api/health")
async def health_check():
    """Lightweight healthcheck for Railway."""
    return {"status": "ok"}


@app.get("/api/ai-engines")
async def public_ai_engines():
    """Public read-only AI engines status (no auth)."""
    out = {"engines": {}}
    try:
        import bert_engine
        out["engines"]["bert"] = {
            "available": bool(bert_engine.engine.initialized),
            "model": bert_engine.MODEL_NAME,
            "ensemble": bert_engine.ENSEMBLE_MODE,
            "uzbert_available": bool(bert_engine.engine.uzbert_initialized),
            "uzbert_model": bert_engine.UZBERT_MODEL,
        }
    except Exception:
        out["engines"]["bert"] = {"available": False}
    for name, mod in [("mistral", "mistral_engine"), ("llama", "llama_engine"), ("russian", "russian_engine"), ("nllb", "translator_engine"), ("ner", "ner_engine")]:
        try:
            m = __import__(mod)
            out["engines"][name] = {
                "available": m.is_available(),
                "mode": m.get_mode(),
                "model": getattr(m, "MODEL_ID", "unknown"),
            }
        except Exception as e:
            out["engines"][name] = {"available": False, "error": str(e)[:100]}
    out["engines"]["gemini"] = {"available": bool(os.environ.get("GOOGLE_API_KEY"))}
    out["engines"]["anthropic"] = {"available": bool(os.environ.get("ANTHROPIC_API_KEY"))}
    return out

# ═══════════════════════════════════════════════════
# Middleware: CORS & Security Headers
# ═══════════════════════════════════════════════════

_DEFAULT_ORIGINS = "http://localhost:3000,https://pharmtech.info,https://www.pharmtech.info,https://frontend-dun-nine-30.vercel.app"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]
# Defensive: always include pharmtech.info domains even if env var was set to something else
for _required in ["https://pharmtech.info", "https://www.pharmtech.info"]:
    if _required not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_required)
# Regex fallback: any pharmtech.info / *.pharmtech.info / vercel.app preview deploys
_ALLOWED_REGEX = r"^https://([a-z0-9-]+\.)*(pharmtech\.info|vercel\.app)$"
logger.info(f"[CORS] Allowed origins: {ALLOWED_ORIGINS}")
logger.info(f"[CORS] Allowed regex: {_ALLOWED_REGEX}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=_ALLOWED_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ═══════════════════════════════════════════════════
# Startup: Initialize DB, BERT, FAISS
# ═══════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    import startup as startup_module
    startup_module.setup_tahrirchi_db()

    db.init_db()
    db.init_faiss_index()
    bert_engine.engine.initialize()

    import asyncio
    from anyio import to_thread

    async def run_migration():
        try:
            await asyncio.sleep(10)
            logger.info("[*] Starting background vector migration...")
            await to_thread.run_sync(db.migrate_vectors)
        except Exception as e:
            logger.error(f"[!] Background migration error: {e}")

    asyncio.create_task(run_migration())

    # ═══════════════════════════════════════════════
    # Phase 6: Nightly dictionary growth scheduler (APScheduler)
    # Runs every night at 03:00 Tashkent time (UTC+5)
    # ═══════════════════════════════════════════════
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from scripts.nightly_dictionary_grow import grow_dictionary

        scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
        scheduler.add_job(
            lambda: grow_dictionary(window_hours=24),
            CronTrigger(hour=3, minute=0),
            id="nightly_grow",
            name="Nightly dictionary growth",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        logger.info("[Scheduler] Nightly dictionary growth scheduled at 03:00 Asia/Tashkent")
    except ImportError:
        logger.warning("[Scheduler] APScheduler not installed — nightly growth disabled")
    except Exception as e:
        logger.error(f"[Scheduler] Failed to start: {e}")


# ═══════════════════════════════════════════════════
# Static Files & Route Registration
# ═══════════════════════════════════════════════════

app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

# Existing routers (already modular)
app.include_router(admin_routes.router)
app.include_router(linguistic_routes.router)

# New modular routers (Phase 2 refactor)
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(sayqallash_routes.router)
app.include_router(editor_routes.router)
app.include_router(projects_routes.router)
app.include_router(websocket_router)
app.include_router(morph_router)
app.include_router(grammar_router)
app.include_router(learn_router)
app.include_router(nlp_admin_router)
app.include_router(tilshunos_router)
app.include_router(assistant_router)


# ═══════════════════════════════════════════════════
# Auto-seed: drugs + Uzbek rules from Ona tili book (idempotent)
# ═══════════════════════════════════════════════════
@app.on_event("startup")
async def auto_seed_databases():
    """Seed drugs DB + Uzbek rules from book on first startup if tables are empty."""
    try:
        import db as _db
        conn = _db.connect_db()
        cur = conn.cursor()

        # Check if drugs table is empty
        try:
            cur.execute("SELECT COUNT(*) FROM drugs")
            drugs_count = cur.fetchone()[0]
        except Exception:
            drugs_count = 0
        conn.close()

        if drugs_count == 0:
            try:
                import seed_drugs
                inserted = seed_drugs.seed()
                logger.info(f"[auto-seed] Drugs: +{inserted} new")
            except Exception as e:
                logger.warning(f"[auto-seed] drugs failed: {e}")

        # Try to seed Uzbek rules from book if PDF text is bundled
        try:
            import seed_uzbek_rules_from_book
            result = seed_uzbek_rules_from_book.main()
            if result:
                logger.info(f"[auto-seed] Uzbek rules: {result}")
        except Exception as e:
            logger.info(f"[auto-seed] uzbek rules skipped: {e}")
    except Exception as e:
        logger.warning(f"[auto-seed] outer failed: {e}")


if __name__ == "__main__":
    import startup
    startup.setup_tahrirchi_db()

    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
