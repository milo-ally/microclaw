"""
microclaw - a friendly TUI for the FastAPI gateway.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple, TypeVar

from microclaw.client import GatewayClient, parse_sse_events


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    if not _supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def title(text: str) -> None:
    line = "═" * max(28, len(text) + 6)
    print(_c(line, "36"))
    print(_c(f"  {text}", "36;1"))
    print(_c(line, "36"))


def section(text: str) -> None:
    print()
    print(_c(f"## {text}", "35;1"))


def info(msg: str) -> None:
    print(_c("INFO", "32;1") + f"  {msg}")


def warn(msg: str) -> None:
    print(_c("WARN", "33;1") + f"  {msg}")


def err(msg: str) -> None:
    print(_c("ERR ", "31;1") + f"  {msg}")


def prompt(text: str, default: Optional[str] = None) -> str:
    if default is not None and default != "":
        s = input(f"{text} [{default}]: ").strip()
        return s if s else str(default)
    return input(f"{text}: ").strip()


def prompt_bool(text: str, default: bool) -> bool:
    d = "y" if default else "n"
    while True:
        s = input(f"{text} [y/n] (default {d}): ").strip().lower()
        if not s:
            return default
        if s in ("y", "yes", "1", "true", "t"):
            return True
        if s in ("n", "no", "0", "false", "f"):
            return False
        warn("Please enter y or n.")


def prompt_choice(text: str, choices: list[str], default_idx: int = 0) -> str:
    assert choices
    for i, c in enumerate(choices, start=1):
        mark = "*" if i - 1 == default_idx else " "
        print(f"  {mark} {i}. {c}")
    while True:
        s = input(f"{text} (1-{len(choices)}) [default {default_idx+1}]: ").strip()
        if not s:
            return choices[default_idx]
        if s.isdigit():
            n = int(s)
            if 1 <= n <= len(choices):
                return choices[n - 1]
        warn("Invalid selection.")


def pause(msg: str = "Press Enter to continue") -> None:
    input(f"\n{msg}...")


def _chat_input() -> str:
    return input(_c("\nYou > ", "36;1")).rstrip("\n")


T = TypeVar("T")


@contextmanager
def spinner(label: str, *, enabled: Optional[bool] = None, interval_s: float = 0.08):
    if enabled is None:
        enabled = sys.stdout.isatty()
    if not enabled:
        print(f"{label} ...")
        yield
        return

    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    stop = threading.Event()

    def run() -> None:
        i = 0
        while not stop.is_set():
            frame = frames[i % len(frames)]
            i += 1
            sys.stdout.write("\r" + _c(frame, "36;1") + " " + label)
            sys.stdout.flush()
            time.sleep(interval_s)
        sys.stdout.write("\r" + (" " * (len(label) + 4)) + "\r")
        sys.stdout.flush()

    th = threading.Thread(target=run, daemon=True)
    th.start()
    try:
        yield
    finally:
        stop.set()
        th.join(timeout=1.0)


def splash() -> None:
    if not sys.stdout.isatty():
        return
    os.system("clear" if os.name != "nt" else "cls")
    print(_c("microclaw 2026.3 · gateway TUI", "31;1"))
    print(_c("You had me at 'microclaw gateway start.'", "90"))
    print()
    art = [
        "███╗   ███╗██╗ ██████╗██████╗  ██████╗  ██████╗██╗      █████╗ ██╗    ██╗",
        "████╗ ████║██║██╔════╝██╔══██╗██╔═══██╗██╔════╝██║     ██╔══██╗██║    ██║",
        "██╔████╔██║██║██║     ██████╔╝██║   ██║██║     ██║     ███████║██║ █╗ ██║",
        "██║╚██╔╝██║██║██║     ██╔══██╗██║   ██║██║     ██║     ██╔══██║██║███╗██║",
        "██║ ╚═╝ ██║██║╚██████╗██║  ██║╚██████╔╝╚██████╗███████╗██║  ██║╚███╔███╔╝",
        "╚═╝     ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ",
    ]
    print(_c("\n".join(art), "37;1"))
    print()
    print(_c("microclaw onboarding", "31;1"))
    print(_c("Security warning — please read.", "90"))
    print()
    print(
        _c(
            "microclaw is a local/hobby agent UI. If tools are enabled, it can read files and run actions.\n"
            "Do not expose it to untrusted users without proper access control.\n",
            "90",
        )
    )


def show_openai_compat_notice() -> None:
    section("Model access note (important)")
    print(
        "microclaw requires both **chat** and **embedding** providers to expose an "
        "**OpenAI-compatible API**.\n"
        "That means the config should look like:\n"
        '  - chat: {"format":"openai","info":{"model":...,"base_url":...,"api_key":...}}\n'
        '  - embeddings: {"format":"openai","info":{"model":...,"base_url":...,"api_key":...}}\n'
    )


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def flow_health(client: GatewayClient) -> None:
    title("microclaw · Gateway health")
    try:
        with spinner("Contacting gateway /api/health"):
            h = client.health()
        print(pretty_json(h))
    except Exception as e:
        err(str(e))
    pause()


def flow_config_view(client: GatewayClient) -> None:
    title("microclaw · Config (view)")
    show_openai_compat_notice()
    try:
        with spinner("Loading /api/config"):
            cfg = client.get_config()
        print(pretty_json(cfg))
    except Exception as e:
        err(str(e))
    pause()


def _edit_provider_block(kind: str, block: dict[str, Any]) -> dict[str, Any]:
    section(f"Edit {kind} provider")
    current_provider = str(block.get("provider", "") or "")
    provider = prompt(f"{kind}.provider", None if not current_provider else current_provider)
    fmt = prompt(f"{kind}.format (must be 'openai')", str(block.get("format", "openai") or "openai"))
    if fmt.strip().lower() != "openai":
        warn("This project expects OpenAI-compatible format. Setting format to 'openai'.")
        fmt = "openai"
    info_block = dict(block.get("info") or {})
    info_block["model"] = prompt(f"{kind}.info.model", str(info_block.get("model", "")))
    info_block["base_url"] = prompt(f"{kind}.info.base_url", str(info_block.get("base_url", "")))
    info_block["api_key"] = prompt(f"{kind}.info.api_key", str(info_block.get("api_key", "")))
    if kind == "llm":
        try:
            temp_default = info_block.get("temperature", 0.1)
            temp_str = prompt(f"{kind}.info.temperature", str(temp_default))
            info_block["temperature"] = float(temp_str)
        except Exception:
            warn("Invalid temperature; keeping previous value.")
        info_block["is_reasoning_model"] = prompt_bool(
            f"{kind}.info.is_reasoning_model", bool(info_block.get("is_reasoning_model", False))
        )
        info_block["is_vision_model"] = prompt_bool(
            f"{kind}.info.is_vision_model", bool(info_block.get("is_vision_model", False))
        )
    return {"provider": provider, "format": "openai", "info": info_block}


def flow_config_edit(client: GatewayClient) -> None:
    title("microclaw · Config (edit)")
    show_openai_compat_notice()
    try:
        with spinner("Loading /api/config"):
            cfg = client.get_config()
    except Exception as e:
        err(f"Failed to load config: {e}")
        pause()
        return

    while True:
        section("Config menu")
        choice = prompt_choice(
            "Select",
            [
                "Edit base info (platform/base_dir/rag_mode/deepagent)",
                "Edit chat model (llm)",
                "Edit embeddings model (embeddings)",
                "Edit tools switches",
                "Save to gateway",
                "Back",
            ],
        )

        if choice.startswith("Edit base info"):
            cfg["platform"] = prompt("platform", str(cfg.get("platform", "")))
            cfg["base_dir"] = prompt("base_dir (agent base dir)", str(cfg.get("base_dir", "")))
            cfg["rag_mode"] = prompt_bool("rag_mode", bool(cfg.get("rag_mode", False)))
            cfg["deepagent"] = prompt_bool("deepagent", bool(cfg.get("deepagent", False)))
        elif choice.startswith("Edit chat model"):
            cfg["llm"] = _edit_provider_block("llm", dict(cfg.get("llm") or {}))
        elif choice.startswith("Edit embeddings"):
            cfg["embeddings"] = _edit_provider_block("embeddings", dict(cfg.get("embeddings") or {}))
        elif choice.startswith("Edit tools"):
            tools = dict(cfg.get("tools") or {})
            section("Tools")
            if not tools:
                warn("No tools block found in config; creating one.")
            for name, entry in sorted(tools.items()):
                if not isinstance(entry, dict):
                    continue
                status = str(entry.get("status", "on"))
                enabled = status.lower() == "on"
                enabled = prompt_bool(f"{name}.status", enabled)
                entry["status"] = "on" if enabled else "off"
                tools[name] = entry
            cfg["tools"] = tools
        elif choice == "Save to gateway":
            print()
            print(_c("About to save config:", "36;1"))
            print(pretty_json(cfg))
            if not prompt_bool("Proceed", True):
                continue
            try:
                with spinner("Saving /api/config"):
                    saved = client.put_config(cfg)
                info("Saved successfully.")
                print(pretty_json(saved))
            except Exception as e:
                err(str(e))
            pause()
        else:
            return


def flow_sessions(client: GatewayClient) -> None:
    title("microclaw · Sessions")
    try:
        with spinner("Loading /api/sessions"):
            sessions = client.list_sessions()
    except Exception as e:
        err(str(e))
        pause()
        return

    if not sessions:
        info("No sessions found.")
        pause()
        return

    section("Recent sessions")
    for i, s in enumerate(sessions[:30], start=1):
        sid = s.get("id", "")
        stitle = s.get("title", "")
        ts = s.get("updated_at", 0)
        try:
            ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
        except Exception:
            ts_str = str(ts)
        print(f"  {i:>2}. {sid}  ·  {stitle}  ·  {ts_str}")

    section("Actions")
    action = prompt_choice("Select", ["View session", "Delete session", "Back"])
    if action == "Back":
        return

    sid = prompt("session id", sessions[0].get("id", "default"))
    if action == "View session":
        try:
            with spinner(f"Loading session '{sid}'"):
                raw = client.get_session(sid)
            print(pretty_json(raw))
        except Exception as e:
            err(str(e))
        pause()
        return
    if action == "Delete session":
        if not prompt_bool(f"Delete session '{sid}'", False):
            return
        try:
            with spinner(f"Deleting session '{sid}'"):
                out = client.delete_session(sid)
            print(pretty_json(out))
        except Exception as e:
            err(str(e))
        pause()


def _new_session_id() -> str:
    return f"session_{time.strftime('%Y%m%d_%H%M%S')}"


def flow_chat(client: GatewayClient) -> None:
    title("microclaw · Chat (streaming)")
    show_openai_compat_notice()

    boot_md = prompt_bool("boot? ", False)

    session_id = _new_session_id()
    info(f"New session: {session_id}")
    show_reasoning = prompt_bool("Show reasoning tokens (if reasoning model)", False)
    image_url = prompt("image_url (optional)", "")
    image_url = image_url.strip() or None

    print()
    info("Type your message. empty=back. Slash: /sessions /clear /session /health /config /delete /clean /menu /help")

    if boot_md:
        user_msg = "Wake up, my friend!"
        info(f"Auto message: {user_msg}")
        payload = {"session_id": session_id, "message": user_msg, "is_reasoning_model": False, "image_url": image_url}

        try:
            with spinner("Connecting SSE /api/chat/stream"):
                it = iter(client.chat_stream_lines(payload))
                first_line = next(it)

            lines = itertools.chain([first_line], it)
            for ev_name, data in parse_sse_events(lines):
                if ev_name == "end":
                    break
                if ev_name == "error":
                    try:
                        obj = json.loads(data)
                        err(obj.get("content") or data)
                    except Exception:
                        err(data)
                    break
                try:
                    obj = json.loads(data)
                except Exception:
                    continue

                et = obj.get("type")
                if et == "token":
                    chunk = obj.get("content") or ""
                    print(chunk, end="", flush=True)
                elif et == "reasoning_token":
                    if show_reasoning:
                        chunk = obj.get("content") or ""
                        print(_c(chunk, "90"), end="", flush=True)
                elif et == "retrieval":
                    section("RAG retrieval")
                    results = obj.get("results") or []
                    if not results:
                        print("(no results)")
                    else:
                        for i, r in enumerate(results[:5], start=1):
                            score = r.get("score", 0)
                            text = (r.get("text") or "").strip().replace("\n", " ")
                            print(f"- [{i}] score={score}  {text[:160]}")
                    print()
                elif et == "toolcall_message":
                    chunk = obj.get("content") or ""
                    print()
                    print(_c("[tool call]", "34;1") + " " + chunk, end="", flush=True)
                elif et == "tool_calling":
                    chunk = obj.get("content") or ""
                    print(_c(chunk, "34"), end="", flush=True)
                elif et == "tool_execute":
                    tname = obj.get("tool") or ""
                    tin = obj.get("input") or ""
                    print()
                    print(_c("[tool execute]", "34;1") + f" {tname}: {tin}")
                elif et == "tool_response":
                    tname = obj.get("tool") or ""
                    tout = obj.get("output") or ""
                    print()
                    print(_c("[tool response]", "32;1") + f" {tname}: {tout}")
                elif et == "tool_execute_done":
                    print()
                    print(_c("--- tool block done, agent continuing ---", "90"))
                elif et == "all_done":
                    print()
        except Exception as e:
            err(str(e))
        print()

    while True:
        user_msg = _chat_input()
        if not user_msg.strip():
            return

        if user_msg.strip().startswith("/"):
            cmd = user_msg.strip().split()[0].lower() if user_msg.strip() else ""
            if cmd == "/sessions":
                try:
                    with spinner("Loading sessions"):
                        sessions = client.list_sessions()
                    section("Sessions")
                    if not sessions:
                        print("(no sessions)")
                    else:
                        for i, s in enumerate(sessions[:20], start=1):
                            sid = s.get("id", "")
                            stitle = s.get("title", "")
                            ts = s.get("updated_at", 0)
                            try:
                                ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
                            except Exception:
                                ts_str = str(ts)
                            print(f"  {i:>2}. {sid}  ·  {stitle}  ·  {ts_str}")
                except Exception as e:
                    err(str(e))
                continue
            if cmd == "/clear":
                try:
                    with spinner(f"Clearing session '{session_id}'"):
                        client.clear_session(session_id)
                    info(f"Session '{session_id}' cleared.")
                except Exception as e:
                    err(str(e))
                continue
            if cmd == "/session":
                parts = user_msg.strip().split(maxsplit=1)
                new_id = parts[1].strip() if len(parts) > 1 else prompt("session_id", session_id)
                if new_id:
                    session_id = new_id
                    info(f"Switched to session '{session_id}'")
                    try:
                        with spinner(f"Loading session '{session_id}'"):
                            raw = client.get_session(session_id)
                        msgs = raw.get("messages", [])
                        if msgs:
                            section("Recent context")
                            for m in msgs[-6:]:
                                role = m.get("role", "")
                                content = (m.get("content", "") or "").strip()
                                if len(content) > 200:
                                    content = content[:197] + "..."
                                if role == "user":
                                    print(_c("You:", "36") + f" {content}")
                                else:
                                    print(_c("Assistant:", "32") + f" {content}")
                        else:
                            info("(empty session)")
                    except Exception as e:
                        warn(f"Could not load history: {e}")
                continue
            if cmd == "/health":
                try:
                    with spinner("Checking gateway"):
                        h = client.health()
                    section("Gateway health")
                    print(pretty_json(h))
                except Exception as e:
                    err(str(e))
                continue
            if cmd == "/config":
                try:
                    with spinner("Loading config"):
                        cfg = client.get_config()
                    section("Config (brief)")
                    for k in ("platform", "base_dir", "rag_mode", "llm", "embeddings"):
                        if k in cfg:
                            v = cfg[k]
                            s = json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else str(v)
                            if len(s) > 100:
                                s = s[:97] + "..."
                            print(f"  {k}: {s}")
                except Exception as e:
                    err(str(e))
                continue
            if cmd == "/delete":
                parts = user_msg.strip().split(maxsplit=1)
                sid_del = parts[1].strip() if len(parts) > 1 else prompt("session_id to delete", "")
                if sid_del:
                    try:
                        with spinner(f"Deleting '{sid_del}'"):
                            client.delete_session(sid_del)
                        info(f"Session '{sid_del}' deleted.")
                    except Exception as e:
                        err(str(e))
                continue
            if cmd == "/clean":
                if not prompt_bool("Clean workspace? Remove all except memory/sessions/skills/storage/workplace", False):
                    continue
                try:
                    with spinner("Cleaning workspace"):
                        out = client.cleanup_workspace()
                    removed = out.get("removed", [])
                    if removed:
                        info(f"Removed: {', '.join(removed)}")
                    else:
                        info("Nothing to remove (workspace already clean).")
                except Exception as e:
                    err(str(e))
                continue
            if cmd == "/menu":
                info("Back to main menu.")
                return
            if cmd == "/help":
                print()
                print(_c("Slash commands:", "35;1"))
                print("  /sessions        List recent sessions")
                print("  /clear           Clear messages in current session")
                print("  /session [id]    Switch session")
                print("  /health          Gateway health check")
                print("  /config          Show brief config")
                print("  /delete [id]     Delete a session")
                print("  /clean           Clean workspace (keep memory/sessions/skills/storage/workplace)")
                print("  /menu            Back to main menu")
                print("  /help            Show this help")
                print()
                continue
            warn(f"Unknown slash command: {cmd}. Use /help for available commands.")
            continue

        payload = {"session_id": session_id, "message": user_msg, "is_reasoning_model": False, "image_url": image_url}

        try:
            with spinner("Connecting SSE /api/chat/stream"):
                it = iter(client.chat_stream_lines(payload))
                first_line = next(it)

            lines = itertools.chain([first_line], it)
            for ev_name, data in parse_sse_events(lines):
                if ev_name == "end":
                    break
                if ev_name == "error":
                    try:
                        obj = json.loads(data)
                        err(obj.get("content") or data)
                    except Exception:
                        err(data)
                    break
                try:
                    obj = json.loads(data)
                except Exception:
                    continue

                et = obj.get("type")
                if et == "token":
                    chunk = obj.get("content") or ""
                    print(chunk, end="", flush=True)
                elif et == "reasoning_token":
                    if show_reasoning:
                        chunk = obj.get("content") or ""
                        print(_c(chunk, "90"), end="", flush=True)
                elif et == "retrieval":
                    section("RAG retrieval")
                    results = obj.get("results") or []
                    if not results:
                        print("(no results)")
                    else:
                        for i, r in enumerate(results[:5], start=1):
                            score = r.get("score", 0)
                            text = (r.get("text") or "").strip().replace("\n", " ")
                            print(f"- [{i}] score={score}  {text[:160]}")
                    print()
                elif et == "toolcall_message":
                    chunk = obj.get("content") or ""
                    print()
                    print(_c("[tool call]", "34;1") + " " + chunk, end="", flush=True)
                elif et == "tool_calling":
                    chunk = obj.get("content") or ""
                    print(_c(chunk, "34"), end="", flush=True)
                elif et == "tool_execute":
                    tname = obj.get("tool") or ""
                    tin = obj.get("input") or ""
                    print()
                    print(_c("[tool execute]", "34;1") + f" {tname}: {tin}")
                elif et == "tool_response":
                    tname = obj.get("tool") or ""
                    tout = obj.get("output") or ""
                    print()
                    print(_c("[tool response]", "32;1") + f" {tname}: {tout}")
                elif et == "tool_execute_done":
                    print()
                    print(_c("--- tool block done, agent continuing ---", "90"))
                elif et == "all_done":
                    print()
        except Exception as e:
            err(str(e))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="microclaw", description="microclaw TUI for ComputerUseAgent gateway")
    parser.add_argument(
        "--gateway",
        default=os.environ.get("MICROCLAW_GATEWAY", "http://127.0.0.1:8000"),
        help="Gateway base URL (env: MICROCLAW_GATEWAY). Default: http://127.0.0.1:8000",
    )
    args = parser.parse_args(argv)

    client = GatewayClient(base_url=args.gateway)
    splash()
    with spinner("Checking gateway availability"):
        ok = True
        try:
            client.health()
        except Exception as e:
            ok = False
            warn(f"Gateway not reachable: {e}")
    if not ok:
        print()
        print("Start the gateway first:")
        print("  python -m uvicorn microclaw.gateway:app --host 127.0.0.1 --port 8000")
        print()
        pause("Press Enter to open menu anyway")

    while True:
        title("microclaw")
        print(f"Gateway: {client.base_url}")
        section("Menu")
        choice = prompt_choice(
            "Select",
            ["Health", "Config (view)", "Config (edit & save)", "Sessions", "Chat (SSE streaming)", "Exit"],
        )
        if choice == "Health":
            flow_health(client)
        elif choice == "Config (view)":
            flow_config_view(client)
        elif choice == "Config (edit & save)":
            flow_config_edit(client)
        elif choice == "Sessions":
            flow_sessions(client)
        elif choice == "Chat (SSE streaming)":
            flow_chat(client)
        else:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

