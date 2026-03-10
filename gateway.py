"""
FastAPI gateway layer for ComputerUseAgent.

This module exposes:
  - /api/health
  - /api/config (get/update config.json)
  - /api/sessions (list/get/delete)
  - /api/chat/stream (SSE stream of agent events)

It intentionally reuses existing agent/runtime code (graph/*, config.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import (
    CONFIG_FILE,
    load_config,
    save_config,
    get_base_dir,
)
from graph.agent import agent_manager
from graph.session_manager import session_manager
from tools.skills_scanner import scan_skills


app = FastAPI(title="ComputerUseAgent Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigPatch(BaseModel):
    """A partial update to config.json (deep-merged at top-level keys)."""

    platform: Optional[str] = None
    base_dir: Optional[str] = None
    rag_mode: Optional[bool] = None
    deepagent: Optional[bool] = None
    llm: Optional[dict[str, Any]] = None
    embeddings: Optional[dict[str, Any]] = None
    tools: Optional[dict[str, Any]] = None
    mcps: Optional[dict[str, Any]] = None


class ChatStreamRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=64)
    message: str = Field(min_length=1)
    enable_thinking: bool = False
    image_url: Optional[str] = None


def _ensure_runtime_initialized(base_dir: Path) -> None:
    """
    Initialize agent and session storage. Safe to call multiple times.
    """
    session_manager.initialize(base_dir)
    agent_manager.initialize(base_dir=base_dir)
    scan_skills(base_dir=base_dir)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "config_file": str(CONFIG_FILE),
        "config_exists": CONFIG_FILE.exists(),
    }


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return load_config()


@app.put("/api/config")
def update_config(patch: ConfigPatch) -> dict[str, Any]:
    current = load_config()
    updates = patch.model_dump(exclude_unset=True)
    merged = {**current, **updates}
    save_config(merged)
    return merged


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    return session_manager.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    return session_manager.get_raw_messages(session_id)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    session_manager.delete_session(session_id)
    return {"deleted": True, "session_id": session_id}


@app.post("/api/sessions/{session_id}/clear")
def clear_session(session_id: str) -> dict[str, Any]:
    """Clear all messages in a session. Session file is kept."""
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    session_manager.clear_messages(session_id)
    return {"cleared": True, "session_id": session_id}


async def _sse_event_generator(req: ChatStreamRequest) -> AsyncGenerator[dict[str, str], None]:
    """
    Yield SSE events where `data` is a JSON string of the agent event.
    """
    try:
        base_dir = Path(get_base_dir())
        if not base_dir.exists():
            raise HTTPException(status_code=400, detail=f"base_dir not found: {base_dir}")

        _ensure_runtime_initialized(base_dir)
        history = session_manager.load_session_for_agent(req.session_id)

        session_manager.save_message(req.session_id, "user", req.message)

        async for event in agent_manager.astream(
            message=req.message,
            history=history,
            image_url=req.image_url,
        ):
            # Persist final assistant content on ALL_DONE
            if event.get("type") == "all_done":
                content = event.get("content") or ""
                if content:
                    session_manager.save_message(req.session_id, "assistant", content)

            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

        yield {"event": "end", "data": json.dumps({"type": "stream_ended"}, ensure_ascii=False)}
    except HTTPException as e:
        yield {"event": "error", "data": json.dumps({"type": "error", "content": e.detail}, ensure_ascii=False)}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}


@app.post("/api/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    """
    SSE endpoint. Each event is identical in shape to the existing TUI event stream.
    """
    return EventSourceResponse(_sse_event_generator(req), media_type="text/event-stream")

