from pathlib import Path 

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_STATUS = get_tools_config()["python_repl_tool"]["status"]

from typing import Optional

from langchain_core.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_experimental.tools import PythonREPLTool


class PythonREPLWithRootTool(PythonREPLTool):
    """Python REPL with optional root_dir (working directory for file ops)."""
    root_dir: Optional[str] = None

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if self.root_dir:
            preamble = f"import os\nos.chdir(r'{self.root_dir}')\n"
            query = preamble + query
        return super()._run(query, run_manager)

def create_python_repl_tool(root_dir: str | None = None) -> PythonREPLTool | None:
    """Create Python REPL tool. root_dir sets the working directory for file operations."""
    if root_dir:
        tool = PythonREPLWithRootTool(root_dir=root_dir)
    else:
        tool = PythonREPLTool()
    tool.name = "python_repl"
    tool.description = (
        "Execute Python code in an interactive REPL environment. "
        "Use this for calculation, data processing, running python scripts, etc. "
        "Input should be valid Python code. Use print() to see output and debug."
    )
    if TOOL_STATUS == "on":
        return tool
    return None


if __name__ == "__main__":
    tool = create_python_repl_tool(root_dir="/home/milo/learnspace/AI_Application/Agent/ComputerUseAgent/agent")
    print(TOOL_STATUS)
    if tool:
        code = "import os\nprint(os.getcwd())"
        out = tool.invoke(code)
        assert isinstance(out, str) and "agent" in out
        print(out.strip())
        print("python_repl ok")