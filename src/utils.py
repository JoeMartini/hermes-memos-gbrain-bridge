"""Utility functions for the bridge."""

from datetime import datetime, timezone
from pathlib import Path


def ensure_dir(p: Path) -> Path:
    """Create directory if it doesn't exist."""
    p.mkdir(parents=True, exist_ok=True)
    return p


def ts_to_iso(ts: int | None) -> str:
    """Convert timestamp to ISO format. Handles both seconds and milliseconds.

    MemOS stores ts in milliseconds, but legacy state files may use seconds.
    This function automatically detects the unit.
    """
    if not ts:
        return ""
    try:
        # Heuristic: if ts > 1e12, it's milliseconds (year ~33658)
        ts_sec = ts / 1000 if ts > 1_000_000_000_000 else ts
        return datetime.fromtimestamp(ts_sec, tz=timezone.utc).isoformat()
    except (OSError, ValueError, OverflowError):
        return ""


def slugify(s: str) -> str:
    """Create a filesystem-safe slug from a string."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s).lower()[:80]


def normalize_ts(ts: int) -> int:
    """Normalize timestamp to milliseconds.

    Args:
        ts: Timestamp in either seconds or milliseconds.

    Returns:
        Timestamp in milliseconds.
    """
    if ts < 1_000_000_000_000:
        return ts * 1000
    return ts
