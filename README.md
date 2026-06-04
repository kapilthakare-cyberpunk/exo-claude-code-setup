# EXO + Claude Code Setup Guide

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/platform-macOS-blue)](https://www.apple.com/macos)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green)](https://www.python.org)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green)](https://nodejs.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/kapilthakare-cyberpunk/exo-claude-code-setup/pulls)

> **Run Claude Code against locally-hosted AI models via EXO — zero cloud API costs, full data privacy.**

## About

Claude Code is Anthropic's powerful agentic coding tool, but it requires a cloud API key and sends code to their servers. This guide shows you how to redirect Claude Code to use [EXO](https://github.com/exo-explore/exo) — a local inference engine that runs open-source models on your own Mac.

**Why?**
- **Privacy** — your code never leaves your machine
- **No API costs** — run unlimited queries
- **Offline-capable** — work without internet
- **Model freedom** — switch between any open-source model

**How it works:** Claude Code speaks the Anthropic Messages API format. EXO speaks the OpenAI Chat API format. A lightweight Python proxy (included) translates between them seamlessly.

```
┌─────────────┐     Anthropic API      ┌──────────────────┐     OpenAI API      ┌─────────┐
│ Claude Code │ ──────────────────►    │ Proxy (port 8080)│ ────────────────►  │ EXO     │
│  (claude)   │ ◄──────────────────    │ translates fmt   │ ◄────────────────  │ :52415  │
└─────────────┘     Anthropic fmt      └──────────────────┘     OpenAI fmt     └─────────┘
```

## Table of Contents

- [System Requirements](#system-requirements)
- [Step 1: Install EXO](#step-1-install-exo)
- [Step 2: Install Claude Code](#step-2-install-claude-code)
- [Step 3: Start EXO](#step-3-start-exo)
- [Step 4: Install Proxy Dependencies](#step-4-install-proxy-dependencies)
- [Step 5: Start the Proxy](#step-5-start-the-proxy)
- [Step 6: Configure Claude Code](#step-6-configure-claude-code)
- [Step 7: Run](#step-7-run)
- [Switching Models](#switching-models)
- [Troubleshooting](#troubleshooting)
- [Model Recommendations](#model-recommendations-by-ram)

## System Requirements

- **Hardware:** Apple Silicon Mac (M1/M2/M3/M4) with 16GB+ RAM
- **Software:** macOS, Python 3.10+, Node.js 18+
- **Storage:** 15–250 GB free space depending on model

## Step 1: Install EXO

```bash
git clone https://github.com/exo-explore/exo.git
cd exo
pip install -e .
```

## Step 2: Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
claude --version
# → 2.x.x (Claude Code)
```

## Step 3: Start EXO

```bash
cd ~/exo
python3 main.py
```

Open **http://127.0.0.1:52415** in a browser:
1. Select a model (e.g. `mlx-community/Qwen3.5-27B-4bit`)
2. Wait for it to download and load
3. Note the exact model ID — you'll need it later

## Step 4: Install Proxy Dependencies

```bash
pip3 install httpx uvicorn fastapi
```

## Step 5: Start the Proxy

```bash
python3 proxy.py
```

The proxy translates between the Anthropic Messages API (what Claude Code speaks) and the OpenAI Chat API (what EXO speaks). It handles:
- System prompt conversion (`role: "system"` → `role: "system"` in OpenAI format)
- Streaming response translation (SSE → SSE with format conversion)
- Non-streaming request/response translation

## Step 6: Configure Claude Code

Create `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8080",
    "ANTHROPIC_API_KEY": "x",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "mlx-community/Qwen3.5-27B-4bit",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "mlx-community/Qwen3.5-27B-4bit",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mlx-community/Qwen3.5-27B-4bit",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "effortLevel": "high"
}
```

Replace `Qwen3.5-27B-4bit` with whatever model you loaded in EXO.

## Step 7: Run

| Component | Command |
|-----------|---------|
| **EXO** | `cd ~/exo && python3 main.py` |
| **Proxy** | `python3 proxy.py` |
| **Claude Code** | `claude` |

Open three terminals (or use tmux) and run each command.

## Switching Models

1. Open EXO web UI at http://127.0.0.1:52415
2. Select and load a new model
3. Update model IDs in `~/.claude/settings.json`
4. Restart the proxy: `pkill -f proxy.py && python3 proxy.py`

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `API Error: 422 role system` | Proxy not running | `python3 proxy.py` |
| `Connection refused` | EXO not running | `cd ~/exo && python3 main.py` |
| `Address already in use` on 8080 | Proxy already running | `pkill -f proxy.py` or use `lsof -i :8080` to find PID and kill it |
| Model gives weak/truncated responses | Model too small | Switch to a larger coding model |
| `Not logged in` banner | Claude Code can't reach Anthropic auth | **Cosmetic only** — it still works; ignore |

## Model Recommendations by RAM

| RAM | Best for coding | RAM usage | Disk |
|-----|----------------|-----------|------|
| 16 GB | `Qwen3.5-27B-4bit` | ~15 GB | ~15 GB |
| 24 GB | `Qwen3.5-27B-4bit` or `Qwen3.5-35B-A3B-4bit` | ~15–19 GB | ~15–19 GB |
| 32 GB | `Qwen3-Coder-Next-4bit` | ~43 GB | ~43 GB |
| 48 GB+ | `Qwen3-Coder-480B-A35B-4bit` | ~276 GB | ~276 GB |
| 64 GB+ | `DeepSeek-V3.2-4bit` | ~360 GB | ~360 GB |

## File Structure

```
exo-claude-code-setup/
├── README.md        # This guide
├── proxy.py         # Anthropic → OpenAI translation proxy
└── LICENSE          # MIT
```

## License

MIT
