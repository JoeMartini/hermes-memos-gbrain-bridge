"""Discover MemOS and Trellis databases across the filesystem."""

from pathlib import Path

from .utils import ensure_dir

# Default locations to scan for Trellis projects
DEFAULT_TRELLIS_SCAN_DIRS = [
    Path.home() / "projects",
    Path.home() / "work",
    Path("/app"),
]

# Base path for Hermes configuration
HERMES_HOME = Path.home() / ".hermes"


def discover_memos_databases(
    hermes_home: Path | None = None,
) -> list[Path]:
    """Discover all MemOS SQLite databases.

    Scans for:
    1. Global default database: ~/.hermes/memos-plugin/data/memos.db
    2. Per-profile databases: ~/.hermes/memos-plugin-<profile>/data/memos.db

    Args:
        hermes_home: Hermes configuration directory. Defaults to ~/.hermes.

    Returns:
        List of paths to memos.db files.
    """
    home = hermes_home or HERMES_HOME
    dbs: list[Path] = []

    # Global default database (legacy/compatibility)
    global_db = home / "memos-plugin" / "data" / "memos.db"
    if global_db.exists():
        dbs.append(global_db)

    # Per-profile databases: memos-plugin-<profile>/data/memos.db
    for plugin_dir in home.glob("memos-plugin-*/"):
        db_path = plugin_dir / "data" / "memos.db"
        if db_path.exists() and db_path not in dbs:
            dbs.append(db_path)

    if dbs:
        print(f"[MemOS] Discovered {len(dbs)} databases:")
        for db in dbs:
            print(f"  - {db}")

    return dbs


def discover_trellis_projects(
    extra_dirs: list[Path] | None = None,
    scan_dirs: list[Path] | None = None,
) -> list[Path]:
    """Discover Trellis projects by scanning for .trellis directories.

    Args:
        extra_dirs: Additional directories to scan.
        scan_dirs: Override default scan directories.

    Returns:
        List of project root paths (parent of .trellis directory).
    """
    projects: list[Path] = []
    dirs = list(scan_dirs) if scan_dirs else list(DEFAULT_TRELLIS_SCAN_DIRS)
    if extra_dirs:
        dirs.extend(extra_dirs)

    for base_dir in dirs:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob(".trellis"):
            if path.is_dir():
                projects.append(path.parent)

    # Deduplicate by resolved path
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in projects:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(p)

    if unique:
        print(f"[Trellis] Discovered {len(unique)} projects:")
        for p in unique:
            print(f"  - {p}")

    return unique
