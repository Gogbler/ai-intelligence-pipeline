"""Intelligent Payload Chunking and Semantic Pruning Engine.

Guarantees payloads never trigger HTTP 413 (Payload Too Large) errors
while preserving high semantic density for entity, pricing, and paper extraction.
"""

import re
from typing import Optional, List
from bs4 import BeautifulSoup


class IntelligentChunker:
    """Prunes noisy DOM elements, extracts structured semantic text, and enforces token budgets."""

    DEFAULT_MAX_CHARS: int = 24_000  # ~6,000 tokens, well below standard 32k/128k context limits
    BOILERPLATE_TAGS: List[str] = [
        "script", "style", "nav", "footer", "header", "noscript",
        "svg", "form", "iframe", "button", "aside", "menu"
    ]
    HIGH_SIGNAL_KEYWORDS: List[str] = [
        "price", "pricing", "plan", "free", "tier", "enterprise", "pro", "month", "year",
        "team", "founder", "employee", "about", "mission", "abstract", "paper", "author", "github"
    ]

    @classmethod
    def clean_html(cls, html_content: str) -> str:
        """Strip boilerplate DOM elements, retaining semantic headings, tables, and text."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        # Strip all boilerplate tags
        for tag in soup.find_all(cls.BOILERPLATE_TAGS):
            tag.decompose()

        # Extract text while preserving spacing between blocks
        text = soup.get_text(separator="\n", strip=True)

        # Collapse excess empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def prune_and_chunk(
        cls,
        raw_text: str,
        max_chars: Optional[int] = None,
        preserve_keywords: bool = True,
    ) -> str:
        """Truncate raw text intelligently to fit within token boundaries.

        If text is longer than max_chars:
        1. Keeps the leading context (title, overview, headers)
        2. Extracts high-signal paragraphs matching pricing, team, or abstract keywords
        3. Appends closing context
        """
        budget = max_chars or cls.DEFAULT_MAX_CHARS
        if len(raw_text) <= budget:
            return raw_text

        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        if not paragraphs:
            return raw_text[:budget]

        # Allocation: 40% head, 40% high-signal keyword chunks, 20% tail
        head_budget = int(budget * 0.40)
        tail_budget = int(budget * 0.20)
        signal_budget = budget - head_budget - tail_budget

        # 1. Collect Head
        head_chunks = []
        head_len = 0
        for p in paragraphs:
            if head_len + len(p) + 2 > head_budget:
                break
            head_chunks.append(p)
            head_len += len(p) + 2

        # 2. Collect Tail
        tail_chunks = []
        tail_len = 0
        for p in reversed(paragraphs):
            if tail_len + len(p) + 2 > tail_budget:
                break
            tail_chunks.insert(0, p)
            tail_len += len(p) + 2

        # 3. Collect Middle High-Signal Paragraphs
        middle_paragraphs = paragraphs[len(head_chunks):len(paragraphs) - len(tail_chunks)]
        signal_chunks = []
        signal_len = 0

        if preserve_keywords:
            for p in middle_paragraphs:
                p_lower = p.lower()
                if any(kw in p_lower for kw in cls.HIGH_SIGNAL_KEYWORDS):
                    if signal_len + len(p) + 2 <= signal_budget:
                        signal_chunks.append(p)
                        signal_len += len(p) + 2

        # Assemble composite payload
        result_parts = []
        if head_chunks:
            result_parts.append("\n\n".join(head_chunks))

        if signal_chunks:
            result_parts.append("\n\n[... High-Density Signal Content ...]\n\n" + "\n\n".join(signal_chunks))

        if tail_chunks:
            result_parts.append("\n\n[... Additional Sections ...]\n\n" + "\n\n".join(tail_chunks))

        assembled = "\n\n".join(result_parts)

        # Strict safety hard cap
        if len(assembled) > budget:
            return assembled[:budget] + "\n[Truncated for context safety]"

        return assembled
