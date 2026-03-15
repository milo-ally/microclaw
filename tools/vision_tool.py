"""Vision tool: use a vision-capable API to understand images (local file or image URL)."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Type

from langchain_core.tools import BaseTool
from openai import OpenAI
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


def _is_image_url(s: str) -> bool:
    """True if input looks like an http(s) image URL."""
    raw = (s or "").strip()
    return raw.lower().startswith(("http://", "https://"))


def _resolve_root(root_dir: str) -> Path:
    """Resolve root directory, expanding ~ and making absolute."""
    if not (root_dir or "").strip():
        return Path.cwd()
    return Path(os.path.expanduser(root_dir.strip())).resolve()


def _resolve_image_path(image_path: str, root: Path) -> Path | None:
    """把任意输入路径统一解析为绝对路径。支持相对路径（相对 root）或绝对路径，会展开 ~。"""
    raw = (image_path or "").strip().replace("\\", "/")
    if not raw:
        return None
    expanded = os.path.expanduser(raw)
    p = Path(expanded)
    if p.is_absolute():
        return p.resolve()
    return (root / expanded).resolve()


class VisionToolInput(BaseModel):
    image_path: str = Field(
        description="Local image path (relative/absolute, e.g. workplace/screenshot.png) OR image URL (http:// or https://)."
    )
    question: str = Field(
        default="Describe this image in detail.",
        description="Question or instruction for the vision model about the image (e.g. 'What is in this image?', 'Extract the text.', 'Describe the chart.').",
    )


class VisionTool(BaseTool):
    name: str = "understand_image"
    description: str = (
        "Use a vision model to understand an image. "
        "Provide either a local image path (relative to project root or absolute) OR an image URL (http(s)://...), and an optional question. "
        "Returns the model's description or answer. Use when the user refers to an image, screenshot, diagram, or image link."
    )
    args_schema: Type[BaseModel] = VisionToolInput
    root_dir: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    def _run(self, image_path: str, question: str = "Describe this image in detail.") -> str:
        raw_input = (image_path or "").strip()
        if not raw_input:
            return "Error: image_path is empty."

        # 网络图片：直接使用 URL，无需读本地文件
        if _is_image_url(raw_input):
            image_url = raw_input
        else:
            # 本地图片：解析路径并转为 base64 data URL
            root = _resolve_root(self.root_dir)
            full_path = _resolve_image_path(raw_input, root)
            if full_path is None:
                return "Error: image_path is empty."
            if self.root_dir.strip():
                try:
                    full_path = full_path.resolve()
                    root_res = root.resolve()
                    if not str(full_path).startswith(str(root_res)):
                        return (
                            f"Access denied: image path must be under the project directory ({root_res}). "
                            f"Resolved path: {full_path}"
                        )
                except Exception as e:
                    return f"Error resolving path: {e}"
            if not full_path.exists():
                return f"File not found: {image_path} (resolved to {full_path})"
            if not full_path.is_file():
                return f"Path is not a file: {image_path}"
            try:
                raw = full_path.read_bytes()
            except Exception as e:
                return f"Error reading image: {e}"
            mime, _ = mimetypes.guess_type(str(full_path))
            if not mime or not mime.startswith("image/"):
                mime = "image/jpeg"
            image_base64 = base64.b64encode(raw).decode("utf-8")
            image_url = f"data:{mime};base64,{image_base64}"

        if not self.base_url or not self.api_key or not self.model:
            return "Vision tool is not configured: set base_url, api_key and model in config.tools.vision_tool."

        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url.rstrip("/"),
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question or "Describe this image in detail."},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=2048,
                temperature=0.7,
            )
            choice = (response.choices or [None])[0]
            if not choice or not choice.message:
                return "Vision API returned no choices."
            content = (choice.message.content or "").strip()
            return content or "(No content)"
        except Exception as e:
            return f"Vision API request failed: {e}"


def create_vision_tool(root_dir: str) -> VisionTool | None:
    tools_cfg = get_tools_config() or {}
    cfg = tools_cfg.get("vision_tool") or {}
    status = str(cfg.get("status", "off")).lower()
    if status != "on":
        return None
    base_url = (cfg.get("base_url") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()
    model = (cfg.get("model") or "").strip()
    if not base_url or not api_key or not model:
        return None
    return VisionTool(
        root_dir=root_dir,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
