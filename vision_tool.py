"""Vision tool: use a vision-capable API to understand local images."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Type

import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


class VisionToolInput(BaseModel):
    image_path: str = Field(
        description="Path to the image file. Can be relative to the project root (e.g. workplace/screenshot.png) or absolute."
    )
    question: str = Field(
        default="Describe this image in detail.",
        description="Question or instruction for the vision model about the image (e.g. 'What is in this image?', 'Extract the text.', 'Describe the chart.').",
    )


class VisionTool(BaseTool):
    name: str = "understand_image"
    description: str = (
        "Use a vision model to understand a local image. "
        "Provide the path to the image file (relative to project root or absolute) and an optional question. "
        "Returns the model's description or answer. Use when the user refers to an image, screenshot, or diagram."
    )
    args_schema: Type[BaseModel] = VisionToolInput
    root_dir: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    def _run(self, image_path: str, question: str = "Describe this image in detail.") -> str:
        root = Path(self.root_dir).resolve()
        normalized = image_path.replace("\\", "/").strip().lstrip("./")
        if not normalized:
            return "Error: image_path is empty."
        full_path = (root / normalized).resolve() if not Path(normalized).is_absolute() else Path(normalized).resolve()
        # Sandbox: if root_dir is set, require path under it
        if self.root_dir and not str(full_path).startswith(str(root)):
            return "Access denied: image path must be under the project directory."
        if not full_path.exists():
            return f"File not found: {image_path}"
        if not full_path.is_file():
            return f"Path is not a file: {image_path}"

        try:
            raw = full_path.read_bytes()
        except Exception as e:
            return f"Error reading image: {e}"

        mime, _ = mimetypes.guess_type(str(full_path))
        if not mime or not mime.startswith("image/"):
            mime = "image/jpeg"
        b64 = base64.standard_b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"

        url = (self.base_url.rstrip("/") + "/chat/completions") if self.base_url else ""
        if not url or not self.api_key or not self.model:
            return "Vision tool is not configured: set base_url, api_key and model in config.tools.vision_tool."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question or "Describe this image in detail."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": 2048,
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            choice = (data.get("choices") or [None])[0]
            if not choice:
                return "Vision API returned no choices."
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            return content.strip() or "(No content)"
        except requests.Timeout:
            return "Vision API request timed out."
        except requests.RequestException as e:
            return f"Vision API request failed: {e}"
        except Exception as e:
            return f"Vision tool error: {e}"


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
