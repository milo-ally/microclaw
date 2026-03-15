"""
microclaw - CLI entry point for ComputerUseAgent.
"""

from __future__ import annotations

import argparse
import json
import os
import webbrowser
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _find_project_root() -> Path:
    """
    Best-effort repo root discovery.

    We prefer walking upwards from the current working directory so that
    console_script works even when invoked from subdirectories.
    """
    start = Path.cwd().resolve()
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists() and (p / "config.json").exists():
            return p
        if (p / "pyproject.toml").exists() and (p / "agent").exists():
            return p
    # fallback: directory of this file (editable installs)
    return Path(__file__).resolve().parents[1]


def _is_gateway_ready(url: str, timeout: float = 30.0) -> bool:
    try:
        import urllib.request

        req = urllib.request.Request(f"{url.rstrip('/')}/api/health")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                time.sleep(0.3)
        return False
    except Exception:
        return False


def _preferred_python_executable(root: Path) -> str:
    """
    Prefer project venv Python when available.

    Some environments may invoke the `microclaw` console script from a different
    interpreter than the project's `.venv`. Starting uvicorn with the wrong
    interpreter can miss dependencies (e.g. langchain), causing gateway startup
    failures during onboarding.
    """
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        cand = Path(venv) / "bin" / "python"
        if cand.exists():
            return str(cand)

    cand = root / ".venv" / "bin" / "python"
    if cand.exists():
        return str(cand)

    return sys.executable


def _run_gateway(port: int) -> subprocess.Popen:
    root = _find_project_root()
    py = _preferred_python_executable(root)
    env = os.environ.copy()
    env["GATEWAY_HOST"] = "127.0.0.1"
    env["GATEWAY_PORT"] = str(port)
    proc = subprocess.Popen(
        [py, "-m", "uvicorn", "microclaw.gateway:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def _run_gui(gateway_url: str, gui_port: int = 7860) -> int:
    root = _find_project_root()
    py = _preferred_python_executable(root)
    env = os.environ.copy()
    env["MICROCLAW_GATEWAY"] = gateway_url
    proc = subprocess.run(
        [py, "-m", "microclaw.gui", "--gateway", gateway_url, "--port", str(gui_port)],
        cwd=str(root),
        env=env,
    )
    return proc.returncode


def _run_tui(gateway_url: str) -> int:
    root = _find_project_root()
    py = _preferred_python_executable(root)
    env = os.environ.copy()
    env["MICROCLAW_GATEWAY"] = gateway_url
    proc = subprocess.run(
        [py, "-m", "microclaw.tui", "--gateway", gateway_url],
        cwd=str(root),
        env=env,
    )
    return proc.returncode


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _boot_sequence() -> None:
    """
    Previously printed a boot animation banner.
    Now intentionally a no-op to keep startup output minimal.
    """
    return


def _splash_ascii() -> None:
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


def _validate_config(cfg) -> tuple[bool, list[str]]:
    errors: list[str] = []

    base_dir = str(cfg.get("base_dir", "") or "").strip()
    if not base_dir:
        errors.append("base_dir is not configured.")

    llm = cfg.get("llm") or {}
    llm_info = llm.get("info") or {}
    if not str(llm_info.get("model", "")).strip():
        errors.append("llm.info.model is not set.")
    if not str(llm_info.get("base_url", "")).strip():
        errors.append("llm.info.base_url is not set.")
    if not str(llm_info.get("api_key", "")).strip():
        errors.append("llm.info.api_key is not set.")

    emb = cfg.get("embeddings") or {}
    emb_info = emb.get("info") or {}
    if not str(emb_info.get("model", "")).strip():
        errors.append("embeddings.info.model is not set.")
    if not str(emb_info.get("base_url", "")).strip():
        errors.append("embeddings.info.base_url is not set.")
    if not str(emb_info.get("api_key", "")).strip():
        errors.append("embeddings.info.api_key is not set.")

    tools = cfg.get("tools") or {}
    required_tools = [
        "ask_user_question_tool",
        "fetch_url_tool",
        "python_repl_tool",
        "sql_tools",
        "read_file_tool",
        "tavily_search_tool",
        "terminal_tool",
        "rm_tool",
        "sed_all_tool",
        "sed_first_tool",
        "write_tool",
        "grep_tool",
    ]
    for name in required_tools:
        entry = tools.get(name)
        if not isinstance(entry, dict):
            errors.append(f"tools.{name} block is missing.")
            continue
        status = str(entry.get("status", "")).lower()
        if status not in ("on", "off"):
            errors.append(f"tools.{name}.status must be 'on' or 'off'.")
        if name == "sql_tools" and status == "on":
            if not str(entry.get("db_uri", "")).strip():
                errors.append("tools.sql_tools.db_uri is required when sql_tools is on.")
        if name == "tavily_search_tool" and status == "on":
            if not str(entry.get("tavily_api_key", "")).strip():
                errors.append("tools.tavily_search_tool.tavily_api_key is required when tavily_search_tool is on.")

    return (len(errors) == 0, errors)


def _onboard_config() -> None:
    from microclaw import config as config_mod

    cfg = config_mod.load_config()

    def _prompt(text: str, default: str | None = None) -> str:
        label = text
        if default:
            label += f" [default {default}]"
        val = input(f"{label}: ").strip()
        return val or (default or "")

    def _prompt_required(text: str, hint: str | None = None) -> str:
        label = text
        if hint:
            label += f" (e.g. {hint})"
        while True:
            val = input(f"{label}: ").strip()
            if val:
                return val
            print("  Please enter a value; empty is not allowed.")

    print()
    print(_c("Step 1: Workspace settings", "36;1"))

    base_dir = str(cfg.get("base_dir", "") or "").strip()
    if not base_dir:
        from microclaw.config import DEFAULT_WORKSPACE_DIR

        default_dir = DEFAULT_WORKSPACE_DIR.resolve()
        print(f"  (Default workspace path: {default_dir})")
        user_input = _prompt("  → Enter workspace directory path", str(default_dir))
        target = Path(user_input).expanduser().resolve()
        config_mod.set_base_dir(str(target))
        print(f"  ✓ base_dir set to: {target}")
    else:
        print(f"  ✓ Using existing base_dir: {base_dir}")

    platform_val = str(cfg.get("platform", "") or "").strip()
    if not platform_val:
        import platform as _plat

        suggested = _plat.system() or "Ubuntu24.04"
        print(f"  (Detected platform: {suggested})")
        platform_val = _prompt_required("  → Platform name (for tools / terminal)", suggested)
        config_mod.set_platform(platform_val)
        print(f"  ✓ platform set to: {platform_val}")
    else:
        print(f"  ✓ Using existing platform: {platform_val}")

    print()
    print(_c("Step 2: Chat model (LLM) configuration", "36;1"))
    llm_cfg = config_mod.get_llm_config() or {}
    llm_info = llm_cfg.get("info") or {}
    llm_temperature = llm_info.get("temperature", 0.2)
    llm_is_reasoning = bool(llm_info.get("is_reasoning_model", True))

    print("  Choose a supported chat model (enter number 1-5):")
    print("    1) deepseek-chat        · fast chat")
    print("    2) deepseek-reasoner    · reasoning model")
    print("    3) MiniMax-M2.5         · reasoning model (MiniMax)")
    print("    4) glm-5 (chat)         · GLM chat")
    print("    5) glm-5 (reasoning)    · GLM reasoning")

    def _pick_model() -> tuple[str, str, str, bool]:
        while True:
            choice = input("  → Select [1-5, default 2]: ").strip() or "2"
            if choice not in {"1", "2", "3", "4", "5"}:
                print("  Please enter a number between 1 and 5.")
                continue
            if choice == "1":
                return "deepseek", "deepseek-chat", "https://api.deepseek.com", False
            if choice == "2":
                return "deepseek", "deepseek-reasoner", "https://api.deepseek.com", True
            if choice == "3":
                return "minimax", "MiniMax-M2.5", "https://api.minimax.chat/v1", True
            if choice == "4":
                return "glm", "glm-5", "https://open.bigmodel.cn/api/paas/v4", False
            if choice == "5":
                return "glm", "glm-5", "https://open.bigmodel.cn/api/paas/v4", True

    llm_provider, llm_model, llm_base_url, llm_is_reasoning = _pick_model()
    print(f"  ✓ Using model: {llm_model}  (provider={llm_provider}, base_url={llm_base_url})")

    # Friendly shortcut: open provider console for API key.
    try:
        if llm_provider == "deepseek":
            print("  → Opening DeepSeek console in your browser (https://platform.deepseek.com) ...")
            webbrowser.open("https://platform.deepseek.com", new=2, autoraise=True)
        elif llm_provider == "minimax":
            print(
                "  → Opening MiniMax key management page "
                "(https://platform.minimaxi.com/user-center/basic-information/interface-key) ..."
            )
            webbrowser.open(
                "https://platform.minimaxi.com/user-center/basic-information/interface-key",
                new=2,
                autoraise=True,
            )
        elif llm_provider == "glm":
            print(
                "  → Opening Zhipu GLM API key page "
                "(https://bigmodel.cn/usercenter/proj-mgmt/apikeys) ..."
            )
            webbrowser.open("https://bigmodel.cn/usercenter/proj-mgmt/apikeys", new=2, autoraise=True)
    except Exception:
        # Best-effort only; failure to open browser should not break onboarding.
        pass

    llm_api_key = _prompt_required("  → LLM api_key")
    try:
        temp_in = input(f"  → LLM temperature (0.0-2.0, current {llm_temperature}): ").strip()
        llm_temperature = float(temp_in or llm_temperature)
    except Exception:
        pass
    # llm_is_reasoning is implied by the menu choice above
    config_mod.set_llm_config(
        {
            "provider": llm_provider,
            "format": "openai",
            "info": {
                "model": llm_model,
                "base_url": llm_base_url,
                "api_key": llm_api_key,
                "temperature": llm_temperature,
                "is_reasoning_model": llm_is_reasoning,
            },
        }
    )
    print("  ✓ LLM configuration saved.")

    print()
    print(_c("Step 3: Embeddings model configuration", "36;1"))
    emb_cfg = config_mod.get_embeddings_config() or {}
    emb_provider = str(emb_cfg.get("provider", "") or "")
    emb_info = emb_cfg.get("info") or {}
    emb_model = str(emb_info.get("model", "") or "")
    emb_base_url = str(emb_info.get("base_url", "") or "")

    emb_provider = _prompt_required("  → Embeddings provider", emb_provider or "aliyun")
    emb_model = _prompt_required("  → Embeddings model", emb_model or "text-embedding-v3")
    emb_base_url = _prompt_required(
        "  → Embeddings base_url",
        emb_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    emb_api_key = _prompt_required("  → Embeddings api_key")

    config_mod.set_embeddings_config(
        {
            "provider": emb_provider,
            "format": "openai",
            "info": {"model": emb_model, "base_url": emb_base_url, "api_key": emb_api_key},
        }
    )
    print("  ✓ Embeddings configuration saved.")

    print()
    print(_c("Step 4: Tool switches", "36;1"))
    tools_cfg = config_mod.get_tools_config() or {}

    def _tool_enabled(name: str, default: bool = True) -> bool:
        entry = tools_cfg.get(name) or {}
        status = str(entry.get("status", "on" if default else "off")).lower()
        return status == "on"

    def _prompt_on_off(label: str, enabled: bool) -> bool:
        d = "on" if enabled else "off"
        s = _prompt(f"  → Enable {label}? [on/off]", d).strip().lower()
        if s not in ("on", "off"):
            return enabled
        return s == "on"

    new_tools: dict[str, dict[str, str]] = {}
    for name in [
        "ask_user_question_tool",
        "fetch_url_tool",
        "python_repl_tool",
        "read_file_tool",
        "terminal_tool",
        "rm_tool",
        "sed_all_tool",
        "sed_first_tool",
        "write_tool",
        "grep_tool",
    ]:
        current = _tool_enabled(name, default=True)
        enabled = _prompt_on_off(name, current)
        new_tools[name] = {"status": "on" if enabled else "off"}

    sql_enabled = _prompt_on_off("sql_tools", _tool_enabled("sql_tools", default=False))
    sql_uri_default = str((tools_cfg.get("sql_tools") or {}).get("db_uri", "") or "")
    sql_uri = sql_uri_default
    if sql_enabled:
        sql_uri = _prompt("  → SQL db_uri (when sql_tools enabled)", sql_uri_default)
    new_tools["sql_tools"] = {"status": "on" if sql_enabled else "off", "db_uri": sql_uri}

    tavily_enabled = _prompt_on_off("tavily_search_tool", _tool_enabled("tavily_search_tool", default=False))
    tavily_key_default = str((tools_cfg.get("tavily_search_tool") or {}).get("tavily_api_key", "") or "")
    tavily_key = tavily_key_default
    if tavily_enabled:
        tavily_key = _prompt("  → Tavily API key (tvly-...)", tavily_key_default)
    new_tools["tavily_search_tool"] = {"status": "on" if tavily_enabled else "off", "tavily_api_key": tavily_key}

    vision_enabled = _prompt_on_off("vision_tool", _tool_enabled("vision_tool", default=False))
    vision_cfg = tools_cfg.get("vision_tool") or {}
    vision_base_url = str(vision_cfg.get("base_url", "") or "")
    vision_api_key = str(vision_cfg.get("api_key", "") or "")
    vision_model = str(vision_cfg.get("model", "") or "")
    if vision_enabled:
        vision_base_url = _prompt("  → Vision API base_url", vision_base_url)
        vision_api_key = _prompt("  → Vision API key", vision_api_key)
        vision_model = _prompt("  → Vision model", vision_model)
    new_tools["vision_tool"] = {
        "status": "on" if vision_enabled else "off",
        "base_url": vision_base_url,
        "api_key": vision_api_key,
        "model": vision_model,
    }

    config_mod.set_managedb_config(new_tools)
    print("  ✓ Tool switches saved.")

    print()
    cfg_after = config_mod.load_config()
    ok, errors = _validate_config(cfg_after)
    if ok:
        print(_c("Config looks complete. You are ready to launch microclaw.", "32;1"))
    else:
        print(_c("Config still has some issues:", "33;1"))
        for msg in errors:
            print(f"  - {msg}")
        print("You can re-run `microclaw onboard` later to fix these.")

    # Best-effort: initialize workspace directory structure from template agent/
    # So that base_dir is ready immediately after onboarding.
    try:
        base_dir_val = str(cfg_after.get("base_dir", "") or "").strip()
        if base_dir_val:
            template = Path(config_mod.CONFIG_FILE).parent / "agent"
            target = Path(base_dir_val).expanduser().resolve()
            if template.exists():
                print()
                print(_c("Step 5: Initializing workspace directory", "36;1"))
                print(f"  Template: {template}")
                print(f"  Target  : {target}")
                created_files = 0
                created_dirs = 0
                for src in template.rglob("*"):
                    rel = src.relative_to(template)
                    dst = target / rel
                    if src.is_dir():
                        if not dst.exists():
                            created_dirs += 1
                        dst.mkdir(parents=True, exist_ok=True)
                    else:
                        if not dst.exists():
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dst)
                            created_files += 1
                print(f"  ✓ Workspace initialized (new dirs: {created_dirs}, new files: {created_files})")
            else:
                print(_c("Warning: agent/ template directory not found; workspace was not initialized.", "33;1"))
    except Exception:
        # Do not block onboarding if workspace initialization fails.
        pass


def _cmd_gui(args: argparse.Namespace) -> int:
    port = args.port
    gui_port = getattr(args, "gui_port", 7860)
    gateway_url = f"http://127.0.0.1:{port}"

    from microclaw import config as config_mod

    cfg = config_mod.load_config()
    ok, _ = _validate_config(cfg)
    if not ok:
        print(_c("Config is missing or incomplete. Redirecting to onboarding wizard...", "33;1"))
        return _cmd_onboard(args)

    _boot_sequence()
    print(f"Starting gateway on port {port}...")
    proc = _run_gateway(port)
    try:
        if not _is_gateway_ready(gateway_url):
            print(f"Gateway failed to start on port {port}", file=sys.stderr)
            return 1
        print(f"Gateway ready at {gateway_url}")
        print(f"Starting GUI on http://127.0.0.1:{gui_port}")
        return _run_gui(gateway_url, gui_port)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def _cmd_tui(args: argparse.Namespace) -> int:
    port = args.port
    gateway_url = f"http://127.0.0.1:{port}"

    from microclaw import config as config_mod

    cfg = config_mod.load_config()
    ok, _ = _validate_config(cfg)
    if not ok:
        print(_c("Config is missing or incomplete. Redirecting to onboarding wizard...", "33;1"))
        return _cmd_onboard(args)

    _boot_sequence()
    print(f"Starting gateway on port {port}...")
    proc = _run_gateway(port)
    try:
        if not _is_gateway_ready(gateway_url):
            print(f"Gateway failed to start on port {port}", file=sys.stderr)
            return 1
        print(f"Gateway ready at {gateway_url}")
        return _run_tui(gateway_url)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def _cmd_onboard(args: argparse.Namespace) -> int:
    port = args.port
    gui_port_default = 7860
    gateway_url = f"http://127.0.0.1:{port}"

    _splash_ascii()
    _boot_sequence()
    _onboard_config()

    print()
    print(_c("Step 6: Booting gateway kernel", "36;1"))
    print(f"  → Starting gateway on port {port} ...")
    proc = _run_gateway(port)
    try:
        if not _is_gateway_ready(gateway_url):
            print(_c(f"  ✗ Gateway failed to start on port {port}", "31;1"), file=sys.stderr)
            return 1
        print(_c("  ✓ Gateway online", "32;1"))
        print(f"    URL: {gateway_url}")

        print()
        print(_c("Step 7: Choose interface to launch", "36;1"))
        print("  [1] TUI (terminal interface)")
        print("  [2] GUI (Gradio web UI)")
        print("  [3] Exit (do not launch UI)")
        choice = input("  → Select [1/2/3, default 1]: ").strip() or "1"

        if choice == "2":
            gui_port_in = input(f"  → GUI port [default {gui_port_default}]: ").strip()
            try:
                gui_port = int(gui_port_in) if gui_port_in else gui_port_default
            except ValueError:
                gui_port = gui_port_default
            print()
            print(_c(f"Launching GUI on http://127.0.0.1:{gui_port}", "32;1"))
            return _run_gui(gateway_url, gui_port)

        if choice == "1":
            print()
            print(_c("Launching TUI (connects to running gateway)...", "32;1"))
            return _run_tui(gateway_url)

        print()
        print(_c("Onboarding complete. No UI launched.", "33;1"))
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass


def _parse_extra_port(extra: list[str]) -> int | None:
    for i, tok in enumerate(extra):
        if tok.lower() == "port" and i + 1 < len(extra):
            try:
                return int(extra[i + 1])
            except ValueError:
                pass
    return None


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if "--" in argv:
        idx = argv.index("--")
        before, after = argv[:idx], argv[idx + 1 :]
        extra_port = _parse_extra_port(after)
        if extra_port is not None:
            argv = before + ["--port", str(extra_port)]

    parser = argparse.ArgumentParser(prog="microclaw", description="ComputerUseAgent CLI")
    subparser = parser.add_subparsers(dest="command", required=True)

    tui_parser = subparser.add_parser("tui", help="Start gateway + TUI")
    tui_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", "8000")),
        help="Gateway port (default: 8000 or GATEWAY_PORT)",
    )
    tui_parser.set_defaults(func=_cmd_tui)

    onboard_parser = subparser.add_parser(
        "onboard",
        help="Run first-time setup wizard (configure base_dir, test gateway, then launch TUI/GUI)",
    )
    onboard_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", "8000")),
        help="Gateway port used during onboarding (default: 8000 or GATEWAY_PORT)",
    )
    onboard_parser.set_defaults(func=_cmd_onboard)

    gui_parser = subparser.add_parser("gui", help="Start gateway + Gradio GUI")
    gui_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", "8000")),
        help="Gateway port (default: 8000 or GATEWAY_PORT)",
    )
    gui_parser.add_argument(
        "--gui-port",
        type=int,
        default=7860,
        help="Gradio GUI port (default: 7860)",
    )
    gui_parser.set_defaults(func=_cmd_gui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

