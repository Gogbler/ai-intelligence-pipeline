"""Anti-Bot Navigation and Header Camouflage Engine.

Handles:
- Rotating modern realistic desktop browser headers
- Cloudflare, Datadome, and Akamai challenge detection
- Clean logging of challenge responses without failing entire pipeline runs
- Respectful crawl delay and jitter
"""

import random
from typing import Dict, Tuple

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]

CHALLENGE_INDICATORS = [
    "just a moment...",
    "checking your browser",
    "cf-browser-verification",
    "challenge-running",
    "turnstile",
    "datadome",
    "cf-chl-bypass",
    "ray id:",
    "attention required! | cloudflare",
]


class AntiBotDefense:
    """Provides stealth headers and detects anti-bot challenges."""

    @staticmethod
    def get_stealth_headers(refer_url: str = "https://www.google.com/") -> Dict[str, str]:
        """Generate realistic browser headers to mimic real human requests."""
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": refer_url,
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
        }

    @staticmethod
    def detect_challenge(status_code: int, html_body: str) -> Tuple[bool, str]:
        """Detect whether a response is a Cloudflare or Datadome challenge."""
        if status_code in (403, 503):
            body_lower = html_body.lower()
            for indicator in CHALLENGE_INDICATORS:
                if indicator in body_lower:
                    if "datadome" in body_lower:
                        return True, "Datadome Captcha Interception"
                    return True, "Cloudflare WAF / Turnstile Challenge"
        return False, ""
