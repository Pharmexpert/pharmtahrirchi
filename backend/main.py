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
from routes.billing_routes import router as billing_router
from routes.syntax_routes import router as syntax_router
from routes.unified_analyze_routes import router as unified_analyze_router
TEMP_DIR = os.path.join(BACKEND_DIR, "temp_files")
# Use persistent volume for uploads on Railway
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
DATA_DIR = os.getenv("DATA_DIR", "/app/data" if IS_RAILWAY else BACKEND_DIR)
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(os.path.join(TEMP_DIR, "imgs"), exist_ok=True)

import datetime as _dt
os.environ["APP_STARTED_AT"] = _dt.datetime.utcnow().isoformat() + "Z"

app = FastAPI()


@app.get("/api/health")
async def health_check():
    """Lightweight healthcheck for Railway."""
    return {"status": "ok"}


@app.get("/api/version")
async def api_version():
    """Build/version info — git SHA, env, deploy timestamp."""
    import subprocess
    sha = "unknown"
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BACKEND_DIR, stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
    except Exception:
        sha = os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")[:7]
    return {
        "sha": sha,
        "env": "railway" if IS_RAILWAY else "local",
        "started_at": os.environ.get("APP_STARTED_AT", ""),
    }


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
    for name, mod in [("mistral", "mistral_engine"), ("llama", "llama_engine"), ("russian", "russian_engine"), ("nllb", "translator_engine"), ("ner", "ner_engine"), ("tahrirchi", "tahrirchi_engine")]:
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

    # Syntax module — Phase 1: 5 ta jadval + canonical seed
    try:
        import syntax_db
        syntax_db.init_syntax_tables()
        syntax_db.seed_canonical_templates()
        syntax_db.seed_basic_word_order_rules()
        logger.info("[syntax] Phase 1 schema + seeds OK")
    except Exception as e:
        logger.warning(f"[syntax] init failed: {e}")

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

        # Weekly learning cycle (Sunday 03:00) — self-improvement pipeline
        try:
            import weekly_learning_cycle
            scheduler.add_job(
                weekly_learning_cycle.run_full_cycle,
                CronTrigger(hour=3, minute=30),  # DAILY at 03:30 Tashkent time
                id="daily_learning",
                name="Daily self-improvement cycle",
                replace_existing=True,
                misfire_grace_time=7200,
            )
            logger.info("[Scheduler] Daily learning cycle scheduled (every day 03:30 Asia/Tashkent)")
        except Exception as ee:
            logger.warning(f"[Scheduler] Daily learning cycle skipped: {ee}")

        # Daily DB backup (02:00 Tashkent — before other cycles)
        try:
            from scripts.db_backup import run_backup as _run_backup
            scheduler.add_job(
                _run_backup,
                CronTrigger(hour=2, minute=0),
                id="daily_backup",
                name="Daily DB backup",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("[Scheduler] Daily DB backup scheduled (02:00 Asia/Tashkent)")
        except Exception as ee:
            logger.warning(f"[Scheduler] Daily backup skipped: {ee}")

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
app.include_router(billing_router)
app.include_router(syntax_router)
app.include_router(unified_analyze_router)


# ═══════════════════════════════════════════════════
# Auto-seed: drugs + Uzbek rules from Ona tili book (idempotent)
# ═══════════════════════════════════════════════════
@app.on_event("startup")
async def auto_seed_databases():
    """Seed databases in background to avoid Railway startup timeout."""
    import asyncio
    asyncio.create_task(_auto_seed_background())


async def _auto_seed_background():
    """Background auto-seed — runs after app is serving traffic."""
    import asyncio
    await asyncio.sleep(5)  # Let app fully start first
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

        # Seed medical terms if empty
        try:
            conn2 = _db.connect_db()
            cur2 = conn2.cursor()
            cur2.execute("SELECT COUNT(*) FROM medical_terms")
            terms_count = cur2.fetchone()[0]
            conn2.close()
            if terms_count == 0:
                import seed_medical_terms
                result = seed_medical_terms.seed()
                logger.info(f"[auto-seed] Medical terms: {result}")
        except Exception as e:
            logger.warning(f"[auto-seed] medical_terms failed: {e}")

        # Auto-import kmashrab wordlist if user_dictionary is small
        try:
            conn3 = _db.connect_db()
            cur3 = conn3.cursor()
            cur3.execute("SELECT COUNT(*) FROM user_dictionary")
            ud_count = cur3.fetchone()[0]
            conn3.close()
            if ud_count < 1000:  # one-time trigger
                import sys as _sys, os as _os
                sd = _os.path.join(_os.path.dirname(__file__), "scripts")
                if sd not in _sys.path:
                    _sys.path.insert(0, sd)
                try:
                    import import_kmashrab
                    r = import_kmashrab.main()
                    logger.info(f"[auto-seed] kmashrab: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] kmashrab failed: {ee}")
                try:
                    import import_additional_dicts
                    r = import_additional_dicts.main()
                    logger.info(f"[auto-seed] extras: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] extras failed: {ee}")
                # New Uzbek spell-check sources (uzbek-spell, uzbek-net, uzhungen qoida, debian)
                try:
                    import import_uzbek_spell
                    r = import_uzbek_spell.main()
                    logger.info(f"[auto-seed] uzbek_spell: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] uzbek_spell failed: {ee}")
                try:
                    import import_uzbek_net_hunspell
                    r = import_uzbek_net_hunspell.main()
                    logger.info(f"[auto-seed] uzbek_net: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] uzbek_net failed: {ee}")
                try:
                    import import_uzhungen_qoida
                    r = import_uzhungen_qoida.main()
                    logger.info(f"[auto-seed] uzhungen qoida: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] uzhungen qoida failed: {ee}")
                try:
                    import import_debian_hunspell
                    r = import_debian_hunspell.main()
                    logger.info(f"[auto-seed] debian_hunspell: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] debian_hunspell failed: {ee}")
                # Post-processing: freq rankings + affix merge + auto REP rules
                try:
                    import build_freq_rankings
                    r = build_freq_rankings.main()
                    logger.info(f"[auto-seed] freq rankings: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] freq rankings failed: {ee}")
                try:
                    import merge_affix_descriptions
                    r = merge_affix_descriptions.main()
                    logger.info(f"[auto-seed] affix merge: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] affix merge failed: {ee}")
                try:
                    import auto_generate_rep_rules
                    r = auto_generate_rep_rules.main(max_words=5000)
                    logger.info(f"[auto-seed] auto REP rules: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] auto REP rules failed: {ee}")
                # Pharmacopoeia Volume 1 data (State pharmacopoeia)
                try:
                    import import_pharmacopoeia
                    r = import_pharmacopoeia.main()
                    logger.info(f"[auto-seed] pharmacopoeia: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] pharmacopoeia failed: {ee}")
        except Exception as e:
            logger.warning(f"[auto-seed] user_dictionary check failed: {e}")

        # ═════════════════════════════════════════════════════════════════
        # POST-PROCESSING — runs regardless of user_dictionary count
        # These are idempotent + check own conditions (needed on every startup)
        # ═════════════════════════════════════════════════════════════════
        try:
            import sys as _sys, os as _os
            sd = _os.path.join(_os.path.dirname(__file__), "scripts")
            if sd not in _sys.path:
                _sys.path.insert(0, sd)

            # 1. uzhungen .qoida descriptions (fetches from GitHub API)
            try:
                conn_q = _db.connect_db()
                cur_q = conn_q.cursor()
                try:
                    cur_q.execute("SELECT COUNT(*) FROM hunspell_affix_descriptions")
                    qcount = cur_q.fetchone()[0]
                except Exception:
                    qcount = 0
                conn_q.close()
                if qcount < 50:
                    import import_uzhungen_qoida
                    r = import_uzhungen_qoida.main()
                    logger.info(f"[post-process] uzhungen qoida: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] uzhungen qoida failed: {ee}")

            # 2. Affix flag mapping (depends on #1)
            try:
                conn_m = _db.connect_db()
                cur_m = conn_m.cursor()
                try:
                    cur_m.execute("SELECT COUNT(*) FROM affix_flag_mapping")
                    mcount = cur_m.fetchone()[0]
                except Exception:
                    mcount = 0
                conn_m.close()
                if mcount < 5:
                    import merge_affix_descriptions
                    r = merge_affix_descriptions.main()
                    logger.info(f"[post-process] affix merge: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] affix merge failed: {ee}")

            # 3. Word frequency rankings (always refresh — rebuild from corpus)
            try:
                conn_f = _db.connect_db()
                cur_f = conn_f.cursor()
                try:
                    cur_f.execute("SELECT COUNT(*) FROM word_frequency_corpus")
                    fcount = cur_f.fetchone()[0]
                except Exception:
                    fcount = 0
                conn_f.close()
                if fcount < 100:
                    import build_freq_rankings
                    r = build_freq_rankings.main()
                    logger.info(f"[post-process] freq rankings: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] freq rankings failed: {ee}")

            # 4. Pharmacopoeia (always try — idempotent, skips duplicates)
            try:
                import import_pharmacopoeia
                r = import_pharmacopoeia.main()
                logger.info(f"[post-process] pharmacopoeia: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] pharmacopoeia failed: {ee}")

            # 5. Editorial-approved disputed words (docx → disputed_board)
            try:
                import import_disputed_board
                r = import_disputed_board.main()
                logger.info(f"[post-process] disputed_board: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] disputed_board failed: {ee}")

            # 6. Pharma DB (TOC + Drug Registry)
            try:
                import import_pharma_db
                r = import_pharma_db.main()
                logger.info(f"[post-process] pharma_db: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] pharma_db failed: {ee}")

            # 7. Colors table (285 uz/ru/en from State Pharmacopoeia)
            try:
                import import_colors_table
                r = import_colors_table.main()
                logger.info(f"[post-process] colors_table: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] colors_table failed: {ee}")

            # 8. Izohli lugat (102 pharmacopoeia terms → annotated_words)
            try:
                import import_izohli_lugat
                r = import_izohli_lugat.main()
                logger.info(f"[post-process] izohli_lugat: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] izohli_lugat failed: {ee}")

            # 9. Style rules seed (55+ USP/Ph.Eur./ICH/WHO rules)
            try:
                import seed_style_rules_full
                r = seed_style_rules_full.main()
                logger.info(f"[post-process] style_rules: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] style_rules failed: {ee}")

            # 10. SI units (61) + pharma solubility (7) + auto-generated style rules (61)
            try:
                import import_si_units_style
                r = import_si_units_style.main()
                logger.info(f"[post-process] si_units: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] si_units failed: {ee}")

            # 11. Uzbek grammar rules + error pairs from MD (176 pairs from @xatoliklar)
            try:
                import import_uzbek_qoidalari
                r = import_uzbek_qoidalari.main()
                logger.info(f"[post-process] uzbek_qoidalari: {r}")
            except Exception as ee:
                logger.warning(f"[post-process] uzbek_qoidalari failed: {ee}")
        except Exception as e:
            logger.warning(f"[post-process] setup failed: {e}")

        # Try to seed Uzbek rules from book if PDF text is bundled
        try:
            import seed_uzbek_rules_from_book
            result = seed_uzbek_rules_from_book.main()
            if result:
                logger.info(f"[auto-seed] Uzbek rules: {result}")
        except Exception as e:
            logger.info(f"[auto-seed] uzbek rules skipped: {e}")

        # Parse u2b3k Hunspell affix rules if files present
        try:
            import parse_hunspell_affix
            if os.path.exists(parse_hunspell_affix.HUNSPELL_DIR):
                affix_result = parse_hunspell_affix.import_rules()
                logger.info(f"[auto-seed] Hunspell affix rules: {affix_result}")
        except Exception as e:
            logger.info(f"[auto-seed] hunspell affix skipped: {e}")

        # Syntax GECTurk-B: Auto-generate synthetic pairs if <5K synth exist
        try:
            conn_sy = _db.connect_db()
            cur_sy = conn_sy.cursor()
            try:
                cur_sy.execute("SELECT COUNT(*) FROM translation_memory WHERE source_db='syntax_synth'")
                synth_n = cur_sy.fetchone()[0]
            except Exception:
                synth_n = 0
            conn_sy.close()
            if synth_n < 5000:
                try:
                    import syntax_synth_generator
                    r = syntax_synth_generator.generate_all(limit_sentences=2000, transforms_per_sent=5)
                    logger.info(f"[auto-seed] syntax_synth: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] syntax_synth failed: {ee}")
        except Exception as e:
            logger.warning(f"[auto-seed] synth check failed: {e}")

        # Syntax GECTurk-A: Auto-verify sayqallash rules (flag noisy ones) on first run
        try:
            conn_v = _db.connect_db()
            cur_v = conn_v.cursor()
            try:
                cur_v.execute("SELECT COUNT(*) FROM sayqallash_rules WHERE quality_flag IS NULL OR quality_flag='unverified'")
                unverified_n = cur_v.fetchone()[0]
            except Exception:
                unverified_n = 0
            conn_v.close()
            if unverified_n > 500:
                try:
                    import syntax_verifier
                    r = syntax_verifier.verify_all_rules(limit=10000)
                    logger.info(f"[auto-seed] rule verification: clean={r.get('clean')}, noisy={r.get('noisy')}, suspicious={r.get('suspicious')}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] verifier failed: {ee}")
        except Exception as e:
            logger.warning(f"[auto-seed] verifier check failed: {e}")

        # Syntax Phase 2: Auto-import UD_Uzbek-UT corpus (if syntax_phrases empty)
        try:
            conn_ud = _db.connect_db()
            cur_ud = conn_ud.cursor()
            try:
                cur_ud.execute("SELECT COUNT(*) FROM syntax_phrases")
                phrases_n = cur_ud.fetchone()[0]
            except Exception:
                phrases_n = 0
            conn_ud.close()
            if phrases_n < 100:
                import sys as _sys, os as _os
                sd = _os.path.join(_os.path.dirname(__file__), "scripts")
                if sd not in _sys.path:
                    _sys.path.insert(0, sd)
                try:
                    import import_ud_uzbek
                    r = import_ud_uzbek.main()
                    logger.info(f"[auto-seed] UD_Uzbek-UT: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] UD_Uzbek-UT failed: {ee}")
        except Exception as e:
            logger.warning(f"[auto-seed] UD check failed: {e}")

        # Auto-import Hunspell REP rules → sayqallash_rules (if REP count low)
        try:
            conn_r = _db.connect_db()
            cur_r = conn_r.cursor()
            cur_r.execute("SELECT COUNT(*) FROM sayqallash_rules WHERE error_type = 'REP/Hunspell'")
            rep_count = cur_r.fetchone()[0]
            conn_r.close()
            if rep_count < 100:
                import hunspell_data
                added = hunspell_data.import_rep_to_sayqallash()
                logger.info(f"[auto-seed] Hunspell REP rules: +{added} (had {rep_count})")
        except Exception as e:
            logger.info(f"[auto-seed] hunspell REP skipped: {e}")

        # Auto-run WHO INN import if drugs < 300
        try:
            conn4 = _db.connect_db()
            cur4 = conn4.cursor()
            cur4.execute("SELECT COUNT(*) FROM drugs")
            drugs_c = cur4.fetchone()[0]
            conn4.close()
            if drugs_c < 300:
                import sys as _sys, os as _os
                sd = _os.path.join(_os.path.dirname(__file__), "scripts")
                if sd not in _sys.path:
                    _sys.path.insert(0, sd)
                import import_who_inn
                r = import_who_inn.seed()
                logger.info(f"[auto-seed] WHO INN: {r}")
        except Exception as e:
            logger.warning(f"[auto-seed] WHO INN failed: {e}")

        # Auto-run sayqallash domain segmentation
        try:
            conn5 = _db.connect_db()
            cur5 = conn5.cursor()
            try:
                cur5.execute("SELECT COUNT(*) FROM sayqallash_rules WHERE domain IS NULL")
                null_domain = cur5.fetchone()[0]
            except Exception:
                null_domain = 0
            if null_domain > 0:
                try:
                    cur5.execute("ALTER TABLE sayqallash_rules ADD COLUMN domain TEXT DEFAULT 'general'")
                except Exception:
                    pass
                cur5.execute("""
                    UPDATE sayqallash_rules SET domain = 'pharma'
                    WHERE context LIKE '%doz%' OR context LIKE '%mg%' OR context LIKE '%ml%'
                       OR wrong_form IN (SELECT inn FROM drugs WHERE inn IS NOT NULL)
                """)
                pharma_n = cur5.rowcount
                try:
                    cur5.execute("""
                        UPDATE sayqallash_rules SET domain = 'medical'
                        WHERE (domain = 'general' OR domain IS NULL)
                          AND wrong_form IN (SELECT term_uz FROM medical_terms WHERE term_uz IS NOT NULL)
                    """)
                    med_n = cur5.rowcount
                except Exception:
                    med_n = 0
                conn5.commit()
                logger.info(f"[auto-seed] domain segment: pharma={pharma_n}, medical={med_n}")
            conn5.close()
        except Exception as e:
            logger.warning(f"[auto-seed] domain segment failed: {e}")

        # Auto-run Sayqallash consolidator (dedup + conflict flag)
        try:
            import sayqallash_consolidator
            cons_result = sayqallash_consolidator.consolidate(semantic=False)  # skip BERT for speed
            logger.info(f"[auto-seed] consolidate: removed {cons_result.get('removed_total', 0)}")
        except Exception as e:
            logger.warning(f"[auto-seed] consolidate failed: {e}")

        # Auto-trigger Tahrirchi datasets (only if translation_memory is empty)
        try:
            conn6 = _db.connect_db()
            cur6 = conn6.cursor()
            try:
                cur6.execute("SELECT COUNT(*) FROM translation_memory")
                tm_count = cur6.fetchone()[0]
            except Exception:
                tm_count = -1
            conn6.close()
            if tm_count < 2000:  # dilmash fix: re-run if under threshold (lutfiy alone gives 1000)
                import sys as _sys, os as _os
                sd = _os.path.join(_os.path.dirname(__file__), "scripts")
                if sd not in _sys.path:
                    _sys.path.insert(0, sd)
                try:
                    import import_tahrirchi_datasets
                    r = import_tahrirchi_datasets.main()
                    logger.info(f"[auto-seed] tahrirchi datasets: {r}")
                except Exception as ee:
                    logger.warning(f"[auto-seed] tahrirchi datasets failed: {ee}")
        except Exception as e:
            logger.warning(f"[auto-seed] tahrirchi check failed: {e}")

    except Exception as e:
        logger.warning(f"[auto-seed] outer failed: {e}")


if __name__ == "__main__":
    import startup
    startup.setup_tahrirchi_db()

    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
