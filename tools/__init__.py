"""Tools module - provides get_all_tools for agent use."""

from pathlib import Path
from langchain_core.tools import BaseTool
from config import get_base_dir


def get_all_tools(base_dir: str | Path | None = None) -> list[BaseTool]:

    root = str(base_dir or get_base_dir())

    tools: list[BaseTool] = []

    from .fetch_url_tool import create_fetch_url_tool
    from .read_file_tool import create_sandboxed_read_file_tool
    from .terminal_tool import create_terminal_tool
    from .python_repl_tool import create_python_repl_tool
    from .ask_user_question_tool import create_ask_user_question_tool
    from .sql_tools import create_sql_tools
    from .tavily_search_tool import create_tavily_search_tool
    
    tools.extend([
        tool for tool in [
            create_fetch_url_tool(),
            create_sandboxed_read_file_tool(root_dir=root),
            create_terminal_tool(root_dir=root),
            create_python_repl_tool(root_dir=root),
            create_ask_user_question_tool(), 
            create_tavily_search_tool()
        ] if tool is not None
    ])

    # 添加sql工具 
    sql_tools = create_sql_tools()
    if sql_tools is not None:
        tools.extend(sql_tools)
    
    return tools


__all__ = ["get_all_tools"]
