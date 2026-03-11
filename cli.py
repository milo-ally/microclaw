"""
microclaw - CLI entry point for ComputerUseAgent.

Usage:
  microclaw tui [--port PORT]
  microclaw gui [--port PORT] [--gui-port PORT]
  microclaw tui -- port 7132   # args after -- parsed as port

Examples:
  microclaw tui               # gateway on 8000, TUI connects to it
  microclaw tui --port 7132   # gateway on 7132, TUI connects to it
  microclaw gui -- port 7132  # gateway on 7132, GUI on 7860
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def _find_project_root() -> Path:
    """Find project root (directory containing gateway.py)."""
    root = Path(__file__).resolve().parent
    if (root / "gateway.py").exists():
        return root
    raise RuntimeError("Cannot find gateway.py in project root")


def _is_gateway_ready(url: str, timeout: float = 30.0) -> bool:
    """Poll until gateway /api/health responds."""
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


def _run_gateway(port: int) -> subprocess.Popen:
    """Start gateway in subprocess with given port."""
    root = _find_project_root()
    env = os.environ.copy()
    env["GATEWAY_HOST"] = "127.0.0.1"
    env["GATEWAY_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gateway:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def _run_gui(gateway_url: str, gui_port: int = 7860) -> int:
    """Run Gradio GUI, connecting to gateway. Returns exit code."""
    root = _find_project_root()
    gui_module = root / "gui.py"
    env = os.environ.copy()
    env["MICROCLAW_GATEWAY"] = gateway_url
    proc = subprocess.run(
        [sys.executable, str(gui_module), "--gateway", gateway_url, "--port", str(gui_port)],
        cwd=str(root),
        env=env,
    )
    return proc.returncode


def _run_tui(gateway_url: str) -> int:
    """Run TUI, connecting to gateway. Returns exit code."""
    root = _find_project_root()
    tui_module = root / "tui.py"
    env = os.environ.copy()
    env["MICROCLAW_GATEWAY"] = gateway_url
    proc = subprocess.run(
        [sys.executable, str(tui_module), "--gateway", gateway_url],
        cwd=str(root),
        env=env,
    )
    return proc.returncode


def _c(text: str, code: str) -> str:
    """Color helper for onboarding UI."""
    return f"\033[{code}m{text}\033[0m"


def _boot_sequence() -> None:
    """
    Lightweight "kernel boot" animation for TUI/GUI/Onboard entry.
    Gives a high-level OS bootloader feel without blocking too long.
    """
    steps = [
        "Bootloader: initializing microclaw runtime...",
        "Kernel: loading config.json and environment...",
        "Kernel: mounting agent workspace and skills...",
        "Kernel: wiring tools, memory, and sessions...",
        "I/O: preparing TUI/GUI interfaces...",
        "System: finalizing startup sequence...",
    ]
    if not sys.stdout.isatty():
        for s in steps:
            print(s)
        return

    for s in steps:
        print(_c("▌", "36;1"), s)
        time.sleep(0.12)
    print()


def _splash_ascii() -> None:
    """
    Render the same ASCII art banner as the TUI splash,
    so that `microclaw onboard` feels like a system bootloader.
    """
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

def _load_config_module():
    """
    Import the config module regardless of whether we are running
    from the editable source tree or from an installed console_script.
    """
    root = _find_project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import importlib

    return importlib.import_module("config")


def _validate_config(cfg) -> tuple[bool, list[str]]:
    """
    Lightweight validator for config.json completeness.

    We only check fields that are required for a healthy runtime:
    - base_dir
    - llm.info.{model, base_url, api_key}
    - embeddings.info.{model, base_url, api_key}
    - tools block exists with known tool entries; when a tool is enabled,
      required extra params must be present (e.g. sql_tools.db_uri, tavily_search_tool.tavily_api_key).
    """
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
    """
    Run step-by-step configuration wizard.

    Goals:
    - Create or update config.json
    - Ensure base_dir is set
    - Collect LLM and Embeddings provider info
    - Configure tool switches and required extra params
    """
    config_mod = _load_config_module()
    cfg = config_mod.load_config()

    def _prompt(text: str, default: str | None = None) -> str:
        """
        Prompt user with an optional default value.
        If the user presses enter with no input, the default is returned.
        """
        label = text
        if default:
            label += f" [default {default}]"
        val = input(f"{label}: ").strip()
        return val or (default or "")

    def _prompt_required(text: str, hint: str | None = None) -> str:
        """
        Prompt user for a non-empty value with an optional hint (example only).
        We intentionally do NOT provide true defaults; user must type explicitly.
        """
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

    # 1) base_dir
    base_dir = str(cfg.get("base_dir", "") or "").strip()
    if not base_dir:
        default_dir = (Path.cwd() / "agent").resolve()
        print(f"  (Suggested workspace path: {default_dir})")
        user_input = _prompt_required("  → Enter workspace directory path")
        target = Path(user_input).expanduser().resolve()
        config_mod.set_base_dir(str(target))
        print(f"  ✓ base_dir set to: {target}")
    else:
        print(f"  ✓ Using existing base_dir: {base_dir}")

    # 2) platform
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

    # 3) LLM config
    print()
    print(_c("Step 2: Chat model (LLM) configuration", "36;1"))
    llm_cfg = config_mod.get_llm_config() or {}
    llm_provider = str(llm_cfg.get("provider", "") or "")
    llm_info = llm_cfg.get("info") or {}
    llm_model = str(llm_info.get("model", "") or "")
    llm_base_url = str(llm_info.get("base_url", "") or "")
    llm_api_key = str(llm_info.get("api_key", "") or "")
    llm_temperature = llm_info.get("temperature", 0.2)
    llm_is_reasoning = bool(llm_info.get("is_reasoning_model", True))
    llm_is_vision = bool(llm_info.get("is_vision_model", False))

    llm_provider = _prompt_required("  → LLM provider", llm_provider or "deepseek")
    llm_model = _prompt_required("  → LLM model", llm_model or "deepseek-reasoner")
    llm_base_url = _prompt_required("  → LLM base_url", llm_base_url or "https://api.deepseek.com")
    llm_api_key = _prompt_required("  → LLM api_key (sk-...)")
    try:
        temp_in = input(f"  → LLM temperature (0.0-2.0, current {llm_temperature}): ").strip()
        llm_temperature = float(temp_in or llm_temperature)
    except Exception:
        pass
    is_reason_str = input(
        f"  → Is this a reasoning model? [y/n] (current {'y' if llm_is_reasoning else 'n'}): "
    ).strip().lower()
    llm_is_reasoning = is_reason_str in ("y", "yes", "1", "true")
    is_vision_str = input(
        f"  → Is this a vision model? [y/n] (current {'y' if llm_is_vision else 'n'}): "
    ).strip().lower()
    llm_is_vision = is_vision_str in ("y", "yes", "1", "true")

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
                "is_vision_model": llm_is_vision,
            },
        }
    )
    print("  ✓ LLM configuration saved.")

    # 4) Embeddings config
    print()
    print(_c("Step 3: Embeddings model configuration", "36;1"))
    emb_cfg = config_mod.get_embeddings_config() or {}
    emb_provider = str(emb_cfg.get("provider", "") or "")
    emb_info = emb_cfg.get("info") or {}
    emb_model = str(emb_info.get("model", "") or "")
    emb_base_url = str(emb_info.get("base_url", "") or "")
    emb_api_key = str(emb_info.get("api_key", "") or "")

    emb_provider = _prompt_required("  → Embeddings provider", emb_provider or "aliyun")
    emb_model = _prompt_required("  → Embeddings model", emb_model or "text-embedding-v3")
    emb_base_url = _prompt_required(
        "  → Embeddings base_url",
        emb_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    emb_api_key = _prompt_required("  → Embeddings api_key (sk-...)")

    config_mod.set_embeddings_config(
        {
            "provider": emb_provider,
            "format": "openai",
            "info": {
                "model": emb_model,
                "base_url": emb_base_url,
                "api_key": emb_api_key,
            },
        }
    )
    print("  ✓ Embeddings configuration saved.")

    # 5) Tools config
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

    # Core tools
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

    # SQL tools
    sql_enabled = _prompt_on_off("sql_tools", _tool_enabled("sql_tools", default=False))
    sql_uri_default = str((tools_cfg.get("sql_tools") or {}).get("db_uri", "") or "")
    sql_uri = sql_uri_default
    if sql_enabled:
        sql_uri = _prompt("  → SQL db_uri (when sql_tools enabled)", sql_uri_default)
    new_tools["sql_tools"] = {
        "status": "on" if sql_enabled else "off",
        "db_uri": sql_uri,
    }

    # Tavily search
    tavily_enabled = _prompt_on_off("tavily_search_tool", _tool_enabled("tavily_search_tool", default=False))
    tavily_key_default = str((tools_cfg.get("tavily_search_tool") or {}).get("tavily_api_key", "") or "")
    tavily_key = tavily_key_default
    if tavily_enabled:
        tavily_key = _prompt("  → Tavily API key (tvly-...)", tavily_key_default)
    new_tools["tavily_search_tool"] = {
        "status": "on" if tavily_enabled else "off",
        "tavily_api_key": tavily_key,
    }

    config_mod.set_managedb_config(new_tools)
    print("  ✓ Tool switches saved.")

    # Final validation summary
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


def _cmd_gui(args: argparse.Namespace) -> int:
    port = args.port
    gui_port = getattr(args, "gui_port", 7860)
    gateway_url = f"http://127.0.0.1:{port}"

    # Ensure config is present and reasonably complete before booting GUI.
    config_mod = _load_config_module()
    cfg = config_mod.load_config()
    ok, _ = _validate_config(cfg)
    if not ok:
        print(_c("Config is missing or incomplete. Redirecting to onboarding wizard...", "33;1"))
        # Reuse onboard flow (will let user choose TUI/GUI).
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

    # Ensure config is present and reasonably complete before booting TUI.
    config_mod = _load_config_module()
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
    """
    Interactive onboarding wizard:
    - Configure base_dir and show LLM settings
    - Start gateway and verify connectivity
    - Let user choose to launch TUI or GUI
    """
    port = args.port
    gui_port_default = 7860
    gateway_url = f"http://127.0.0.1:{port}"

    # Header with a bit of "OS bootloader" feel (reuse TUI ASCII art)
    _splash_ascii()
    _boot_sequence()

    # 1) Config wizard
    _onboard_config()

    print()
    print(_c("Step 3: Booting gateway kernel", "36;1"))
    print(f"  → Starting gateway on port {port} ...")
    proc = _run_gateway(port)
    try:
        if not _is_gateway_ready(gateway_url):
            print(_c(f"  ✗ Gateway failed to start on port {port}", "31;1"), file=sys.stderr)
            return 1
        print(_c("  ✓ Gateway online", "32;1"))
        print(f"    URL: {gateway_url}")

        # 2) Choose interface
        print()
        print(_c("Step 4: Choose interface to launch", "36;1"))
        print("  [1] TUI (terminal interface)")
        print("  [2] GUI (Gradio web UI)")
        print("  [3] Exit (do not launch UI)")
        choice = input("  → Select [1/2/3, default 1]: ").strip() or "1"

        if choice == "2":
            # Optional GUI port override
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
    """Parse 'port 7132' from extra args after --."""
    for i, tok in enumerate(extra):
        if tok.lower() == "port" and i + 1 < len(extra):
            try:
                return int(extra[i + 1])
            except ValueError:
                pass
    return None


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    # Handle "openclaw tui -- port 7132" style: split at -- and parse port from remainder
    if "--" in argv:
        idx = argv.index("--")
        before, after = argv[:idx], argv[idx + 1:]
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
