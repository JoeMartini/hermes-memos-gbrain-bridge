"""Import exported Markdown files into gbrain knowledge base."""

import json
import os
import shutil
import subprocess
from pathlib import Path


def fix_gbrain_config(config_path: Path | None = None) -> None:
    """Repair common gbrain configuration issues.

    - Moves stale .env files to .env.bak (they override config.json)
    - Fixes masked passwords in database_url
    """
    config_file = config_path or Path.home() / ".gbrain" / "config.json"
    env_path = Path.home() / "gbrain" / ".env"

    # Remove stale .env that may override config
    if env_path.exists():
        backup = env_path.with_suffix(".env.bak")
        shutil.move(str(env_path), str(backup))
        print("[gbrain] Moved stale .env to .env.bak")

    # Fix masked password in config.json
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            pw = config.get("password", "")
            db_url = config.get("database_url", "")

            if "***" in db_url and pw and pw != "***":
                import urllib.parse
                encoded_pw = urllib.parse.quote(pw, safe="")
                fixed_url = db_url.replace("***", encoded_pw)
                config["database_url"] = fixed_url
                config_file.write_text(json.dumps(config, indent=2))
                print("[gbrain] Fixed masked password in config.json")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[gbrain] Config check warning: {e}")


def import_to_gbrain(
    import_dir: Path,
    gbrain_home: Path | None = None,
    dry_run: bool = False,
    bun_path: str | None = None,
) -> int:
    """Import Markdown files into gbrain.

    Args:
        import_dir: Directory containing Markdown files to import.
        gbrain_home: Path to gbrain installation. Defaults to ~/gbrain.
        dry_run: If True, only print what would be done.
        bun_path: Path to bun executable. Defaults to $BUN_PATH or "bun".

    Returns:
        Number of files imported (0 on failure).
    """
    files = list(import_dir.rglob("*.md"))
    if not files:
        print("[gbrain] No files to import")
        return 0

    print(f"[gbrain] Importing {len(files)} files from {import_dir}")

    if dry_run:
        print("[DRY-RUN] Would run:")
        print(f"  cd {gbrain_home or '~/gbrain'} && bun src/cli.ts import {import_dir} --no-embed")
        return len(files)

    gbrain = gbrain_home or Path.home() / "gbrain"
    cli = gbrain / "src" / "cli.ts"

    if not cli.exists():
        print(f"[gbrain] CLI not found: {cli}")
        return 0

    fix_gbrain_config()

    # Resolve bun path: env var > parameter > default "bun"
    bun = bun_path or os.environ.get("BUN_PATH", "bun")

    try:
        result = subprocess.run(
            [bun, str(cli), "import", str(import_dir), "--no-embed"],
            cwd=str(gbrain),
            capture_output=True,
            text=True,
            timeout=300,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[gbrain] Error: {result.stderr}", file=__import__("sys").stderr)
            return 0
        return len(files)
    except subprocess.TimeoutExpired:
        print("[gbrain] Import timed out after 300s")
        return 0
    except FileNotFoundError:
        print(f"[gbrain] 'bun' command not found: {bun}")
        return 0
