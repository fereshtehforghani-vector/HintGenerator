"""
Unified LLM interface supporting OpenAI GPT-4o and Google Gemini 2.5 Pro.
"""

import os
import base64
from pathlib import Path
from typing import Literal, Union

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


class LLMInterface:
    """
    Thin wrapper around OpenAI or Gemini chat models.

    Usage
    -----
    llm = LLMInterface(provider="OpenAI")
    reply = llm.chat(system_prompt, user_prompt)
    reply = llm.chat_with_image(system_prompt, user_prompt, image_bytes)
    """

    SUPPORTED = ("OpenAI", "Gemini")

    def __init__(
        self,
        provider: Literal["OpenAI", "Gemini"] = "OpenAI",
        temperature: float = 0.3,
        max_tokens: int = 8000,
    ):
        if provider not in self.SUPPORTED:
            raise ValueError(f"provider must be one of {self.SUPPORTED}")
        self.provider    = provider
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self._llm        = self._init_llm()

    def _init_llm(self):
        if self.provider == "OpenAI":
            if not os.environ.get("OPENAI_API_KEY"):
                raise EnvironmentError("OPENAI_API_KEY is not set.")
            return ChatOpenAI(
                model="gpt-4o",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        # Gemini
        if not os.environ.get("GOOGLE_API_KEY"):
            raise EnvironmentError("GOOGLE_API_KEY is not set.")
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            google_api_key=os.environ["GOOGLE_API_KEY"],
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        return self._llm.invoke(messages).content

    def chat_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_source: Union[str, Path, bytes],
    ) -> str:
        """Send an image alongside a text prompt (vision models only)."""
        if isinstance(image_source, (str, Path)):
            img_path = Path(image_source)
            img_bytes = img_path.read_bytes()
            suffix = img_path.suffix.lower().lstrip(".")
        else:
            img_bytes = image_source
            suffix = "png"

        mime_map  = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                     "gif": "gif", "webp": "webp"}
        mime_type = mime_map.get(suffix, "png")
        b64       = base64.b64encode(img_bytes).decode()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[
                {"type": "text", "text": user_prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{mime_type};base64,{b64}",
                               "detail": "high"}},
            ]),
        ]
        return self._llm.invoke(messages).content

    def __repr__(self):
        model = "gpt-4o" if self.provider == "OpenAI" else "gemini-2.5-pro"
        return f"LLMInterface(provider={self.provider!r}, model={model!r})"
