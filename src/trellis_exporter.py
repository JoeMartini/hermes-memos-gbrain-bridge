"""Export Trellis workspace journals and task archives to Markdown."""

import json
from pathlib import Path

from .utils import ensure_dir, slugify


def _read_text_safe(filepath: Path) -> str | None:
    """Read file text with encoding fallback.

    Args:
        filepath: Path to file.

    Returns:
        File content or None if unreadable.
    """
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return filepath.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            print(f"[Trellis] Warning: Could not decode {filepath}")
            return None
    except OSError as e:
        print(f"[Trellis] Warning: Could not read {filepath}: {e}")
        return None


def export_trellis_workspace(
    trellis_dirs: list[Path],
    out_dir: Path,
    since_ts: int | None = None,
) -> int:
    """Export Trellis workspace journals to Markdown.

    Args:
        trellis_dirs: List of Trellis project root directories.
        out_dir: Directory to write exported files.
        since_ts: Only export files modified after this timestamp (seconds or ms).

    Returns:
        Number of journals exported.
    """
    count = 0
    since_sec = since_ts / 1000 if since_ts and since_ts > 1_000_000_000_000 else since_ts

    for trellis_dir in trellis_dirs:
        workspace_dir = trellis_dir / ".trellis" / "workspace"
        if not workspace_dir.exists():
            continue

        for journal_file in workspace_dir.rglob("journal-*.md"):
            if since_sec and journal_file.stat().st_mtime <= since_sec:
                continue

            rel_path = journal_file.relative_to(trellis_dir)
            project_name = trellis_dir.name

            content = _read_text_safe(journal_file)
            if content is None or not content.strip():
                continue

            md = "\n".join([
                f"# Trellis Journal: {project_name}",
                "",
                f"**Source:** {rel_path}",
                f"**Project:** {project_name}",
                "",
                "---",
                "",
                content,
            ])

            trellis_out = ensure_dir(out_dir / "trellis" / "workspace")
            filename = f"{slugify(project_name)}-{slugify(journal_file.stem)}.md"
            (trellis_out / filename).write_text(md, encoding="utf-8")
            count += 1

    print(f"[Trellis] Exported {count} workspace journals")
    return count


def export_trellis_tasks(
    trellis_dirs: list[Path],
    out_dir: Path,
    since_ts: int | None = None,
) -> int:
    """Export Trellis task archives to Markdown.

    Args:
        trellis_dirs: List of Trellis project root directories.
        out_dir: Directory to write exported files.
        since_ts: Only export files modified after this timestamp.

    Returns:
        Number of tasks exported.
    """
    count = 0
    since_sec = since_ts / 1000 if since_ts and since_ts > 1_000_000_000_000 else since_ts

    for trellis_dir in trellis_dirs:
        tasks_dir = trellis_dir / ".trellis" / "tasks"
        if not tasks_dir.exists():
            continue

        project_name = trellis_dir.name

        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            prd_file = task_dir / "prd.md"
            task_json = task_dir / "task.json"

            if not prd_file.exists():
                continue

            if since_sec and prd_file.stat().st_mtime <= since_sec:
                continue

            meta = {}
            if task_json.exists():
                try:
                    content = _read_text_safe(task_json)
                    if content:
                        meta = json.loads(content)
                except json.JSONDecodeError:
                    pass

            prd_content = _read_text_safe(prd_file)
            if prd_content is None or not prd_content.strip():
                continue

            md = "\n".join([
                f"# Trellis Task: {meta.get('title', task_dir.name)}",
                "",
                f"**Project:** {project_name}",
                f"**Task ID:** {meta.get('id', task_dir.name)}",
                f"**Status:** {meta.get('status', 'unknown')}",
                f"**Priority:** {meta.get('priority', 'unknown')}",
                f"**Scope:** {meta.get('scope', 'unknown')}",
                "",
                "---",
                "",
                prd_content,
            ])

            trellis_out = ensure_dir(out_dir / "trellis" / "tasks")
            filename = f"{slugify(project_name)}-{slugify(meta.get('id', task_dir.name))}.md"
            (trellis_out / filename).write_text(md, encoding="utf-8")
            count += 1

    print(f"[Trellis] Exported {count} task archives")
    return count
