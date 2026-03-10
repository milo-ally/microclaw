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


def _onboard_config() -> None:
    """
    Run one-time (or repeatable) configuration wizard:
    - Ensure base_dir is set
    - Show current LLM model info for user awareness
    """
    config_mod = _load_config_module()
    cfg = config_mod.load_config()

    # 1) base_dir
    base_dir = str(cfg.get("base_dir", "") or "").strip()
    if not base_dir:
        print(_c("Step 1: Configure workspace base_dir", "36;1"))
        default_dir = (Path.cwd() / "agent").resolve()
        user_input = input(
            f"  → Enter workspace directory path "
            f"[default: {default_dir}]: "
        ).strip()
        target = Path(user_input or str(default_dir)).expanduser().resolve()
        config_mod.set_base_dir(str(target))
        print(f"  ✓ base_dir set to: {target}")
    else:
        print(_c("Step 1: Workspace base_dir", "36;1"))
        print(f"  ✓ Using existing base_dir: {base_dir}")

    # 2) LLM info (read-only for now, just surface to user)
    llm_cfg = config_mod.get_llm_config() or {}
    model_name = llm_cfg.get("model") or "<not set>"
    base_url = llm_cfg.get("base_url") or "<not set>"
    print()
    print(_c("Step 2: LLM configuration (from config.json)", "36;1"))
    print(f"  - model:    {model_name}")
    print(f"  - base_url: {base_url}")
    print("  (Edit config.json or use your own tooling if you need to change these.)")


def _cmd_gui(args: argparse.Namespace) -> int:
    port = args.port
    gui_port = getattr(args, "gui_port", 7860)
    gateway_url = f"http://127.0.0.1:{port}"

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
