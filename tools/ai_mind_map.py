#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Mind Map Tool
Summarizes user text into mind map Markdown with a selected LLM model,
then reuses the existing local mind map renderers.
"""

import re
from typing import Any, Generator

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class AIMindMapTool(Tool):
    """Generate a mind map from plain text by asking an LLM to produce Markdown first."""

    _LAYOUT_ALIASES = {
        "center": "center",
        "centre": "center",
        "radial": "center",
        "中心": "center",
        "中心结构": "center",
        "中心辐射": "center",
        "左右": "horizontal",
        "左右结构": "horizontal",
        "水平": "horizontal",
        "水平结构": "horizontal",
        "horizontal": "horizontal",
        "left_right": "horizontal",
        "free": "free",
        "smart": "free",
        "自由": "free",
        "自由结构": "free",
        "智能自由结构": "free",
    }

    def _normalize_layout_mode(self, layout_mode: Any) -> str:
        value = str(layout_mode or "free").strip().lower()
        return self._LAYOUT_ALIASES.get(value, "free")

    def _get_layout_tool_class(self, layout_mode: str) -> type[Tool]:
        normalized = self._normalize_layout_mode(layout_mode)
        if normalized == "center":
            from tools.mind_map_center import MindMapCenterTool

            return MindMapCenterTool
        if normalized == "horizontal":
            from tools.mind_map_horizontal import MindMapHorizontalTool

            return MindMapHorizontalTool
        from tools.mind_map_free import MindMapFreeTool

        return MindMapFreeTool

    def _to_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    def _clean_llm_markdown(self, text: Any) -> str:
        markdown = "" if text is None else str(text)
        markdown = re.sub(r"<think>.*?</think>", "", markdown, flags=re.DOTALL | re.IGNORECASE)
        markdown = re.sub(r"<thought>.*?</thought>", "", markdown, flags=re.DOTALL | re.IGNORECASE)
        markdown = markdown.replace("\\n", "\n").strip()

        fenced = re.search(r"```(?:markdown|md)?\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            markdown = fenced.group(1).strip()
        else:
            markdown = re.sub(r"^```(?:markdown|md)?\s*", "", markdown, flags=re.IGNORECASE).strip()
            markdown = re.sub(r"\s*```$", "", markdown).strip()

        lines = [line.rstrip() for line in markdown.splitlines() if line.strip()]
        markdown = "\n".join(lines).strip()
        if not markdown:
            return "# AI Mind Map"

        has_markdown_structure = any(
            line.lstrip().startswith("#") or re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line)
            for line in lines
        )
        if has_markdown_structure:
            return markdown

        bullet_lines = [f"- {line.strip()}" for line in lines]
        return "# AI Mind Map\n" + "\n".join(bullet_lines)

    def _build_prompt(self, text_content: str, layout_mode: str) -> str:
        layout_tips = {
            "center": "Use a balanced 2-4 level hierarchy suitable for a center radial mind map.",
            "horizontal": "Use a clear left-to-right hierarchy. It can be deeper when the content has steps or timelines.",
            "free": "Use a concise hierarchy. The renderer will automatically choose center or horizontal layout.",
        }
        tip = layout_tips.get(layout_mode, layout_tips["free"])
        return f"""
You are an expert mind map organizer.

Convert the user's text into clean Markdown for a mind map.

Requirements:
1. Return Markdown only. Do not use code fences.
2. Use exactly one level-1 heading as the central topic.
3. Use headings and bullet lists to express hierarchy.
4. Keep node text short, clear, and faithful to the source.
5. Preserve the user's source language unless the source clearly mixes languages.
6. {tip}

User text:
{text_content}
""".strip()

    def _invoke_llm(self, llm_model: dict[str, Any], prompt: str) -> str:
        from dify_plugin.entities.model.message import UserPromptMessage

        messages = [UserPromptMessage(content=prompt)]
        invoke_fn = getattr(self, "invoke_model", None)
        if callable(invoke_fn):
            response = invoke_fn(model=llm_model, messages=messages)
            message = getattr(response, "message", None)
            if message is not None:
                return getattr(message, "content", "")
            return getattr(response, "content", str(response))

        session = getattr(self, "session", None)
        if session and getattr(session, "model", None):
            llm_service = getattr(session.model, "llm", None)
            if not llm_service:
                raise AttributeError("No LLM service found in current Dify session.")
            response = llm_service.invoke(model_config=llm_model, prompt_messages=messages, stream=False)
            if hasattr(response, "message"):
                return response.message.content
            return getattr(response, "content", str(response))

        raise AttributeError("No available LLM invoke interface.")

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            llm_model = tool_parameters.get("model_config")
            text_content = str(tool_parameters.get("text_content") or "").strip()
            layout_mode = self._normalize_layout_mode(tool_parameters.get("layout_mode"))
            filename = str(tool_parameters.get("filename") or "").strip()
            download_md = self._to_bool(tool_parameters.get("download_md", False))

            if not llm_model:
                yield self.create_text_message("AI mind map generation failed: Please select an LLM model.")
                yield self.create_json_message({"success": False, "error": "model_config is required"})
                return
            if not text_content:
                yield self.create_text_message("AI mind map generation failed: No text content provided.")
                yield self.create_json_message({"success": False, "error": "text_content is required"})
                return

            prompt = self._build_prompt(text_content, layout_mode)
            model_output = self._invoke_llm(llm_model, prompt)
            markdown_content = self._clean_llm_markdown(model_output)

            yield self.create_text_message("AI Markdown generated successfully. Rendering mind map...")

            layout_tool_class = self._get_layout_tool_class(layout_mode)
            layout_tool = layout_tool_class(runtime=self.runtime, session=self.session)
            render_parameters = {
                "markdown_content": markdown_content,
                "filename": filename,
                "download_md": download_md,
            }

            for message in layout_tool._invoke(render_parameters):
                yield message

            yield self.create_json_message(
                {
                    "success": True,
                    "layout_mode": layout_mode,
                    "generated_markdown": markdown_content,
                }
            )
        except Exception as e:
            error_msg = str(e)
            yield self.create_text_message(f"AI mind map generation failed: {error_msg}")
            yield self.create_json_message({"success": False, "error": error_msg})


def get_tool():
    return AIMindMapTool
