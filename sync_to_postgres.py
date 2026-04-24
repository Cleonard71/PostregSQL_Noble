"""
Sync markdown memory files -> claude_hub.memory.entries.
Markdown remains source of truth. Run anytime to refresh the DB mirror.

Usage:  python sync_to_postgres.py
"""
import hashlib
import os
import re
from pathlib import Path

import psycopg  # pip install psycopg[binary]

MEMORY_DIR = Path(__file__).parent
DSN = os.environ.get(
    "CLAUDE_HUB_DSN",
    "host=localhost port=5432 dbname=claude_hub user=postgres password=RVlQ02nCAEzvbcT6gSrx",
)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_memory_file(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    meta_raw, body = m.groups()
    meta = {}
    for line in meta_raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if meta.get("type") not in {"user", "feedback", "project", "reference"}:
        return None
    body = body.strip()
    return {
        "name": meta.get("name", path.stem),
        "description": meta.get("description", ""),
        "type": meta["type"],
        "body": body,
        "source_file": path.name,
        "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def main():
    files = [p for p in MEMORY_DIR.glob("*.md") if p.name != "MEMORY.md"]
    parsed = [e for e in (parse_memory_file(p) for p in files) if e]

    added = updated = removed = 0
    with psycopg.connect(DSN, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("SELECT source_file, content_hash FROM memory.entries")
        existing = dict(cur.fetchall())
        seen = set()

        for e in parsed:
            seen.add(e["source_file"])
            if e["source_file"] not in existing:
                cur.execute(
                    """INSERT INTO memory.entries
                       (name, description, type, body, source_file, content_hash)
                       VALUES (%(name)s, %(description)s, %(type)s, %(body)s,
                               %(source_file)s, %(content_hash)s)""",
                    e,
                )
                added += 1
            elif existing[e["source_file"]] != e["content_hash"]:
                cur.execute(
                    """UPDATE memory.entries
                       SET name=%(name)s, description=%(description)s, type=%(type)s,
                           body=%(body)s, content_hash=%(content_hash)s, updated_at=now()
                       WHERE source_file=%(source_file)s""",
                    e,
                )
                updated += 1

        stale = set(existing) - seen
        for src in stale:
            cur.execute("DELETE FROM memory.entries WHERE source_file=%s", (src,))
            removed += 1

        cur.execute(
            """INSERT INTO memory.sync_log
               (direction, entries_added, entries_updated, entries_removed, notes)
               VALUES ('md_to_db', %s, %s, %s, %s)""",
            (added, updated, removed, f"{len(parsed)} files scanned"),
        )
        conn.commit()

    print(f"Sync complete: +{added} new, ~{updated} updated, -{removed} removed ({len(parsed)} total)")


if __name__ == "__main__":
    main()
