"""
SQLite DB backup to cloud storage (S3 / Cloudflare R2 / local).

Runs daily via cron (separate from learning cycle).
Retains last 30 daily backups.

Env vars:
    BACKUP_PROVIDER     — "s3" | "r2" | "local" (default: local)
    S3_BUCKET           — bucket name
    S3_ACCESS_KEY_ID
    S3_SECRET_ACCESS_KEY
    S3_ENDPOINT_URL     — for R2: https://<account>.r2.cloudflarestorage.com
    S3_REGION           — default: auto
    BACKUP_LOCAL_DIR    — local fallback (default: /app/data/backups)
"""
import os
import sys
import sqlite3
import shutil
import gzip
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="[db_backup] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
BACKUP_PROVIDER = os.getenv("BACKUP_PROVIDER", "local").lower()
LOCAL_DIR = os.getenv("BACKUP_LOCAL_DIR", "/app/data/backups")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


def create_snapshot() -> str:
    """Create a consistent SQLite snapshot using backup API."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"pharma_{timestamp}.db"
    os.makedirs(LOCAL_DIR, exist_ok=True)
    snapshot_path = os.path.join(LOCAL_DIR, snapshot_name)

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(snapshot_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    # Gzip for size
    gz_path = snapshot_path + ".gz"
    with open(snapshot_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(snapshot_path)

    size_mb = os.path.getsize(gz_path) / (1024 * 1024)
    log.info(f"Snapshot created: {gz_path} ({size_mb:.1f} MB)")
    return gz_path


def upload_s3(local_path: str) -> bool:
    """Upload to S3 or Cloudflare R2."""
    try:
        import boto3
    except ImportError:
        log.warning("boto3 not installed — install with: pip install boto3")
        return False

    bucket = os.getenv("S3_BUCKET")
    access_key = os.getenv("S3_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    endpoint = os.getenv("S3_ENDPOINT_URL")  # R2: https://<acct>.r2.cloudflarestorage.com
    region = os.getenv("S3_REGION", "auto")

    if not (bucket and access_key and secret_key):
        log.warning("S3 credentials not set — skipping upload")
        return False

    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint,
            region_name=region,
        )
        key = f"pharma-backups/{os.path.basename(local_path)}"
        client.upload_file(local_path, bucket, key)
        log.info(f"✓ Uploaded to s3://{bucket}/{key}")
        return True
    except Exception as e:
        log.error(f"S3 upload failed: {e}")
        return False


def cleanup_old_local():
    """Remove local backups older than RETENTION_DAYS."""
    if not os.path.exists(LOCAL_DIR):
        return
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for fname in os.listdir(LOCAL_DIR):
        if not fname.startswith("pharma_"):
            continue
        fpath = os.path.join(LOCAL_DIR, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                removed += 1
        except Exception:
            pass
    if removed:
        log.info(f"Cleaned {removed} old backups")


def run_backup():
    try:
        snapshot = create_snapshot()
        if BACKUP_PROVIDER in ("s3", "r2"):
            upload_s3(snapshot)
        cleanup_old_local()
        return {"success": True, "snapshot": os.path.basename(snapshot)}
    except Exception as e:
        log.error(f"Backup failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print(run_backup())
