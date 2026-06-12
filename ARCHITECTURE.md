# Architecture: Hermes-MemOS-gbrain Bridge

## System Context

This bridge solves the problem of **fragmented knowledge** across an AI agent infrastructure:

1. **Hermes Agent** generates session traces (conversations, tool calls, reflections) stored in per-profile SQLite databases via MemOS
2. **Trellis** generates project journals and task PRDs as Markdown files in `.trellis/`
3. **gbrain** provides vector search and semantic retrieval over a unified knowledge graph

Without the bridge, each system is a knowledge silo. The bridge makes them queryable as one.

## Data Flow

```
Hermes Session → MemOS (SQLite) → Bridge Export → gbrain Import ← Trellis Workspace
     │                │                  │              │                  │
     │                │                  │              │                  │
     ▼                ▼                  ▼              ▼                  ▼
  Conversation    Trace Record      Markdown File   Vector Embed    Project Journal
  Tool Output     (ts, value,      (profile/id.md)  (4096-dim)     (project/task.md)
  Reflection      summary, text)
```

## Component Breakdown

### 1. MemOS Exporter (`src/memos_exporter.py`)

**Responsibility**: Extract high-value traces from MemOS SQLite databases

**Key Design Decisions**:
- **Database Discovery**: Scans `~/.hermes/memos-plugin*` directories to find all databases
- **Incremental Filter**: Uses `ts > since_ts` with automatic ms/sec unit conversion
- **Value Filter**: Only exports traces meeting at least one criterion:
  - `value >= 0.3` (MemOS computed value score)
  - `priority >= 0.4` (MemOS priority score)
  - `summary IS NOT NULL` (has been summarized by MemOS LLM)
- **Cross-DB Deduplication**: Maintains `seen_trace_ids` set across all databases

**Timestamp Handling** (Critical):
```
MemOS stores: ts = milliseconds since epoch (e.g. 1780670365236)
State file stores: last_run_ts = milliseconds since epoch (since v2.1)

Query conversion: since_ts_ms = since_ts * 1000 if since_ts < 1e12 else since_ts
```

### 2. Trellis Exporter (`src/trellis_exporter.py`)

**Responsibility**: Extract project journals and task archives from Trellis workspaces

**Key Design Decisions**:
- **Auto-Discovery**: Scans `~/projects`, `~/work`, `/app` for `.trellis` directories
- **Incremental Filter**: Uses file mtime > since_ts for journals and tasks
- **Workspace Journals**: Converts `workspace/journal-*.md` to `trellis/workspace/*.md`
- **Task Archives**: Converts `tasks/*/prd.md` + `task.json` to `trellis/tasks/*.md`

### 3. gbrain Importer (`src/gbrain_importer.py`)

**Responsibility**: Import exported Markdown into gbrain with proper config

**Key Design Decisions**:
- **Idempotent**: gbrain's `import --no-embed` skips unchanged files by content hash
- **Config Repair**: Automatically fixes masked passwords in `~/.gbrain/config.json`
- **Env Cleanup**: Moves stale `.env` files to `.env.bak` to prevent connection issues

### 4. Bridge Orchestrator (`scripts/bridge.py`)

**Responsibility**: Coordinate export → import pipeline with state management

**State File** (`~/.hermes/memos-plugin/scripts/.bridge_state.json`):
```json
{
  "last_run": "2026-06-12T07:22:13+00:00",
  "last_run_ts": 1781248933402,  # milliseconds since epoch
  "profiles": ["default", "work", "personal"],
  "total_exported": 1283,
  "total_imported": 1285,
  "version": "2.1"
}
```

**Modes**:
- **Incremental** (default): Exports since `last_run_ts`, skips unchanged
- **Full Sync** (`--full-sync`): Clears export dir, re-exports everything
- **Dry Run** (`--dry-run`): Preview without writing to gbrain

## Multi-Profile Memory Architecture

```
~/.hermes/
├── profiles/
│   ├── default/
│   │   └── config.yaml          ← plugins: { enabled: ["memos"] }
│   ├── work/
│   │   └── config.yaml          ← plugins: { enabled: ["memos"] }
│   └── personal/
│       └── config.yaml          ← plugins: { enabled: ["memos"] }
│
├── memos-plugin/                 ← Global/shared database (legacy)
│   ├── data/memos.db
│   └── config.yaml
├── memos-plugin-default/         ← Profile-isolated database
│   ├── data/memos.db
│   └── config.yaml
├── memos-plugin-work/         ← Profile-isolated database
│   ├── data/memos.db
│   └── config.yaml
└── memos-plugin-personal/             ← Profile-isolated database
    ├── data/memos.db
    └── config.yaml
```

**Why Profile Isolation?**
- Each profile may have different model providers, personalities, or security contexts
- Isolation prevents cross-contamination of sensitive memories
- Bridge aggregates them at the gbrain level for unified search

## Knowledge Value Pipeline

```
Hermes Session
     │
     ▼ (every N turns)
┌─────────────────┐
│  MemOS MemAgent │ ← LLM-assisted extraction of key facts
│  (value scoring)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SQLite Storage  │ ← value, priority, summary, embedding vectors
│ (traces table)  │
└────────┬────────┘
         │
         ▼ (every 6 hours via cron)
┌─────────────────┐
│  Bridge Filter  │ ← value >= 0.3 OR priority >= 0.4 OR summary IS NOT NULL
│  (deduplication)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Markdown Export │ ← structured trace → readable Markdown
│ (profile/id.md) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  gbrain Import  │ ← chunking + embedding + vector store
│  (pgvector)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Unified Search │ ← semantic + keyword hybrid retrieval
│  (gbrain CLI)   │
└─────────────────┘
```

## Trellis Integration

```
project/
└── .trellis/
    ├── workspace/
    │   ├── journal-2026-06-01.md   → trellis/workspace/project-journal-2026-06-01.md
    │   └── journal-2026-06-12.md   → trellis/workspace/project-journal-2026-06-12.md
    └── tasks/
        ├── task-a/
        │   ├── prd.md              → trellis/tasks/project-task-a.md
        │   └── task.json           (metadata: title, status, priority)
        └── task-b/
            ├── prd.md
            └── task.json
```

## Deployment Options

### Option A: Cron (Recommended for single-node)

```cron
0 */6 * * * /path/to/bridge/scripts/bridge.sh
```

### Option B: Systemd Timer

```ini
# /etc/systemd/system/memos-gbrain-bridge.timer
[Unit]
Description=Run MemOS-gbrain bridge every 6 hours

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Option C: GitHub Actions (for cloud-hosted)

See `.github/workflows/sync.yml`

## Monitoring & Debugging

### Check bridge status

```bash
cat ~/.hermes/memos-plugin/scripts/.bridge_state.json
```

### Check last run log

```bash
tail -f ~/.hermes/memos-plugin/logs/bridge-sync.log
```

### Verify gbrain content

```bash
gbrain list -n 20
gbrain get <profile>/<trace_id>
gbrain search "your query"
```

### Manual dry-run

```bash
python3 scripts/bridge.py --dry-run
```

## Security Considerations

1. **API Keys**: Store in `~/.gbrain/config.json` (600 permissions) or env vars
2. **Database URLs**: Never commit passwords; use connection strings with secrets in env
3. **Profile Isolation**: Each profile's MemOS database is independent; bridge only reads
4. **File Permissions**: Bridge state file should be 600 (contains timestamps only, no secrets)

## Performance Characteristics

| Metric | Typical Value |
|--------|---------------|
| Incremental sync time | 2-10s (for < 100 new traces) |
| Full sync time | 20-60s (for ~1000 traces) |
| gbrain import time | 2-30s depending on new pages |
| Disk usage (export) | ~1-5 MB per 1000 traces |
| Memory usage | < 100 MB |

## Troubleshooting

### "No traces exported" on incremental run

- Check `last_run_ts` in state file is in milliseconds (should be > 1e12)
- Verify MemOS databases have traces with `ts > last_run_ts`

### "gbrain import failed"

- Check `~/.gbrain/config.json` has valid `database_url`
- Remove stale `~/gbrain/.env` if it exists
- Run `gbrain doctor` to verify database connectivity

### Duplicate traces in gbrain

- Ensure bridge script version >= 2.1 (has cross-DB deduplication)
- Run `--full-sync` once to clean export directory

## Migration from v1 to v2

See [MIGRATION.md](MIGRATION.md) if upgrading from the original single-database bridge.
