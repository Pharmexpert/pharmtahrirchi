from fastapi import APIRouter, Depends, HTTPException, Response, Request
from typing import List, Dict, Any
import db
from auth import get_admin_user, get_current_user, can_edit_db
import pandas as pd
import io

router = APIRouter(prefix="/api/admin", tags=["admin"])

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
    """Retrieve all rules for administration with filtering (read-only for all users)."""
    rules = db.get_all_rules(lang or 'uz', limit=100000)
    if q:
        q = q.lower()
        rules = [r for r in rules if q in r['wrong_form'].lower() or q in r['correct_form'].lower() or q in (r.get('context') or '').lower()]
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

@router.get("/db-stats")
async def get_db_stats(current_user: dict = Depends(get_current_user)):
    """Detailed database statistics for admin reporting."""
    conn = db.connect_db()
    cursor = conn.cursor()
    stats = {}
    for table in ['projects', 'alignments', 'sayqallash_rules', 'users', 'paragraphs_dashboard']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except: stats[table] = 0
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
    """Approve or update a user status."""
    user_id = payload.get("userId")
    # Support both "approve" (legacy) and direct status updates
    status = payload.get("status", "approved")
    db.update_user_status(user_id, status)
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
