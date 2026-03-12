"""
Shared Gateway client for microclaw TUI/GUI.

This module was renamed from `microclaw.gateway_client` to `microclaw.client`.
The old module path has been removed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional, Tuple


@dataclass(frozen=True)
class GatewayClient:
    base_url: str
    timeout_s: float = 60.0

    def _url(self, path: str) -> str:
        return urllib.parse.urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def request_json(
        self,
        method: str,
        path: str,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        url = self._url(path)
        data = None
        req_headers = {"Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            data = raw
            req_headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, method=method.upper(), data=data, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                text = resp.read().decode(charset, errors="replace")
                if not text.strip():
                    return None
                return json.loads(text)
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(e)
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e}") from e

    def health(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/health")

    def get_config(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/config")

    def put_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        return self.request_json("PUT", "/api/config", body=patch)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self.request_json("GET", "/api/sessions")

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self.request_json("GET", f"/api/sessions/{urllib.parse.quote(session_id)}")

    def delete_session(self, session_id: str) -> dict[str, Any]:
        return self.request_json("DELETE", f"/api/sessions/{urllib.parse.quote(session_id)}")

    def clear_session(self, session_id: str) -> dict[str, Any]:
        return self.request_json("POST", f"/api/sessions/{urllib.parse.quote(session_id)}/clear")

    def cleanup_workspace(self) -> dict[str, Any]:
        return self.request_json("POST", "/api/cleanup", body={})

    def list_workplace_files(self) -> list[str]:
        return self.request_json("GET", "/api/files/workplace") or []

    def read_workplace_file(self, filename: str) -> str:
        r = self.request_json("GET", f"/api/files/workplace/{urllib.parse.quote(filename)}")
        return (r or {}).get("content", "")

    def write_workplace_file(self, filename: str, content: str) -> None:
        self.request_json(
            "PUT",
            f"/api/files/workplace/{urllib.parse.quote(filename)}",
            body={"content": content},
        )

    def read_memory(self) -> str:
        r = self.request_json("GET", "/api/files/memory")
        return (r or {}).get("content", "")

    def write_memory(self, content: str) -> None:
        self.request_json("PUT", "/api/files/memory", body={"content": content})

    def chat_stream_lines(self, payload: dict[str, Any]) -> Iterable[str]:
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
            resp = urllib.request.urlopen(req, timeout=self.timeout_s)  # noqa: S310
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(e)
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e}") from e

        with resp:
            for raw_line in resp:
                try:
                    line = raw_line.decode("utf-8", errors="replace")
                except Exception:
                    continue
                yield line.rstrip("\r\n")


def parse_sse_events(lines: Iterable[str]) -> Iterator[Tuple[str, str]]:
    event_name = "message"
    data_lines: list[str] = []
    for line in lines:
        if not line:
            if data_lines:
                yield (event_name, "\n".join(data_lines))
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())

