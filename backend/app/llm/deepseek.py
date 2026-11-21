"""DeepSeek LLM Provider Implementation.

Third-tier fallback provider for structured JSON extraction.
"""

import json
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.llm.rate_limiter import RateLimitError, ContextOverflowError
from app.utils.logger import get_logger

logger = get_logger("DeepSeekProvider")


class DeepSeekProvider:
    """Client for DeepSeek API."""

    BASE_URL = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model
        self.name = f"DeepSeek {model} (Tier 3)"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def extract_structured_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call DeepSeek API with JSON object response enforcement."""
        if not self.is_available():
            raise ValueError("DEEPSEEK_API_KEY is not configured.")

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
                raise RateLimitError("DeepSeek 429 Rate Limit Exceeded", float(retry_after) if retry_after else None)
            elif resp.status_code == 413:
                raise ContextOverflowError("DeepSeek 413 Context Overflow")
            elif resp.status_code != 200:
                raise RuntimeError(f"DeepSeek API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            try:
                content_text = data["choices"][0]["message"]["content"]
                return json.loads(content_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                raise ValueError(f"Failed to parse structured JSON from DeepSeek response: {e}")
