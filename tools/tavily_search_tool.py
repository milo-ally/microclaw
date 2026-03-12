from __future__ import annotations

from microclaw.config import get_tools_config

from langchain_tavily.tavily_search import TavilySearch

def create_tavily_search_tool() -> TavilySearch | None:
    tool_cfg = (get_tools_config() or {}).get("tavily_search_tool") or {}
    status = str(tool_cfg.get("status", "off")).lower()
    api_key = str(tool_cfg.get("tavily_api_key", "") or "")
    if not api_key or not api_key.startswith("tvly-"):
        return None
    if status == "on":
        tool = TavilySearch(
            tavily_api_key=api_key
        )
        return tool
    return None

# test
if __name__ == "__main__":
    print(f"工具状态: {TOOL_STATUS}")
    tool = create_tavily_search_tool()
    if tool:
        try:
            out = tool.invoke({
                "query": "What happened at the last wimbledon"
            })
            assert isinstance(out, str) and len(out) > 0
            print(out[:800] + ("..." if len(out) > 800 else ""))
            print("Tavily 搜索工具调用成功！")
        except Exception as e:
            print(f"调用失败：{e}")
    else:
        print("工具未启用或 API Key 配置错误")
