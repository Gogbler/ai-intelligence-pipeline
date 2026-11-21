"""SQLAlchemy ORM Models for FrontierAtlas Intelligence Graph.

Stores:
- Startups
- Products
- Research Papers
- Jobs
- News
- Entity Mapping Logs
- Pipeline Execution Logs
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StartupDB(Base):
    __tablename__ = "startups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(String(10), default="1.0")
    record_type = Column(String(50), default="STARTUP")
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=False, unique=True, index=True)
    entity_name = Column(String(255), nullable=False, index=True)
    raw_name = Column(String(255), nullable=True)
    employee_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_startup_entity_name", "entity_name"),
    )


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(String(10), default="1.0")
    record_type = Column(String(50), default="PRODUCT")
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=False, unique=True, index=True)
    startup_name = Column(String(255), nullable=False, index=True)
    product_name = Column(String(255), nullable=True)
    pricing_model = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_product_startup_name", "startup_name"),
    )


class ResearchPaperDB(Base):
    __tablename__ = "research_papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(String(10), default="1.0")
    record_type = Column(String(50), default="RESEARCH_PAPER")
    title = Column(String(512), nullable=False, index=True)
    authors_json = Column(JSON, nullable=False)
    paper_url = Column(String(1024), nullable=False, unique=True, index=True)
    github_url = Column(String(1024), nullable=True, index=True)
    github_stars = Column(Integer, nullable=True)
    published_date = Column(DateTime, nullable=False, index=True)
    source_name = Column(String(255), default="ArXiv / Papers with Code")
    metadata_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(String(10), default="1.0")
    record_type = Column(String(50), default="JOB")
    company = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    source_name = Column(String(255), nullable=True)
    source_url = Column(String(1024), nullable=True, unique=True, index=True)
    published_date = Column(DateTime, nullable=False, index=True)
    is_remote = Column(Boolean, default=False)
    role_family = Column(String(100), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class NewsDB(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(String(10), default="1.0")
    record_type = Column(String(50), default="NEWS")
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False)
    summary = Column(Text, nullable=False)
    full_text = Column(Text, nullable=True)
    published_date = Column(DateTime, nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class EntityMappingLogDB(Base):
    __tablename__ = "entity_mapping_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_name = Column(String(255), nullable=False, index=True)
    canonical_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), default="STARTUP")
    resolution_method = Column(String(100), nullable=False)
    confidence_score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class PipelineExecutionLogDB(Base):
    __tablename__ = "pipeline_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # RUNNING, SUCCESS, FAILED
    records_acquired = Column(Integer, default=0)
    records_saved = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
