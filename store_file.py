"""
store_file.py — copy a file into claude_hub Files storage and register metadata.

Usage:
    python store_file.py <source_path> [--app smart_agent|medical_records|shared]
                                       [--description "..."]
                                       [--tags tag1 tag2 ...]

Examples:
    python store_file.py C:\\Documents\\report.pdf --app shared
    python store_file.py xray.jpg --app medical_records --tags patient_42 imaging
"""
import argparse
import hashlib
import mimetypes
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

import psycopg

FILES_ROOT = Path(r"C:\Users\Cyd_L\Documents\Claude\Files")
DSN = os.environ.get(
    "CLAUDE_HUB_DSN",
    "host=localhost port=5432 dbname=claude_hub user=claude_app password=Noble#9603#",
)
VALID_APPS = {"smart_agent", "medical_records", "shared"}


def store(source: Path, app_slug: str, description: str | None, tags: list[str] | None):
    if not source.exists() or not source.is_file():
        sys.exit(f"ERROR: source file not found: {source}")
    if app_slug not in VALID_APPS:
        sys.exit(f"ERROR: app must be one of {VALID_APPS}, got {app_slug!r}")

    # Build a unique stored filename: YYYYMMDD_HHMMSS_<short-uuid>_<original>
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    safe_name = source.name.replace(" ", "_")
    stored_filename = f"{stamp}_{short_id}_{safe_name}"
    target_dir = FILES_ROOT / app_slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / stored_filename

    # Copy with metadata preserved
    shutil.copy2(source, target_path)
    size = target_path.stat().st_size
    mime, _ = mimetypes.guess_type(source.name)

    with psycopg.connect(DSN, autocommit=True) as conn, conn.cursor() as cur:
        # Look up app_id
        cur.execute("SELECT id FROM apps_shared.applications WHERE slug = %s", (app_slug,))
        row = cur.fetchone()
        if row:
            app_id = row[0]
        else:
            # 'shared' isn't in the seed; insert if missing
            cur.execute(
                """INSERT INTO apps_shared.applications (slug, name, description)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (slug) DO NOTHING
                   RETURNING id""",
                (app_slug, app_slug.replace("_", " ").title(), f"{app_slug} files namespace"),
            )
            r = cur.fetchone()
            app_id = r[0] if r else None

        cur.execute(
            """INSERT INTO apps_shared.files
               (app_id, original_name, stored_path, mime_type, size_bytes, description, tags)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (app_id, source.name, str(target_path), mime, size, description, tags),
        )
        file_id = cur.fetchone()[0]

    print(f"Stored: {target_path}")
    print(f"  id={file_id}  app={app_slug}  size={size:,} bytes  mime={mime}")
    return file_id


def main():
    ap = argparse.ArgumentParser(description="Store a file in claude_hub")
    ap.add_argument("source", type=Path)
    ap.add_argument("--app", default="shared", choices=sorted(VALID_APPS))
    ap.add_argument("--description", default=None)
    ap.add_argument("--tags", nargs="*", default=None)
    args = ap.parse_args()
    store(args.source.resolve(), args.app, args.description, args.tags)


if __name__ == "__main__":
    main()
