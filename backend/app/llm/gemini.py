"""Google Gemini Flash LLM Provider Implementation.

First-tier provider for structured canonical entity extraction.
"""

import json
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.llm.rate_limiter import RateLimitError, ContextOverflowError
from app.utils.logger import get_logger

logger = get_logger("GeminiProvider")


class GeminiProvider:
    """Client for Google Gemini Flash models."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.name = "Gemini Flash (Tier 1)"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def extract_structured_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call Gemini Flash with structured JSON output enforcement."""
        if not self.is_available():
            raise ValueError("GEMINI_API_KEY is not configured.")

        url = f"{self.BASE_URL}?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            }
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise RateLimitError("Gemini 429 Rate Limit Exceeded", float(retry_after) if retry_after else None)
            elif resp.status_code == 413:
                raise ContextOverflowError("Gemini 413 Context Overflow")
            elif resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            try:
                content_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                raise ValueError(f"Failed to parse structured JSON from Gemini response: {e}")
