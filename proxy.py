#!/usr/bin/env python3
"""
Anthropic → OpenAI API translation proxy.

Sits between Claude Code (Anthropic Messages API) and EXO (OpenAI Chat API).
Handles streaming and non-streaming requests, including system prompt conversion.

Usage:
    python3 proxy.py
"""

import json
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

EXO_BASE = "http://127.0.0.1:52415/v1"
PROXY_PORT = 8080

app = FastAPI(title="Claude Code → EXO Proxy")


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    body = await request.json()
    model = body.get("model", "")
    stream = body.get("stream", False)

    # Separate system message from user/assistant messages
    system_text = None
    messages = []
    for msg in body.get("messages", []):
        if msg.get("role") == "system":
            system_text = msg.get("content", "")
        else:
            messages.append({"role": msg["role"], "content": msg["content"]})

    openai_body = {
        "model": model,
        "messages": messages,
        "max_tokens": body.get("max_tokens", 8192),
        "stream": stream,
        "temperature": body.get("temperature", 0.7),
    }
    if system_text:
        openai_body["messages"].insert(0, {"role": "system", "content": system_text})

    headers = {
        "Authorization": "Bearer x",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        if stream:
            req = client.post(f"{EXO_BASE}/chat/completions", json=openai_body, headers=headers)
            resp = await req

            async def transform_stream():
                # Message start event (required by Anthropic SSE format)
                start = {
                    "type": "message_start",
                    "message": {
                        "id": "msg_1",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": model,
                        "stop_reason": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                }
                yield f"data: {json.dumps(start)}\n\n"

                full_text = ""
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text += content
                            block = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": content},
                            }
                            yield f"data: {json.dumps(block)}\n\n"

                        finish = chunk["choices"][0].get("finish_reason")
                        if finish:
                            msg_delta = {
                                "type": "message_delta",
                                "delta": {"stop_reason": finish, "stop_sequence": None},
                                "usage": {"output_tokens": len(full_text.split())},
                            }
                            yield f"data: {json.dumps(msg_delta)}\n\n"

                yield "data: [DONE]\n\n"

            return StreamingResponse(
                transform_stream(),
                media_type="text/event-stream",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # Non-streaming
        resp = await client.post(f"{EXO_BASE}/chat/completions", json=openai_body, headers=headers)
        data = resp.json()
        choice = data["choices"][0]

        anthropic_resp = {
            "id": data.get("id", "msg_1"),
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
                "id": "mlx-community/Qwen3.5-27B-4bit",
                "object": "model",
                "created": 1677610602,
                "owned_by": "exo",
            }
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    print(f"Starting proxy on http://127.0.0.1:{PROXY_PORT}")
    print(f"Forwarding to EXO at {EXO_BASE}")
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="info")
