"""Asynchronous Base Scraper Engine.

Features:
- Semaphore-driven concurrency control
- Checkpointing for resilient resume-after-interruption
- Polite delays with randomized jitter
- Anti-bot stealth headers and challenge detection
- Automatic retries on transient network errors
"""

import asyncio
import json
import os
import random
from typing import Optional, Set
import httpx
from app.config import settings
from app.scrapers.antibot import AntiBotDefense
from app.utils.logger import get_logger

logger = get_logger("BaseScraper")


class AsyncBaseScraper:
    """Foundational async crawler with rate limiting, retries, and checkpointing."""

    def __init__(
        self,
        name: str,
        concurrency: int = 10,
        request_delay: float = 0.2,
        checkpoint_dir: Optional[str] = None,
    ):
        self.name = name
        self.concurrency = concurrency
        self.request_delay = request_delay
        self.semaphore = asyncio.Semaphore(concurrency)
        self.checkpoint_dir = checkpoint_dir or os.path.join(settings.DATA_EXPORT_DIR, "..", "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.checkpoint_file = os.path.join(self.checkpoint_dir, f"{self.name.lower().replace(' ', '_')}_visited.json")
        self.visited_urls: Set[str] = self._load_checkpoint()

    def _load_checkpoint(self) -> Set[str]:
        """Load previously processed URLs to enable zero-duplicate resumption."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data)
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to load checkpoint: {e}")
        return set()

    def _save_checkpoint(self):
        """Save visited URLs to checkpoint disk file."""
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(list(self.visited_urls), f)
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to write checkpoint: {e}")

    async def fetch_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        retries: int = 3,
        headers: Optional[dict] = None,
    ) -> Optional[str]:
        """Fetch a single URL asynchronously with concurrency throttle, anti-bot headers, and backoff."""
        if url in self.visited_urls:
            return None

        async with self.semaphore:
            req_headers = headers or AntiBotDefense.get_stealth_headers(refer_url=url)
            for attempt in range(1, retries + 1):
                try:
                    # Respectful jittered delay
                    await asyncio.sleep(self.request_delay + random.uniform(0.05, 0.2))

                    resp = await client.get(url, headers=req_headers, timeout=settings.REQUEST_TIMEOUT)

                    # Challenge / Anti-Bot Inspection
                    is_challenge, challenge_type = AntiBotDefense.detect_challenge(resp.status_code, resp.text)
                    if is_challenge:
                        logger.warning(f"[{self.name}] {challenge_type} triggered on {url}. Logging block and continuing.")
                        return None

                    if resp.status_code == 200:
                        self.visited_urls.add(url)
                        if len(self.visited_urls) % 50 == 0:
                            self._save_checkpoint()
                        return resp.text

                    elif resp.status_code == 429:
                        wait = 2.0 * attempt + random.uniform(0.5, 1.5)
                        logger.warning(f"[{self.name}] HTTP 429 on {url}. Sleeping {wait:.2f}s...")
                        await asyncio.sleep(wait)

                    elif resp.status_code in (404, 410):
                        logger.debug(f"[{self.name}] Target URL not found: {url} ({resp.status_code})")
                        return None

                    else:
                        logger.warning(f"[{self.name}] HTTP {resp.status_code} on {url} (attempt {attempt}/{retries})")

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt == retries:
                        logger.error(f"[{self.name}] Network failed for {url}: {e}")
                    await asyncio.sleep(1.0 * attempt)
                except Exception as e:
                    logger.error(f"[{self.name}] Unexpected error fetching {url}: {e}")
                    return None

        return None
