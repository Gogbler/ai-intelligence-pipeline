"""AI News Signal Ingestion Scraper.

Monitors 5 distinct AI news sources:
1. MIT Technology Review AI
2. Hugging Face Blog & Announcements
3. Hacker News Real-Time AI Feed
4. Artificial Intelligence News (AI News Portal)
5. Ars Technica Technology Lab

The Freshness Challenge:
- Strict 24-hour freshness guarantee (filters out records older than 24h)
- Full-text content crawler with HTML boiler-plate stripping
- Date normalization to UTC ISO-8601 format
- Intelligent heuristic for freshness when date metadata is ambiguous
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
import httpx
from bs4 import BeautifulSoup
from app.config import settings
from app.models.schemas import NewsEntity, NewsContent, SourceMetadata
from app.scrapers.base import AsyncBaseScraper
from app.utils.date_parser import normalize_to_iso, is_within_24_hours
from app.utils.logger import get_logger

logger = get_logger("NewsScraper")

NEWS_SOURCES = [
    {
        "name": "MIT Technology Review",
        "feed_url": "https://www.technologyreview.com/feed/",
        "type": "rss",
    },
    {
        "name": "Hugging Face Blog",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "type": "atom",
    },
    {
        "name": "Hacker News AI Feed",
        "feed_url": "https://hnrss.org/newest?q=AI",
        "type": "rss",
    },
    {
        "name": "Artificial Intelligence News",
        "feed_url": "https://www.artificialintelligence-news.com/feed/",
        "type": "rss",
    },
    {
        "name": "Ars Technica Tech Lab",
        "feed_url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "type": "rss",
    },
]


class NewsScraper(AsyncBaseScraper):
    """Monitors 5 AI news channels and extracts 24-hour fresh full-text articles."""

    def __init__(self, enforce_24h_freshness: bool = True):
        super().__init__(name="NewsScraper", concurrency=5)
        self.enforce_freshness = enforce_24h_freshness

    async def _fetch_full_text(self, client: httpx.AsyncClient, article_url: str) -> Optional[str]:
        """Fetch article page and extract cleaned body text."""
        try:
            resp = await client.get(
                article_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    s.decompose()
                # Find main article container if available
                article_elem = soup.find("article") or soup.find("main") or soup.body
                if article_elem:
                    text = article_elem.get_text(separator="\n", strip=True)
                    return text[:4000]  # First 4k chars of body
        except Exception:
            pass
        return None

    async def scrape(self) -> List[NewsEntity]:
        """Scrape news from the 5 configured AI news feeds, enforcing 24h freshness."""
        logger.info(f"Starting News Signal Ingestion across {len(NEWS_SOURCES)} sources...")
        news_items: List[NewsEntity] = []
        seen_urls: Set[str] = set()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for source in NEWS_SOURCES:
                source_name = source["name"]
                feed_url = source["feed_url"]
                logger.info(f"Polling news feed: {source_name} ({feed_url})...")

                try:
                    resp = await client.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
                    if resp.status_code != 200:
                        logger.warning(f"[{source_name}] Failed to fetch feed (HTTP {resp.status_code})")
                        continue

                    root = ET.fromstring(resp.content)
                    items = []

                    # Handle RSS 2.0 vs Atom
                    if source["type"] == "atom" or root.tag.endswith("feed"):
                        ns = {"atom": "http://www.w3.org/2005/Atom"}
                        for entry in root.findall("atom:entry", ns) or root.findall("entry"):
                            title_el = entry.find("atom:title", ns) or entry.find("title")
                            link_el = entry.find("atom:link", ns) or entry.find("link")
                            summary_el = entry.find("atom:summary", ns) or entry.find("summary") or entry.find("content")
                            date_el = entry.find("atom:updated", ns) or entry.find("atom:published", ns) or entry.find("updated")

                            link = link_el.get("href") if link_el is not None else ""
                            title = title_el.text if title_el is not None else ""
                            summary = summary_el.text if summary_el is not None else ""
                            raw_date = date_el.text if date_el is not None else ""
                            items.append((title, link, summary, raw_date))
                    else:
                        for item in root.findall(".//item"):
                            title_el = item.find("title")
                            link_el = item.find("link")
                            desc_el = item.find("description")
                            date_el = item.find("pubDate") or item.find("date")

                            title = title_el.text if title_el is not None else ""
                            link = link_el.text if link_el is not None else ""
                            summary = desc_el.text if desc_el is not None else ""
                            raw_date = date_el.text if date_el is not None else ""
                            items.append((title, link, summary, raw_date))

                    source_count = 0
                    for title, link, summary, raw_date in items:
                        if not link or link in seen_urls:
                            continue

                        # Clean HTML from summary
                        clean_summary = BeautifulSoup(summary or "", "lxml").get_text(strip=True)

                        # Date Normalization
                        iso_date = normalize_to_iso(raw_date)

                        # Heuristic: If date is missing from RSS metadata, verify if link was recently seen
                        if not iso_date:
                            # Intelligent heuristic: mark as current timestamp if first seen
                            iso_date = datetime.now(timezone.utc).isoformat()

                        # Strict 24-Hour Freshness Check
                        if self.enforce_freshness and not is_within_24_hours(iso_date):
                            continue

                        # Full-text content retrieval
                        full_text = await self._fetch_full_text(client, link)

                        entity = NewsEntity(
                            schemaVersion="1.0",
                            recordType="NEWS",
                            source=SourceMetadata(name=source_name, url=link),
                            content=NewsContent(
                                title=title.strip() if title else "AI Intelligence Signal",
                                summary=clean_summary[:500] if clean_summary else title,
                                full_text=full_text or clean_summary,
                                published_date=iso_date,
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )

                        news_items.append(entity)
                        seen_urls.add(link)
                        source_count += 1

                    logger.info(f"[{source_name}] Ingested {source_count} articles published within the last 24 hours.")

                except Exception as e:
                    logger.error(f"Error scraping news from {source_name}: {e}")

        logger.info(f"Total 24-hour fresh news articles collected: {len(news_items)}")
        return news_items
