import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ApiConfig:
    """Configuration for procare-api service."""
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8080")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "info"))
    sqlite_path: str = field(default_factory=lambda: os.getenv("SQLITE_PATH", "/data/procare.db"))
    ingest_token: Optional[str] = field(default_factory=lambda: os.getenv("INGEST_TOKEN"))
    cors_origins: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))