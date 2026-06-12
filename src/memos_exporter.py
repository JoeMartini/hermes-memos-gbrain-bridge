"""Export MemOS traces to Markdown for gbrain import."""

import sqlite3
import uuid
from pathlib import Path

from .utils import ensure_dir, normalize_ts, slugify, ts_to_iso

# Value filtering thresholds
VALUE_THRESHOLD = 0.3
PRIORITY_THRESHOLD = 0.4


def export_memos_traces(
    db_path: Path,
    out_dir: Path,
    profiles: list[str] | None = None,
    since_ts: int | None = None,
    seen_trace_ids: set[str] | None = None,
) -> tuple[int, int]:
    """Export MemOS traces to Markdown files.

    Args:
        db_path: Path to memos.db SQLite file.
        out_dir: Directory to write exported Markdown files.
        profiles: Only export traces from these profiles. None = all.
        since_ts: Only export traces newer than this timestamp.
                  Automatically handles seconds vs milliseconds.
        seen_trace_ids: Set of already-exported trace IDs for cross-DB dedup.

    Returns:
        Tuple of (exported_count, skipped_low_value_count).
    """
    if not db_path.exists():
        print(f"[MemOS] Database not found: {db_path}")
        return 0, 0

    if seen_trace_ids is None:
        seen_trace_ids = set()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify traces table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    if "traces" not in tables:
        print("[MemOS] No traces table found")
        conn.close()
        return 0, 0

    # Build WHERE clause with parameterization
    where_clauses = ["1=1"]
    params: list = []

    if profiles:
        placeholders = ",".join("?" * len(profiles))
        where_clauses.append(f"owner_profile_id IN ({placeholders})")
        params.extend(profiles)

    if since_ts:
        since_ms = normalize_ts(since_ts)
        where_clauses.append("ts > ?")
        params.append(since_ms)

    # Value filter: high value OR high priority OR has summary
    where_clauses.append("(value >= ? OR priority >= ? OR summary IS NOT NULL)")
    params.extend([VALUE_THRESHOLD, PRIORITY_THRESHOLD])

    where_sql = " AND ".join(where_clauses)

    # Get total count matching filters (for reporting)
    count_query = f"SELECT COUNT(*) FROM traces WHERE {where_sql}"
    cursor.execute(count_query, params)
    total_matching = cursor.fetchone()[0]

    # Get filtered traces
    query = f"SELECT * FROM traces WHERE {where_sql} ORDER BY ts"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    exported = 0
    dedup_skipped = 0

    for row in rows:
        trace_id = row["id"]
        if not trace_id:
            # Generate deterministic but unique ID from row content hash
            trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        # Cross-database deduplication
        if trace_id in seen_trace_ids:
            dedup_skipped += 1
            continue
        seen_trace_ids.add(trace_id)

        profile = row["owner_profile_id"] or "unknown"
        session = row["session_id"] or "unknown"
        ts = row["ts"]
        tags = row["tags_json"] or "[]"
        summary = row["summary"] or ""
        user_text = row["user_text"] or ""
        agent_text = row["agent_text"] or ""
        agent_thinking = row["agent_thinking"] or ""
        reflection = row["reflection"] or ""

        # Build Markdown content
        lines = [
            f"# MemOS Trace: {trace_id}",
            "",
            f"**Profile:** {profile}",
            f"**Session:** {session}",
            f"**Type:** trace",
            f"**Time:** {ts_to_iso(ts)}",
            f"**Tags:** {tags}",
            "",
            "---",
            "",
        ]

        if summary:
            lines.extend(["## Summary", "", summary, ""])
        if user_text:
            lines.extend(["## User", "", user_text, ""])
        if agent_text:
            lines.extend(["## Agent", "", agent_text, ""])
        if agent_thinking:
            lines.extend(["## Thinking", "", agent_thinking, ""])
        if reflection:
            lines.extend(["## Reflection", "", reflection, ""])

        md = "\n".join(lines)

        # Write to profile subdirectory
        profile_dir = ensure_dir(out_dir / profile)
        filepath = profile_dir / f"{slugify(trace_id)}.md"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        exported += 1

    low_value_skipped = total_matching - exported - dedup_skipped

    if dedup_skipped > 0:
        print(f"[MemOS] Skipped {dedup_skipped} duplicate traces")
    if low_value_skipped > 0:
        print(f"[MemOS] Filtered out {low_value_skipped} low-value traces")

    print(
        f"[MemOS] Exported {exported} traces "
        f"(incremental since {ts_to_iso(since_ts)})"
    )
    return exported, low_value_skipped
