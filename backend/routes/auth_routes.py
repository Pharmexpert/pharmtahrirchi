import os
import logging
import random
import string
import requests
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
import db
from auth import create_access_token, verify_token, get_current_user

logger = logging.getLogger("auth_routes")

router = APIRouter(tags=["auth"])

GOOGLE_CLIENT_ID = "1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com"


@router.post("/api/auth/google")
async def auth_google(payload: Dict[str, Any]):
    credential = payload.get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="Google credential required")
    try:
        resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}")
        if not resp.ok: raise HTTPException(status_code=401, detail="Invalid token")
        google_data = resp.json()
        email, name = google_data.get("email"), google_data.get("name")
    except Exception: raise HTTPException(status_code=401, detail="Google verification failed")
    user = db.get_user_by_email(email)
    if not user:
        user_id = f"google_{int(datetime.utcnow().timestamp())}"
        db.create_user(user_id, email, name, avatar_url=google_data.get("picture"), auto_approve=True)
        user = db.get_user_by_email(email)
    else:
        if user["status"] == "pending":
            db.update_user_status(user["id"], "approved")
            user = db.get_user_by_email(email)
    if user["status"] == "rejected": raise HTTPException(status_code=403, detail="Rejected")
    db.update_user_login(user["id"])
    token = create_access_token({"userId": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {"success": True, "token": token, "user": user}


@router.post("/api/auth/register")
async def register(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    name = payload.get("name", "").strip()
    password = payload.get("password")
    department = payload.get("department", "").strip()
    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Barcha maydonlarni тўлдиринг")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Бундай Email аллақачон мавжуд")
    user_id = f"user_{int(datetime.utcnow().timestamp())}"
    db.create_user(user_id, email, name, password=password, department=department)
    return {"success": True, "message": "Рўйхатдан ўтиш муваффақиятли! Админ тасдиқлашини кутинг."}


@router.post("/api/auth/login")
async def login_api(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")

    if not email:
        raise HTTPException(status_code=400, detail="Email манзилини киритинг")

    user_data = db.get_user_by_email(email)
    pw_required = True
    if user_data and user_data.get('role') == 'admin' and not user_data.get('password_hash'):
        pw_required = False

    if pw_required and not password:
        raise HTTPException(status_code=400, detail="Паролни киритинг")

    if not db.verify_password(email, password or ""):
        raise HTTPException(status_code=401, detail="Email ёки парол хато")
    user = db.get_user_by_email(email)
    if not user: raise HTTPException(status_code=401, detail="Фойдаланувчи топилмади")
    if user["email"] != "texnopharm@gmail.com" and user["status"] != "approved":
        detail = "Ҳисобингиз ҳали тасдиқланмаган" if user["status"] == "pending" else "Ҳисобингиз рад этилган"
        raise HTTPException(status_code=403, detail=detail)
    db.update_user_login(user["id"])
    token = create_access_token({"userId": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {"success": True, "token": token, "user": user}


@router.get("/api/auth/me")
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header: raise HTTPException(status_code=401)
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    user = db.get_user_by_id(payload["userId"])
    return {"user": user}


@router.post("/api/auth/forgot-password")
async def forgot_password(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email манзилини киритинг")

    user = db.get_user_by_email(email)
    if not user:
        return {"success": True, "message": "Агар ушбу Email мавжуд бўлса, тиклаш коди юборилди."}

    code = ''.join(random.choices(string.digits, k=6))
    db.create_reset_code(email, code)

    email_sent = False
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if smtp_host and smtp_user and smtp_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(
                f"Сизнинг парол тиклаш кодингиз: {code}\n\nУшбу код 15 дақиқа ичида амал қилади.",
                "plain", "utf-8"
            )
            msg["Subject"] = "Pharma Aligner — Парол тиклаш коди"
            msg["From"] = smtp_user
            msg["To"] = email

            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [email], msg.as_string())
            email_sent = True
            logger.info(f"[*] Password reset code sent to {email}")
        except Exception as e:
            logger.error(f"[!] SMTP error: {e}")

    if not email_sent:
        logger.info(f"PASSWORD RESET CODE for {email}: {code} (SMTP not configured)")

    return {"success": True, "message": "Тиклаш коди Email манзилингизга юборилди."}


@router.post("/api/auth/reset-password")
async def reset_password(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    code = payload.get("code", "").strip()
    new_password = payload.get("password")

    if not email or not code or not new_password:
        raise HTTPException(status_code=400, detail="Барча майдонларни тўлдиринг")

    saved_code = db.get_reset_code(email)
    if not saved_code or saved_code != code:
        raise HTTPException(status_code=400, detail="Хато ёки муддати ўтган тиклаш коди")

    db.update_user_password(email, new_password)
    db.delete_reset_code(email)

    return {"success": True, "message": "Парол муваффақиятли ўзгартирилди! Энди янги парол билан киришингиз мумкин."}


@router.post("/api/profile/update")
async def update_profile(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    db.update_user_profile(current_user["id"], name=name or None, email=email or None)
    return {"status": "updated"}


@router.post("/api/profile/password")
async def update_password(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    import hashlib
    old_password = payload.get("old_password", "")
    new_password = payload.get("new_password", "")

    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Парол камида 6 та белгидан иборат бўлиши керак")

    existing_hash = db.get_user_password_hash(current_user["id"])
    if existing_hash and existing_hash.strip():
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if old_hash != existing_hash:
            raise HTTPException(status_code=400, detail="Эски парол нотўғри")

    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
    db.set_user_password(current_user["id"], new_hash)
    return {"status": "password_updated"}
