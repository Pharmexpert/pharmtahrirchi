import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import db
from auth import get_current_user
from processor import export_to_docx

logger = logging.getLogger("projects")

BACKEND_DIR = os.environ.get("BACKEND_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DIR = os.path.join(BACKEND_DIR, "temp_files")

router = APIRouter(tags=["projects"])


@router.post("/api/save")
async def save_data(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        project_id = payload.get("project_id", "default")
        data = payload.get("data", [])
        specialist = payload.get("specialist_name", current_user.get("name", "Aniqlanmagan"))

        db.save_alignments(project_id, data, user_id=current_user["id"])
        db.update_project_metadata(project_id, specialist, user_id=current_user["id"])

        for row in data:
            if row.get("type") == "content" and (row.get("ru_proposed") or row.get("uz_proposed")):
                try:
                    db.record_dashboard_entry(
                        en=row.get("en", ""),
                        ru=row.get("ru_proposed", row.get("ru_v1", "")),
                        uz=row.get("uz_proposed", row.get("uz_v1", "")),
                        specialist=specialist,
                        text_id=project_id,
                        action_type="Bulk Save"
                    )
                except Exception as de:
                    print(f"Dashboard recording error for row: {de}")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/export-pdf")
async def export_project_pdf(project_id: str, current_user: Dict = Depends(get_current_user)):
    """Export project as PDF using reportlab (3-column landscape table)."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        data = db.get_history(project_id)
        if not data:
            raise HTTPException(status_code=404, detail="Project not found")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                                leftMargin=10*mm, rightMargin=10*mm,
                                topMargin=10*mm, bottomMargin=10*mm)

        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.fontSize = 8
        normal.leading = 10

        # Build table data
        rows = [['№', 'ENGLISH', 'РУССКИЙ', 'ЎЗБЕКЧА']]
        for i, r in enumerate(data, 1):
            en = r.get('en_text', '') or ''
            ru = r.get('confirmed_ru_text') or r.get('ru_proposed') or r.get('ru_v1') or ''
            uz = r.get('confirmed_uz_text') or r.get('uz_proposed') or r.get('uz_v1') or ''
            rows.append([
                str(i),
                Paragraph(en[:500], normal),
                Paragraph(ru[:500], normal),
                Paragraph(uz[:500], normal),
            ])

        col_widths = [15*mm, 90*mm, 90*mm, 90*mm]
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))

        doc.build([table])
        buf.seek(0)

        return FileResponse(
            path=None,
            media_type="application/pdf",
            filename=f"PharmaExpert_{project_id}.pdf"
        ) if False else __pdf_response(buf, project_id)
    except ImportError:
        raise HTTPException(status_code=503, detail="reportlab not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def __pdf_response(buf, project_id):
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="PharmaExpert_{project_id}.pdf"'}
    )


@router.get("/api/projects/{project_id}/export")
async def export_project_live(project_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        data = db.get_history(project_id)
        if not data:
            raise HTTPException(status_code=404, detail="Project not found")

        output_path = os.path.abspath(os.path.join(TEMP_DIR, f"live_export_{project_id}.docx"))
        export_to_docx(data, output_path)

        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"PharmaExpert_{project_id}.docx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/polishing-summary")
async def get_polishing_summary(project_id: str, current_user: Dict = Depends(get_current_user)):
    summary = db.get_project_polishing_summary(project_id)
    if not summary:
        return {"status": "none"}
    return {"status": "success", "summary": summary}


@router.post("/api/projects/{project_id}/finish")
async def finish_project(project_id: str, payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        data = payload.get("data", [])
        specialist = payload.get("specialist_name", current_user.get("name", "Aniqlanmagan"))

        if data:
            db.save_alignments(project_id, data, user_id=current_user["id"])

        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET status = 'finished', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

        db.record_dashboard_entry(
            en="[PROJECT FINISHED]",
            ru="Проект завершен",
            uz="Лойиҳа якунланди",
            specialist=specialist,
            text_id=project_id,
            action_type="Project Finished"
        )

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/preview")
async def preview_project(project_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        data = db.get_history(project_id)
        return {"alignments": data[:50]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/save-row")
async def save_single_row(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        new_id = db.save_single_row(payload, user_id=current_user["id"])

        try:
            db.record_dashboard_entry(
                en=payload.get("en", ""),
                ru=payload.get("ru_proposed", ""),
                uz=payload.get("uz_proposed", ""),
                specialist=payload.get("specialist_name", current_user.get("name", "Aniqlanmagan")),
                text_id=payload.get("text_id", ""),
                action_type=payload.get("action_type", "Manual Edit")
            )
        except Exception as de:
            print(f"Dashboard recording error: {de}")

        return {"status": "success", "new_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard/all")
async def get_dashboard_all(current_user: Dict = Depends(get_current_user)):
    try:
        entries = db.get_dashboard_entries()
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/dashboard/record")
async def record_dashboard_manual(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        db.record_dashboard_entry(
            en=payload.get("en"),
            ru=payload.get("ru"),
            uz=payload.get("uz"),
            specialist=payload.get("specialist", current_user.get("name")),
            text_id=payload.get("text_id"),
            action_type=payload.get("action_type", "Manual Edit")
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/dashboard/{entry_id}")
async def delete_dashboard_entry(entry_id: int, current_user: Dict = Depends(get_current_user)):
    """Delete a dashboard entry by ID."""
    conn = db.connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM paragraphs_dashboard WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@router.get("/api/user/me")
async def get_my_profile(current_user: Dict = Depends(get_current_user)):
    return current_user


@router.put("/api/user/me")
async def update_my_profile(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        db.update_user_profile(current_user["id"], payload)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects")
async def list_projects(current_user: Dict = Depends(get_current_user)):
    projects = db.list_projects()
    return {"projects": projects}


@router.delete("/api/projects/{project_id}")
async def delete_project_api(project_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        file_path = db.get_project_file_path(project_id)
        db.delete_project(project_id)

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                if file_path.lower().endswith(".pdf"):
                    docx_path = file_path.rsplit(".", 1)[0] + ".docx"
                    if os.path.exists(docx_path):
                        os.remove(docx_path)
            except Exception as fe:
                logger.error(f"Error deleting physical file: {fe}")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/delete-row/{text_id}/{sentence_no}")
async def delete_row(text_id: str, sentence_no: int, current_user: Dict = Depends(get_current_user)):
    try:
        db.delete_row(sentence_no, text_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/history/{text_id}")
@router.get("/api/alignments/{text_id}")
async def get_history(text_id: str):
    data = db.get_history(text_id)
    return {"alignments": data}


@router.post("/api/export")
async def export_data(payload: Dict[str, Any]):
    filename = payload.get("filename", "aligned_output.docx")
    data = payload.get("data", [])
    file_basename = os.path.basename(filename)
    output_path = os.path.abspath(os.path.join(TEMP_DIR, f"confirmed_{file_basename}"))
    try:
        export_to_docx(data, output_path)
        download_name = f"confirmed_{file_basename}"
        if not download_name.endswith(".docx"):
            download_name += ".docx"
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/specialists")
async def get_specialists():
    try:
        names = db.get_unique_specialists()
        return {"specialists": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/synonyms")
async def get_synonyms_list(word: str = None, lang: str = None, grouped: str = None, current_user: Dict = Depends(get_current_user)):
    syns = db.get_synonyms(word=word, lang=lang, limit=10000000)

    if grouped == "true":
        # Group synonyms by word: word → [synonym1, synonym2, ...]
        from collections import defaultdict
        groups = defaultdict(lambda: {"synonyms": [], "lang": "", "total_freq": 0, "ids": []})
        for s in syns:
            key = (s["word"], s.get("lang", "uz"))
            g = groups[key]
            g["word"] = s["word"]
            g["lang"] = s.get("lang", "uz")
            g["synonyms"].append({"id": s["id"], "synonym": s["synonym"], "frequency": s.get("frequency", 0), "source": s.get("source", "")})
            g["total_freq"] += s.get("frequency", 0)
            g["ids"].append(s["id"])

        result = sorted(groups.values(), key=lambda x: x["word"].lower())
        return {"groups": result, "total_words": len(result), "total_synonyms": len(syns)}

    return {"synonyms": syns, "total": len(syns)}


@router.post("/api/synonyms/save")
async def save_synonym_endpoint(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    word = payload.get("word", "").strip()
    synonym = payload.get("synonym", "").strip()
    lang = payload.get("lang", "uz")
    if not word or not synonym:
        raise HTTPException(status_code=400, detail="word and synonym required")
    db.save_synonym(word, synonym, lang, source='manual', created_by=current_user.get("name", ""))
    return {"status": "saved"}


@router.put("/api/synonyms/{syn_id}")
async def update_synonym_endpoint(syn_id: int, payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Update a synonym's word or synonym text."""
    db.update_synonym(syn_id, payload)
    return {"status": "updated"}


@router.post("/api/synonyms/select")
async def select_synonym(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    word = payload.get("word", "").strip()
    synonym = payload.get("synonym", "").strip()
    lang = payload.get("lang", "uz")
    if word and synonym:
        db.increment_synonym_frequency(word, synonym, lang)
    return {"status": "ok"}


@router.delete("/api/synonyms/{syn_id}")
async def delete_synonym_endpoint(syn_id: int, current_user: Dict = Depends(get_current_user)):
    db.delete_synonym(syn_id)
    return {"status": "deleted"}
