from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

from pathlib import Path 

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config, get_llm_config

MODEL = get_llm_config()["info"]["model"]
API_KEY = get_llm_config()["info"]["api_key"]
BASE_URL = get_llm_config()["info"]["base_url"]

TOOL_STATUS = get_tools_config()["sql_tools"]["status"]
DB_URI = get_tools_config()["sql_tools"]["db_uri"]


model = ChatOpenAI(
    model=MODEL, 
    api_key=API_KEY, 
    base_url=BASE_URL
)


def create_sql_tools() -> list | None:
    if TOOL_STATUS == "on":
        db = SQLDatabase.from_uri(DB_URI)
        toolkit = SQLDatabaseToolkit(db=db, llm=model)
        tools = toolkit.get_tools()
        return tools
    return None

if __name__ == "__main__": 
    tools = create_sql_tools()
    for tool in tools:
        print(tool.name)