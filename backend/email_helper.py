"""
Email helper for Pharma Expert notifications.

Supports:
  - Password reset codes
  - Admin approval notifications
  - Weekly/daily cycle reports
  - Project completion notifications

Requires env vars:
  SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_PORT (default 587)
  SMTP_FROM (default: "Pharma Expert <noreply@pharmtech.info>")
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger("email_helper")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_FROM = os.getenv("SMTP_FROM", "Pharma Expert <noreply@pharmtech.info>")


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send a single email. Returns True on success."""
    if not is_configured():
        logger.warning(f"[email] SMTP not configured — skipping send to {to}")
        return False
    if not to:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        logger.info(f"[email] Sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[email] Send failed to {to}: {e}")
        return False


# ─────────────────────────────────────────────
# High-level templates
# ─────────────────────────────────────────────

def send_approval(email: str, name: str) -> bool:
    subject = "Pharma Expert — Ҳисобингиз тасдиқланди"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg, #7C3AED, #6D28D9); color: white; padding: 24px; border-radius: 12px 12px 0 0;">
        <h1 style="margin: 0;">🎉 Ҳисобингиз тасдиқланди!</h1>
      </div>
      <div style="background: white; padding: 24px; border: 1px solid #E5E7EB; border-radius: 0 0 12px 12px;">
        <p>Ҳурматли <strong>{name}</strong>,</p>
        <p>Pharma Expert платформасидаги ҳисобингиз администратор томонидан <strong>тасдиқланди</strong>.</p>
        <p>Энди сиз тизимга кириб барча функциялардан фойдалана оласиз:</p>
        <ul>
          <li>🧬 Тилшунос — илмий таҳрир ва таржима</li>
          <li>🤖 Фармацевт ёрдамчиси — AI chat, edit, translate</li>
          <li>📊 Дашборд — лойиҳаларни бошқариш</li>
        </ul>
        <p style="text-align: center; margin: 24px 0;">
          <a href="https://www.pharmtech.info" style="background: #7C3AED; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 700;">Платформага кириш</a>
        </p>
        <p style="color: #6B7280; font-size: 0.85rem;">Pharma Expert — илмий-фармацевтик ҳужжатлар учун AI асосидаги платформа</p>
      </div>
    </div>
    """
    text = f"Hurmatli {name},\n\nPharma Expert hisobingiz tasdiqlandi. https://www.pharmtech.info"
    return send_email(email, subject, html, text)


def send_project_finished(email: str, name: str, project_name: str) -> bool:
    subject = f"Pharma Expert — «{project_name}» лойиҳаси якунланди"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #16A34A; color: white; padding: 24px; border-radius: 12px 12px 0 0;">
        <h1 style="margin: 0;">✓ Лойиҳа якунланди</h1>
      </div>
      <div style="background: white; padding: 24px; border: 1px solid #E5E7EB; border-radius: 0 0 12px 12px;">
        <p>Ҳурматли <strong>{name}</strong>,</p>
        <p>«<strong>{project_name}</strong>» лойиҳаси муваффақиятли якунланди.</p>
        <p style="color: #6B7280;">Лойиҳа архивга ўтказилди, лекин сиз уни ҳамон кўриб чиқишингиз мумкин.</p>
      </div>
    </div>
    """
    return send_email(email, subject, html)


def send_daily_cycle_report(admin_email: str, cycle_result: dict) -> bool:
    subject = "Pharma Expert — Кунлик ўрганиш цикли ҳисоботи"
    new_rules = cycle_result.get("new_rules_from_llm", 0)
    cons = cycle_result.get("consolidation", {})
    finetune = cycle_result.get("finetune_exported", 0)
    duration = cycle_result.get("duration_seconds", 0)
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>📊 Кунлик ўрганиш цикли</h2>
      <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 6px; border-bottom: 1px solid #E5E7EB;">Янги Sayqallash qoidalari</td><td style="padding: 6px; border-bottom: 1px solid #E5E7EB; text-align: right;"><strong>+{new_rules}</strong></td></tr>
        <tr><td style="padding: 6px; border-bottom: 1px solid #E5E7EB;">Дубликатлар ўчирилди</td><td style="padding: 6px; border-bottom: 1px solid #E5E7EB; text-align: right;">{cons.get('exact_duplicates_removed', 0)}</td></tr>
        <tr><td style="padding: 6px; border-bottom: 1px solid #E5E7EB;">Конфликтлар</td><td style="padding: 6px; border-bottom: 1px solid #E5E7EB; text-align: right;">{cons.get('conflicts_found', 0)}</td></tr>
        <tr><td style="padding: 6px; border-bottom: 1px solid #E5E7EB;">Fine-tune экспорт</td><td style="padding: 6px; border-bottom: 1px solid #E5E7EB; text-align: right;">{finetune} sample</td></tr>
        <tr><td style="padding: 6px;">Давомийлик</td><td style="padding: 6px; text-align: right;">{duration:.1f}s</td></tr>
      </table>
      <p style="color: #6B7280; font-size: 0.85rem;">Цикл ҳар куни 03:30 Тошкент вақтида автоматик ишлайди.</p>
    </div>
    """
    return send_email(admin_email, subject, html)
