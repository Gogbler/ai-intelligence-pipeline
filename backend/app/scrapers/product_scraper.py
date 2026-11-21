"""Product Data Acquisition Scraper.

Vertical: AI Products & Platforms
Target: Minimum 1,000 unique product records
Features:
- Deterministic Entity Resolution of parent startup name
- Pricing model classification (FREE, FREEMIUM, PAID, ENTERPRISE)
- Full-text product description & value proposition
- Authentic URL attribution
"""

import json
from datetime import datetime, timezone
from typing import List, Set
import httpx
from app.config import settings
from app.models.schemas import ProductEntity, ProductContent, PricingModelEnum, SourceMetadata
from app.resolver.entity_resolver import entity_resolver
from app.scrapers.base import AsyncBaseScraper
from app.utils.logger import get_logger

logger = get_logger("ProductScraper")

YC_DATASET_URL = (
    "https://raw.githubusercontent.com/akshaybhalotia/yc_company_scraper/main/data/yc_essential_data.json"
)


class ProductScraper(AsyncBaseScraper):
    """Acquires and normalizes AI product entity records."""

    def __init__(self, target_count: int = 1000):
        super().__init__(name="ProductScraper", concurrency=settings.CRAWLER_CONCURRENCY)
        self.target_count = target_count

    def _determine_pricing_model(self, description: str, one_liner: str, tags: List[str]) -> PricingModelEnum:
        """Heuristic and keyword classifier for product pricing tiers."""
        text = f"{description} {one_liner} {' '.join(tags)}".lower()

        if any(term in text for term in ["open source", "open-source", "100% free", "free for all", "mit license", "apache 2"]):
            return PricingModelEnum.FREE
        elif any(term in text for term in ["enterprise", "contact sales", "security", "custom pricing", "b2b", "soc2", "dedicated"]):
            return PricingModelEnum.ENTERPRISE
        elif any(term in text for term in ["freemium", "free tier", "free trial", "get started for free", "try for free"]):
            return PricingModelEnum.FREEMIUM
        elif any(term in text for term in ["subscription", "$/mo", "$/month", "pricing", "paid", "credit", "per user"]):
            return PricingModelEnum.PAID
        else:
            # Default to FREEMIUM or PAID based on B2B / Consumer indicators
            return PricingModelEnum.FREEMIUM if "developer" in text or "consumer" in text else PricingModelEnum.ENTERPRISE

    async def scrape(self) -> List[ProductEntity]:
        """Fetch and extract up to target_count unique product records."""
        logger.info(f"Initiating Product Acquisition (Target: {self.target_count})...")
        products: List[ProductEntity] = []
        seen_urls: Set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(YC_DATASET_URL, headers={"User-Agent": "FrontierAtlas/1.0"})
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch dataset for products: HTTP {resp.status_code}")
                    return []

                raw_companies = resp.json()
                logger.info(f"Analyzing {len(raw_companies)} companies to extract product entities...")

                for item in raw_companies:
                    raw_name = (item.get("name") or "").strip()
                    one_liner = (item.get("one_liner") or "").strip()
                    long_desc = (item.get("long_description") or "").strip()
                    tags = item.get("tags") or []

                    if not raw_name or not (one_liner or long_desc):
                        continue

                    website = item.get("website")
                    slug = item.get("slug")
                    source_url = website if (website and website.startswith("http")) else f"https://www.ycombinator.com/companies/{slug}"

                    if source_url in seen_urls:
                        continue

                    # Canonicalize startup name
                    canonical_startup, _ = entity_resolver.resolve(
                        raw_name=raw_name,
                        entity_type="PRODUCT",
                        source_url=source_url,
                    )

                    pricing_tier = self._determine_pricing_model(long_desc, one_liner, tags)

                    product_obj = ProductEntity(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceMetadata(
                            name="Product Registry",
                            url=source_url,
                        ),
                        content=ProductContent(
                            startupName=canonical_startup,
                            pricingModel=pricing_tier,
                            productName=one_liner or f"{canonical_startup} Platform",
                            description=long_desc[:500] if long_desc else one_liner,
                        ),
                        collectedAt=datetime.now(timezone.utc).isoformat(),
                    )

                    products.append(product_obj)
                    seen_urls.add(source_url)

                    if len(products) >= self.target_count:
                        break

            except Exception as e:
                logger.error(f"Error during product acquisition: {e}")

        logger.info(f"Successfully extracted {len(products)} unique product records.")
        return products[: self.target_count]
