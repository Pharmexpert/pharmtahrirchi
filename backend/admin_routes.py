from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List, Dict, Any
import db
from auth import get_admin_user
import pandas as pd
import io

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/rules/export")
async def export_rules_xlsx(lang: str = None, current_user: dict = Depends(get_admin_user)):
    """Export all correction rules to an XLSX file."""
    try:
        rules = db.get_all_rules(lang or 'uz', limit=10000)
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
async def get_all_rules(lang: str = None, q: str = None, current_user: dict = Depends(get_admin_user)):
    """Retrieve all rules for administration with filtering."""
    rules = db.get_all_rules(lang or 'uz', limit=2000)
    if q:
        q = q.lower()
        rules = [r for r in rules if q in r['wrong_form'].lower() or q in r['correct_form'].lower() or q in (r['context'] or '').lower()]
    return {"rules": rules}

@router.post("/rules")
async def upsert_rule(payload: Dict[str, Any], current_user: dict = Depends(get_admin_user)):
    """Add or update a correction rule."""
    rule_id = payload.get("id")
    if rule_id:
        db.update_sayqallash_rule(rule_id, payload)
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
        return {"status": "created"}

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, current_user: dict = Depends(get_admin_user)):
    """Delete a correction rule."""
    db.delete_sayqallash_rule(rule_id)
    return {"status": "deleted"}

@router.get("/db-stats")
async def get_db_stats(current_user: dict = Depends(get_admin_user)):
    """Detailed database statistics for admin reporting."""
    conn = db.connect_db()
    cursor = conn.cursor()
    stats = {}
    for table in ['projects', 'alignments', 'sayqallash_rules', 'users']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]
    import os
    pharma_db_size = os.path.getsize(db.DB_PATH) / (1024 * 1024)
    tahrirchi_db_size = os.path.getsize(db.TAHRIRCHI_DB_PATH) / (1024 * 1024) if os.path.exists(db.TAHRIRCHI_DB_PATH) else 0
    conn.close()
    return {
        "counts": stats,
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
