"""Unit tests for Canonical Pydantic Schemas."""

import pytest
from pydantic import ValidationError
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


def test_startup_entity_valid():
    entity = StartupEntity(
        schemaVersion="1.0",
        recordType="STARTUP",
        source=SourceMetadata(name="YC", url="https://ycombinator.com/companies/openai"),
        content=StartupContent(
            entityName="OpenAI",
            data=StartupContentData(employeeCount=1500),
        ),
    )
    assert entity.recordType == "STARTUP"
    assert entity.content.entityName == "OpenAI"
    assert entity.content.data.employeeCount == 1500
    assert entity.collectedAt is not None


def test_startup_entity_invalid_url():
    with pytest.raises(ValidationError):
        StartupEntity(
            source=SourceMetadata(name="Bad", url="not_a_valid_url"),
            content=StartupContent(entityName="Test"),
        )


def test_product_entity_pricing_enum():
    entity = ProductEntity(
        source=SourceMetadata(name="Site", url="https://example.com"),
        content=ProductContent(
            startupName="Anthropic",
            pricingModel=PricingModelEnum.FREEMIUM,
            productName="Claude 3.5 Sonnet",
        ),
    )
    assert entity.content.pricingModel == PricingModelEnum.FREEMIUM

    with pytest.raises(ValidationError):
        ProductEntity(
            source=SourceMetadata(name="Site", url="https://example.com"),
            content=ProductContent(
                startupName="Anthropic",
                pricingModel="INVALID_TIER",  # type: ignore
            ),
        )


def test_research_paper_entity():
    entity = ResearchPaperEntity(
        source=SourceMetadata(name="ArXiv", url="https://arxiv.org/abs/1706.03762"),
        content=ResearchPaperContent(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            paper_url="https://arxiv.org/abs/1706.03762",
            github_url="https://github.com/tensorflow/tensor2tensor",
            github_stars=15000,
            published_date="2017-06-12T00:00:00Z",
        ),
    )
    assert entity.recordType == "RESEARCH_PAPER"
    assert len(entity.content.authors) == 2
    assert entity.content.github_stars == 15000


def test_job_entity():
    entity = JobEntity(
        source=SourceMetadata(name="RemoteOK", url="https://remoteok.com/l/123"),
        content=JobContent(
            company="Perplexity",
            title="AI Systems Engineer",
            date="2026-11-21T10:00:00Z",
            is_remote=True,
            role_family="Engineering",
        ),
    )
    assert entity.content.is_remote is True
    assert entity.content.role_family == "Engineering"


def test_news_entity():
    entity = NewsEntity(
        source=SourceMetadata(name="MIT Tech Review", url="https://technologyreview.com/story/1"),
        content=NewsContent(
            title="Next-Gen AI Systems Launch",
            summary="New breakthrough in reasoning models.",
            published_date="2026-11-21T08:00:00Z",
        ),
    )
    assert entity.recordType == "NEWS"
    assert entity.content.title.startswith("Next-Gen")


def test_entity_mapping_log():
    log = EntityMappingLog(
        raw_name="Open AI, Inc.",
        canonical_name="OpenAI",
        entity_type="STARTUP",
        resolution_method="LEGAL_SUFFIX_NORMALIZATION",
        confidence_score=0.98,
    )
    assert log.raw_name == "Open AI, Inc."
    assert log.canonical_name == "OpenAI"
    assert log.confidence_score == 0.98
