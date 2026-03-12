from __future__ import annotations

from microclaw.config import get_tools_config

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import json 


class AskUserQuestionInput(BaseModel):
    question: str = Field(description="The question to ask the user")

class AskUserQuestionTool(BaseTool):
    name: str = "ask_user_question"
    description: str = (
        "Ask the user a question to get information or permission to proceed"
        "Use this tool when you need to get information or permission from the user"
        "or when you are uncertain about the next step"
        "for example, the question you ask to the user can be like: (a):...\n (b):...\n (c):..."
    )
    args_schema: Type[BaseModel] = AskUserQuestionInput
    def _run(self, question: str) -> str:
        return json.dumps({
            'question_you_should_pass_to_user': question, 
            'mention_to_user_requirements': "You should tell the user question you've just prepared"
        }, ensure_ascii=False)


def create_ask_user_question_tool() -> AskUserQuestionTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("ask_user_question_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return AskUserQuestionTool()
    return None 

if __name__ == "__main__": 
    tool = create_ask_user_question_tool()
    if tool:
        print(tool.name)
        print(tool.args)