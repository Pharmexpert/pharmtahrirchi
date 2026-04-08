"""
Download u2b3k/uz-hunspell v2 files (Latin + Cyrillic) to Railway volume.

Source: https://github.com/u2b3k/uz-hunspell
License: GPL-3.0
Word count: 90,000+ base words with affix rules
"""
import os
import sys
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="[hunspell_v2] %(message)s")
log = logging.getLogger()

BASE = "https://raw.githubusercontent.com/u2b3k/uz-hunspell/main"
DEST = os.getenv("HUNSPELL_V2_PATH", "/app/data/hunspell")

FILES = [
    ("uz_UZ.aff", f"{BASE}/uz_UZ.aff"),
    ("uz_UZ.dic", f"{BASE}/uz_UZ.dic"),
    ("uz_UZ_Cyrl.aff", f"{BASE}/uz_UZ_Cyrl.aff"),
    ("uz_UZ_Cyrl.dic", f"{BASE}/uz_UZ_Cyrl.dic"),
    ("affixes.txt", f"{BASE}/affixes.txt"),
]


def main():
    if os.getenv("HUNSPELL_V2_ENABLED") != "1":
        log.info("HUNSPELL_V2_ENABLED != 1 — skipping")
        return 0

    os.makedirs(DEST, exist_ok=True)

    downloaded = 0
    for name, url in FILES:
        dest_path = os.path.join(DEST, name)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100:
            log.info(f"✓ {name} already exists ({os.path.getsize(dest_path) // 1024} KB)")
            continue
        try:
            log.info(f"Downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
            with open(dest_path, "wb") as f:
                f.write(data)
            log.info(f"✓ {name} ({len(data) // 1024} KB)")
            downloaded += 1
        except Exception as e:
            log.error(f"  Failed {name}: {e}")

    log.info(f"Hunspell v2: {downloaded} new files downloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
