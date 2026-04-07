"""
Upload tahrirchi.db to Railway volume via SSH proxy.

Usage (local machine, not Railway):
    cd backend
    pip install paramiko
    python scripts/upload_tahrirchi_to_railway.py

Prerequisites:
    - Railway CLI installed and logged in
    - Run from backend/ directory
    - tahrirchi.db must exist in backend/ directory
"""
import os
import sys
import subprocess
import time

LOCAL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tahrirchi.db")
REMOTE_PATH = "/app/data/tahrirchi.db"

def upload_via_railway_run():
    """Upload file using railway run + cat piping."""
    if not os.path.exists(LOCAL_FILE):
        print(f"[!] Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    size_mb = os.path.getsize(LOCAL_FILE) / (1024 * 1024)
    print(f"[*] Uploading {LOCAL_FILE} ({size_mb:.1f} MB) to Railway volume...")
    print(f"[*] This may take 5-15 minutes depending on connection speed.")

    # Method: pipe file content through `railway run cat > file`
    # Works for binary but slow
    start = time.time()

    cmd = [
        "railway", "run", "--",
        "bash", "-c", f"cat > {REMOTE_PATH}"
    ]

    with open(LOCAL_FILE, "rb") as f:
        result = subprocess.run(cmd, stdin=f, capture_output=True)

    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"[+] Upload completed in {elapsed:.1f}s")
        print(f"[*] Verifying on remote...")

        # Verify
        verify_cmd = [
            "railway", "run", "--",
            "bash", "-c",
            f"ls -la {REMOTE_PATH} && python -c \"import sqlite3; c=sqlite3.connect('{REMOTE_PATH}'); print('Words:', c.execute('SELECT COUNT(*) FROM dictionary').fetchone()[0])\""
        ]
        verify = subprocess.run(verify_cmd, capture_output=True, text=True)
        print(verify.stdout)
        if verify.returncode != 0:
            print(f"[!] Verification failed: {verify.stderr}")
    else:
        print(f"[!] Upload failed: {result.stderr.decode()}")
        sys.exit(1)


if __name__ == "__main__":
    upload_via_railway_run()
