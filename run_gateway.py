"""
Run the FastAPI gateway server.

Usage:
  python run_gateway.py

Env:
  GATEWAY_HOST (default: 127.0.0.1)
  GATEWAY_PORT (default: 8000)
"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    uvicorn.run("gateway:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

