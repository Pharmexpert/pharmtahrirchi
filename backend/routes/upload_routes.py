import os
import shutil
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pdf2docx import Converter
import db
from auth import get_current_user
from processor import ParagraphAligner
from routes.rate_limit import upload_limiter

logger = logging.getLogger("upload")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")

router = APIRouter(tags=["upload"])


@router.post("/api/upload")
@router.post("/api/upload-docx")
@router.post("/upload")
async def upload_file(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), mode: str = "auto", text_id: str = "", current_user: Dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    if not upload_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Жуда кўп юклаш. 1 дақиқа кутинг.")

    allowed_extensions = {".docx", ".pdf"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Фақат DOCX ва PDF файллар қабул қилинади. Юборилган: {file_ext}")

    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл ҳажми 50MB дан ошмаслиги керак")
    file.file.seek(0)

    persistent_file_path = os.path.join(UPLOADS_DIR, f"{int(datetime.utcnow().timestamp())}_{file.filename}")
    with open(persistent_file_path, "wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)

    processing_path = persistent_file_path

    if file.filename.lower().endswith(".pdf"):
        docx_path = persistent_file_path.rsplit(".", 1)[0] + ".docx"
        try:
            logger.info(f"[*] Converting PDF to DOCX: {file.filename}")
            cv = Converter(persistent_file_path)
            cv.convert(docx_path)
            cv.close()
            processing_path = docx_path
        except Exception as e:
            logger.error(f"[!] PDF Conversion Error: {e}")
            raise HTTPException(status_code=500, detail=f"PDF конвертация қилишда хатолик: {str(e)}")

    try:
        aligner = ParagraphAligner(processing_path)
        if mode == "ready":
            data = aligner.process_ready_form()
        else:
            data = aligner.process()

        if not text_id.strip():
            specialist_short = current_user.get("name", "User").split()[0][:6] if current_user.get("name") else "User"
            text_id = f"{specialist_short}_{int(datetime.utcnow().timestamp())}"

        for row in data:
            row["text_id"] = text_id

        db.update_project_metadata(text_id, current_user.get("name", "Aniqlanmagan"), user_id=current_user["id"])

        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET original_filename = ?, file_path = ? WHERE id = ?", (file.filename, persistent_file_path, text_id))
        conn.commit()
        conn.close()

        db.save_alignments(text_id, data, user_id=current_user["id"])

        from routes.sayqallash_routes import pre_polish_document
        background_tasks.add_task(pre_polish_document, text_id)

        return {"filename": file.filename, "data": data, "text_id": text_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/files")
async def list_files(current_user: Dict = Depends(get_current_user)):
    try:
        files = db.list_uploaded_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/files/{filename}/download")
async def download_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    return FileResponse(
        file_path,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/api/files/{filename}/preview")
async def preview_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    preview = db.get_file_text_preview(file_path)
    return {"preview": preview, "filename": filename}


@router.post("/api/files/upload")
async def upload_file_to_directory(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    safe_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)
    return {"success": True, "filename": safe_name, "original": file.filename}


@router.delete("/api/files/{filename}")
async def delete_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/files/{filename}/open")
async def open_file_in_editor(filename: str, background_tasks: BackgroundTasks, mode: str = "auto", current_user: Dict = Depends(get_current_user)):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")

    processing_path = file_path
    original_filename = filename

    if filename.lower().endswith(".pdf"):
        docx_path = file_path.rsplit(".", 1)[0] + ".docx"
        if not os.path.exists(docx_path):
            try:
                cv = Converter(file_path)
                cv.convert(docx_path)
                cv.close()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF конвертация хатоси: {str(e)}")
        processing_path = docx_path

    try:
        aligner = ParagraphAligner(processing_path)
        data = aligner.process_ready_form() if mode == "ready" else aligner.process()

        specialist_short = current_user.get("name", "User").split()[0][:6] if current_user.get("name") else "User"
        text_id = f"{specialist_short}_{int(datetime.utcnow().timestamp())}"

        for row in data:
            row["text_id"] = text_id

        db.update_project_metadata(text_id, current_user.get("name", "Aniqlanmagan"), user_id=current_user["id"])

        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET original_filename = ?, file_path = ? WHERE id = ?", (original_filename, file_path, text_id))
        conn.commit()
        conn.close()

        db.save_alignments(text_id, data, user_id=current_user["id"])

        from routes.sayqallash_routes import pre_polish_document
        background_tasks.add_task(pre_polish_document, text_id)

        return {"filename": original_filename, "data": data, "text_id": text_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
