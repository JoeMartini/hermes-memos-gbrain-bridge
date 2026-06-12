# Hermes-MemOS-gbrain Bridge

A unified memory-to-knowledge bridge that connects **Hermes Agent** sessions (via MemOS), **Trellis** project workspaces, and **gbrain** personal knowledge base into a single searchable, embedding-powered knowledge system.

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Hermes Agent   │     │    Trellis      │     │     gbrain      │
│  (MemOS Plugin) │     │  (Project Mgmt) │     │  (Knowledge DB) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ traces                │ journals/tasks        │ embedding
         │ (SQLite)              │ (Markdown)            │ (pgvector)
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Bridge (this project)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ MemOS Export │  │Trellis Export│  │   gbrain Import      │  │
│  │  (incremental)│  │(auto-discover)│  │  (dedup + embed)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Profile Support**: Automatically discovers and aggregates MemOS databases from all Hermes profiles
- **Incremental Sync**: Only exports traces modified since last run (millisecond-precision timestamps)
- **Cross-Database Deduplication**: Skips traces that already exist in other databases
- **Value Filtering**: Exports only high-value traces (`value >= 0.3`, `priority >= 0.4`, or has summary)
- **Auto-Discovery**: Scans common directories for Trellis projects
- **Cron-Ready**: Lock-file protected, runnable via systemd timer or cron
- **Zero-Downtime**: gbrain import is idempotent — unchanged pages are skipped

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOURNAME/hermes-memos-gbrain-bridge.git
cd hermes-memos-gbrain-bridge

# 2. Install dependencies (Python 3.11+)
pip install -r requirements.txt

# 3. Configure
# See docs/SILICONFLOW_INTEGRATION.md for SiliconFlow (硅基流动) setup
cp config/memos-plugin.yaml ~/.hermes/memos-plugin/config.yaml
cp config/gbrain.json ~/.gbrain/config.json
# Edit configs with your API keys (use environment variables!)

# 4. Install systemd service or cron
sudo cp systemd/memos-gbrain-bridge.service /etc/systemd/system/
sudo systemctl enable --now memos-gbrain-bridge.timer

# 5. Run first sync
python3 scripts/bridge.py --full-sync
```

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and data flow |
| [SETUP.md](SETUP.md) | Step-by-step deployment guide |
| [docs/SILICONFLOW_INTEGRATION.md](docs/SILICONFLOW_INTEGRATION.md) | SiliconFlow (硅基流动) API integration |
| [docs/GBRAIN_SETUP.md](docs/GBRAIN_SETUP.md) | Complete gbrain installation guide |

## Components

| Component | Purpose | Source |
|-----------|---------|--------|
| **Hermes Agent** | AI agent framework with session memory | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |
| **MemOS Plugin** | SQLite-based memory layer for Hermes | Built-in Hermes plugin |
| **Trellis** | Structured project workspace & tasks | Custom / or [trellis-workspace](https://github.com/example) |
| **gbrain** | Postgres-native knowledge brain with hybrid RAG | [garrytan/gbrain](https://github.com/garrytan/gbrain) |

## LLM / Embedding Provider

This system is tested and validated with **SiliconFlow (硅基流动)**:

- **Embedding**: `Qwen/Qwen3-Embedding-8B` (4096 dims, Matryoshka-compatible, currently free)
- **LLM**: `Qwen/Qwen3-8B`
- **API**: OpenAI-compatible endpoint at `https://api.siliconflow.cn/v1`

Other OpenAI-compatible providers (OpenAI, Azure, DashScope, etc.) can also be used. See [docs/SILICONFLOW_INTEGRATION.md](docs/SILICONFLOW_INTEGRATION.md) for details.

## Requirements

- Python 3.11+
- PostgreSQL 15+ with pgvector extension (or Docker)
- Bun (for gbrain)
- Hermes Agent (with MemOS plugin enabled)

## License

MIT
