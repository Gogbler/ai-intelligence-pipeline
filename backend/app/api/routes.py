"""REST API Routes for FrontierAtlas Intelligence Pipeline.
"""

import os
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import settings
from app.database.session import get_db
from app.models.db_models import (
    StartupDB,
    ProductDB,
    ResearchPaperDB,
    JobDB,
    NewsDB,
    EntityMappingLogDB,
    PipelineExecutionLogDB,
)
from app.llm.orchestrator import llm_orchestrator
from app.pipelines.runner import pipeline_runner

router = APIRouter()

PIPELINE_STATE = {
    "is_running": False,
    "last_run": None,
    "last_summary": None,
}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve aggregate database counts for dashboard display."""
    startup_count = db.query(func.count(StartupDB.id)).scalar() or 0
    product_count = db.query(func.count(ProductDB.id)).scalar() or 0
    paper_count = db.query(func.count(ResearchPaperDB.id)).scalar() or 0
    job_count = db.query(func.count(JobDB.id)).scalar() or 0
    news_count = db.query(func.count(NewsDB.id)).scalar() or 0
    mapping_count = db.query(func.count(EntityMappingLogDB.id)).scalar() or 0

    return {
        "startups": startup_count,
        "products": product_count,
        "research_papers": paper_count,
        "jobs": job_count,
        "news": news_count,
        "entity_mappings": mapping_count,
        "total_records": startup_count + product_count + paper_count + job_count + news_count,
    }


@router.get("/sources")
def get_source_health() -> List[Dict[str, Any]]:
    """Return health and status of all configured signal sources."""
    return [
        {"name": "ArXiv AI/ML API", "type": "Research", "status": "ONLINE", "target": "Papers with Code & Stars"},
        {"name": "Hugging Face Daily Papers", "type": "Research", "status": "ONLINE", "target": "Code links & Repos"},
        {"name": "Y Combinator Registry", "type": "Startups & Products", "status": "ONLINE", "target": "Verified Directory"},
        {"name": "MIT Technology Review", "type": "News", "status": "ONLINE", "target": "AI Signals"},
        {"name": "Hugging Face Announcements", "type": "News", "status": "ONLINE", "target": "Open Source AI"},
        {"name": "Hacker News AI Feed", "type": "News", "status": "ONLINE", "target": "Real-time AI"},
        {"name": "Artificial Intelligence News", "type": "News", "status": "ONLINE", "target": "Industry Signals"},
        {"name": "Ars Technica Tech Lab", "type": "News", "status": "ONLINE", "target": "Emerging Tech"},
        {"name": "RemoteOK AI", "type": "Jobs", "status": "ONLINE", "target": "Global Remote"},
        {"name": "WeWorkRemotely AI", "type": "Jobs", "status": "ONLINE", "target": "Engineering Roles"},
        {"name": "Hacker News Hiring", "type": "Jobs", "status": "ONLINE", "target": "Venture Openings"},
        {"name": "Remotive AI Jobs", "type": "Jobs", "status": "ONLINE", "target": "Distributed Teams"},
        {"name": "Jobicy AI Tech", "type": "Jobs", "status": "ONLINE", "target": "Specialized Roles"},
    ]


@router.get("/llm/metrics")
def get_llm_metrics() -> Dict[str, Any]:
    """Return LLM multi-tier orchestration telemetry."""
    return llm_orchestrator.get_metrics()


@router.get("/entity-mappings")
def get_entity_mappings(limit: int = 50, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return recent entity resolution mapping logs."""
    logs = (
        db.query(EntityMappingLogDB)
        .order_by(EntityMappingLogDB.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "raw_name": log.raw_name,
            "canonical_name": log.canonical_name,
            "entity_type": log.entity_type,
            "resolution_method": log.resolution_method,
            "confidence_score": log.confidence_score,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]


@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return recent articles, jobs, papers, and startups."""
    recent_news = (
        db.query(NewsDB)
        .order_by(NewsDB.published_date.desc())
        .limit(5)
        .all()
    )
    recent_jobs = (
        db.query(JobDB)
        .order_by(JobDB.published_date.desc())
        .limit(5)
        .all()
    )
    recent_papers = (
        db.query(ResearchPaperDB)
        .order_by(ResearchPaperDB.published_date.desc())
        .limit(5)
        .all()
    )
    recent_startups = (
        db.query(StartupDB)
        .order_by(StartupDB.id.desc())
        .limit(5)
        .all()
    )

    return {
        "news": [
            {"title": n.title, "source": n.source_name, "url": n.source_url, "date": n.published_date.isoformat()}
            for n in recent_news
        ],
        "jobs": [
            {"company": j.company, "title": j.title, "role": j.role_family, "remote": j.is_remote, "date": j.published_date.isoformat()}
            for j in recent_jobs
        ],
        "papers": [
            {"title": p.title, "url": p.paper_url, "stars": p.github_stars, "github_url": p.github_url}
            for p in recent_papers
        ],
        "startups": [
            {"name": s.entity_name, "url": s.source_url, "employees": s.employee_count}
            for s in recent_startups
        ],
    }


@router.post("/pipeline/run")
async def trigger_pipeline(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger the global data acquisition pipeline."""
    if PIPELINE_STATE["is_running"]:
        return {"status": "ALREADY_RUNNING", "message": "Pipeline is currently executing."}

    async def _run_task():
        PIPELINE_STATE["is_running"] = True
        try:
            summary = await pipeline_runner.execute_full_pipeline()
            PIPELINE_STATE["last_summary"] = summary
            PIPELINE_STATE["last_run"] = summary.get("status")
        finally:
            PIPELINE_STATE["is_running"] = False

    background_tasks.add_task(_run_task)
    return {"status": "STARTED", "message": "Pipeline triggered asynchronously."}


@router.get("/pipeline/status")
def get_pipeline_status() -> Dict[str, Any]:
    """Check running status of ingestion pipeline."""
    return PIPELINE_STATE


@router.get("/exports")
def get_exports_metadata() -> Dict[str, Any]:
    """Return available exported files and instructions."""
    export_dir = settings.DATA_EXPORT_DIR
    files = []
    if os.path.exists(export_dir):
        for f in os.listdir(export_dir):
            full_path = os.path.join(export_dir, f)
            files.append({
                "filename": f,
                "size_bytes": os.path.getsize(full_path),
                "path": full_path,
            })

    return {
        "export_directory": export_dir,
        "files": files,
        "google_sheets_tabs": [
            "Startups", "Products", "Research Papers", "Jobs", "News", "Entity Mapping Log"
        ],
        "import_instructions": "Create a new Google Sheet, click File -> Import, and import either the 6 individual CSVs into their corresponding tabs or the master .xlsx file directly.",
    }
