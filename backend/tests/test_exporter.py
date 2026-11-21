"""Unit tests for Exporter Service and Multi-Tab Excel Generation."""

import os
import tempfile
import pandas as pd
from app.services.exporter import DataExporter
from app.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
    PricingModelEnum,
    SourceMetadata,
    StartupContent,
    StartupContentData,
    ProductContent,
    ResearchPaperContent,
    JobContent,
    NewsContent,
)


def test_exporter_generates_all_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = DataExporter(export_dir=tmp_dir)

        startups = [
            StartupEntity(
                source=SourceMetadata(name="YC", url="https://ycombinator.com/companies/openai"),
                content=StartupContent(
                    entityName="OpenAI",
                    data=StartupContentData(employeeCount=1500),
                ),
            )
        ]
        products = [
            ProductEntity(
                source=SourceMetadata(name="Web", url="https://openai.com/chatgpt"),
                content=ProductContent(
                    startupName="OpenAI",
                    pricingModel=PricingModelEnum.FREEMIUM,
                    productName="ChatGPT Plus",
                ),
            )
        ]
        papers = [
            ResearchPaperEntity(
                source=SourceMetadata(name="ArXiv", url="https://arxiv.org/abs/1706.03762"),
                content=ResearchPaperContent(
                    title="Attention Is All You Need",
                    authors=["A. Vaswani"],
                    paper_url="https://arxiv.org/abs/1706.03762",
                    github_url="https://github.com/tensorflow/tensor2tensor",
                    github_stars=15000,
                    published_date="2017-06-12T00:00:00Z",
                ),
            )
        ]
        jobs = [
            JobEntity(
                source=SourceMetadata(name="RemoteOK", url="https://remoteok.com/l/1"),
                content=JobContent(
                    company="OpenAI",
                    title="Research Engineer",
                    date="2026-11-21T10:00:00Z",
                    is_remote=False,
                    role_family="Engineering",
                ),
            )
        ]
        news = [
            NewsEntity(
                source=SourceMetadata(name="TechReview", url="https://technologyreview.com/1"),
                content=NewsContent(
                    title="New AI Frontier",
                    summary="Summary text",
                    published_date="2026-11-21T09:00:00Z",
                ),
            )
        ]
        logs = [
            EntityMappingLog(
                raw_name="Open AI, Inc.",
                canonical_name="OpenAI",
                entity_type="STARTUP",
                resolution_method="LEGAL_SUFFIX_NORMALIZATION",
                confidence_score=0.98,
            )
        ]

        # Export CSVs
        p1 = exporter.export_startups(startups)
        p2 = exporter.export_products(products)
        p3 = exporter.export_research_papers(papers)
        p4 = exporter.export_jobs(jobs)
        p5 = exporter.export_news(news)
        p6 = exporter.export_entity_mapping_log(logs)

        assert os.path.exists(p1)
        assert os.path.exists(p2)
        assert os.path.exists(p3)
        assert os.path.exists(p4)
        assert os.path.exists(p5)
        assert os.path.exists(p6)

        # Export Master Excel Workbook
        excel_path = exporter.export_master_workbook(
            startups=startups,
            products=products,
            papers=papers,
            jobs=jobs,
            news=news,
            mapping_logs=logs,
        )
        assert os.path.exists(excel_path)

        # Verify sheets
        with pd.ExcelFile(excel_path) as xl:
            expected_sheets = ["Startups", "Products", "Research Papers", "Jobs", "News", "Entity Mapping Log"]
            for s in expected_sheets:
                assert s in xl.sheet_names
