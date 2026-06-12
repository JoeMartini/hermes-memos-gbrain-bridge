#!/usr/bin/env python3
"""
Hermes-MemOS-gbrain Bridge v2.1

Synchronizes session memories from Hermes Agent (via MemOS) and project
knowledge from Trellis workspaces into a unified gbrain knowledge base.

Usage:
    python3 bridge.py                    # Incremental sync
    python3 bridge.py --full-sync        # Full re-sync
    python3 bridge.py --dry-run          # Preview without importing
    python3 bridge.py --profiles a,b     # Only sync specific profiles
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
SRC_DIR = SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from database_discovery import discover_memos_databases, discover_trellis_projects
from gbrain_importer import import_to_gbrain
from memos_exporter import export_memos_traces
from trellis_exporter import export_trellis_tasks, export_trellis_workspace
from utils import ts_to_iso

# ─── Configuration ──────────────────────────────────────────────────────────

DEFAULT_GBRAIN_HOME = Path.home() / "gbrain"
DEFAULT_MEMOS_HOME = Path.home() / ".hermes" / "memos-plugin"
DEFAULT_OUT_DIR = DEFAULT_MEMOS_HOME / "scripts" / "export"
BRIDGE_STATE_FILE = DEFAULT_MEMOS_HOME / "scripts" / ".bridge_state.json"

# ─── State Management ───────────────────────────────────────────────────────


def load_state() -> dict:
    """Load bridge state from JSON file."""
    if BRIDGE_STATE_FILE.exists():
        return json.loads(BRIDGE_STATE_FILE.read_text())
    return {
        "last_run": None,
        "last_run_ts": None,
        "profiles": [],
        "total_exported": 0,
        "total_imported": 0,
        "version": "2.1",
    }


def save_state(state: dict) -> None:
    """Save bridge state to JSON file."""
    BRIDGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BRIDGE_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes-MemOS-gbrain Bridge",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without importing to gbrain",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default="",
        help="Comma-separated profile names (default: all)",
    )
    parser.add_argument(
        "--trellis-dirs",
        type=str,
        default="",
        help="Comma-separated Trellis project directories",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=None,
        help="Only export traces after this Unix timestamp (ms or sec)",
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Force full sync (ignore last_run_ts)",
    )
    parser.add_argument(
        "--no-auto-discover",
        action="store_true",
        default=False,
        help="Disable auto-discovery of Trellis projects",
    )
    args = parser.parse_args()

    # Resolve paths
    gbrain_home = Path(os.environ.get("GBRAIN_HOME", DEFAULT_GBRAIN_HOME))
    out_dir = DEFAULT_OUT_DIR

    # Load state
    state = load_state()

    # Determine sync mode and since_ts
    if args.full_sync:
        since_ts = None
        if out_dir.exists() and not args.dry_run:
            shutil.rmtree(out_dir)
            print("[Bridge] Full sync mode: cleaned export directory")
    else:
        since_ts = args.since or state.get("last_run_ts")
        if since_ts:
            print(f"[Bridge] Incremental sync since {ts_to_iso(since_ts)}")
        else:
            print("[Bridge] No previous run found, performing full sync")
            if out_dir.exists() and not args.dry_run:
                shutil.rmtree(out_dir)

    # Parse profiles filter
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()] or None

    # Discover Trellis projects
    trellis_dirs: list[Path] = []
    if args.trellis_dirs:
        trellis_dirs = [
            Path(d.strip()) for d in args.trellis_dirs.split(",") if d.strip()
        ]
    if not args.no_auto_discover:
        discovered = discover_trellis_projects(
            extra_dirs=trellis_dirs if trellis_dirs else None
        )
        seen = {p.resolve() for p in trellis_dirs}
        for p in discovered:
            if p.resolve() not in seen:
                trellis_dirs.append(p)

    total_exported = 0
    total_skipped = 0

    # 1. Export MemOS traces (multi-database, incremental, dedup)
    seen_trace_ids: set[str] = set()
    memos_dbs = discover_memos_databases()

    for db_path in memos_dbs:
        db_exported, db_skipped = export_memos_traces(
            db_path, out_dir, profiles, since_ts, seen_trace_ids
        )
        total_exported += db_exported
        total_skipped += db_skipped

    # 2. Export Trellis workspace data
    if trellis_dirs:
        total_exported += export_trellis_workspace(trellis_dirs, out_dir, since_ts)
        total_exported += export_trellis_tasks(trellis_dirs, out_dir, since_ts)

    # 3. Import to gbrain
    total_imported = import_to_gbrain(
        import_dir=out_dir,
        gbrain_home=gbrain_home,
        dry_run=args.dry_run,
    )

    # Update state
    if not args.dry_run:
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        state["last_run_ts"] = int(datetime.now(timezone.utc).timestamp() * 1000)
        state["profiles"] = profiles if profiles is not None else []
        state["total_exported"] = state.get("total_exported", 0) + total_exported
        state["total_imported"] = state.get("total_imported", 0) + total_imported
        state["version"] = "2.1"
        save_state(state)

    print(f"\n{'=' * 40}")
    print(f"Exported: {total_exported}")
    if total_skipped:
        print(f"Skipped (low-value): {total_skipped}")
    print(f"Imported: {total_imported}")
    print(f"Output:   {out_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
