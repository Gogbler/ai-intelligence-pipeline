"""Groq Llama 3 LLM Provider Implementation.

Second-tier fallback provider for high-throughput structured JSON extraction.
"""

import json
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.llm.rate_limiter import RateLimitError, ContextOverflowError
from app.utils.logger import get_logger

logger = get_logger("GroqProvider")


class GroqProvider:
    """Client for Groq LPU inference (Llama-3 models)."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.name = f"Groq {model} (Tier 2)"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def extract_structured_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call Groq API with JSON object response enforcement."""
        if not self.is_available():
            raise ValueError("GROQ_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise RateLimitError("Groq 429 Rate Limit Exceeded", float(retry_after) if retry_after else None)
            elif resp.status_code == 413:
                raise ContextOverflowError("Groq 413 Context Overflow")
            elif resp.status_code != 200:
                raise RuntimeError(f"Groq API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            try:
                content_text = data["choices"][0]["message"]["content"]
                return json.loads(content_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                raise ValueError(f"Failed to parse structured JSON from Groq response: {e}")
