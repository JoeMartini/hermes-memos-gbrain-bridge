# Setup Guide: Hermes-MemOS-gbrain Bridge

Complete step-by-step guide to deploy this bridge on a new Hermes Agent instance.

> **Important**: This guide assumes you have access to MemOS plugin and gbrain. See the component-specific docs for detailed installation:
> - [docs/GBRAIN_SETUP.md](docs/GBRAIN_SETUP.md) — Complete gbrain installation
> - [docs/SILICONFLOW_INTEGRATION.md](docs/SILICONFLOW_INTEGRATION.md) — SiliconFlow API setup (embedding + LLM)

## Prerequisites

- Linux/macOS with Python 3.11+
- PostgreSQL 15+ with pgvector extension (or Docker)
- Bun (for gbrain)
- Hermes Agent installed (with MemOS plugin)

## Step 1: Install gbrain

```bash
# Install Bun
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"

# Install gbrain (from source)
git clone https://github.com/garrytan/gbrain.git ~/gbrain
cd ~/gbrain && bun install && bun link

# Initialize gbrain
# For SiliconFlow: set SILICONFLOW_API_KEY first, then choose siliconflow provider
gbrain init
```

Choose **PGLite** for zero-config or **PostgreSQL** for production.

See [docs/GBRAIN_SETUP.md](docs/GBRAIN_SETUP.md) for detailed installation options.

## Step 2: Configure gbrain

### For SiliconFlow (recommended, domestic, free embedding)

```bash
export SILICONFLOW_API_KEY=sk-...brain config set embedding_model siliconflow:Qwen/Qwen3-Embedding-8B
gbrain config set embedding_dimensions 4096
```

Edit `~/.gbrain/config.json`:

```json
{
  "engine": "postgres",
  "embedding_model": "siliconflow:Qwen/Qwen3-Embedding-8B",
  "embedding_dimensions": 4096,
  "host": "localhost",
  "port": 5432,
  "database": "gbrain",
  "user": "gbrain_user",
  "password": "YOUR_PASSWORD"
}
```

> **Note**: `SILICONFLOW_API_KEY` is read from environment variable. Never write it to config file.

If using Docker:

```bash
docker compose -f docker-compose.yml up -d
```

## Step 3: Enable MemOS in Hermes

For each profile you want to sync:

```bash
# Edit profile config
nano ~/.hermes/profiles/<profile>/config.yaml
```

Add:

```yaml
plugins:
  enabled:
    - memos

memory:
  memory_enabled: true
  user_profile_enabled: true
```

## Step 4: Configure MemOS Plugin

```bash
# Create per-profile MemOS config
mkdir -p ~/.hermes/memos-plugin-<profile>
cp config/memos-plugin.yaml ~/.hermes/memos-plugin-<profile>/config.yaml
nano ~/.hermes/memos-plugin-<profile>/config.yaml
```

### For SiliconFlow

```yaml
llm:
  provider: openai_compatible
  base_url: https://api.siliconflow.cn/v1
  api_key: ${SILICONFLOW_API_KEY}
  model: Qwen/Qwen3-8B

embedding:
  provider: openai_compatible
  base_url: https://api.siliconflow.cn/v1
  api_key: ${SILICONFLOW_API_KEY}
  model: Qwen/Qwen3-Embedding-8B
  dimensions: 4096
```

See [docs/SILICONFLOW_INTEGRATION.md](docs/SILICONFLOW_INTEGRATION.md) for complete SiliconFlow configuration.

## Step 5: Install Bridge

```bash
git clone https://github.com/YOURNAME/hermes-memos-gbrain-bridge.git ~/hermes-memos-gbrain-bridge
cd ~/hermes-memos-gbrain-bridge
```

## Step 6: Run First Sync

```bash
# Full sync to bootstrap
python3 scripts/bridge.py --full-sync
```

## Step 7: Set Up Automation

### Option A: Cron

```bash
# Add to crontab
crontab -e
```

Add:

```cron
0 */6 * * * /home/YOURNAME/hermes-memos-gbrain-bridge/scripts/bridge.sh
```

### Option B: Systemd Timer

```bash
sudo cp systemd/memos-gbrain-bridge.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memos-gbrain-bridge.timer
```

Verify:

```bash
systemctl list-timers memos-gbrain-bridge.timer
```

## Verification

### Check bridge state

```bash
cat ~/.hermes/memos-plugin/scripts/.bridge_state.json
```

### Check gbrain content

```bash
gbrain list -n 20
gbrain search "your query"
```

### Check logs

```bash
tail -f ~/.hermes/memos-plugin/logs/bridge-sync.log
```

## Troubleshooting

### "No MemOS databases found"

- Verify MemOS plugin is enabled in profile config
- Check `~/.hermes/memos-plugin-*/data/memos.db` exists
- Run Hermes session to generate initial traces

### "gbrain import failed"

- Check `~/.gbrain/config.json` has valid credentials
- Remove stale `~/gbrain/.env` if present
- Run `gbrain doctor` for diagnostics
- Check [docs/GBRAIN_SETUP.md](docs/GBRAIN_SETUP.md) for detailed troubleshooting

### "0 traces exported"

- Check if traces have value scores: `value >= 0.3` or `priority >= 0.4`
- Or run with `--full-sync` to bypass incremental filter
- Verify timestamps: check `ts` column format in memos.db

### "unknown provider siliconflow"

- gbrain version too old. Upgrade: `cd ~/gbrain && git pull && bun install`
- See [docs/SILICONFLOW_INTEGRATION.md](docs/SILICONFLOW_INTEGRATION.md) for version requirements

### Permission errors

```bash
chmod +x scripts/bridge.py scripts/bridge.sh
```

## Migration from Bridge v1

If you have the old single-script bridge:

1. Back up old export directory: `cp -r ~/.hermes/memos-plugin/scripts/export ~/bridge-export-backup`
2. Install new bridge
3. Run `--full-sync` once to rebuild
4. Update cron to use `scripts/bridge.sh`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GBRAIN_HOME` | `~/gbrain` | Path to gbrain installation |
| `MEMOS_HOME` | `~/.hermes/memos-plugin` | Path to MemOS plugin directory |
| `BRIDGE_HOME` | `~/.hermes/memos-plugin` | Path for logs and state |
| `BUN_PATH` | `bun` | Path to Bun executable |
| `SILICONFLOW_API_KEY` | — | SiliconFlow API key (for embedding + LLM) |

## Multi-Profile Setup

The bridge automatically discovers all profiles:

```
~/.hermes/
├── profiles/
│   ├── default/
│   ├── work/
│   └── personal/
├── memos-plugin-default/
├── memos-plugin-work/
└── memos-plugin-personal/
```

Each profile's traces are exported to `export/<profile>/` and maintain
profile attribution in gbrain search results.
