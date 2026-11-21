"""Main Pipeline Orchestrator for FrontierAtlas Intelligence Ingestion.

Coordinates:
1. Research Papers Vertical Scrape (Target: 1,000 papers + live GitHub stars)
2. Startups Vertical Scrape (Target: 1,000 unique records)
3. Products Vertical Scrape (Target: 1,000 unique records)
4. AI News Ingestion (5 distinct sources, 24h freshness filter)
5. AI Jobs Ingestion (5 distinct sources, 24h freshness filter)
6. Entity Resolution Audit Trail
7. Database Persistence & 6-Tab CSV/Excel Generation
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from app.database.session import SessionLocal, init_db
from app.models.db_models import (
    StartupDB,
    ProductDB,
    ResearchPaperDB,
    JobDB,
    NewsDB,
    EntityMappingLogDB,
    PipelineExecutionLogDB,
)
from app.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
)
from app.resolver.entity_resolver import entity_resolver
from app.scrapers.research_scraper import ResearchPaperScraper
from app.scrapers.startup_scraper import StartupScraper
from app.scrapers.product_scraper import ProductScraper
from app.scrapers.news_scraper import NewsScraper
from app.scrapers.jobs_scraper import JobsScraper
from app.services.exporter import exporter
from app.utils.logger import get_logger

logger = get_logger("PipelineRunner")


class PipelineRunner:
    """Manages the full lifecycle of data acquisition, enrichment, resolution, and storage."""

    def __init__(self):
        init_db()

    def _persist_to_database(
        self,
        db: Session,
        startups: List[StartupEntity],
        products: List[ProductEntity],
        papers: List[ResearchPaperEntity],
        jobs: List[JobEntity],
        news: List[NewsEntity],
        mapping_logs: List[EntityMappingLog],
    ):
        """Batch insert records into the database with deduplication."""
        logger.info("Persisting ingested entities to primary database...")

        # 1. Startups
        for s in startups:
            existing = db.query(StartupDB).filter(StartupDB.source_url == s.source.url).first()
            if not existing:
                db.add(
                    StartupDB(
                        schema_version=s.schemaVersion,
                        record_type=s.recordType,
                        source_name=s.source.name,
                        source_url=s.source.url,
                        entity_name=s.content.entityName,
                        employee_count=s.content.data.employeeCount,
                    )
                )

        # 2. Products
        for p in products:
            existing = db.query(ProductDB).filter(ProductDB.source_url == p.source.url).first()
            if not existing:
                db.add(
                    ProductDB(
                        schema_version=p.schemaVersion,
                        record_type=p.recordType,
                        source_name=p.source.name,
                        source_url=p.source.url,
                        startup_name=p.content.startupName,
                        product_name=p.content.productName,
                        pricing_model=p.content.pricingModel.value if hasattr(p.content.pricingModel, "value") else str(p.content.pricingModel),
                        description=p.content.description,
                    )
                )

        # 3. Research Papers
        for r in papers:
            existing = db.query(ResearchPaperDB).filter(ResearchPaperDB.paper_url == r.content.paper_url).first()
            if not existing:
                pub_dt = datetime.fromisoformat(r.content.published_date.replace("Z", "+00:00"))
                db.add(
                    ResearchPaperDB(
                        schema_version=r.schemaVersion,
                        record_type=r.recordType,
                        title=r.content.title,
                        authors_json=r.content.authors,
                        paper_url=r.content.paper_url,
                        github_url=r.content.github_url,
                        github_stars=r.content.github_stars,
                        published_date=pub_dt,
                    )
                )

        # 4. Jobs
        for j in jobs:
            j_url = j.source.url if j.source else None
            existing = db.query(JobDB).filter(JobDB.source_url == j_url).first() if j_url else None
            if not existing:
                job_dt = datetime.fromisoformat(j.content.date.replace("Z", "+00:00"))
                db.add(
                    JobDB(
                        schema_version=j.schemaVersion,
                        record_type=j.recordType,
                        company=j.content.company,
                        title=j.content.title,
                        source_name=j.source.name if j.source else "Job Board",
                        source_url=j_url,
                        published_date=job_dt,
                        is_remote=j.content.is_remote,
                        role_family=j.content.role_family,
                    )
                )

        # 5. News
        for n in news:
            existing = db.query(NewsDB).filter(NewsDB.source_url == n.source.url).first()
            if not existing:
                news_dt = datetime.fromisoformat(n.content.published_date.replace("Z", "+00:00"))
                db.add(
                    NewsDB(
                        schema_version=n.schemaVersion,
                        record_type=n.recordType,
                        source_name=n.source.name,
                        source_url=n.source.url,
                        title=n.content.title,
                        summary=n.content.summary,
                        full_text=n.content.full_text,
                        published_date=news_dt,
                    )
                )

        # 6. Entity Mapping Logs
        for m in mapping_logs[-500:]:  # Persist recent mappings
            db.add(
                EntityMappingLogDB(
                    raw_name=m.raw_name,
                    canonical_name=m.canonical_name,
                    entity_type=m.entity_type,
                    resolution_method=m.resolution_method,
                    confidence_score=m.confidence_score,
                )
            )

        db.commit()
        logger.info("Database persistence completed successfully.")

    async def execute_full_pipeline(
        self,
        startup_target: int = 1000,
        product_target: int = 1000,
        paper_target: int = 1000,
    ) -> Dict[str, Any]:
        """Execute the end-to-end data acquisition and ingestion workflow."""
        start_time = time.time()
        logger.info("==================================================================")
        logger.info("LAUNCHING FRONTIERATLAS GLOBAL INTELLIGENCE INGESTION PIPELINE")
        logger.info("==================================================================")

        db = SessionLocal()
        exec_log = PipelineExecutionLogDB(
            pipeline_name="full_intelligence_graph_ingestion",
            status="RUNNING",
            start_time=datetime.now(timezone.utc),
        )
        db.add(exec_log)
        db.commit()

        try:
            # 1. Scrape Startups
            startup_scraper = StartupScraper(target_count=startup_target)
            startups = await startup_scraper.scrape()

            # 2. Scrape Products
            product_scraper = ProductScraper(target_count=product_target)
            products = await product_scraper.scrape()

            # 3. Scrape Research Papers
            paper_scraper = ResearchPaperScraper(target_count=paper_target)
            papers = await paper_scraper.scrape()

            # 4. Scrape News (5 sources, 24h freshness)
            news_scraper = NewsScraper(enforce_24h_freshness=True)
            news = await news_scraper.scrape()

            # 5. Scrape Jobs (5 sources, 24h freshness)
            jobs_scraper = JobsScraper(enforce_24h_freshness=True)
            jobs = await jobs_scraper.scrape()

            # 6. Fetch Entity Mapping Logs
            mapping_logs = entity_resolver.get_mapping_logs()

            # 7. Persist to Database
            self._persist_to_database(db, startups, products, papers, jobs, news, mapping_logs)

            # 8. Export to 6 CSVs + Master Excel Workbook
            csv_paths = {
                "startups": exporter.export_startups(startups),
                "products": exporter.export_products(products),
                "research_papers": exporter.export_research_papers(papers),
                "jobs": exporter.export_jobs(jobs),
                "news": exporter.export_news(news),
                "entity_mapping_log": exporter.export_entity_mapping_log(mapping_logs),
            }
            master_excel = exporter.export_master_workbook(
                startups=startups,
                products=products,
                papers=papers,
                jobs=jobs,
                news=news,
                mapping_logs=mapping_logs,
            )

            elapsed_seconds = round(time.time() - start_time, 2)
            total_records = len(startups) + len(products) + len(papers) + len(jobs) + len(news)

            # Update DB Execution Log
            exec_log.status = "SUCCESS"
            exec_log.records_acquired = total_records
            exec_log.records_saved = total_records
            exec_log.end_time = datetime.now(timezone.utc)
            db.commit()

            summary = {
                "status": "SUCCESS",
                "elapsed_seconds": elapsed_seconds,
                "counts": {
                    "startups": len(startups),
                    "products": len(products),
                    "research_papers": len(papers),
                    "jobs": len(jobs),
                    "news": len(news),
                    "entity_mappings": len(mapping_logs),
                    "total": total_records,
                },
                "exports": {
                    "csv_files": csv_paths,
                    "master_excel": master_excel,
                },
            }
            logger.info(f"Pipeline executed successfully in {elapsed_seconds}s. Total records: {total_records}")
            return summary

        except Exception as e:
            logger.error(f"Pipeline execution encountered fatal error: {e}", exc_info=True)
            exec_log.status = "FAILED"
            exec_log.error_details = str(e)
            exec_log.end_time = datetime.now(timezone.utc)
            db.commit()
            raise
        finally:
            db.close()


pipeline_runner = PipelineRunner()
