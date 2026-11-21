"""AI Research Papers Scraper with GitHub Repository & Live Star Tracking.

Vertical: Research Papers
Sources:
- ArXiv API (cs.AI, cs.LG, cs.CL, cs.CV)
- Hugging Face Daily Papers API
- Papers with Code Linkage
- GitHub API for live stargazer counts
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional, Dict
import httpx
from app.config import settings
from app.models.schemas import ResearchPaperEntity, ResearchPaperContent, SourceMetadata
from app.scrapers.base import AsyncBaseScraper
from app.utils.date_parser import normalize_to_iso
from app.utils.logger import get_logger

logger = get_logger("ResearchPaperScraper")

GITHUB_URL_REGEX = re.compile(r"https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", re.IGNORECASE)


class ResearchPaperScraper(AsyncBaseScraper):
    """Acquires AI research papers from ArXiv / HF and correlates GitHub stars."""

    def __init__(self, target_count: int = 1000):
        super().__init__(name="ResearchPaperScraper", concurrency=settings.CRAWLER_CONCURRENCY)
        self.target_count = target_count
        self.github_stars_cache: Dict[str, int] = {}

    async def _fetch_github_stars(self, client: httpx.AsyncClient, repo_url: str) -> Optional[int]:
        """Fetch real-time GitHub stargazer count from GitHub API."""
        if not repo_url:
            return None

        # Clean repo url
        match = GITHUB_URL_REGEX.search(repo_url)
        if not match:
            return None

        owner, repo = match.group(1), match.group(2)
        repo_clean = f"{owner}/{repo.rstrip('.git')}"

        if repo_clean in self.github_stars_cache:
            return self.github_stars_cache[repo_clean]

        api_url = f"https://api.github.com/repos/{repo_clean}"
        headers = {"User-Agent": "FrontierAtlas-Intelligence-Engine/1.0"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            resp = await client.get(api_url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                stars = resp.json().get("stargazers_count", 0)
                self.github_stars_cache[repo_clean] = stars
                return stars
        except Exception:
            pass

        return None

    async def scrape(self) -> List[ResearchPaperEntity]:
        """Collect up to target_count unique AI research papers with GitHub correlation."""
        papers: List[ResearchPaperEntity] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT, follow_redirects=True) as client:
            # 1. Fetch from Hugging Face Daily Papers (high density of code links)
            logger.info("Fetching research papers from Hugging Face Papers API...")
            try:
                hf_url = "https://huggingface.co/api/daily_papers?limit=100"
                resp = await client.get(hf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
                if resp.status_code == 200:
                    hf_data = resp.json()
                    for item in hf_data:
                        p = item.get("paper", {})
                        pid = p.get("id")
                        if not pid:
                            continue
                        paper_url = f"https://arxiv.org/abs/{pid}"
                        if paper_url in seen_urls:
                            continue

                        title = p.get("title", "").strip()
                        authors = [a.get("name", "") for a in p.get("authors", []) if a.get("name")]
                        pub_date = normalize_to_iso(p.get("publishedAt")) or datetime.now(timezone.utc).isoformat()
                        summary = p.get("summary", "")

                        # Extract GitHub link from summary or HF page
                        github_match = GITHUB_URL_REGEX.search(summary)
                        github_url = github_match.group(0).rstrip(".") if github_match else None
                        stars = await self._fetch_github_stars(client, github_url) if github_url else None

                        entity = ResearchPaperEntity(
                            schemaVersion="1.0",
                            recordType="RESEARCH_PAPER",
                            source=SourceMetadata(name="Hugging Face / ArXiv", url=paper_url),
                            content=ResearchPaperContent(
                                title=title,
                                authors=authors,
                                paper_url=paper_url,
                                github_url=github_url,
                                github_stars=stars,
                                published_date=pub_date,
                            ),
                        )
                        papers.append(entity)
                        seen_urls.add(paper_url)
            except Exception as e:
                logger.warning(f"Error fetching from HF papers: {e}")

            logger.info(f"Collected {len(papers)} papers from HF. Continuing via ArXiv API to reach {self.target_count}...")

            # 2. Paginate ArXiv API across AI / ML categories
            batch_size = 200
            start_index = 0
            categories = ["cat:cs.AI", "cat:cs.LG", "cat:cs.CL", "cat:cs.CV"]
            cat_query = "+OR+".join(categories)

            while len(papers) < self.target_count and start_index < 3000:
                query_url = (
                    f"https://export.arxiv.org/api/query?search_query={cat_query}"
                    f"&start={start_index}&max_results={batch_size}&sortBy=submittedDate&sortOrder=descending"
                )
                logger.info(f"Querying ArXiv batch start={start_index}, current total={len(papers)}...")

                try:
                    resp = await client.get(query_url, headers={"User-Agent": "FrontierAtlas/1.0"}, timeout=15.0)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        # Atom namespace
                        ns = {"atom": "http://www.w3.org/2005/Atom"}
                        entries = root.findall("atom:entry", ns)

                        if not entries:
                            logger.info("No more entries returned by ArXiv.")
                            break

                        for entry in entries:
                            id_elem = entry.find("atom:id", ns)
                            title_elem = entry.find("atom:title", ns)
                            summary_elem = entry.find("atom:summary", ns)
                            published_elem = entry.find("atom:published", ns)
                            author_elems = entry.findall("atom:author", ns)

                            raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                            paper_url = raw_id.replace("http://", "https://")
                            if not paper_url or paper_url in seen_urls:
                                continue

                            title = re.sub(r"\s+", " ", title_elem.text.strip()) if title_elem is not None and title_elem.text else "Untitled Paper"
                            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
                            pub_date = normalize_to_iso(published_elem.text) if published_elem is not None else datetime.now(timezone.utc).isoformat()
                            authors = [
                                a.find("atom:name", ns).text.strip()
                                for a in author_elems
                                if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
                            ]

                            # Inspect summary for GitHub repository references
                            github_match = GITHUB_URL_REGEX.search(summary)
                            github_url = None
                            github_stars = None
                            if github_match:
                                github_url = github_match.group(0).rstrip(".,)")
                                github_stars = await self._fetch_github_stars(client, github_url)

                            entity = ResearchPaperEntity(
                                schemaVersion="1.0",
                                recordType="RESEARCH_PAPER",
                                source=SourceMetadata(name="ArXiv", url=paper_url),
                                content=ResearchPaperContent(
                                    title=title,
                                    authors=authors,
                                    paper_url=paper_url,
                                    github_url=github_url,
                                    github_stars=github_stars,
                                    published_date=pub_date or datetime.now(timezone.utc).isoformat(),
                                ),
                            )
                            papers.append(entity)
                            seen_urls.add(paper_url)

                            if len(papers) >= self.target_count:
                                break

                        start_index += batch_size
                        # Respect ArXiv etiquette
                        await asyncio.sleep(1.2)
                    elif resp.status_code == 429:
                        logger.warning("ArXiv 429 rate limit. Backing off 5 seconds...")
                        await asyncio.sleep(5.0)
                    else:
                        logger.warning(f"ArXiv query failed with HTTP {resp.status_code}")
                        break
                except Exception as e:
                    logger.error(f"Error querying ArXiv: {e}")
                    await asyncio.sleep(2.0)
                    start_index += batch_size

        logger.info(f"Research Paper Scrape Completed. Acquired {len(papers)} legitimate records.")
        return papers[: self.target_count]
