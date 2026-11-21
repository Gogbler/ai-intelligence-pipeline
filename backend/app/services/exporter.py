"""Export Service for FrontierAtlas Intelligence Pipeline.

Generates:
1. Six individual CSV files for direct Google Sheets / database ingestion:
   - startups_min1000.csv
   - products_min1000.csv
   - research_papers_min1000.csv
   - jobs_24h_fresh.csv
   - news_24h_fresh.csv
   - entity_mapping_log.csv
2. Multi-Tab Excel Workbook (frontieratlas_intelligence_graph.xlsx) containing all 6 tabs.
3. Clean summary metrics for logging & dashboard display.
"""

import os
import json
from typing import List, Dict, Any
import pandas as pd
from app.config import settings
from app.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
)
from app.utils.logger import get_logger

logger = get_logger("Exporter")


class DataExporter:
    """Exports structured canonical entities to CSVs and multi-tab Excel."""

    def __init__(self, export_dir: str = settings.DATA_EXPORT_DIR):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export_startups(self, startups: List[StartupEntity]) -> str:
        """Export Startups tab."""
        records = []
        for s in startups:
            records.append({
                "schemaVersion": s.schemaVersion,
                "recordType": s.recordType,
                "source.name": s.source.name,
                "source.url": s.source.url,
                "content.entityName": s.content.entityName,
                "content.data.employeeCount": s.content.data.employeeCount,
                "collectedAt": s.collectedAt,
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "startups_min1000.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} startups to {path}")
        return path

    def export_products(self, products: List[ProductEntity]) -> str:
        """Export Products tab."""
        records = []
        for p in products:
            records.append({
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "source.name": p.source.name,
                "source.url": p.source.url,
                "content.startupName": p.content.startupName,
                "content.pricingModel": p.content.pricingModel.value if hasattr(p.content.pricingModel, "value") else str(p.content.pricingModel),
                "content.productName": p.content.productName,
                "content.description": p.content.description,
                "collectedAt": p.collectedAt,
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "products_min1000.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} products to {path}")
        return path

    def export_research_papers(self, papers: List[ResearchPaperEntity]) -> str:
        """Export Research Papers tab."""
        records = []
        for r in papers:
            records.append({
                "schemaVersion": r.schemaVersion,
                "recordType": r.recordType,
                "content.title": r.content.title,
                "content.authors": ", ".join(r.content.authors) if isinstance(r.content.authors, list) else str(r.content.authors),
                "content.paper_url": r.content.paper_url,
                "content.github_url": r.content.github_url or "",
                "content.github_stars": r.content.github_stars if r.content.github_stars is not None else "",
                "content.published_date": r.content.published_date,
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "research_papers_min1000.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} research papers to {path}")
        return path

    def export_jobs(self, jobs: List[JobEntity]) -> str:
        """Export Jobs tab."""
        records = []
        for j in jobs:
            records.append({
                "schemaVersion": j.schemaVersion,
                "recordType": j.recordType,
                "content.company": j.content.company,
                "content.date": j.content.date,
                "content.is_remote": j.content.is_remote,
                "content.role_family": j.content.role_family,
                "source.name": j.source.name if j.source else "",
                "source.url": j.source.url if j.source else "",
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "jobs_24h_fresh.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} jobs to {path}")
        return path

    def export_news(self, news: List[NewsEntity]) -> str:
        """Export News tab."""
        records = []
        for n in news:
            records.append({
                "schemaVersion": n.schemaVersion,
                "recordType": n.recordType,
                "source.name": n.source.name,
                "source.url": n.source.url,
                "content.title": n.content.title,
                "content.summary": n.content.summary,
                "content.published_date": n.content.published_date,
                "collectedAt": n.collectedAt,
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "news_24h_fresh.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} news items to {path}")
        return path

    def export_entity_mapping_log(self, logs: List[EntityMappingLog]) -> str:
        """Export Entity Mapping Log tab."""
        records = []
        for l in logs:
            records.append({
                "raw_name": l.raw_name,
                "canonical_name": l.canonical_name,
                "entity_type": l.entity_type,
                "resolution_method": l.resolution_method,
                "confidence_score": l.confidence_score,
                "timestamp": l.timestamp,
            })
        df = pd.DataFrame(records)
        path = os.path.join(self.export_dir, "entity_mapping_log.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} entity mapping logs to {path}")
        return path

    def export_master_workbook(
        self,
        startups: List[StartupEntity],
        products: List[ProductEntity],
        papers: List[ResearchPaperEntity],
        jobs: List[JobEntity],
        news: List[NewsEntity],
        mapping_logs: List[EntityMappingLog],
    ) -> str:
        """Create a single unified Excel spreadsheet with 6 distinct tabs matching Google Sheets."""
        excel_path = os.path.join(self.export_dir, "frontieratlas_intelligence_graph.xlsx")

        # Startups DF
        df_startups = pd.DataFrame([
            {
                "schemaVersion": s.schemaVersion,
                "recordType": s.recordType,
                "source.name": s.source.name,
                "source.url": s.source.url,
                "content.entityName": s.content.entityName,
                "content.data.employeeCount": s.content.data.employeeCount,
                "collectedAt": s.collectedAt,
            }
            for s in startups
        ])

        # Products DF
        df_products = pd.DataFrame([
            {
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "source.name": p.source.name,
                "source.url": p.source.url,
                "content.startupName": p.content.startupName,
                "content.pricingModel": p.content.pricingModel.value if hasattr(p.content.pricingModel, "value") else str(p.content.pricingModel),
                "content.productName": p.content.productName,
                "content.description": p.content.description,
                "collectedAt": p.collectedAt,
            }
            for p in products
        ])

        # Papers DF
        df_papers = pd.DataFrame([
            {
                "schemaVersion": r.schemaVersion,
                "recordType": r.recordType,
                "content.title": r.content.title,
                "content.authors": ", ".join(r.content.authors) if isinstance(r.content.authors, list) else str(r.content.authors),
                "content.paper_url": r.content.paper_url,
                "content.github_url": r.content.github_url or "",
                "content.github_stars": r.content.github_stars if r.content.github_stars is not None else "",
                "content.published_date": r.content.published_date,
            }
            for r in papers
        ])

        # Jobs DF
        df_jobs = pd.DataFrame([
            {
                "schemaVersion": j.schemaVersion,
                "recordType": j.recordType,
                "content.company": j.content.company,
                "content.date": j.content.date,
                "content.is_remote": j.content.is_remote,
                "content.role_family": j.content.role_family,
                "source.name": j.source.name if j.source else "",
                "source.url": j.source.url if j.source else "",
            }
            for j in jobs
        ])

        # News DF
        df_news = pd.DataFrame([
            {
                "schemaVersion": n.schemaVersion,
                "recordType": n.recordType,
                "source.name": n.source.name,
                "source.url": n.source.url,
                "content.title": n.content.title,
                "content.summary": n.content.summary,
                "content.published_date": n.content.published_date,
                "collectedAt": n.collectedAt,
            }
            for n in news
        ])

        # Mapping Log DF
        df_mapping = pd.DataFrame([
            {
                "raw_name": l.raw_name,
                "canonical_name": l.canonical_name,
                "entity_type": l.entity_type,
                "resolution_method": l.resolution_method,
                "confidence_score": l.confidence_score,
                "timestamp": l.timestamp,
            }
            for l in mapping_logs
        ])

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_startups.to_excel(writer, sheet_name="Startups", index=False)
            df_products.to_excel(writer, sheet_name="Products", index=False)
            df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
            df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
            df_news.to_excel(writer, sheet_name="News", index=False)
            df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)

        logger.info(f"Master 6-Tab Workbook successfully generated at: {excel_path}")
        return excel_path


exporter = DataExporter()
