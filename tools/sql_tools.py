from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

from __future__ import annotations

from microclaw.config import get_llm_config, get_tools_config


def create_sql_tools() -> list | None:
    tools_cfg = get_tools_config() or {}
    sql_cfg = tools_cfg.get("sql_tools") or {}
    status = str(sql_cfg.get("status", "off")).lower()
    db_uri = str(sql_cfg.get("db_uri", "") or "").strip()
    if status != "on":
        return None
    if not db_uri:
        return None

    llm_info = (get_llm_config().get("info") or {})
    model_name = str(llm_info.get("model", "") or "").strip()
    api_key = str(llm_info.get("api_key", "") or "").strip()
    base_url = str(llm_info.get("base_url", "") or "").strip()
    if not model_name or not api_key or not base_url:
        return None

    model = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)
    db = SQLDatabase.from_uri(db_uri)
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    return toolkit.get_tools()
    return None

if __name__ == "__main__": 
    tools = create_sql_tools()
    for tool in tools:
        print(tool.name)