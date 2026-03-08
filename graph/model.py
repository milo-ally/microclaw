"""Chat model that preserves reasoning_content from Doubao/Volcengine and other providers."""

from langchain_core.messages import AIMessageChunk
from langchain_core.language_models.chat_models import ChatResult
from langchain_openai import ChatOpenAI


class ChatOpenAIWithReasoning(ChatOpenAI):
    def _create_chat_result(
        self,
        response,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        if not result.generations:
            return result
        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                result.generations[0].message.additional_kwargs["reasoning_content"] = (
                    msg.reasoning_content
                )
        return result

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        """流式时从 delta 提取 reasoning_content"""
        gen = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if gen is None:
            return None
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        if choices:
            delta = choices[0].get("delta") or {}
            if delta.get("reasoning_content"):
                msg = gen.message
                if isinstance(msg, AIMessageChunk):
                    msg.additional_kwargs["reasoning_content"] = delta["reasoning_content"]
        return gen
