# EXO + Claude Code Setup Guide

Locally-hosted AI coding assistant using [EXO](https://github.com/exo-explore/exo) as the inference engine with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) as the frontend.

## System Requirements

- **Hardware:** Apple Silicon Mac (M1/M2/M3/M4) with 16GB+ RAM
- **Software:** macOS, Python 3.10+, Node.js 18+
- **Storage:** 15-250GB free space depending on model size

## Architecture

```
┌─────────────┐     Anthropic API      ┌──────────────────┐     OpenAI API      ┌─────────┐
│ Claude Code │ ──────────────────►    │ Proxy (port 8080)│ ────────────────►  │ EXO     │
│  (claude)   │ ◄──────────────────    │ translates fmt   │ ◄────────────────  │ :52415  │
└─────────────┘     Anthropic fmt      └──────────────────┘     OpenAI fmt     └─────────┘
```

Claude Code speaks the Anthropic Messages API. EXO speaks the OpenAI Chat API. The proxy translates between them.

---

## Step 1: Install EXO

```bash
# Clone EXO
git clone https://github.com/exo-explore/exo.git
cd exo

# Install
pip install -e .
```

## Step 2: Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
claude --version
# Should print: 2.x.x (Claude Code)
```

## Step 3: Start EXO

```bash
cd ~/exo
python3 main.py
```

This starts EXO's web UI at **http://127.0.0.1:52415**

Open that URL in a browser and:
1. Select/load a model (e.g., `mlx-community/Qwen3.5-27B-4bit`)
2. Wait for download + load to complete
3. Note the model ID shown in the UI

## Step 4: Install Proxy Dependencies

The proxy translates between Anthropic and OpenAI API formats.

```bash
pip3 install httpx uvicorn fastapi
```

## Step 5: Create the Proxy

Save this as `/tmp/claude_exo_proxy.py`:

```python
import json
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

app = FastAPI()
EXO_BASE = "http://127.0.0.1:52415/v1"

@app.post("/v1/messages")
async def proxy_messages(request: Request):
    body = await request.json()

    system_text = None
    messages = []
    for msg in body.get("messages", []):
        if msg.get("role") == "system":
            system_text = msg.get("content", "")
        else:
            messages.append(msg)

    openai_body = {
        "model": body.get("model", ""),
        "messages": messages,
        "max_tokens": body.get("max_tokens", 4096),
        "stream": body.get("stream", False),
        "temperature": body.get("temperature", 0.7),
    }
    if system_text:
        openai_body["messages"].insert(0, {"role": "system", "content": system_text})

    headers = {
        "Authorization": "Bearer x",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        if openai_body["stream"]:
            req = client.post(
                f"{EXO_BASE}/chat/completions",
                json=openai_body,
                headers=headers,
            )
            resp = await req

            async def stream_transform():
                prefix = 'data: {"type":"message_start","message":{"id":"msg_1","type":"message","role":"assistant","content":[],"model":"' + body.get("model", "") + '","stop_reason":null,"usage":{"input_tokens":0,"output_tokens":0}}}\n\n'
                yield prefix

                full_text = ""
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if delta.get("content"):
                            text = delta["content"]
                            full_text += text
                            yield f'data: {{"type":"content_block_delta","index":0,"delta":{{"type":"text_delta","text":{json.dumps(text)}}}}}\n\n'
                        if chunk["choices"][0].get("finish_reason"):
                            finish = chunk["choices"][0]["finish_reason"]
                            yield f'data: {{"type":"message_delta","delta":{{"stop_reason":"{finish}","stop_sequence":null}},"usage":{{"output_tokens":{len(full_text.split())}}}}}\n\n'

                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_transform(),
                media_type="text/event-stream",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            resp = await client.post(f"{EXO_BASE}/chat/completions", json=openai_body, headers=headers)
            data = resp.json()
            choice = data["choices"][0]
            anthropic_resp = {
                "id": data.get("id", ""),
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": choice["message"]["content"]}],
                "model": data["model"],
                "stop_reason": choice.get("finish_reason", "end_turn"),
                "usage": {
                    "input_tokens": data["usage"].get("prompt_tokens", 0),
                    "output_tokens": data["usage"].get("completion_tokens", 0),
                },
            }
            return JSONResponse(content=anthropic_resp)

@app.get("/v1/models")
async def list_models():
    return {
        "data": [
            {
                "id": body.get("model", ""),
                "object": "model",
                "created": 1677610602,
                "owned_by": "exo",
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
```

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

## Step 7: Run

**Terminal 1 — EXO:**
```bash
cd ~/exo && python3 main.py
```

**Terminal 2 — Proxy:**
```bash
python3 /tmp/claude_exo_proxy.py
```

**Terminal 3 — Claude Code:**
```bash
claude
```

## Switching Models

1. Open EXO web UI at http://127.0.0.1:52415
2. Select a new model (wait for download + load)
3. Update the model IDs in `~/.claude/settings.json`
4. Restart the proxy (`pkill -f claude_exo_proxy && python3 /tmp/claude_exo_proxy.py`)

## Troubleshooting

### "API Error: 422 role system"
The proxy is not running. Start it with `python3 /tmp/claude_exo_proxy.py`.

### "Connection refused"
EXO is not running. Start it with `cd ~/exo && python3 main.py`.

### Model stuck/weak responses
The model is too small for the task. Switch to a larger coding model (Qwen3.5-27B-4bit or better).

### "Address already in use" on port 8080
Kill the existing proxy: `pkill -f claude_exo_proxy`

## Model Recommendations by RAM

| RAM | Best coding model | RAM usage |
|-----|------------------|-----------|
| 16GB | Qwen3.5-27B-4bit | ~15GB |
| 24GB | Qwen3.5-27B-4bit or Qwen3.5-35B-A3B-4bit | ~15-19GB |
| 32GB | Qwen3-Coder-Next-4bit | ~43GB |
| 64GB+ | Qwen3-Coder-480B-A35B-8bit or DeepSeek-V3.2-8bit | ~276-720GB |
