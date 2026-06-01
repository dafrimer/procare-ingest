import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    procare_auth_token: Optional[str] = field(default_factory=lambda: os.getenv("PROCARE_AUTH_TOKEN"))
    procare_email: Optional[str] = field(default_factory=lambda: os.getenv("PROCARE_EMAIL"))
    procare_password: Optional[str] = field(default_factory=lambda: os.getenv("PROCARE_PASSWORD"))
    procare_site_url: str = field(default_factory=lambda: os.getenv("PROCARE_SITE_URL", "https://api-school.procareconnect.com"))
    procare_site_id: Optional[str] = field(default_factory=lambda: os.getenv("PROCARE_SITE_ID"))
    procare_auth_url: str = field(default_factory=lambda: os.getenv("PROCARE_AUTH_URL", "https://online-auth.procareconnect.com/sessions/"))
    db_adapter: str = field(default_factory=lambda: os.getenv("DB_ADAPTER", "mysql"))
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "procare"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", "procare"))
    db_password: Optional[str] = field(default_factory=lambda: os.getenv("DB_PASSWORD"))
    sync_interval_minutes: int = field(default_factory=lambda: int(os.getenv("SYNC_INTERVAL_MINUTES", "15")))
    activity_lookback_days: int = field(default_factory=lambda: int(os.getenv("ACTIVITY_LOOKBACK_DAYS", "30")))
    run_once: bool = field(default_factory=lambda: os.getenv("RUN_ONCE", "false").lower() == "true")
    page_size: int = field(default_factory=lambda: int(os.getenv("PAGE_SIZE", "100")))
    token_cache_path: str = field(default_factory=lambda: os.getenv("TOKEN_CACHE_PATH", "/data/.token_cache.json"))

    @property
    def db_url(self) -> str:
        if self.db_adapter == "postgres":
            driver = "postgresql+psycopg2"
        else:
            driver = "mysql+pymysql"
        return f"{driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def validate(self):
        if not self.procare_auth_token and not (self.procare_email and self.procare_password):
            raise ValueError("Must set PROCARE_AUTH_TOKEN or both PROCARE_EMAIL and PROCARE_PASSWORD")
        if not self.db_password:
            raise ValueError("DB_PASSWORD is required")
