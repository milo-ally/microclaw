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


def _cmd_gui(args: argparse.Namespace) -> int:
    port = args.port
    gui_port = getattr(args, "gui_port", 7860)
    gateway_url = f"http://127.0.0.1:{port}"

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
