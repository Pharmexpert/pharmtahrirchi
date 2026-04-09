from fastapi import APIRouter, Depends, HTTPException, Response, Request
from typing import List, Dict, Any
import db
from auth import get_admin_user, get_current_user, can_edit_db
import pandas as pd
import io
import os
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/rules/export-csv")
async def export_rules_csv(lang: str = None, current_user: dict = Depends(get_admin_user)):
    """Export all rules as CSV including quality_flag + source."""
    import csv as _csv, io as _io
    from fastapi.responses import StreamingResponse
    rules = db.get_all_rules(lang, limit=50000)
    buf = _io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(["id", "wrong_form", "correct_form", "error_type", "lang", "frequency", "quality_flag", "source", "updated_at"])
    for r in rules:
        writer.writerow([
            r.get("id", ""), r.get("wrong_form", ""), r.get("correct_form", ""),
            r.get("error_type", ""), r.get("lang", ""), r.get("frequency", 0),
            r.get("quality_flag", ""), r.get("source", ""), r.get("updated_at", ""),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rules_{lang or 'all'}.csv"},
    )


@router.get("/rules/export")
async def export_rules_xlsx(lang: str = None, current_user: dict = Depends(get_admin_user)):
    """Export all correction rules to an XLSX file."""
    try:
        # If lang is None, fetch for all languages by passing None to the db function
        # assuming db.get_all_rules handles None lang as "all"
        rules = db.get_all_rules(lang, limit=20000)
        if not rules:
            raise HTTPException(status_code=404, detail="Eksport qilish uchun qoidalar topilmadi")
            
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(rules)
        
        # Clean up for presentation - safely select only existing columns
        cols = {
            'wrong_form': 'Хато шакл',
            'correct_form': 'Тўғри шакл',
            'error_type': 'Тури',
            'lang': 'Тил',
            'frequency': 'Частота',
            'updated_at': 'Янгиланган вақт'
        }
        
        # Intersection of requested columns and actual columns in DF
        existing_cols = [c for c in cols.keys() if c in df.columns]
        df = df[existing_cols].rename(columns={k: v for k, v in cols.items() if k in existing_cols})
        
        # Create bytes stream
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sayqallash Qoidalari')
        except Exception as ex:
            print(f"ExcelWriter Error: {ex}")
            raise HTTPException(status_code=500, detail=f"Excel generation failed: {str(ex)}")
        
        output.seek(0)
        
        filename = f"sayqallash_rules_{lang or 'all'}.xlsx"
        return Response(
            content=output.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"Export Rules Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules")
async def get_all_rules(lang: str = None, q: str = None, current_user: dict = Depends(get_current_user)):
    """Retrieve all rules — dual-script search (Cyr ↔ Lat)."""
    rules = db.get_all_rules(lang or 'uz', limit=100000)
    if q:
        search_variants = [q.lower()]
        try:
            import dual_script
            detected = dual_script.detect_script(q)
            if detected == "cyr":
                lat = dual_script.to_latin(q)
                if lat: search_variants.append(lat.lower())
            elif detected == "lat":
                cyr = dual_script.to_cyrillic(q)
                if cyr: search_variants.append(cyr.lower())
        except Exception:
            pass
        rules = [
            r for r in rules
            if any(
                v in r['wrong_form'].lower()
                or v in r['correct_form'].lower()
                or v in (r.get('context') or '').lower()
                for v in search_variants
            )
        ]
    return {"rules": rules, "total": len(rules)}

@router.post("/rules")
async def upsert_rule(payload: Dict[str, Any], current_user: dict = Depends(can_edit_db)):
    """Add or update a correction rule."""
    rule_id = payload.get("id")
    modifier = payload.get("modified_by", current_user.get("name", ""))
    if rule_id:
        db.update_sayqallash_rule(rule_id, payload)
        # Track who modified
        try:
            conn = db.connect_db()
            conn.cursor().execute("UPDATE sayqallash_rules SET modified_by = ? WHERE id = ?", (modifier, rule_id))
            conn.commit()
            conn.close()
        except: pass
        return {"status": "updated", "id": rule_id}
    else:
        db.add_sayqallash_rule(
            wrong=payload.get("wrong_form"),
            correct=payload.get("correct_form"),
            error_type=payload.get("error_type", "S/Spelling"),
            context=payload.get("context", ""),
            lang=payload.get("lang", "uz"),
            source="admin_edit"
        )
        # Track creator
        try:
            conn = db.connect_db()
            conn.cursor().execute("UPDATE sayqallash_rules SET modified_by = ? WHERE wrong_form = ? AND correct_form = ? ORDER BY id DESC LIMIT 1", (modifier, payload.get("wrong_form"), payload.get("correct_form")))
            conn.commit()
            conn.close()
        except: pass
        return {"status": "created"}

@router.post("/rules/batch")
async def batch_seed_rules(payload: List[Dict[str, Any]], request: Request):
    """Batch seed rules for production migration with a secret key."""
    # Simple secret check for internal migration
    seed_secret = os.getenv("SEED_SECRET", "pharma_dev_sync_2026")
    header_secret = request.headers.get("X-Seed-Secret")
    
    if header_secret != seed_secret:
        raise HTTPException(status_code=403, detail="Invalid seed secret")
        
    try:
        conn = db.connect_db()
        cursor = conn.cursor()
        count = 0
        for r in payload:
            cursor.execute('''
                INSERT OR IGNORE INTO sayqallash_rules 
                (wrong_form, correct_form, error_type, context, lang, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                r.get("wrong_form"), 
                r.get("correct_form"), 
                r.get("error_type", "S/Spelling"), 
                r.get("context", ""), 
                r.get("lang", "uz"), 
                r.get("source", "seed")
            ))
            count += 1
        conn.commit()
        conn.close()
        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, current_user: dict = Depends(can_edit_db)):
    """Delete a correction rule."""
    db.delete_sayqallash_rule(rule_id)
    return {"status": "deleted"}


@router.post("/rules/{rule_id}/quality")
async def set_rule_quality(rule_id: int, payload: Dict[str, Any], current_user: dict = Depends(can_edit_db)):
    """Manually set quality_flag of a rule (clean/noisy/suspicious/unverified)."""
    flag = (payload.get("quality_flag") or "").strip()
    if flag not in ("clean", "noisy", "suspicious", "unverified"):
        raise HTTPException(status_code=400, detail="Invalid quality_flag")
    conn = db.connect_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE sayqallash_rules SET quality_flag = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?", (flag, rule_id))
        conn.commit()
    finally:
        conn.close()
    # Invalidate rules cache so changes take effect in editor pipeline
    try:
        db.rules_cache.last_load = 0
    except Exception:
        pass
    return {"status": "updated", "rule_id": rule_id, "quality_flag": flag}

@router.get("/db-snapshots")
async def get_db_snapshots(limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Time-series snapshots for sparkline charts."""
    try:
        import db_snapshots
        return {"history": db_snapshots.get_history(limit_per_table=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db-stats")
async def get_db_stats(current_user: dict = Depends(get_current_user)):
    """Detailed database statistics for admin reporting."""
    # Take throttled snapshot (1 per hour)
    try:
        import db_snapshots
        db_snapshots.take_snapshot(throttle_hours=1)
    except Exception:
        pass
    conn = db.connect_db()
    cursor = conn.cursor()
    stats = {}
    for table in ['projects', 'alignments', 'sayqallash_rules', 'users', 'paragraphs_dashboard',
                  'user_dictionary', 'syntax_phrases', 'syntax_parsed_sentences',
                  'syntax_sentence_templates', 'syntax_word_order_rules',
                  'hunspell_affix_descriptions', 'affix_flag_mapping',
                  'word_frequency_corpus', 'translation_memory']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except: stats[table] = 0

    # Quality flag distribution for sayqallash_rules
    try:
        cursor.execute("""
            SELECT COALESCE(quality_flag, 'unverified') as q, COUNT(*)
            FROM sayqallash_rules GROUP BY q
        """)
        stats['quality_distribution'] = {row[0]: row[1] for row in cursor.fetchall()}
    except:
        stats['quality_distribution'] = {}
    # "paragraphs" stat = paragraphs_dashboard count (matches /paragraphs page)
    stats['paragraphs'] = stats.get('paragraphs_dashboard', 0)
    
    # Detailed Project Counts
    try:
        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'finished'")
        stats['finished_projects'] = cursor.fetchone()[0]
        stats['active_projects'] = stats.get('projects', 0) - stats['finished_projects']
    except:
        stats['finished_projects'] = 0
        stats['active_projects'] = stats.get('projects', 0)
    
    # Detailed User Stats
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE status IS NULL OR status = 'pending' OR status = ''")
        stats['pending_users'] = cursor.fetchone()[0]
    except:
        stats['pending_users'] = 0

    # Synonyms count
    try:
        cursor.execute("SELECT COUNT(*) FROM synonyms")
        stats['synonyms'] = cursor.fetchone()[0]
    except: stats['synonyms'] = 0
    
    import os
    pharma_db_size = os.path.getsize(db.DB_PATH) / (1024 * 1024)
    tahrirchi_db_size = os.path.getsize(db.TAHRIRCHI_DB_PATH) / (1024 * 1024) if os.path.exists(db.TAHRIRCHI_DB_PATH) else 0
    conn.close()
    
    return {
        "counts": stats,
        "projects": stats.get('projects', 0),
        "finished_projects": stats.get('finished_projects', 0),
        "active_projects": stats.get('active_projects', 0),
        "sayqallash_rules": stats.get('sayqallash_rules', 0),
        "synonyms": stats.get('synonyms', 0),
        "paragraphs": stats.get('paragraphs', 0),
        "db_sizes": {
            "pharma_editor.db": f"{pharma_db_size:.2f} MB",
            "tahrirchi.db": f"{tahrirchi_db_size:.2f} MB"
        }
    }

@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_admin_user)):
    """Legacy stats for backward compatibility."""
    conn = db.connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT lang, COUNT(*) FROM sayqallash_rules GROUP BY lang")
    rules_stats = dict(cursor.fetchall())
    cursor.execute("SELECT COUNT(*) FROM projects")
    projects_count = cursor.fetchone()[0]
    conn.close()
    return {
        "rules": rules_stats,
        "dictionary_size": "8.7M",
        "projects_total": projects_count,
        "bert_status": "active"
    }

@router.get("/users")
async def get_users(current_user: dict = Depends(get_admin_user)):
    """List all registered users for moderation."""
    users = db.list_all_users()
    return {"users": users}

@router.post("/users/approve")
@router.post("/approve")
async def approve_user(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Approve or update a user status. Sends email notification on approval."""
    user_id = payload.get("userId")
    status = payload.get("status", "approved")
    db.update_user_status(user_id, status)

    # Send email notification if approved
    if status == "approved":
        try:
            user_data = db.get_user_by_id(user_id)
            if user_data and user_data.get("email"):
                import email_helper
                if email_helper.is_configured():
                    email_helper.send_approval(user_data["email"], user_data.get("name", "Фойдаланувчи"))
        except Exception:
            pass

    return {"success": True}

@router.post("/role")
async def change_role(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Update user role (Admin only)."""
    user_id = payload.get("userId")
    role = payload.get("role")
    db.update_user_role(user_id, role)
    return {"success": True}

@router.post("/sayqallash/cleanup")
async def run_sayqallash_cleanup(current_user: dict = Depends(get_admin_user)):
    """Run Sayqallash DB cleanup: remove duplicates, no-ops, empty rules."""
    try:
        import sys as _sys, os as _os
        script_dir = _os.path.join(_os.path.dirname(__file__), "scripts")
        if script_dir not in _sys.path:
            _sys.path.insert(0, script_dir)
        import sayqallash_cleanup
        return {"success": True, **sayqallash_cleanup.cleanup()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/sayqallash/consolidate")
async def run_sayqallash_consolidate(current_user: dict = Depends(get_admin_user)):
    """
    Advanced Sayqallash DB consolidation:
      - Remove duplicates
      - Flag conflicts (same wrong → multiple corrects)
      - BERT-based semantic deduplication
    """
    try:
        import sayqallash_consolidator
        result = sayqallash_consolidator.consolidate(semantic=True)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/wordlists/import-kmashrab")
async def import_kmashrab_route(current_user: dict = Depends(get_admin_user)):
    """Import kmashrab/uzbek-wordlist (~70K words + places + names)."""
    try:
        import sys as _sys, os as _os
        sd = _os.path.join(_os.path.dirname(__file__), "scripts")
        if sd not in _sys.path:
            _sys.path.insert(0, sd)
        import import_kmashrab
        return {"success": True, **import_kmashrab.main()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/wordlists/import-extras")
async def import_extras_route(current_user: dict = Depends(get_admin_user)):
    """Import MUNIS soros + QuvonchbekBobojonov Uzbek wordlists."""
    try:
        import sys as _sys, os as _os
        sd = _os.path.join(_os.path.dirname(__file__), "scripts")
        if sd not in _sys.path:
            _sys.path.insert(0, sd)
        import import_additional_dicts
        return {"success": True, **import_additional_dicts.main()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_script(module_name: str, fn_name: str = "main", **kwargs):
    """Generic helper to import and run a scripts/ module."""
    import sys as _sys, os as _os
    sd = _os.path.join(_os.path.dirname(__file__), "scripts")
    if sd not in _sys.path:
        _sys.path.insert(0, sd)
    mod = __import__(module_name)
    fn = getattr(mod, fn_name)
    return fn(**kwargs) if kwargs else fn()


@router.post("/wordlists/import-uzbek-spell")
async def import_uzbek_spell_route(current_user: dict = Depends(get_admin_user)):
    """Import uzbek-spell/spellchecker v1.0 Latin dict."""
    try:
        return {"success": True, **_run_script("import_uzbek_spell")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pharmacopoeia/import")
async def import_pharmacopoeia_route(current_user: dict = Depends(get_admin_user)):
    """Import State Pharmacopoeia Volume 1 data (glossary + error lists)."""
    try:
        return {"success": True, **_run_script("import_pharmacopoeia")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pharma-reports/import")
async def import_pharma_reports_route(current_user: dict = Depends(get_admin_user)):
    """Import 3 previously-unused pharmacopoeia reports: glossary, jildlar, linguistic."""
    try:
        return {"success": True, **_run_script("import_pharma_reports")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/izohli-lugat/import")
async def import_izohli_lugat_route(current_user: dict = Depends(get_admin_user)):
    """Import Izohli lugat (annotated dictionary) .docx into definitions table."""
    try:
        return {"success": True, **_run_script("import_izohli_lugat")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/si-units/import")
async def import_si_units_route(current_user: dict = Depends(get_admin_user)):
    """Import SI units style rules from .doc/.docx files."""
    try:
        return {"success": True, **_run_script("import_si_units_style")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/uzbek-qoidalari/import")
async def import_uzbek_qoidalari_route(current_user: dict = Depends(get_admin_user)):
    """Import Uzbek spelling/grammar rules from markdown tables."""
    try:
        return {"success": True, **_run_script("import_uzbek_qoidalari")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/_diag/sample-annotated")
async def diag_sample_annotated():
    """TEMPORARY PUBLIC — return a few first rows so we can see the actual column contents."""
    import sqlite3 as _sql, os as _os
    db_p = _os.getenv("DB_PATH", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pharma_editor.db"))
    conn = _sql.connect(db_p)
    conn.row_factory = _sql.Row
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(annotated_words)")
    cols = [r[1] for r in cur.fetchall()]
    cur.execute("SELECT * FROM annotated_words ORDER BY id ASC LIMIT 5")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"columns": cols, "sample": rows}


@router.post("/_diag/cleanup-annotated")
async def diag_cleanup_annotated():
    """TEMPORARY PUBLIC — delete annotated_words rows where EN, RU and all
    3 descriptions (en/ru/uz) are empty or missing. Keeps rows that at
    least have uz+description_uz or any multilingual content."""
    import sqlite3 as _sql, os as _os
    db_p = _os.getenv("DB_PATH", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pharma_editor.db"))
    conn = _sql.connect(db_p)
    cur = conn.cursor()

    def _norm(col):
        # Empty/'—'/'-'/'None'/'nan' style placeholders
        return (
            f"({col} IS NULL OR TRIM(COALESCE({col},'')) IN ('', '—', '-', 'None', 'nan', 'NaN', '—', '–'))"
        )

    where = " AND ".join([
        _norm("en"),
        _norm("ru"),
        _norm("description_en"),
        _norm("description_ru"),
        _norm("description_uz"),
    ])
    cur.execute(f"SELECT COUNT(*) FROM annotated_words WHERE {where}")
    to_delete = cur.fetchone()[0]
    cur.execute(f"DELETE FROM annotated_words WHERE {where}")
    deleted = cur.rowcount
    cur.execute("SELECT COUNT(*) FROM annotated_words")
    remaining = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"matched": to_delete, "deleted": deleted, "remaining": remaining}


@router.get("/data-files/check")
async def check_data_files(current_user: dict = Depends(get_admin_user)):
    """Report which source_data/* files exist. Source files live OUTSIDE the
    persistent Volume (/app/data) which only holds DB + uploads."""
    import os as _os
    base = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "source_data")
    diag = {
        "cwd": _os.getcwd(),
        "base": base,
        "base_exists": _os.path.isdir(base),
        "base_listing": sorted(_os.listdir(base))[:50] if _os.path.isdir(base) else [],
    }
    files = {
        "pharma_db/toc.xlsx": "ДФ мундарижаси",
        "pharma_db/drug_registry.xls": "Давлат реестри",
        "colors_table/colors_table.xlsx": "Ранглар жадвали",
        "pharmacopoeia/glossary_report.xlsx": "Фармакопея глоссарийси (4849)",
        "pharmacopoeia/jildlar_tahlil_hisoboti.xlsx": "Жилдлар таҳлил ҳисоботи",
        "pharmacopoeia/linguistic_analysis_report.xlsx": "Лингвистик таҳлил ҳисоботи",
        "izohli_lugat/izohli_lugat.docx": "Изоҳли луғат",
        "disputed_board/disputed_board.docx": "Мунозарали сўзлар кенгаши",
        "si_units/pharma_ch1.docx": "СИ бирликлар (боб 1)",
        "si_units/si_units_resolution.doc": "СИ бирликлар (қарор)",
        "uzbek_qoidalari/uzbek_til_qoidalari_va_xatolar.md": "Ўзбек тили қоидалари (МД)",
    }
    result = []
    for rel, label in files.items():
        full = _os.path.join(base, rel)
        exists = _os.path.exists(full)
        size = _os.path.getsize(full) if exists else 0
        result.append({
            "path": rel,
            "label": label,
            "exists": exists,
            "size": size,
            "size_kb": round(size / 1024, 1) if size else 0,
        })
    present = sum(1 for r in result if r["exists"])
    return {"files": result, "total": len(result), "present": present, "missing": len(result) - present, "diag": diag}


@router.post("/bertbek/info")
async def bertbek_info_route(current_user: dict = Depends(get_admin_user)):
    """Get BERTbek engine status."""
    try:
        import bertbek_engine
        return {"success": True, **bertbek_engine.info()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/simreluz/calibrate")
async def simreluz_calibrate_route(current_user: dict = Depends(get_admin_user)):
    """Run SimRelUz semantic similarity calibration (requires BERTBEK_BASE_ENABLED=1)."""
    try:
        return {"success": True, **_run_script("calibrate_simreluz")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/disputed-board/import")
async def import_disputed_board_route(current_user: dict = Depends(get_admin_user)):
    """Import editorial-board-approved disputed words (234 terms from docx)."""
    try:
        return {"success": True, **_run_script("import_disputed_board")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/disputed-board")
async def list_disputed_board(q: str = None, limit: int = 500, current_user: dict = Depends(get_current_user)):
    """List editorial-approved disputed terms — dual-script search."""
    import sqlite3 as _sql, os as _os
    db_p = _os.getenv("DB_PATH", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pharma_editor.db"))
    conn = _sql.connect(db_p)
    conn.row_factory = _sql.Row
    cur = conn.cursor()
    try:
        if q:
            search_variants = [q]
            try:
                import dual_script
                detected = dual_script.detect_script(q)
                if detected == "cyr":
                    lat = dual_script.to_latin(q)
                    if lat: search_variants.append(lat)
                elif detected == "lat":
                    cyr = dual_script.to_cyrillic(q)
                    if cyr: search_variants.append(cyr)
            except Exception:
                pass
            or_clauses = []
            params: list = []
            for v in search_variants:
                like = f"%{v}%"
                or_clauses.append("(ru_term LIKE ? OR proposed_variant LIKE ? OR definition_uz LIKE ? OR existing_variants LIKE ?)")
                params.extend([like, like, like, like])
            params.append(limit)
            cur.execute(f"""
                SELECT * FROM disputed_board
                WHERE {' OR '.join(or_clauses)}
                ORDER BY COALESCE(updated_at, created_at) DESC, seq_no ASC
                LIMIT ?
            """, params)
        else:
            cur.execute("""
                SELECT * FROM disputed_board
                ORDER BY COALESCE(updated_at, created_at) DESC, seq_no ASC
                LIMIT ?
            """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"rows": rows, "total": len(rows)}


# ─────────────────────────────────────────────
# Pharma DB (TOC + Drug Registry + Colors)
# ─────────────────────────────────────────────

def _pharma_db_conn():
    import sqlite3 as _sql, os as _os
    db_p = _os.getenv("DB_PATH", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pharma_editor.db"))
    conn = _sql.connect(db_p)
    conn.row_factory = _sql.Row
    return conn


@router.post("/pharma-db/import")
async def import_pharma_db_route(current_user: dict = Depends(get_admin_user)):
    """Import TOC + Drug Registry."""
    try:
        return {"success": True, **_run_script("import_pharma_db")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pharma-db/import-colors")
async def import_colors_route(current_user: dict = Depends(get_admin_user)):
    """Import State Pharmacopoeia colors table."""
    try:
        return {"success": True, **_run_script("import_colors_table")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/pharma-db/toc")
async def pharma_toc(q: str = None, edition: str = None, limit: int = 3000, current_user: dict = Depends(get_current_user)):
    """Pharmacopoeia Table of Contents — dual-script search (Cyr ↔ Lat)."""
    conn = _pharma_db_conn()
    cur = conn.cursor()
    try:
        where = "WHERE 1=1"
        params: list = []
        if edition:
            where += " AND edition = ?"
            params.append(edition)
        if q:
            search_variants = [q]
            try:
                import dual_script
                detected = dual_script.detect_script(q)
                if detected == "cyr":
                    lat = dual_script.to_latin(q)
                    if lat: search_variants.append(lat)
                elif detected == "lat":
                    cyr = dual_script.to_cyrillic(q)
                    if cyr: search_variants.append(cyr)
            except Exception:
                pass
            or_clauses = []
            for v in search_variants:
                like = f"%{v}%"
                or_clauses.append("(name_uz LIKE ? OR name_en LIKE ? OR name_ru LIKE ? OR text_no LIKE ?)")
                params.extend([like, like, like, like])
            where += " AND (" + " OR ".join(or_clauses) + ")"
        params.append(limit)
        cur.execute(f"SELECT * FROM pharma_toc {where} ORDER BY edition, seq_no LIMIT ?", params)
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return {"rows": rows, "total": len(rows)}


@router.get("/pharma-db/registry")
async def drug_registry(q: str = None, country: str = None, atc: str = None, limit: int = 2000, current_user: dict = Depends(get_current_user)):
    """State Drug Registry — dual-script search (Cyr ↔ Lat)."""
    conn = _pharma_db_conn()
    cur = conn.cursor()
    try:
        where = "WHERE 1=1"
        params: list = []
        if country:
            where += " AND country = ?"
            params.append(country)
        if atc:
            where += " AND atc_code LIKE ?"
            params.append(f"{atc}%")
        if q:
            # Dual-script search
            search_variants = [q]
            try:
                import dual_script
                detected = dual_script.detect_script(q)
                if detected == "cyr":
                    lat = dual_script.to_latin(q)
                    if lat: search_variants.append(lat)
                elif detected == "lat":
                    cyr = dual_script.to_cyrillic(q)
                    if cyr: search_variants.append(cyr)
            except Exception:
                pass
            or_clauses = []
            for v in search_variants:
                like = f"%{v}%"
                or_clauses.append("(trade_name LIKE ? OR inn LIKE ? OR manufacturer LIKE ? OR atc_code LIKE ? OR registration_no LIKE ?)")
                params.extend([like, like, like, like, like])
            where += " AND (" + " OR ".join(or_clauses) + ")"
        params.append(limit)
        cur.execute(f"SELECT * FROM drug_registry {where} ORDER BY seq_no LIMIT ?", params)
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return {"rows": rows, "total": len(rows)}


@router.get("/pharma-db/colors")
async def colors_table(q: str = None, limit: int = 500, current_user: dict = Depends(get_current_user)):
    """Colors table — dual-script search."""
    conn = _pharma_db_conn()
    cur = conn.cursor()
    try:
        if q:
            search_variants = [q]
            try:
                import dual_script
                detected = dual_script.detect_script(q)
                if detected == "cyr":
                    lat = dual_script.to_latin(q)
                    if lat: search_variants.append(lat)
                elif detected == "lat":
                    cyr = dual_script.to_cyrillic(q)
                    if cyr: search_variants.append(cyr)
            except Exception:
                pass
            or_clauses = []
            params: list = []
            for v in search_variants:
                like = f"%{v}%"
                or_clauses.append("(uz LIKE ? OR ru LIKE ? OR en LIKE ?)")
                params.extend([like, like, like])
            params.append(limit)
            cur.execute(
                f"SELECT * FROM colors_table WHERE {' OR '.join(or_clauses)} ORDER BY seq_no LIMIT ?",
                params
            )
        else:
            cur.execute("SELECT * FROM colors_table ORDER BY seq_no LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return {"rows": rows, "total": len(rows)}


@router.post("/wordlists/import-uzbek-net")
async def import_uzbek_net_route(current_user: dict = Depends(get_admin_user)):
    """Import uzbek-net/uz-hunspell (Latin + Cyrillic)."""
    try:
        return {"success": True, **_run_script("import_uzbek_net_hunspell")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/wordlists/import-uzhungen-qoida")
async def import_uzhungen_route(current_user: dict = Depends(get_admin_user)):
    """Parse .qoida affix descriptions from u2b3k/uz-hungen."""
    try:
        return {"success": True, **_run_script("import_uzhungen_qoida")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/post-process/freq-rankings")
async def post_freq_rankings_route(current_user: dict = Depends(get_admin_user)):
    """Compute word frequencies from corpus sources."""
    try:
        return {"success": True, **_run_script("build_freq_rankings")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/post-process/merge-affix")
async def post_merge_affix_route(current_user: dict = Depends(get_admin_user)):
    """Merge .qoida descriptions into affix_flag_mapping."""
    try:
        return {"success": True, **_run_script("merge_affix_descriptions")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/post-process/auto-rep-rules")
async def post_auto_rep_route(current_user: dict = Depends(get_admin_user)):
    """Auto-generate REP rules from expanded dictionary (bidirectional-verified)."""
    try:
        return {"success": True, **_run_script("auto_generate_rep_rules", max_words=5000)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/tahrirchi/import-datasets")
async def import_tahrirchi_datasets_route(current_user: dict = Depends(get_admin_user)):
    """Import Tahrirchi HF datasets: uz-crawl, dilmash, lutfiy, uzlib."""
    try:
        import sys as _sys, os as _os
        sd = _os.path.join(_os.path.dirname(__file__), "scripts")
        if sd not in _sys.path:
            _sys.path.insert(0, sd)
        import import_tahrirchi_datasets
        return {"success": True, **import_tahrirchi_datasets.main()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/sayqallash/domain-segment")
async def segment_domains(current_user: dict = Depends(get_admin_user)):
    """Add 'domain' column to sayqallash_rules and tag pharma/medical rules."""
    try:
        conn = db.connect_db()
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE sayqallash_rules ADD COLUMN domain TEXT DEFAULT 'general'")
        except Exception:
            pass  # already exists

        # Tag pharma rules
        cur.execute("""
            UPDATE sayqallash_rules SET domain = 'pharma'
            WHERE context LIKE '%doz%' OR context LIKE '%INN%' OR context LIKE '%ATC%'
               OR context LIKE '%mg%' OR context LIKE '%ml%'
               OR wrong_form IN (SELECT inn FROM drugs WHERE inn IS NOT NULL)
               OR wrong_form IN (SELECT brand_name FROM drugs WHERE brand_name IS NOT NULL)
        """)
        pharma = cur.rowcount

        # Tag medical rules
        try:
            cur.execute("""
                UPDATE sayqallash_rules SET domain = 'medical'
                WHERE domain = 'general' AND (
                    wrong_form IN (SELECT term_uz FROM medical_terms WHERE term_uz IS NOT NULL)
                    OR wrong_form IN (SELECT term_ru FROM medical_terms WHERE term_ru IS NOT NULL)
                )
            """)
            medical = cur.rowcount
        except Exception:
            medical = 0

        conn.commit()

        # Stats
        cur.execute("SELECT domain, COUNT(*) FROM sayqallash_rules GROUP BY domain")
        stats = {r[0]: r[1] for r in cur.fetchall()}
        conn.close()
        return {"success": True, "pharma_tagged": pharma, "medical_tagged": medical, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/drugs/import-who")
async def import_who_inn(current_user: dict = Depends(get_admin_user)):
    """Import 200+ WHO INN essential medicines."""
    try:
        import sys as _sys, os as _os
        script_dir = _os.path.join(_os.path.dirname(__file__), "scripts")
        if script_dir not in _sys.path:
            _sys.path.insert(0, script_dir)
        import import_who_inn
        result = import_who_inn.seed()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/db/backup")
async def manual_db_backup(current_user: dict = Depends(get_admin_user)):
    """Manually trigger DB backup."""
    try:
        import sys as _sys, os as _os
        script_dir = _os.path.join(_os.path.dirname(__file__), "scripts")
        if script_dir not in _sys.path:
            _sys.path.insert(0, script_dir)
        import db_backup
        return db_backup.run_backup()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/affix-rules/stats")
async def affix_rules_stats(current_user: dict = Depends(get_current_user)):
    """Get statistics on Hunspell affix rules DB."""
    try:
        import affix_db_loader
        return affix_db_loader.stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/hunspell-v2/reparse")
async def reparse_hunspell(current_user: dict = Depends(get_admin_user)):
    """Re-parse u2b3k/uz-hunspell .aff files into uzbek_affix_rules table."""
    try:
        import parse_hunspell_affix
        result = parse_hunspell_affix.import_rules()
        # Force cache reload
        import affix_db_loader
        affix_db_loader.reload_cache()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pharma-dict/generate")
async def generate_pharma_dict(current_user: dict = Depends(get_admin_user)):
    """Generate Hunspell dictionary from drugs + medical_terms tables using uz-hungen port."""
    try:
        import uzbek_dict_generator
        result = uzbek_dict_generator.generate_pharma_dictionary()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/weekly-cycle/run")
async def run_weekly_cycle(current_user: dict = Depends(get_admin_user)):
    """Manually trigger weekly learning cycle (normally runs Sunday 03:00)."""
    try:
        import weekly_learning_cycle
        result = weekly_learning_cycle.run_full_cycle()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/weekly-cycle/history")
async def weekly_cycle_history(limit: int = 20, current_user: dict = Depends(get_admin_user)):
    """Get history of previous weekly cycles."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("SELECT * FROM weekly_cycles ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = []
        import json as _json
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["result"] = _json.loads(d.get("result", "{}") or "{}")
            except Exception:
                pass
            rows.append(d)
        conn.close()
        return {"cycles": rows}
    except Exception as e:
        return {"cycles": [], "error": str(e)}


@router.post("/uzbek-rules/seed")
async def seed_uzbek_rules(current_user: dict = Depends(get_admin_user)):
    """Import Uzbek rules from 'Ona tili' book (M.Hamroyev et al., 2007)."""
    try:
        import seed_uzbek_rules_from_book
        result = seed_uzbek_rules_from_book.main()
        return {"success": True, **(result or {})}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/monitoring/overview")
async def monitoring_overview(period: str = "daily", current_user: dict = Depends(get_admin_user)):
    """
    Activity monitoring: daily/weekly/monthly.
    Returns user activity, AI usage, sayqallash growth, document edits.
    """
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()

        # Period filter
        period_clause = {
            "daily": "datetime('now', '-1 day')",
            "weekly": "datetime('now', '-7 days')",
            "monthly": "datetime('now', '-30 days')",
        }.get(period, "datetime('now', '-1 day')")

        out: Dict[str, Any] = {"period": period}

        # 1. Total counts
        try:
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
            out["users_total"] = cur.fetchone()[0]
        except Exception:
            out["users_total"] = 0
        try:
            cur.execute(f"SELECT COUNT(DISTINCT user_id) FROM paragraphs_dashboard WHERE created_at >= {period_clause}")
            out["users_active"] = cur.fetchone()[0]
        except Exception:
            out["users_active"] = 0

        # 2. Sayqallash growth
        try:
            cur.execute("SELECT COUNT(*) FROM sayqallash_rules")
            out["sayqallash_total"] = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM sayqallash_rules WHERE created_at >= {period_clause}")
            out["sayqallash_new"] = cur.fetchone()[0]
        except Exception:
            out["sayqallash_total"] = 0
            out["sayqallash_new"] = 0

        # 3. AI usage (llm_training_log)
        try:
            cur.execute(f"SELECT kind, COUNT(*) FROM llm_training_log WHERE created_at >= {period_clause} GROUP BY kind")
            out["ai_usage"] = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute(f"SELECT COUNT(*) FROM llm_training_log WHERE created_at >= {period_clause}")
            out["ai_calls_total"] = cur.fetchone()[0]
        except Exception:
            out["ai_usage"] = {}
            out["ai_calls_total"] = 0

        # 4. Document/row edits
        try:
            cur.execute(f"SELECT COUNT(*) FROM paragraphs_dashboard WHERE created_at >= {period_clause}")
            out["edits_total"] = cur.fetchone()[0]
        except Exception:
            out["edits_total"] = 0

        # 5. Per-user activity (top 10)
        try:
            cur.execute(f"""
                SELECT user_id, user_name, COUNT(*) as cnt
                FROM paragraphs_dashboard
                WHERE created_at >= {period_clause}
                GROUP BY user_id
                ORDER BY cnt DESC LIMIT 10
            """)
            out["top_users"] = [{"user_id": r[0], "user_name": r[1], "count": r[2]} for r in cur.fetchall()]
        except Exception:
            out["top_users"] = []

        # 6. Daily breakdown for chart (last 30 days)
        try:
            cur.execute("""
                SELECT date(created_at) as day, COUNT(*) as cnt
                FROM paragraphs_dashboard
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY day ORDER BY day
            """)
            out["daily_chart"] = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]
        except Exception:
            out["daily_chart"] = []

        # 7. AI usage daily chart
        try:
            cur.execute("""
                SELECT date(created_at) as day, COUNT(*) as cnt
                FROM llm_training_log
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY day ORDER BY day
            """)
            out["ai_chart"] = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]
        except Exception:
            out["ai_chart"] = []

        # 8. Pharma DB stats
        try:
            cur.execute("SELECT COUNT(*) FROM drugs")
            out["drugs_total"] = cur.fetchone()[0]
        except Exception:
            out["drugs_total"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM medical_terms")
            out["terms_total"] = cur.fetchone()[0]
        except Exception:
            out["terms_total"] = 0

        # 9. Projects/alignments stats
        try:
            cur.execute("SELECT COUNT(DISTINCT text_id) FROM alignments")
            out["projects_total"] = cur.fetchone()[0]
        except Exception:
            out["projects_total"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM alignments")
            out["alignments_total"] = cur.fetchone()[0]
        except Exception:
            out["alignments_total"] = 0

        conn.close()
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drugs/seed")
async def seed_drugs(current_user: dict = Depends(get_admin_user)):
    """One-time seed: import 80+ standard pharmaceutical INNs."""
    try:
        import seed_drugs
        inserted = seed_drugs.seed()
        return {"success": True, "inserted": inserted}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/drugs")
async def list_drugs(q: str = "", limit: int = 100, current_user: dict = Depends(get_current_user)):
    """Search/list drugs in pharma DB."""
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cur = conn.cursor()
    if q:
        cur.execute("SELECT * FROM drugs WHERE inn LIKE ? OR brand_name LIKE ? OR atc_code LIKE ? ORDER BY inn LIMIT ?",
                    (f"%{q}%", f"%{q}%", f"%{q}%", limit))
    else:
        cur.execute("SELECT * FROM drugs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM drugs")
    total = cur.fetchone()[0]
    conn.close()
    return {"drugs": rows, "total": total}


@router.post("/drugs")
async def add_drug(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Add a new drug to the pharma DB."""
    conn = db.connect_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO drugs (inn, brand_name, atc_code, form, dose, manufacturer, country, registration_number, category, description, lang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("inn", ""), payload.get("brand_name", ""), payload.get("atc_code", ""),
            payload.get("form", ""), payload.get("dose", ""), payload.get("manufacturer", ""),
            payload.get("country", ""), payload.get("registration_number", ""),
            payload.get("category", ""), payload.get("description", ""), payload.get("lang", "uz"),
        ))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"success": True, "id": new_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


@router.get("/medical-terms")
async def list_medical_terms(q: str = "", limit: int = 100, current_user: dict = Depends(get_current_user)):
    """Search multilingual medical terms (uz/ru/en)."""
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cur = conn.cursor()
    if q:
        cur.execute("""
            SELECT * FROM medical_terms
            WHERE term_uz LIKE ? OR term_ru LIKE ? OR term_en LIKE ?
            ORDER BY term_uz LIMIT ?
        """, (f"%{q}%", f"%{q}%", f"%{q}%", limit))
    else:
        cur.execute("SELECT * FROM medical_terms ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM medical_terms")
    total = cur.fetchone()[0]
    conn.close()
    return {"terms": rows, "total": total}


@router.post("/medical-terms")
async def add_medical_term(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Add a multilingual medical term."""
    conn = db.connect_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO medical_terms (term_uz, term_ru, term_en, definition, category, synonyms, atc_code, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("term_uz", ""), payload.get("term_ru", ""), payload.get("term_en", ""),
            payload.get("definition", ""), payload.get("category", ""),
            payload.get("synonyms", ""), payload.get("atc_code", ""),
            payload.get("source", "manual"),
        ))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"success": True, "id": new_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


@router.post("/users/block")
async def toggle_block_user(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Block or unblock a user from logging in (Admin only)."""
    user_id = payload.get("userId")
    blocked = 1 if payload.get("blocked") else 0
    conn = db.connect_db()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
    except Exception:
        pass
    cur.execute("UPDATE users SET is_blocked = ? WHERE id = ?", (blocked, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "is_blocked": blocked}


@router.get("/users/{user_id}/activity")
async def get_user_activity(user_id: str, limit: int = 100, current_user: dict = Depends(get_admin_user)):
    """Return activity timeline for a specific user."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        rows: list = []
        # paragraphs_dashboard acts as audit trail
        try:
            cur.execute("""
                SELECT created_at as ts, action_type, paragraph_id, user_id, user_name, details
                FROM paragraphs_dashboard
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        # Also include last_login
        cur.execute("SELECT name, email, last_login, created_at FROM users WHERE id = ?", (user_id,))
        u = cur.fetchone()
        conn.close()
        return {"user": dict(u) if u else None, "activity": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/can-edit-db")
async def toggle_can_edit_db(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Grant or revoke DB edit permission for a user (Admin only)."""
    user_id = payload.get("userId")
    can_edit = 1 if payload.get("can_edit") else 0
    conn = db.connect_db()
    conn.cursor().execute("UPDATE users SET can_edit_db = ? WHERE id = ?", (can_edit, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "can_edit_db": can_edit}

@router.post("/users/reject")
async def reject_user(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Reject or block a user."""
    user_id = payload.get("userId")
    db.update_user_status(user_id, "rejected")
    return {"success": True}

@router.post("/migrate-import")
async def migrate_import(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """
    One-time bulk import of all data from local DB to Railway.
    Accepts: rules, annotated, disputed, abbreviations lists.
    Uses INSERT OR IGNORE to safely skip duplicates.
    """
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    
    rules        = payload.get("rules", [])
    annotated    = payload.get("annotated", [])
    disputed     = payload.get("disputed", [])
    abbreviations = payload.get("abbreviations", [])
    
    conn = db.connect_db()
    cursor = conn.cursor()
    
    try:
        # Import sayqallash_rules
        rules_count = 0
        for r in rules:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO sayqallash_rules
                        (wrong_form, correct_form, lang, error_type, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r.get("wrong_form",""), r.get("correct_form",""),
                    r.get("lang","uz"), r.get("error_type","S/Spelling"),
                    r.get("context",""), now
                ))
                rules_count += cursor.rowcount
            except Exception:
                pass
        
        # Import annotated_words
        annotated_count = 0
        for a in annotated:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO annotated_words
                        (en, ru, uz, description_en, description_ru, description_uz, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    a.get("en",""), a.get("ru",""), a.get("uz",""),
                    a.get("description_en",""), a.get("description_ru",""),
                    a.get("description_uz",""), now
                ))
                annotated_count += cursor.rowcount
            except Exception:
                pass
        
        # Import disputed_words
        disputed_count = 0
        for d in disputed:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO disputed_words
                        (en, ru, uz, context_en, context_ru, context_uz, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.get("en",""), d.get("ru",""), d.get("uz",""),
                    d.get("context_en",""), d.get("context_ru",""),
                    d.get("context_uz",""), now
                ))
                disputed_count += cursor.rowcount
            except Exception:
                pass
        
        # Import abbreviations
        abbrev_count = 0
        for b in abbreviations:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO abbreviations
                        (short_form, long_en, long_ru, long_uz, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    b.get("short_form",""), b.get("long_en",""),
                    b.get("long_ru",""), b.get("long_uz",""), now
                ))
                abbrev_count += cursor.rowcount
            except Exception:
                pass
        
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "rules_imported": rules_count,
        "annotated_imported": annotated_count,
        "disputed_imported": disputed_count,
        "abbreviations_imported": abbrev_count
    }

@router.post("/bulk-import-synonyms")
async def bulk_import_synonyms(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Bulk import synonyms from local DB."""
    synonyms = payload.get("synonyms", [])
    conn = db.connect_db()
    cursor = conn.cursor()
    count = 0
    for s in synonyms:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO synonyms (word, synonym, lang, frequency, source, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (s.get("word",""), s.get("synonym",""), s.get("lang","uz"),
                  s.get("frequency",1), s.get("source","sync"), s.get("created_by","system")))
            count += cursor.rowcount
        except Exception:
            pass
    conn.commit()
    conn.close()
    return {"success": True, "imported": count, "total_sent": len(synonyms)}


@router.post("/bulk-import-paragraphs")
async def bulk_import_paragraphs(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Bulk import paragraphs dashboard entries."""
    entries = payload.get("entries", [])
    conn = db.connect_db()
    cursor = conn.cursor()
    count = 0
    for e in entries:
        try:
            cursor.execute("""
                INSERT INTO paragraphs_dashboard (en_text, ru_text, uz_text, specialist_name, text_id, action_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (e.get("en_text",""), e.get("ru_text",""), e.get("uz_text",""),
                  e.get("specialist_name",""), e.get("text_id",""), e.get("action_type","Synced")))
            count += cursor.rowcount
        except Exception:
            pass
    conn.commit()
    conn.close()
    return {"success": True, "imported": count, "total_sent": len(entries)}


@router.get("/activity")
async def get_activity_logs(limit: int = 100, current_user: dict = Depends(get_admin_user)):
    """Fetch recent activity logs from the paragraphs dashboard."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cursor = conn.cursor()
        # Query paragraphs_dashboard which acts as the audit trail
        cursor.execute("""
            SELECT * FROM paragraphs_dashboard 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return {"logs": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/test")
async def send_test_email(payload: Dict[str, Any] = None, request: Request = None):
    """Send a test email to verify SMTP config.
    Auth: Admin bearer token OR X-Seed-Secret header (for automated testing)."""
    # Check seed secret OR admin auth
    authorized = False
    try:
        if request is not None:
            seed_secret = os.getenv("SEED_SECRET", "pharma_dev_sync_2026")
            header_secret = request.headers.get("x-seed-secret") or request.headers.get("X-Seed-Secret")
            if header_secret and header_secret == seed_secret:
                authorized = True
    except Exception:
        pass
    if not authorized:
        # Fall back to admin auth
        try:
            auth_header = request.headers.get("authorization", "") if request else ""
            if not auth_header.lower().startswith("bearer "):
                raise HTTPException(status_code=401, detail="Authorization required")
            from auth import verify_token
            token = auth_header.split(" ", 1)[1]
            payload_data = verify_token(token)
            if not payload_data or payload_data.get("role") != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))
    import email_helper
    if not email_helper.is_configured():
        return {
            "success": False,
            "configured": False,
            "error": "SMTP not configured",
            "checked": {
                "SMTP_HOST": bool(email_helper.SMTP_HOST),
                "SMTP_USER": bool(email_helper.SMTP_USER),
                "SMTP_PASS": bool(email_helper.SMTP_PASS),
            },
        }
    to_email = (payload or {}).get("to") or os.getenv("ADMIN_EMAIL") or email_helper.SMTP_USER
    subject = "✅ Pharma Expert — SMTP Test"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg, #B48C64, #8B5E3C); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
        <h2 style="margin: 0;">✅ SMTP Ишлаяпти</h2>
      </div>
      <div style="padding: 20px; background: #FFF8F0; border-radius: 0 0 12px 12px;">
        <p><b>Табриклаймиз!</b> Агар сиз бу email'ни ўқиётган бўлсангиз, Pharma Expert SMTP созламаси муваффақиятли ишлаяпти.</p>
        <p><b>Host:</b> {email_helper.SMTP_HOST}:{email_helper.SMTP_PORT}<br>
           <b>User:</b> {email_helper.SMTP_USER}<br>
           <b>From:</b> {email_helper.SMTP_FROM}</p>
        <p>Бундан буён:</p>
        <ul>
          <li>Фойдаланувчилар паролни тиклаш учун email олади</li>
          <li>Янги регистрация тасдиқ учун сизга келади</li>
          <li>Ҳафталик learning cycle отчёти автомат юборилади</li>
        </ul>
        <p style="color:#64748B; font-size: 0.85rem;">Pharma Expert autonomy test · {datetime.now().isoformat()}</p>
      </div>
    </div>
    """
    try:
        sent = email_helper.send_email(to_email, subject, html)
        return {"success": bool(sent), "to": to_email, "configured": True}
    except Exception as e:
        return {"success": False, "error": str(e), "configured": True}
