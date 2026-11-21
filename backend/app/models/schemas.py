"""Canonical Pydantic Schemas for FrontierAtlas / GraphOne AI Intelligence Pipeline.

Strictly adheres to the assessment specification:
- StartupEntity
- ProductEntity
- ResearchPaperEntity
- JobEntity
- NewsEntity
- EntityMappingLog
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMetadata(BaseModel):
    name: str = Field(..., description="Name of the source site")
    url: str = Field(..., description="Original source URL")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Source URL must be a valid http or https URL")
        return v


# -------------------------------------------------------------------------
# 1. Startup Entity
# -------------------------------------------------------------------------
class StartupContentData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees (if available)")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name")
    data: StartupContentData = Field(default_factory=StartupContentData)


class StartupEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="STARTUP", description="Fixed to STARTUP")
    source: SourceMetadata
    content: StartupContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format collection timestamp",
    )


# -------------------------------------------------------------------------
# 2. Product Entity
# -------------------------------------------------------------------------
class ProductContent(BaseModel):
    startupName: str = Field(..., description="Canonical startup name")
    pricingModel: PricingModelEnum = Field(..., description="Pricing model tier")
    productName: Optional[str] = Field(None, description="Product Name")
    description: Optional[str] = Field(None, description="Product summary")


class ProductEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="PRODUCT", description="Fixed to PRODUCT")
    source: SourceMetadata
    content: ProductContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format collection timestamp",
    )


# -------------------------------------------------------------------------
# 3. Research Paper Entity
# -------------------------------------------------------------------------
class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page")
    github_url: Optional[str] = Field(None, description="Link to associated code repository (if any)")
    github_stars: Optional[int] = Field(None, description="Current number of stars on the GitHub repository")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    source: Optional[SourceMetadata] = None
    content: ResearchPaperContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format collection timestamp",
    )


# -------------------------------------------------------------------------
# 4. Job Entity
# -------------------------------------------------------------------------
class JobContent(BaseModel):
    company: str = Field(..., description="Canonical company name")
    title: Optional[str] = Field(None, description="Job title / role")
    date: str = Field(..., description="ISO-8601 publication date")
    is_remote: bool = Field(default=False, description="Remote eligibility")
    role_family: str = Field(..., description="Functional category (e.g. Engineering, Research, Product)")


class JobEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="JOB", description="Fixed to JOB")
    source: Optional[SourceMetadata] = None
    content: JobContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format collection timestamp",
    )


# -------------------------------------------------------------------------
# 5. News Entity
# -------------------------------------------------------------------------
class NewsContent(BaseModel):
    title: str = Field(..., description="Headline of the article")
    summary: str = Field(..., description="Concise summary or lead paragraph")
    full_text: Optional[str] = Field(None, description="Cleaned full-text content")
    published_date: str = Field(..., description="ISO-8601 publication date")


class NewsEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="NEWS", description="Fixed to NEWS")
    source: SourceMetadata
    content: NewsContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format collection timestamp",
    )


# -------------------------------------------------------------------------
# 6. Entity Mapping Log Entity
# -------------------------------------------------------------------------
class EntityMappingLog(BaseModel):
    raw_name: str = Field(..., description="Raw extracted entity name")
    canonical_name: str = Field(..., description="Resolved canonical name")
    entity_type: str = Field(default="STARTUP", description="Entity type (STARTUP or PRODUCT)")
    resolution_method: str = Field(..., description="Rule or algorithm applied")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 resolution timestamp",
    )
