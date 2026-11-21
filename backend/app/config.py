"""Configuration settings for FrontierAtlas AI Intelligence Pipeline.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "FrontierAtlas AI Intelligence Pipeline"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///C:/Users/royal/.gemini/antigravity/scratch/ai-intelligence-pipeline/data/intelligence_graph.db",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # LLM API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # GitHub (Optional, elevates public rate limits from 60/hr to 5,000/hr)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Crawler Settings
    CRAWLER_CONCURRENCY: int = int(os.getenv("CRAWLER_CONCURRENCY", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    BACKOFF_FACTOR: float = float(os.getenv("BACKOFF_FACTOR", "1.5"))

    # Exports
    DATA_EXPORT_DIR: str = os.getenv(
        "DATA_EXPORT_DIR",
        "C:/Users/royal/.gemini/antigravity/scratch/ai-intelligence-pipeline/data/exports",
    )

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
