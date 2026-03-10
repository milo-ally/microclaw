"""
microclaw GUI - Gradio-based web interface.

Features (parity with TUI):
  - Health check
  - Config view/edit
  - Sessions list/view/delete/clear
  - Chat with SSE streaming
  - File editor: workplace/*.md, memory/MEMORY.md
"""

from __future__ import annotations

import argparse
import json
import re
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Generator, Optional

import gradio as gr


@dataclass(frozen=True)
class GatewayClient:
    base_url: str
    timeout_s: float = 60.0

    def _url(self, path: str) -> str:
        return urllib.parse.urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _request_json(
        self,
        method: str,
        path: str,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = self._url(path)
        data = None
        req_headers = {"Accept": "application/json"}
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            data = raw
            req_headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, method=method.upper(), data=data, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                text = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
                if not text.strip():
                    return None
                return json.loads(text)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network: {e}") from e

    def health(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/health")

    def get_config(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/config")

    def put_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("PUT", "/api/config", body=patch)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._request_json("GET", "/api/sessions")

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/api/sessions/{urllib.parse.quote(session_id)}")

    def delete_session(self, session_id: str) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/sessions/{urllib.parse.quote(session_id)}")

    def clear_session(self, session_id: str) -> dict[str, Any]:
        return self._request_json("POST", f"/api/sessions/{urllib.parse.quote(session_id)}/clear")

    def chat_stream(self, payload: dict[str, Any]) -> Generator[tuple[str, str], None, None]:
        """Yield (role, chunk) for streaming display."""
        url = self._url("/api/chat/stream")
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            method="POST",
            data=raw,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout_s)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            raise RuntimeError(str(e)) from e

        buf = []
        event_name = "message"
        with resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    if buf:
                        data = "\n".join(buf)
                        buf = []
                        if event_name == "error":
                            try:
                                obj = json.loads(data)
                                yield ("assistant", f"<span style='color:#c22'>Error: {obj.get('content', data)}</span>")
                            except Exception:
                                yield ("assistant", f"<span style='color:#c22'>Error: {data}</span>")
                            event_name = "message"
                            continue
                        if event_name == "end":
                            event_name = "message"
                            continue
                        try:
                            obj = json.loads(data)
                        except Exception:
                            event_name = "message"
                            continue
                        et = obj.get("type")
                        content = obj.get("content") or ""
                        if et == "token":
                            yield ("assistant", content)
                        elif et == "reasoning_token":
                            yield ("assistant", f"<span style='color:#888'>{content}</span>")


                        elif et == "tool_calling":
                            # Don't stream raw tool-calling args (often large JSON).
                            # Tool execution status is handled separately via tool_execute/tool_response events.
                            continue
                        elif et == "toolcall_message":
                            # Don't surface internal toolcall messages (often verbose JSON / system prompts).
                            # GUI 只展示上层助手回复和精简的工具状态，由 _chat_stream_ui 控制。
                            pass
                        
                        elif et == "tool_execute":
                            tname = obj.get("tool", "")
                            tin = obj.get("input", "")
                            yield ("assistant", f"<span style='color:#36c'>[tool] {tname}: {str(tin)[:80]}...</span>\n")
                        
                        elif et == "tool_response":
                            tname = obj.get("tool", "")
                            tout = obj.get("output", "")

                            yield ("assistant", f"<span style='color:#2a2'>[done] {tname}: {str(tout)[:80]}...</span>\n")
                        elif et == "retrieval":
                            results = obj.get("results") or []
                            if results:
                                parts = ["<span style='color:#888'>[RAG]</span>"]
                                for r in results[:3]:
                                    text = (r.get("text") or "")[:100]
                                    parts.append(f"• {text}...")
                                yield ("assistant", "\n".join(parts) + "\n")
                        elif et == "all_done":
                            pass
                    event_name = "message"
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                elif line.startswith("data:"):
                    buf.append(line[5:].lstrip())

    def list_workplace_files(self) -> list[str]:
        return self._request_json("GET", "/api/files/workplace") or []

    def read_workplace_file(self, filename: str) -> str:
        r = self._request_json("GET", f"/api/files/workplace/{urllib.parse.quote(filename)}")
        return r.get("content", "")

    def write_workplace_file(self, filename: str, content: str) -> None:
        self._request_json("PUT", f"/api/files/workplace/{urllib.parse.quote(filename)}", body={"content": content})

    def read_memory(self) -> str:
        r = self._request_json("GET", "/api/files/memory")
        return r.get("content", "")

    def write_memory(self, content: str) -> None:
        self._request_json("PUT", "/api/files/memory", body={"content": content})

    def cleanup_workspace(self) -> dict[str, Any]:
        """Remove workspace files/dirs except memory, sessions, skills, storage, workplace."""
        return self._request_json("POST", "/api/cleanup", body={})


# Global client (set by main)
_client: Optional[GatewayClient] = None


def _client_or_raise() -> GatewayClient:
    if _client is None:
        raise RuntimeError("Gateway client not initialized")
    return _client


def _health_ui() -> str:
    try:
        c = _client_or_raise()
        h = c.health()
        return f"```json\n{json.dumps(h, ensure_ascii=False, indent=2)}\n```"
    except Exception as e:
        return f"❌ **Error:** {e}"


# Tools with optional extra params (param_key -> label)
_TOOL_EXTRA_PARAMS = {
    "sql_tools": [("db_uri", "DB URI")],
    "tavily_search_tool": [("tavily_api_key", "Tavily API Key")],
}
_COMMON_TOOLS = [
    "ask_user_question_tool",
    "fetch_url_tool",
    "python_repl_tool",
    "sql_tools",
    "read_file_tool",
    "tavily_search_tool",
    "terminal_tool",
]


def _config_load_to_form() -> tuple:
    """Load config from gateway and return values for all form fields."""
    try:
        c = _client_or_raise()
        cfg = c.get_config()
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}") from e

    platform = str(cfg.get("platform", ""))
    base_dir = str(cfg.get("base_dir", ""))
    rag_mode = bool(cfg.get("rag_mode", False))
    deepagent = bool(cfg.get("deepagent", False))

    llm = cfg.get("llm") or {}
    llm_provider = str(llm.get("provider", "openai"))
    llm_info = llm.get("info") or {}
    llm_model = str(llm_info.get("model", ""))
    llm_base_url = str(llm_info.get("base_url", ""))
    llm_api_key = str(llm_info.get("api_key", ""))
    llm_temperature = float(llm_info.get("temperature", 0.1))
    llm_enable_thinking = bool(llm_info.get("enable_thinking", False))
    llm_is_vision = bool(llm_info.get("is_vision_model", False))

    emb = cfg.get("embeddings") or {}
    emb_provider = str(emb.get("provider", "openai"))
    emb_info = emb.get("info") or {}
    emb_model = str(emb_info.get("model", ""))
    emb_base_url = str(emb_info.get("base_url", ""))
    emb_api_key = str(emb_info.get("api_key", ""))

    tools = cfg.get("tools") or {}
    tool_checks = []
    tool_extras = []
    for t in _COMMON_TOOLS:
        entry = tools.get(t) or {}
        status = str(entry.get("status", "off")).lower()
        tool_checks.append(status == "on")
        for param_key, _ in _TOOL_EXTRA_PARAMS.get(t, []):
            tool_extras.append(str(entry.get(param_key, "")))

    mcps_json = json.dumps(cfg.get("mcps") or {}, ensure_ascii=False, indent=2)

    return (
        platform,
        base_dir,
        rag_mode,
        deepagent,
        llm_provider,
        llm_model,
        llm_base_url,
        llm_api_key,
        llm_temperature,
        llm_enable_thinking,
        llm_is_vision,
        emb_provider,
        emb_model,
        emb_base_url,
        emb_api_key,
        *tool_checks,
        *tool_extras,
        mcps_json,
    )


def _config_save_from_form(
    platform: str,
    base_dir: str,
    rag_mode: bool,
    deepagent: bool,
    llm_provider: str,
    llm_model: str,
    llm_base_url: str,
    llm_api_key: str,
    llm_temperature: float,
    llm_enable_thinking: bool,
    llm_is_vision: bool,
    emb_provider: str,
    emb_model: str,
    emb_base_url: str,
    emb_api_key: str,
    tool_ask: bool,
    tool_fetch: bool,
    tool_python: bool,
    tool_sql: bool,
    tool_read: bool,
    tool_tavily: bool,
    tool_terminal: bool,
    sql_db_uri: str,
    tavily_api_key: str,
    mcps_json: str,
) -> str:
    """Collect form values and save to gateway."""
    try:
        c = _client_or_raise()
        def _s(x):
            return (x or "").strip()

        tools_map = {
            "ask_user_question_tool": {"status": "on" if tool_ask else "off"},
            "fetch_url_tool": {"status": "on" if tool_fetch else "off"},
            "python_repl_tool": {"status": "on" if tool_python else "off"},
            "sql_tools": {"status": "on" if tool_sql else "off", "db_uri": _s(sql_db_uri) or ""},
            "read_file_tool": {"status": "on" if tool_read else "off"},
            "tavily_search_tool": {"status": "on" if tool_tavily else "off", "tavily_api_key": _s(tavily_api_key) or ""},
            "terminal_tool": {"status": "on" if tool_terminal else "off"},
        }
        llm = {
            "provider": _s(llm_provider) or "openai",
            "format": "openai",
            "info": {
                "model": _s(llm_model),
                "base_url": _s(llm_base_url),
                "api_key": _s(llm_api_key),
                "temperature": float(llm_temperature or 0.1),
                "enable_thinking": bool(llm_enable_thinking),
                "is_vision_model": bool(llm_is_vision),
            },
        }
        embeddings = {
            "provider": _s(emb_provider) or "openai",
            "format": "openai",
            "info": {
                "model": _s(emb_model),
                "base_url": _s(emb_base_url),
                "api_key": _s(emb_api_key),
            },
        }
        mcps = {}
        if _s(mcps_json):
            mcps = json.loads(mcps_json)

        base_dir_val = _s(base_dir)
        platform_val = _s(platform)
        patch = {
            "rag_mode": rag_mode,
            "deepagent": deepagent,
            "llm": llm,
            "embeddings": embeddings,
            "tools": tools_map,
            "mcps": mcps,
        }
        if platform_val:
            patch["platform"] = platform_val
        if base_dir_val:
            patch["base_dir"] = base_dir_val
        c.put_config(patch)
        return "✅ **Config saved successfully.**"
    except json.JSONDecodeError as e:
        return f"❌ **Invalid MCPs JSON:** {e}"
    except Exception as e:
        return f"❌ **Error:** {e}"


def _sessions_list_ui() -> str:
    try:
        c = _client_or_raise()
        sessions = c.list_sessions()
        if not sessions:
            return "_No sessions._"
        lines = ["| ID | Title | Updated |", "|----|-------|---------|"]
        for s in sessions[:30]:
            sid = s.get("id", "")
            title = (s.get("title") or "")[:40]
            ts = s.get("updated_at", 0)
            try:
                import time
                ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
            except Exception:
                ts_str = str(ts)
            lines.append(f"| {sid} | {title} | {ts_str} |")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ **Error:** {e}"


def _session_delete_ui(session_id: str) -> str:
    if not session_id.strip():
        return "⚠️ Enter a session ID."
    try:
        c = _client_or_raise()
        c.delete_session(session_id.strip())
        return f"✅ Deleted session `{session_id}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _session_clear_ui(session_id: str) -> str:
    if not session_id.strip():
        return "⚠️ Enter a session ID."
    try:
        c = _client_or_raise()
        c.clear_session(session_id.strip())
        return f"✅ Cleared session `{session_id}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _sessions_for_dropdown() -> tuple[list[tuple[str, str]], str]:
    """Return (choices, default_value) for session dropdown. choices: [(label, id), ...]"""
    try:
        c = _client_or_raise()
        sessions = c.list_sessions()
        choices = [("➕ New chat", "__new__")]
        for s in sessions:
            sid = s.get("id", "")
            if not sid:
                continue
            # Use hash-like session id directly as the display label
            choices.append((sid, sid))
        return choices, "__new__"
    except Exception:
        return [("➕ New chat", "__new__")], "__new__"


def _load_session_ui(session_id: str) -> tuple[list[dict[str, str]], str]:
    """Load session messages into chatbot format. Returns (chatbot_history, session_id_for_chat)."""
    if not session_id or session_id == "__new__":
        new_id = f"session_{time.strftime('%Y%m%d_%H%M%S')}"
        return [], new_id
    try:
        c = _client_or_raise()
        data = c.get_session(session_id)
        messages = data.get("messages", [])
        history = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant"):
                history.append({"role": role, "content": content})
        return history, session_id
    except Exception:
        return [], session_id


def _chat_stream_ui(
    message: str,
    history: list[dict[str, str]],
    session_id: str,
) -> Generator[list[dict[str, str]], None, None]:
    """Yield chat history in Gradio 6 messages format: [{\"role\": \"user\"|\"assistant\", \"content\": \"...\"}].

    优化点：
    - 普通助手回复保持一个连续气泡，逐 token 更新。
    - 工具 / RAG 等结构化信息不再打印详细输入输出，只显示一个包含工具名的状态气泡，
      例如“Calling tool `terminal_tool` ··”，减少单条消息的复杂度和体积。
    """

    def _is_tool_like_chunk(text: str) -> bool:
        t = (text or "").lstrip()
        return (
            t.startswith("<span style='color:#36c'>[tool]")
            or t.startswith("<span style='color:#36c'>[done]")
            or t.startswith("<span style='color:#888'>[RAG]")
        )

    def _strip_tags(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text or "").strip()

    def _parse_tool_name(text: str) -> str:
        """从工具相关的 HTML 片段里提取工具名。"""
        clean = _strip_tags(text)
        for prefix in ("[tool]", "[done]"):
            if clean.startswith(prefix):
                rest = clean[len(prefix) :].strip()
                return (rest.split(":", 1)[0] or "tool").strip()
        if clean.startswith("[RAG]"):
            return "retrieval"
        return "tool"

    if not message.strip():
        yield history
        return
    base_history: list[dict[str, str]] = history + [{"role": "user", "content": message}]
    display_history = list(base_history)
    current_assistant = ""
    current_assistant_index: Optional[int] = None

    try:
        c = _client_or_raise()
        payload = {"session_id": session_id or "default", "message": message, "enable_thinking": False}
        for _role, chunk in c.chat_stream(payload):
            # 完全隐藏工具 / RAG 相关的系统输出，只展示模型最终自然语言回复
            if _is_tool_like_chunk(chunk):
                continue

            # 普通 model 输出：累积到当前 assistant 气泡
            current_assistant += chunk
            if current_assistant_index is None:
                display_history.append({"role": "assistant", "content": current_assistant})
                current_assistant_index = len(display_history) - 1
            else:
                display_history[current_assistant_index] = {
                    "role": "assistant",
                    "content": current_assistant,
                }
            yield display_history
    except Exception as e:
        display_history.append({"role": "assistant", "content": f"❌ **Error:** {e}"})
        yield display_history


def _workplace_files_ui() -> dict:
    """Return gr.update(choices=...) for dropdown."""
    try:
        c = _client_or_raise()
        files = c.list_workplace_files()
        return gr.update(choices=files)
    except Exception:
        return gr.update(choices=[])


def _workplace_load_ui(filename: str) -> str:
    if not filename:
        return ""
    try:
        c = _client_or_raise()
        return c.read_workplace_file(filename)
    except Exception as e:
        return f"Error: {e}"


def _workplace_save_ui(filename: str, content: str) -> str:
    if not filename:
        return "⚠️ Select a file first."
    try:
        c = _client_or_raise()
        c.write_workplace_file(filename, content)
        return f"✅ Saved `{filename}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _memory_load_ui() -> str:
    try:
        c = _client_or_raise()
        return c.read_memory()
    except Exception as e:
        return f"Error: {e}"


def _memory_save_ui(content: str) -> str:
    try:
        c = _client_or_raise()
        c.write_memory(content)
        return "✅ Saved MEMORY.md."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _cleanup_workspace_ui() -> str:
    """Clean workspace: remove all except memory, sessions, skills, storage, workplace."""
    try:
        c = _client_or_raise()
        out = c.cleanup_workspace()
        removed = out.get("removed", [])
        if removed:
            return f"✅ **Workspace cleaned.** Removed: {', '.join(removed)}"
        return "✅ **Workspace already clean.** Nothing to remove."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _build_ui(gateway_url: str) -> gr.Blocks:
    global _client
    _client = GatewayClient(base_url=gateway_url)

    with gr.Blocks(title="microclaw") as demo:
        gr.Markdown("# microclaw · Gateway GUI")

        with gr.Tabs():
            # ---- Chat ----
            with gr.TabItem("💬 Chat"):
                with gr.Column(elem_classes=["chat-main"]):
                    with gr.Row():
                        refresh_sessions_btn = gr.Button("🔄", scale=0)
                        sessions_dd = gr.Dropdown(
                            label="Select session",
                            choices=[("➕ New chat", "__new__")],
                            value="__new__",
                            allow_custom_value=False,
                        )
                    session_id_state = gr.State(value=f"session_{time.strftime('%Y%m%d_%H%M%S')}")
                    chatbot = gr.Chatbot(
                        label="",
                        elem_classes=["chat-container"],
                        height=520,
                        show_label=False,
                    )
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Type your message... (supports markdown)",
                        lines=4,
                        show_label=False,
                        elem_id="chat-input",
                    )
                    with gr.Row(elem_classes=["bottom-actions"]):
                        submit_btn = gr.Button("Send", variant="primary", elem_id="send-btn")
                        clear_btn = gr.Button("Clear")
                        clean_btn = gr.Button("🧹 Clean workspace", variant="secondary")
                    gr.Markdown(
                        "_Clean workspace removes all files except memory, sessions, skills, storage, and workplace._",
                        elem_classes=["clean-note"],
                    )
                    clean_status = gr.Markdown("")

                def _refresh_sessions():
                    choices, _ = _sessions_for_dropdown()
                    return gr.update(choices=choices, value="__new__"), f"session_{time.strftime('%Y%m%d_%H%M%S')}"

                def _on_session_select(sid):
                    hist, chat_id = _load_session_ui(sid)
                    return hist, chat_id

                refresh_sessions_btn.click(
                    _refresh_sessions,
                    outputs=[sessions_dd, session_id_state],
                ).then(lambda: [], outputs=[chatbot])
                sessions_dd.change(
                    _on_session_select,
                    inputs=[sessions_dd],
                    outputs=[chatbot, session_id_state],
                )
                def _refresh_choices_after_send(sid):
                    choices, _ = _sessions_for_dropdown()
                    ids = [c[1] for c in choices]
                    if sid and sid in ids:
                        return gr.update(choices=choices, value=sid)
                    return gr.update(choices=choices)

                submit_btn.click(
                    _chat_stream_ui,
                    inputs=[msg, chatbot, session_id_state],
                    outputs=[chatbot],
                ).then(lambda: "", outputs=[msg]).then(
                    _refresh_choices_after_send,
                    inputs=[session_id_state],
                    outputs=[sessions_dd],
                )
                clear_btn.click(lambda: [], outputs=[chatbot])
                clean_btn.click(_cleanup_workspace_ui, outputs=[clean_status])

                demo.load(_refresh_sessions, outputs=[sessions_dd, session_id_state])

            # ---- Config ----
            with gr.TabItem("⚙️ Config"):
                config_status = gr.Markdown("_Click Load to fetch config._")
                with gr.Row():
                    config_load_btn = gr.Button("Load config")
                    config_save_btn = gr.Button("Save config", variant="primary")

                with gr.Accordion("Basic", open=True):
                    cfg_platform = gr.Textbox(label="Platform", placeholder="e.g. Ubuntu24.04")
                    cfg_base_dir = gr.Textbox(label="Base directory (agent path)", placeholder="/path/to/agent")
                    with gr.Row():
                        cfg_rag_mode = gr.Checkbox(label="RAG mode", value=False)
                        cfg_deepagent = gr.Checkbox(label="DeepAgent", value=False)

                with gr.Accordion("LLM (Chat model)", open=True):
                    cfg_llm_provider = gr.Textbox(label="Provider", placeholder="deepseek / openai")
                    cfg_llm_model = gr.Textbox(label="Model", placeholder="deepseek-chat")
                    cfg_llm_base_url = gr.Textbox(label="Base URL", placeholder="https://api.deepseek.com")
                    cfg_llm_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")
                    with gr.Row():
                        cfg_llm_temp = gr.Number(label="Temperature", value=0.1, minimum=0, maximum=2, step=0.1)
                        cfg_llm_thinking = gr.Checkbox(label="Enable thinking", value=False)
                        cfg_llm_vision = gr.Checkbox(label="Vision model", value=False)

                with gr.Accordion("Embeddings", open=True):
                    cfg_emb_provider = gr.Textbox(label="Provider", placeholder="aliyun / openai")
                    cfg_emb_model = gr.Textbox(label="Model", placeholder="text-embedding-v3")
                    cfg_emb_base_url = gr.Textbox(label="Base URL", placeholder="https://...")
                    cfg_emb_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")

                with gr.Accordion("Tools (switch on/off)", open=True):
                    gr.Markdown("Toggle each tool. Some tools have extra parameters below.")
                    with gr.Row():
                        cfg_tool_ask = gr.Checkbox(label="ask_user_question", value=True)
                        cfg_tool_fetch = gr.Checkbox(label="fetch_url", value=True)
                        cfg_tool_python = gr.Checkbox(label="python_repl", value=True)
                        cfg_tool_sql = gr.Checkbox(label="sql_tools", value=False)
                        cfg_tool_read = gr.Checkbox(label="read_file", value=True)
                        cfg_tool_tavily = gr.Checkbox(label="tavily_search", value=False)
                        cfg_tool_terminal = gr.Checkbox(label="terminal", value=True)
                    with gr.Row():
                        cfg_sql_db_uri = gr.Textbox(
                            label="SQL: DB URI (when sql_tools enabled)",
                            placeholder="postgresql+psycopg2://user:pass@host:5432/db",
                            visible=True,
                        )
                        cfg_tavily_key = gr.Textbox(
                            label="Tavily: API Key (when tavily_search enabled)",
                            placeholder="tvly-...",
                            type="password",
                        )

                with gr.Accordion("MCPs (advanced JSON)", open=False):
                    cfg_mcps_json = gr.Textbox(
                        label="MCPs config (JSON)",
                        lines=8,
                        placeholder='{"server-name": {"transport": "streamable-http", "url": "http://..."}}',
                    )

                config_load_btn.click(
                    _config_load_to_form,
                    outputs=[
                        cfg_platform,
                        cfg_base_dir,
                        cfg_rag_mode,
                        cfg_deepagent,
                        cfg_llm_provider,
                        cfg_llm_model,
                        cfg_llm_base_url,
                        cfg_llm_api_key,
                        cfg_llm_temp,
                        cfg_llm_thinking,
                        cfg_llm_vision,
                        cfg_emb_provider,
                        cfg_emb_model,
                        cfg_emb_base_url,
                        cfg_emb_api_key,
                        cfg_tool_ask,
                        cfg_tool_fetch,
                        cfg_tool_python,
                        cfg_tool_sql,
                        cfg_tool_read,
                        cfg_tool_tavily,
                        cfg_tool_terminal,
                        cfg_sql_db_uri,
                        cfg_tavily_key,
                        cfg_mcps_json,
                    ],
                )
                config_save_btn.click(
                    _config_save_from_form,
                    inputs=[
                        cfg_platform,
                        cfg_base_dir,
                        cfg_rag_mode,
                        cfg_deepagent,
                        cfg_llm_provider,
                        cfg_llm_model,
                        cfg_llm_base_url,
                        cfg_llm_api_key,
                        cfg_llm_temp,
                        cfg_llm_thinking,
                        cfg_llm_vision,
                        cfg_emb_provider,
                        cfg_emb_model,
                        cfg_emb_base_url,
                        cfg_emb_api_key,
                        cfg_tool_ask,
                        cfg_tool_fetch,
                        cfg_tool_python,
                        cfg_tool_sql,
                        cfg_tool_read,
                        cfg_tool_tavily,
                        cfg_tool_terminal,
                        cfg_sql_db_uri,
                        cfg_tavily_key,
                        cfg_mcps_json,
                    ],
                    outputs=[config_status],
                )

            # ---- Sessions ----
            with gr.TabItem("📋 Sessions"):
                sessions_refresh = gr.Button("Refresh list")
                sessions_md = gr.Markdown("_Click Refresh to load._")
                with gr.Row():
                    session_del_id = gr.Textbox(label="Session ID to delete", placeholder="default")
                    session_del_btn = gr.Button("Delete", variant="stop")
                with gr.Row():
                    session_clear_id = gr.Textbox(label="Session ID to clear", placeholder="default")
                    session_clear_btn = gr.Button("Clear messages")
                session_status = gr.Markdown("")
                sessions_refresh.click(_sessions_list_ui, outputs=[sessions_md])
                session_del_btn.click(_session_delete_ui, inputs=[session_del_id], outputs=[session_status]).then(
                    _sessions_list_ui, outputs=[sessions_md]
                )
                session_clear_btn.click(_session_clear_ui, inputs=[session_clear_id], outputs=[session_status]).then(
                    _sessions_list_ui, outputs=[sessions_md]
                )

            # ---- Health ----
            with gr.TabItem("❤️ Health"):
                health_btn = gr.Button("Check gateway")
                health_md = gr.Markdown("_Click to check._")
                health_btn.click(_health_ui, outputs=[health_md])

            # ---- Files: workplace ----
            with gr.TabItem("📁 Workplace files"):
                gr.Markdown("Edit `workplace/*.md` files.")
                with gr.Row():
                    wp_file_dd = gr.Dropdown(
                        label="Select file",
                        choices=[],
                        allow_custom_value=False,
                    )
                    wp_refresh_btn = gr.Button("Refresh list")
                wp_editor = gr.Textbox(label="Content", lines=20)
                wp_save_btn = gr.Button("Save", variant="primary")
                wp_status = gr.Markdown("")

                wp_refresh_btn.click(_workplace_files_ui, outputs=[wp_file_dd])
                wp_file_dd.change(_workplace_load_ui, inputs=[wp_file_dd], outputs=[wp_editor])
                wp_save_btn.click(_workplace_save_ui, inputs=[wp_file_dd, wp_editor], outputs=[wp_status])
                demo.load(_workplace_files_ui, outputs=[wp_file_dd])

            # ---- Files: memory ----
            with gr.TabItem("🧠 Memory (MEMORY.md)"):
                gr.Markdown("Edit `memory/MEMORY.md` — long-term memory.")
                memory_editor = gr.Textbox(label="MEMORY.md", lines=20)
                with gr.Row():
                    memory_load_btn = gr.Button("Load")
                    memory_save_btn = gr.Button("Save", variant="primary")
                memory_status = gr.Markdown("")
                memory_load_btn.click(_memory_load_ui, outputs=[memory_editor])
                memory_save_btn.click(_memory_save_ui, inputs=[memory_editor], outputs=[memory_status])
                demo.load(_memory_load_ui, outputs=[memory_editor])

        gr.Markdown(f"_Gateway: {gateway_url}_")

        # JS hotkeys: Enter to send, Ctrl+Enter for newline in chat input
        demo.load(
            None,
            js="""
            () => {
                const inputRoot = document.querySelector('#chat-input textarea, #chat-input input');
                const sendBtn = document.querySelector('#send-btn');
                if (!inputRoot || !sendBtn) return;
                inputRoot.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
                        // Enter: send message
                        e.preventDefault();
                        sendBtn.click();
                    } else if (e.key === 'Enter' && e.ctrlKey) {
                        // Ctrl+Enter: insert newline
                        e.preventDefault();
                        const el = e.target;
                        const start = el.selectionStart ?? el.value.length;
                        const end = el.selectionEnd ?? el.value.length;
                        const value = el.value ?? "";
                        el.value = value.slice(0, start) + "\\n" + value.slice(end);
                        const pos = start + 1;
                        el.selectionStart = el.selectionEnd = pos;
                    }
                });
            }
            """,
        )

    return demo


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="microclaw gui", description="microclaw Gradio GUI")
    parser.add_argument(
        "--gateway",
        default=os.environ.get("MICROCLAW_GATEWAY", "http://127.0.0.1:8000"),
        help="Gateway base URL",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=7860,
        help="Gradio server port (default: 7860)",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create public share link",
    )
    args = parser.parse_args(argv)

    demo = _build_ui(args.gateway)
    demo.launch(
        server_name="127.0.0.1",
        server_port=args.port,
        share=args.share,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .chat-container {
            max-height: 70vh;
        }
        .session-sidebar {
            min-width: 220px;
        }
        .chat-main {
            min-width: 0;
        }
        .bottom-actions {
            display: flex;
            gap: 0.75rem;
            justify-content: flex-start;
        }
        .bottom-actions > button {
            flex: 0 0 auto;
        }
        .clean-note {
            font-size: 0.85rem;
            color: #666;
        }
        """,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
