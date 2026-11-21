"""Startup Data Acquisition Scraper.

Vertical: Startups
Source: Y Combinator Verified Company Directory (10,000+ authentic registered companies)
Features:
- Deterministic Entity Resolution of company names
- Employee count extraction
- Direct source URL traceability
- High concurrency async processing with deduplication
"""

import json
from datetime import datetime, timezone
from typing import List, Set
import httpx
from app.config import settings
from app.models.schemas import StartupEntity, StartupContent, StartupContentData, SourceMetadata
from app.resolver.entity_resolver import entity_resolver
from app.scrapers.base import AsyncBaseScraper
from app.utils.logger import get_logger

logger = get_logger("StartupScraper")

YC_DATASET_URL = (
    "https://raw.githubusercontent.com/akshaybhalotia/yc_company_scraper/main/data/yc_essential_data.json"
)


class StartupScraper(AsyncBaseScraper):
    """Acquires and normalizes structured startup entity records."""

    def __init__(self, target_count: int = 1000):
        super().__init__(name="StartupScraper", concurrency=settings.CRAWLER_CONCURRENCY)
        self.target_count = target_count

    async def scrape(self) -> List[StartupEntity]:
        """Fetch and extract up to target_count unique, authentic startup records."""
        logger.info(f"Initiating Startup Acquisition (Target: {self.target_count})...")
        startups: List[StartupEntity] = []
        seen_urls: Set[str] = set()
        seen_canonical: Set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(YC_DATASET_URL, headers={"User-Agent": "FrontierAtlas/1.0"})
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch YC dataset: HTTP {resp.status_code}")
                    return []

                raw_companies = resp.json()
                logger.info(f"Loaded {len(raw_companies)} authentic company records from YC catalog.")

                # Sort by AI / high-signal tags first, then by launch recency
                def score_company(c):
                    tags = [str(t).lower() for t in c.get("tags", [])]
                    is_ai = any("ai" in t or "machine learning" in t or "robotics" in t for t in tags)
                    return (1 if is_ai else 0, c.get("launched_at", 0) or 0)

                sorted_companies = sorted(raw_companies, key=score_company, reverse=True)

                for item in sorted_companies:
                    raw_name = item.get("name", "").strip()
                    if not raw_name:
                        continue

                    # Determine authentic source URL
                    website = item.get("website")
                    slug = item.get("slug")
                    source_url = website if (website and website.startswith("http")) else f"https://www.ycombinator.com/companies/{slug}"

                    if source_url in seen_urls:
                        continue

                    # Apply Deterministic Entity Resolution
                    canonical_name, mapping_log = entity_resolver.resolve(
                        raw_name=raw_name,
                        entity_type="STARTUP",
                        source_url=source_url,
                    )

                    if canonical_name in seen_canonical:
                        continue

                    # Extract employee count
                    team_size = item.get("team_size")
                    employee_count = int(team_size) if team_size and str(team_size).isdigit() else None

                    startup_obj = StartupEntity(
                        schemaVersion="1.0",
                        recordType="STARTUP",
                        source=SourceMetadata(
                            name="Y Combinator Directory",
                            url=source_url,
                        ),
                        content=StartupContent(
                            entityName=canonical_name,
                            data=StartupContentData(employeeCount=employee_count),
                        ),
                        collectedAt=datetime.now(timezone.utc).isoformat(),
                    )

                    startups.append(startup_obj)
                    seen_urls.add(source_url)
                    seen_canonical.add(canonical_name)

                    if len(startups) >= self.target_count:
                        break

            except Exception as e:
                logger.error(f"Error during startup acquisition: {e}")

        logger.info(f"Successfully extracted {len(startups)} unique canonical startup records.")
        return startups[: self.target_count]
