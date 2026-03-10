import json 
import time 
from pathlib import Path 
from typing import Any, Optional 



class SessionManager: 
    """
    Manages conversation history as JSON files in sessions/ directory.
    
    Storage format: 
    {
        "title": "Session Title",
        "created_at": 1706000000, 
        "updated_at": 1706000100,
        "messages": [
            {"role": "user", "content": "..."},
            ...
        ]
    }
    """
    def __init__(self) -> None: 
        self._session_dir: Path | None = None 

    def initialize(self, base_dir: Path) -> None:
        self._session_dir = base_dir / "sessions" 
        self._session_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        assert self._session_dir is not None 
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return self._session_dir / f"{safe_id}.json" 

    def _read_file(self, session_id: str) -> dict[str, Any]:
        """Read session file and normalize to format"""
        path = self._session_path(session_id) 
        if not path.exists():
            return {} 
        try:
            data = json.loads(path.read_text(encoding="utf-8")) 
            if isinstance(data, list):
                now = time.time() 
                return {
                    "title": session_id, 
                    "created_at": path.stat().st_ctime, 
                    "updated_at": now, 
                    "messages": data, 
                }
            return data 
        except (json.JSONDecodeError, Exception):
            return {} 

    def _write_file(self, session_id: str, data: dict[str, Any]) -> None:
        """Write session data to file"""
        path = self._session_path(session_id)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_session(self, session_id: str) -> dict[str, Any]:
        """load session history messages from a session"""
        data = self._read_file(session_id)
        if not data: 
            return {} 
        return data.get("messages", []) 


    def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        tool_calls: list[dict[str, Any]] | None = None, 
    ) -> None:
        """save a message to a session"""
        data = self._read_file(session_id)
        if not data: 
            now = time.time() 
            data = {
                "title": "New Chat", 
                "created_at": now, 
                "updated_at": now, 
                "messages": [], 
            } 
        msg: dict[str, Any] = {"role": role, "content": content}
        if tool_calls: 
            msg["tool_calls"] = tool_calls # adding tool calls to the message
        data["messages"].append(msg)
        self._write_file(session_id, data)

    def rename_session(self, session_id: str, title: str) -> None:
        """rename a session"""
        data = self._read_file(session_id)
        if not data: 
            raise FileNotFoundError(f"Session {session_id} not found")
        data["title"] = title 
        self._write_file(session_id, data)

    def update_title(self, session_id: str, title: str) -> None:
        """Update the title of a session (alias for rename_session)"""
        self.rename_session(session_id, title)

    def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()

    def clear_messages(self, session_id: str) -> None:
        """Clear all messages in a session, keep the session file."""
        data = self._read_file(session_id)
        if not data:
            now = time.time()
            data = {
                "title": "New Chat",
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
        data["messages"] = []
        data["updated_at"] = time.time()
        self._write_file(session_id, data)

    def get_raw_messages(self, session_id: str) -> dict[str, Any]:
        """Get raw session data (title, messages, etc.)"""
        data = self._read_file(session_id)
        if not data:
            return {"title": "", "messages": []}
        return data 

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with metadata""" 
        assert self._session_dir is not None 
        sessions: list[dict[str, Any]] = []
        for f in sorted(self._session_dir.glob("*.json"), key=lambda p: p.stat().st_ctime, reverse=True):
            try: 
                raw = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(raw, dict): 
                    title = raw.get("title", f.stem)
                    updated_at = raw.get("updated_at", f.stat().st_ctime) 
                else:
                    title = f.stem
                    updated_at = f.stat().st_ctime 
            except Exception:
                title = f.stem 
                updated_at = f.stat().st_ctime 
            sessions.append({
                "id": f.stem, 
                "title": title, 
                "updated_at": updated_at
            })
        return sessions 

    def compress_history(self, session_id: str, summary: str, num_to_remove: int) -> None:
        """Archive first N messages and store summary as compressed context"""
        assert self._session_dir is not None 
        data = self._read_file(session_id) 
        if not data: 
            return 
        messages = data.get("messages", []) 
        archived_messages = messages[:num_to_remove]

        # archive messages
        archive_dir = self._session_dir / "archive"  
        archive_dir.mkdir(exist_ok=True)
        archive_data = {
            "session_id": session_id, 
            "archive_at": time.time(), 
            "messages": archived_messages
        }
        archive_path = archive_dir / f"{session_id}_{time.time()}.json"
        archive_path.write_text(
            json.dumps(archive_data, ensure_ascii=False), 
            encoding="utf-8"
        )

        # Remove archived messages from session
        data["messages"] = messages[num_to_remove:]
        
        # Append summary as compressed context 
        existing_context = data.get("compressed_context", "") 
        if existing_context:
            data["compressed_context"] = f"{existing_context}\n\n{summary}"
        else: 
            data["compressed_context"] = summary 
        self._write_file(session_id, data)

    def load_session_for_agent(self, session_id: str) -> dict[str, Any]:
        """ 
        Load session history messages for agent processing, 
        """
        data = self._read_file(session_id)
        messages = data.get("messages", []) if data else [] 

        merged: list[dict[str, Any]] = []  
        compressed = data.get("compressed_context", "") if data else ""  
        if compressed:
            merged.append({
                "role": "assistant", 
                "content": f"Here is the summary of the previous conversation:\n {compressed}"
            })
        for msg in messages: 
            if (
                merged
                and merged[-1]["role"] == "assistant"
                and msg["role"] == "assistant"
            ): 
                # Combine assistant messages
                merged[-1]["content"] = (merged[-1].get("content", "") or "") + "\n" + (msg.get("content") or "")
            else:
                merged.append({
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                })
        return merged 


    def get_session_count(self, session_id: str) -> int:
        """Return the number of messages in a session"""
        data = self._read_file(session_id) 
        if not data: 
            return 0 
        return len(data.get("messages", [])) 


session_manager = SessionManager()