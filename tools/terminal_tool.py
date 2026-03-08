import subprocess
from pathlib import Path
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

PLATFORM = config.get_platform()

BLACKLISTED_COMMANDS_FOR_LINUX = [
    "rm -rf /", 
    "rm -rf ~", 
    "rm -rf *", 
    "mkfs", 
    "dd if=",
    "chmod 777", 
    ":(){ :|:& };:" 
]
BLACKLISTED_COMMANDS_FOR_WINDOWSPOWERSHELL = [
    "Format-Volume", 
    "Remove-Item -Recurse -Force", 
    "del /f /s /q"
]

def _get_blacklist() -> list[str]:
    p = PLATFORM.lower()
    if "win" in p or "powershell" in p:
        return BLACKLISTED_COMMANDS_FOR_WINDOWSPOWERSHELL
    return BLACKLISTED_COMMANDS_FOR_LINUX


class TerminalInput(BaseModel):
    command: str = Field(description="Shell command to execute (e.g. 'ls -la', 'pwd')")


class TerminalTool(BaseTool):
    name: str = "terminal"
    description: str = (
        f"Run shell commands on this {PLATFORM} machine."
        "Execute a shell command and return the output. "
        "Use for listing files, running scripts, checking system info. "
        "Input should be a single command. Dangerous commands are blocked."
    )
    args_schema: Type[BaseModel] = TerminalInput
    timeout: int = 60
    cwd: str | None = None

    def _run(self, command: str) -> str:
        try:
            cmd = command.strip()
            for blocked in _get_blacklist():
                if blocked in cmd:
                    return f"Blocked: command contains forbidden pattern '{blocked}'"

            cwd_path = Path(self.cwd) if self.cwd else None
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd_path,
            )
            out = result.stdout or ""
            err = result.stderr or ""
            if err:
                out = out.rstrip() + "\n[stderr]\n" + err.rstrip()
            if len(out) > 5000:
                out = out[:5000] + "\n...[truncated]"
            return out or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out ({self.timeout}s limit)"
        except Exception as e:
            return f"Error: {str(e)}"
    async def _arun(self, command: str) -> str:
        return self._run(command)


def create_terminal_tool(root_dir: str | None = None, timeout: int = 60) -> TerminalTool:
    """Create terminal tool. root_dir sets the working directory for commands."""
    return TerminalTool(cwd=root_dir, timeout=timeout)


if __name__ == "__main__":
    tool = create_terminal_tool(root_dir="/home/milo/learnspace/AI_Application/Model_API_Integration")
    out = tool.invoke({"command": "echo hello && ls -la"})
    assert isinstance(out, str) and "hello" in out
    print(out)
    print("terminal ok")
