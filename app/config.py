"""
Smart Complaint Management System
Configuration module using Pydantic Settings for type-safe environment variable loading.
"""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SmartComplaintManager"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "smart_complaint_db"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Logging
    log_level: str = "DEBUG"
    log_file: str = "logs/app.log"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Escalation thresholds (hours)
    escalation_notify_hours: int = 24    # notify staff
    escalation_admin_hours: int = 48     # escalate to admin
    escalation_critical_hours: int = 72  # mark critical
    escalation_interval_minutes: int = 5 # scheduler poll interval

    @property
    def database_url(self) -> str:
        """Construct the MySQL database URL for SQLAlchemy."""
        encoded_password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (singleton per process)."""
    return Settings()
