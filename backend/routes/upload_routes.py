import os
import re
import shutil
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pdf2docx import Converter
import db
from auth import get_current_user
from processor import ParagraphAligner
from routes.rate_limit import upload_limiter

logger = logging.getLogger("upload")

BACKEND_DIR = os.environ.get("BACKEND_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Use persistent volume for uploads on Railway, local dir otherwise
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
DATA_DIR = os.getenv("DATA_DIR", "/app/data" if IS_RAILWAY else BACKEND_DIR)
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

router = APIRouter(tags=["upload"])


def _safe_user_folder(user: Dict) -> str:
    name = (user.get("name") or "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    if cleaned:
        return cleaned
    return f"user_{user.get('id', 'unknown')}"


def _user_upload_dir(user: Dict) -> str:
    safe = _safe_user_folder(user)
    ym = datetime.utcnow().strftime("%Y-%m")
    path = os.path.join(UPLOADS_DIR, "users", safe, ym)
    os.makedirs(path, exist_ok=True)
    return path


def _resolve_upload_path(filename: str) -> str:
    """Resolve a user-provided filename (possibly with sub-path) to an absolute path
    inside UPLOADS_DIR; reject traversal."""
    # Normalize slashes
    rel = filename.replace("\\", "/").lstrip("/")
    abs_path = os.path.abspath(os.path.join(UPLOADS_DIR, rel))
    uploads_abs = os.path.abspath(UPLOADS_DIR)
    if not abs_path.startswith(uploads_abs + os.sep) and abs_path != uploads_abs:
        raise HTTPException(status_code=400, detail="Invalid path")
    return abs_path


def _enforce_ownership(abs_path: str, current_user: Dict):
    """Non-admin can only access their own files."""
    if current_user.get("role") == "admin":
        return
    owner_id = db.get_file_owner_id(abs_path)
    if owner_id is None:
        # Legacy files without owner: non-admin denied
        raise HTTPException(status_code=403, detail="Рухсат йўқ")
    if owner_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Рухсат йўқ")


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

    user_dir = _user_upload_dir(current_user)
    persistent_file_path = os.path.join(user_dir, f"{int(datetime.utcnow().timestamp())}_{file.filename}")
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
        is_admin = current_user.get("role") == "admin"
        files = db.list_uploaded_files(current_user_id=current_user.get("id"), is_admin=is_admin)
        return {"files": files, "is_admin": is_admin}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/files/{filename:path}/download")
async def download_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = _resolve_upload_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    _enforce_ownership(file_path, current_user)
    return FileResponse(
        file_path,
        filename=os.path.basename(filename),
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(filename)}"'}
    )


@router.get("/api/files/{filename:path}/preview")
async def preview_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = _resolve_upload_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    _enforce_ownership(file_path, current_user)
    preview = db.get_file_text_preview(file_path)
    return {"preview": preview, "filename": filename}


@router.post("/api/files/upload")
async def upload_file_to_directory(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    user_dir = _user_upload_dir(current_user)
    safe_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_path = os.path.join(user_dir, safe_name)
    with open(file_path, "wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)
    # Register ownership in projects table so ownership checks work
    try:
        text_id = f"file_{int(datetime.utcnow().timestamp())}_{current_user.get('id','u')}"
        db.update_project_metadata(text_id, current_user.get("name", ""), user_id=current_user.get("id"))
        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET original_filename = ?, file_path = ? WHERE id = ?",
                       (file.filename, file_path, text_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not register upload ownership: {e}")
    rel = os.path.relpath(file_path, UPLOADS_DIR).replace("\\", "/")
    return {"success": True, "filename": rel, "original": file.filename}


@router.post("/api/folders/create")
async def create_folder(payload: Dict[str, Any] = {}, current_user: Dict = Depends(get_current_user)):
    """Create a new folder in uploads directory."""
    folder_name = payload.get("name", "").strip()
    parent = payload.get("parent", "").strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="Папка номи керак")
    # Sanitize
    folder_name = folder_name.replace("/", "_").replace("\\", "_").replace("..", "")
    base = os.path.join(UPLOADS_DIR, parent) if parent else UPLOADS_DIR
    folder_path = os.path.join(base, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return {"success": True, "folder": folder_name, "path": os.path.relpath(folder_path, UPLOADS_DIR)}


@router.get("/api/folders")
async def list_folders(current_user: Dict = Depends(get_current_user)):
    """List all folders in uploads directory."""
    folders = []
    for root, dirs, files_in_dir in os.walk(UPLOADS_DIR):
        rel = os.path.relpath(root, UPLOADS_DIR)
        if rel == ".":
            rel = ""
        for d in dirs:
            folder_path = os.path.join(rel, d) if rel else d
            full_path = os.path.join(root, d)
            file_count = len([f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))])
            folders.append({"name": d, "path": folder_path, "file_count": file_count})
    return {"folders": folders}


@router.delete("/api/folders/{folder_name}")
async def delete_folder(folder_name: str, current_user: Dict = Depends(get_current_user)):
    """Delete an empty folder."""
    folder_path = os.path.join(UPLOADS_DIR, folder_name)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise HTTPException(status_code=404, detail="Папка топилмади")
    try:
        import shutil
        shutil.rmtree(folder_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/files/move")
async def move_file(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Move a file to a different folder."""
    filename = payload.get("filename", "")
    target_folder = payload.get("target_folder", "")
    if not filename:
        raise HTTPException(status_code=400, detail="Файл номи керак")

    src = _resolve_upload_path(filename)
    if not os.path.exists(src):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    _enforce_ownership(src, current_user)

    dst_dir = _resolve_upload_path(target_folder) if target_folder else UPLOADS_DIR
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(filename))

    import shutil
    shutil.move(src, dst)
    new_path = os.path.relpath(dst, UPLOADS_DIR)
    return {"success": True, "new_path": new_path}


@router.put("/api/folders/rename")
async def rename_folder(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Rename a folder."""
    old_path = payload.get("path", "")
    new_name = payload.get("new_name", "").strip().replace("/", "_").replace("\\", "_").replace("..", "")
    if not old_path or not new_name:
        raise HTTPException(status_code=400, detail="Йўл ва янги ном керак")

    src = os.path.join(UPLOADS_DIR, old_path)
    if not os.path.exists(src) or not os.path.isdir(src):
        raise HTTPException(status_code=404, detail="Папка топилмади")

    parent = os.path.dirname(src)
    dst = os.path.join(parent, new_name)
    os.rename(src, dst)
    return {"success": True, "new_path": os.path.relpath(dst, UPLOADS_DIR)}


@router.post("/api/folders/move")
async def move_folder(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Move a folder into another folder or back to root."""
    folder_path = payload.get("folder", "")
    target = payload.get("target", "")  # empty = root
    if not folder_path:
        raise HTTPException(status_code=400, detail="Папка номи керак")

    src = os.path.join(UPLOADS_DIR, folder_path)
    if not os.path.exists(src) or not os.path.isdir(src):
        raise HTTPException(status_code=404, detail="Папка топилмади")

    folder_name = os.path.basename(folder_path)
    dst_parent = os.path.join(UPLOADS_DIR, target) if target else UPLOADS_DIR
    dst = os.path.join(dst_parent, folder_name)

    if os.path.abspath(src) == os.path.abspath(dst):
        return {"success": True, "new_path": folder_path}
    # Prevent moving into itself
    if os.path.abspath(dst).startswith(os.path.abspath(src)):
        raise HTTPException(status_code=400, detail="Папкани ўзига кўчириш мумкин эмас")

    import shutil
    os.makedirs(dst_parent, exist_ok=True)
    shutil.move(src, dst)
    new_path = os.path.relpath(dst, UPLOADS_DIR)
    return {"success": True, "new_path": new_path}


@router.delete("/api/files/{filename:path}")
async def delete_file(filename: str, current_user: Dict = Depends(get_current_user)):
    file_path = _resolve_upload_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    _enforce_ownership(file_path, current_user)
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/files/{filename:path}/open")
async def open_file_in_editor(filename: str, background_tasks: BackgroundTasks, mode: str = "auto", current_user: Dict = Depends(get_current_user)):
    file_path = _resolve_upload_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    _enforce_ownership(file_path, current_user)

    processing_path = file_path
    original_filename = os.path.basename(filename)

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

        # Auto-extract text_id from filename (e.g. "3.2. CONTAINERS..." → "3.2")
        import re as _re
        clean_name = _re.sub(r'^\d+_', '', original_filename)  # Remove timestamp prefix
        num_match = _re.match(r'^([\d]+\.[\d.]*\d)', clean_name)
        if num_match:
            text_id = num_match.group(1)
        else:
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
