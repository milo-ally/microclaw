"""Chat model that preserves reasoning_content from Doubao/Volcengine and other providers."""

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.language_models.chat_models import ChatResult
from langchain_openai import ChatOpenAI


class DeepSeekChatModel(ChatOpenAI):
    
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str, 
        temperature: float = 0.3,
        **kwargs  # eg: extra_body
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )


class DeepSeekReasoningModel(ChatOpenAI):

    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str , 
        temperature: float = 0.3, 
        **kwargs  # eg: extra_body
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )
    
    def _get_request_payload(
        self, 
        input_, 
        *, 
        stop=None, 
        **kwargs
    ):
        """Ensure assistant messages include reasoning_content for DeepSeek thinking+tool_calls API."""
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for i, m in enumerate(messages):
            if i < len(payload.get("messages", [])) and isinstance(m, AIMessage):
                # DeepSeek requires reasoning_content on assistant messages in thinking mode
                payload["messages"][i]["reasoning_content"] = (
                    (m.additional_kwargs or {}).get("reasoning_content") or ""
                )
        return payload

    def _create_chat_result(
        self,
        response,
        generation_info: dict | None = None,
    ) -> ChatResult:
        """Extract reasoning_content"""
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
        """Extract reasoning_content from delta"""
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


class MinimaxReasoningModel(ChatOpenAI):

    @staticmethod
    def _normalize_reasoning_details(details) -> str:
        """
        MiniMax returns `reasoning_details` (often list[{"text": "..."}]).
        Normalize it into a single string so downstream code can treat it as
        `reasoning_content`.
        """
        if not details:
            return ""
        if isinstance(details, str):
            return details
        if isinstance(details, list):
            parts: list[str] = []
            for item in details:
                if not item:
                    continue
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    t = item.get("text")
                    if isinstance(t, str) and t:
                        parts.append(t)
            return "".join(parts)
        return str(details)

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.3,
        **kwargs
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs
        )

    def _create_chat_result(
        self, response, generation_info: dict | None = None
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        if not result.generations:
            return result
        msg = response.choices[0].message
        if hasattr(msg, "reasoning_details") and msg.reasoning_details:
            result.generations[0].message.additional_kwargs["reasoning_content"] = self._normalize_reasoning_details(
                msg.reasoning_details
            )
        return result

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        gen = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if gen is None:
            return None
        rc = ""

        # LangChain/OpenAI-compatible providers vary here:
        # - some yield objects with `.choices[0].delta`
        # - some yield dict chunks like {"choices":[{"delta": {...}}]}
        if isinstance(chunk, dict):
            choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", []) or []
            first = choices[0] if choices else {}
            delta = first.get("delta", {}) if isinstance(first, dict) else {}
            rc = self._normalize_reasoning_details(delta.get("reasoning_details"))
        else:
            choices = getattr(chunk, "choices", None) or []
            delta = getattr(choices[0], "delta", None) if choices else None
            rc = self._normalize_reasoning_details(getattr(delta, "reasoning_details", None) if delta is not None else None)

        if rc and isinstance(gen.message, AIMessageChunk):
            gen.message.additional_kwargs["reasoning_content"] = rc
        return gen


class GLMReasoningModel(ChatOpenAI):

    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str , 
        temperature: float = 0.3, 
        **kwargs  # eg: extra_body
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )
    
    def _get_request_payload(
        self, 
        input_, 
        *, 
        stop=None, 
        **kwargs
    ):
        """Ensure assistant messages include reasoning_content for DeepSeek thinking+tool_calls API."""
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for i, m in enumerate(messages):
            if i < len(payload.get("messages", [])) and isinstance(m, AIMessage):
                # DeepSeek requires reasoning_content on assistant messages in thinking mode
                payload["messages"][i]["reasoning_content"] = (
                    (m.additional_kwargs or {}).get("reasoning_content") or ""
                )
        return payload

    def _create_chat_result(
        self,
        response,
        generation_info: dict | None = None,
    ) -> ChatResult:
        """Extract reasoning_content"""
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
        """Extract reasoning_content from delta"""
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


class GLMChatModel(ChatOpenAI):

    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str , 
        temperature: float = 0.3, 
        **kwargs  # eg: extra_body
    ):
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )
