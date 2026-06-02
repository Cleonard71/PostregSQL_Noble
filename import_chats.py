"""
import_chats.py — slurp all Claude Code session transcripts into claude_hub.chats

Walks ~/.claude/projects/ for *.jsonl, parses each line, upserts a session row
and one message row per line.  Idempotent — safe to re-run.

Usage:
    python import_chats.py                 # import everything
    python import_chats.py --dry-run       # show what would import
    python import_chats.py --since 2026-04-01   # only sessions modified after date
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Json

PROJECTS_ROOT = Path.home() / ".claude" / "projects"
DSN = os.environ.get("CLAUDE_HUB_DSN")
if not DSN:
    sys.exit("Set CLAUDE_HUB_DSN env var, e.g.: host=localhost port=5432 dbname=claude_hub user=claude_app password=YOUR_PW")


def _strip_nulls(obj):
    """Recursively remove \\u0000 from strings — PostgreSQL JSONB rejects them."""
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, list):
        return [_strip_nulls(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items()}
    return obj


def extract_text(rec: dict) -> str | None:
    """Best-effort flatten of message content to plain text for full-text search."""
    if "content" in rec and isinstance(rec["content"], str):
        return rec["content"]
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    name = block.get("name", "tool")
                    parts.append(f"[tool_use:{name}]")
                elif block.get("type") == "tool_result":
                    parts.append("[tool_result]")
        if parts:
            return "\n".join(parts)
    return None


def derive_role(rec: dict) -> str | None:
    msg = rec.get("message") or {}
    return msg.get("role") or rec.get("role")


def parse_ts(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def import_file(cur, jsonl_path: Path, project_dir: str, dry: bool) -> tuple[int, int]:
    session_id = jsonl_path.stem
    msgs = []
    started = ended = None
    with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
        for seq, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_ts(rec.get("timestamp"))
            if ts:
                started = ts if started is None or ts < started else started
                ended = ts if ended is None or ts > ended else ended
            text = extract_text(rec)
            if text is not None:
                text = text.replace("\x00", "")
            msgs.append((
                seq,
                ts,
                derive_role(rec),
                rec.get("type"),
                text,
                _strip_nulls(rec),
            ))
    if not msgs:
        return (0, 0)

    if dry:
        return (1, len(msgs))

    cur.execute(
        """INSERT INTO chats.sessions
           (id, project_path, started_at, ended_at, message_count, source, raw_path, updated_at)
           VALUES (%s, %s, %s, %s, %s, 'claude_code', %s, now())
           ON CONFLICT (id) DO UPDATE SET
             ended_at = EXCLUDED.ended_at,
             message_count = EXCLUDED.message_count,
             updated_at = now()""",
        (session_id, project_dir, started, ended, len(msgs), str(jsonl_path)),
    )
    # Wipe and re-insert messages so re-imports stay consistent
    cur.execute("DELETE FROM chats.messages WHERE session_id = %s", (session_id,))
    cur.executemany(
        """INSERT INTO chats.messages
           (session_id, seq, timestamp, role, event_type, content, raw)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        [(session_id, seq, ts, role, et, content, Json(raw))
         for (seq, ts, role, et, content, raw) in msgs],
    )
    return (1, len(msgs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", help="ISO date — only files modified after")
    args = ap.parse_args()

    cutoff = None
    if args.since:
        cutoff = datetime.fromisoformat(args.since).timestamp()

    if not PROJECTS_ROOT.exists():
        sys.exit(f"No projects dir at {PROJECTS_ROOT}")

    sessions_imported = messages_imported = files_skipped = 0
    with psycopg.connect(DSN, autocommit=False) as conn, conn.cursor() as cur:
        for project_dir in sorted(PROJECTS_ROOT.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl in sorted(project_dir.glob("*.jsonl")):
                if cutoff and jsonl.stat().st_mtime < cutoff:
                    files_skipped += 1
                    continue
                s, m = import_file(cur, jsonl, project_dir.name, args.dry_run)
                sessions_imported += s
                messages_imported += m
        if not args.dry_run:
            conn.commit()

    verb = "Would import" if args.dry_run else "Imported"
    print(f"{verb}: {sessions_imported} sessions, {messages_imported} messages "
          f"({files_skipped} skipped by --since)")


if __name__ == "__main__":
    main()
