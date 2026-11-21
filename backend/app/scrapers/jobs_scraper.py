"""AI Job Boards Signal Ingestion Scraper.

Monitors 5 distinct AI job sources:
1. RemoteOK API
2. WeWorkRemotely RSS
3. Hacker News Jobs Feed
4. Remotive API
5. Jobicy API

The Freshness Challenge:
- Strict 24-hour freshness guarantee (filters out listings older than 24h)
- Canonical company resolution using EntityResolver
- Role family taxonomy categorization (Engineering, Research, Data, Product)
- Remote eligibility detection
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
import httpx
from bs4 import BeautifulSoup
from app.config import settings
from app.models.schemas import JobEntity, JobContent, SourceMetadata
from app.resolver.entity_resolver import entity_resolver
from app.scrapers.base import AsyncBaseScraper
from app.utils.date_parser import normalize_to_iso, is_within_24_hours
from app.utils.logger import get_logger

logger = get_logger("JobsScraper")


class JobsScraper(AsyncBaseScraper):
    """Monitors 5 AI job boards and ingests 24-hour fresh openings."""

    def __init__(self, enforce_24h_freshness: bool = True):
        super().__init__(name="JobsScraper", concurrency=5)
        self.enforce_freshness = enforce_24h_freshness

    def _classify_role_family(self, title: str, description: str = "") -> str:
        """Classify job title into functional role families."""
        text = f"{title} {description}".lower()
        if any(w in text for w in ["research", "scientist", "phd", "alignment", "postdoc"]):
            return "Research"
        elif any(w in text for w in ["data engineer", "analytics", "etl", "sql", "pipeline", "bi"]):
            return "Data"
        elif any(w in text for w in ["product manager", "pm", "product lead", "growth"]):
            return "Product"
        elif any(w in text for w in ["designer", "ui/ux", "frontend", "visual"]):
            return "Design"
        else:
            return "Engineering"

    async def _scrape_remoteok(self, client: httpx.AsyncClient) -> List[JobEntity]:
        """Fetch fresh jobs from RemoteOK API."""
        items: List[JobEntity] = []
        try:
            resp = await client.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                for job in data[1:]:  # Skip legal header item
                    raw_date = job.get("date")
                    iso_date = normalize_to_iso(raw_date)
                    if self.enforce_freshness and not is_within_24_hours(iso_date):
                        continue

                    raw_company = job.get("company", "Tech Co")
                    canonical_company, _ = entity_resolver.resolve(raw_company, entity_type="STARTUP")
                    title = job.get("position", "Software Engineer")
                    url = job.get("url") or f"https://remoteok.com/l/{job.get('id')}"

                    items.append(
                        JobEntity(
                            schemaVersion="1.0",
                            recordType="JOB",
                            source=SourceMetadata(name="RemoteOK", url=url),
                            content=JobContent(
                                company=canonical_company,
                                title=title,
                                date=iso_date or datetime.now(timezone.utc).isoformat(),
                                is_remote=True,
                                role_family=self._classify_role_family(title, job.get("description", "")),
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except Exception as e:
            logger.warning(f"RemoteOK scraper error: {e}")
        return items

    async def _scrape_weworkremotely(self, client: httpx.AsyncClient) -> List[JobEntity]:
        """Fetch fresh jobs from WeWorkRemotely RSS."""
        items: List[JobEntity] = []
        try:
            url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    raw_date = item.findtext("pubDate")
                    iso_date = normalize_to_iso(raw_date)
                    if self.enforce_freshness and not is_within_24_hours(iso_date):
                        continue

                    full_title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    # Usually "Company: Job Title"
                    parts = full_title.split(":", 1)
                    raw_company = parts[0].strip() if len(parts) > 1 else "Tech Startup"
                    job_title = parts[1].strip() if len(parts) > 1 else full_title

                    canonical_company, _ = entity_resolver.resolve(raw_company, entity_type="STARTUP")

                    items.append(
                        JobEntity(
                            schemaVersion="1.0",
                            recordType="JOB",
                            source=SourceMetadata(name="WeWorkRemotely", url=link),
                            content=JobContent(
                                company=canonical_company,
                                title=job_title,
                                date=iso_date or datetime.now(timezone.utc).isoformat(),
                                is_remote=True,
                                role_family=self._classify_role_family(job_title),
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except Exception as e:
            logger.warning(f"WeWorkRemotely scraper error: {e}")
        return items

    async def _scrape_hn_jobs(self, client: httpx.AsyncClient) -> List[JobEntity]:
        """Fetch fresh jobs from Hacker News Jobs Feed."""
        items: List[JobEntity] = []
        try:
            url = "https://hnrss.org/jobs"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    raw_date = item.findtext("pubDate")
                    iso_date = normalize_to_iso(raw_date)
                    if self.enforce_freshness and not is_within_24_hours(iso_date):
                        continue

                    title = item.findtext("title", "")
                    link = item.findtext("link", "")

                    # HN titles: "Company (Location) is hiring a Role"
                    raw_company = title.split(" is hiring")[0].split("(")[0].strip() if " is hiring" in title else "HN AI Startup"
                    canonical_company, _ = entity_resolver.resolve(raw_company, entity_type="STARTUP")

                    items.append(
                        JobEntity(
                            schemaVersion="1.0",
                            recordType="JOB",
                            source=SourceMetadata(name="Hacker News Jobs", url=link),
                            content=JobContent(
                                company=canonical_company,
                                title=title,
                                date=iso_date or datetime.now(timezone.utc).isoformat(),
                                is_remote="remote" in title.lower(),
                                role_family=self._classify_role_family(title),
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except Exception as e:
            logger.warning(f"Hacker News jobs error: {e}")
        return items

    async def _scrape_remotive(self, client: httpx.AsyncClient) -> List[JobEntity]:
        """Fetch fresh jobs from Remotive API."""
        items: List[JobEntity] = []
        try:
            url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=50"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json().get("jobs", [])
                for job in data:
                    raw_date = job.get("publication_date")
                    iso_date = normalize_to_iso(raw_date)
                    if self.enforce_freshness and not is_within_24_hours(iso_date):
                        continue

                    raw_company = job.get("company_name", "Tech Startup")
                    canonical_company, _ = entity_resolver.resolve(raw_company, entity_type="STARTUP")
                    title = job.get("title", "Engineer")
                    link = job.get("url", "")

                    items.append(
                        JobEntity(
                            schemaVersion="1.0",
                            recordType="JOB",
                            source=SourceMetadata(name="Remotive", url=link),
                            content=JobContent(
                                company=canonical_company,
                                title=title,
                                date=iso_date or datetime.now(timezone.utc).isoformat(),
                                is_remote=True,
                                role_family=self._classify_role_family(title),
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except Exception as e:
            logger.warning(f"Remotive jobs error: {e}")
        return items

    async def _scrape_jobicy(self, client: httpx.AsyncClient) -> List[JobEntity]:
        """Fetch fresh jobs from Jobicy API."""
        items: List[JobEntity] = []
        try:
            url = "https://jobicy.com/api/v2/remote-jobs?count=50"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json().get("jobs", [])
                for job in data:
                    raw_date = job.get("pubDate")
                    iso_date = normalize_to_iso(raw_date)
                    if self.enforce_freshness and not is_within_24_hours(iso_date):
                        continue

                    raw_company = job.get("companyName", "AI Venture")
                    canonical_company, _ = entity_resolver.resolve(raw_company, entity_type="STARTUP")
                    title = job.get("jobTitle", "Engineer")
                    link = job.get("url", "")

                    items.append(
                        JobEntity(
                            schemaVersion="1.0",
                            recordType="JOB",
                            source=SourceMetadata(name="Jobicy", url=link),
                            content=JobContent(
                                company=canonical_company,
                                title=title,
                                date=iso_date or datetime.now(timezone.utc).isoformat(),
                                is_remote=True,
                                role_family=self._classify_role_family(title),
                            ),
                            collectedAt=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except Exception as e:
            logger.warning(f"Jobicy jobs error: {e}")
        return items

    async def scrape(self) -> List[JobEntity]:
        """Scrape jobs across all 5 job boards and filter strictly for 24h freshness."""
        logger.info("Starting Job Signal Ingestion across 5 distinct job boards...")
        all_jobs: List[JobEntity] = []
        seen_urls: Set[str] = set()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            results = await asyncio.gather(
                self._scrape_remoteok(client),
                self._scrape_weworkremotely(client),
                self._scrape_hn_jobs(client),
                self._scrape_remotive(client),
                self._scrape_jobicy(client),
                return_exceptions=True,
            )

            for res in results:
                if isinstance(res, list):
                    for job in res:
                        url = job.source.url if job.source else ""
                        if url and url not in seen_urls:
                            all_jobs.append(job)
                            seen_urls.add(url)

        logger.info(f"Total 24-hour fresh jobs collected across 5 boards: {len(all_jobs)}")
        return all_jobs
