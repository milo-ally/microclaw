import os
import re
from pathlib import Path
from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


class GrepInput(BaseModel):
    pattern: str = Field(description="Pattern to search")
    path: str = Field(
        description="Root directory or file to search. Relative paths are resolved against the workspace base_dir."
    )
    use_regex: Optional[bool] = Field(default=False, description="Set to True to use regex matching; False to use KMP exact string match.")

class GrepTool(BaseTool):
    name: str = "grep"
    description: str = (
        "Search text in files recursively. "
        "Use KMP for exact string match (safe for code), or regex for pattern matching. "
        "Like: grep -r pattern path"
    )
    args_schema: Type[BaseModel] = GrepInput
    root_dir: str | None = None

    def _kmp_build_lps(self, pattern):
        m = len(pattern)
        lps = [0] * m
        length = 0
        i = 1
        while i < m:
            if pattern[i] == pattern[length]:
                length += 1
                lps[i] = length
                i += 1
            else:
                if length != 0:
                    length = lps[length - 1]
                else:
                    lps[i] = 0
                    i += 1
        return lps

    def _kmp_search(self, text, pattern):
        if not pattern:
            return False
        n = len(text)
        m = len(pattern)
        if m > n:
            return False
        lps = self._kmp_build_lps(pattern)
        i = j = 0
        while i < n:
            if pattern[j] == text[i]:
                i += 1
                j += 1
            if j == m:
                return True
            elif i < n and pattern[j] != text[i]:
                if j != 0:
                    j = lps[j - 1]
                else:
                    i += 1
        return False

    def _regex_search(self, text, pattern):
        try:
            return re.search(pattern, text) is not None
        except re.error:
            return False

    def _resolve_path(self, path: str) -> str:
        p = Path(path)
        if p.is_absolute() or not self.root_dir:
            return str(p)
        root = Path(self.root_dir).resolve()
        return str((root / path).expanduser().resolve())

    def _run(self, pattern: str, path: str, use_regex: bool = False) -> str:
        matches = []
        max_results = 20

        try:
            search_root = self._resolve_path(path)
            for root, _, files in os.walk(search_root):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                    except:
                        continue

                    for idx, line in enumerate(lines):
                        matched = False
                        if use_regex:
                            matched = self._regex_search(line, pattern)
                        else:
                            matched = self._kmp_search(line, pattern)

                        if matched:
                            matches.append(f"{fpath}:{idx+1}: {line.strip()}")
                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break
                if len(matches) >= max_results:
                    break
        except Exception as e:
            return f"Error: {str(e)}"

        if not matches:
            return "No matches found"
        return "\n".join(matches)

    async def _arun(self, pattern: str, path: str, use_regex: bool = False) -> str:
        return self._run(pattern, path, use_regex)


def create_grep_tool(root_dir: str | None = None) -> GrepTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("grep_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return GrepTool(root_dir=root_dir)
    return None


if __name__ == "__main__":
    """
    Self-test for GrepTool using real project files.

    - Uses the `agent/` folder as search root (read-only).
    - Runs both exact (KMP) and regex search on realistic patterns.
    """
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    agent_dir = project_root / "agent"

    print(f"Project root: {project_root}")
    print(f"Agent dir:   {agent_dir}  (exists={agent_dir.exists()})")
    print(f"grep_tool status: {TOOL_STATUS}")

    tool = create_grep_tool()
    if tool is None:
        print("GrepTool is disabled in config.tools.grep_tool.status == 'off'.")
    else:
        if not agent_dir.exists():
            print("agent/ folder not found; cannot run real-file test.")
        else:
            # 1) Search for the word 'IDENTITY' in agent/ (should hit IDENTITY.md)
            print("\n[Exact search in agent/ for 'IDENTITY']")
            out1 = tool._run(pattern="我", path=str(agent_dir), use_regex=False)
            print(out1[:2000])

            # 2) Regex search for markdown headings
            # print("\n[Regex search in agent/ for '^# ']")
            # out2 = tool._run(pattern=r"^# ", path=str(agent_dir), use_regex=True)
            # print(out2[:2000])

