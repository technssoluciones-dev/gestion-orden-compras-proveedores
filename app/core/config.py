"""ProcureFlow AI — Application Settings (Pydantic Settings v2)."""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="ProcureFlow AI")
    app_env: str = Field(default="development")
    app_version: str = Field(default="2.0.0")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_workers: int = Field(default=4)
    debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production-minimum-32-chars")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://procureflow:procureflow_pass@localhost:5432/procureflow_db"
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=40)
    database_echo: bool = Field(default=False)

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production-jwt-secret-key")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_cache_ttl: int = Field(default=300)

    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/")
    rabbitmq_exchange: str = Field(default="procureflow.events")

    # AI — defaults to "none" so it doesn't fail when no key configured
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4-turbo-preview")
    openai_max_tokens: int = Field(default=2000)
    anthropic_api_key: Optional[str] = Field(default=None)
    ai_provider: str = Field(default="none")  # none | openai | anthropic

    # Email
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    email_from: str = Field(default="noreply@procureflow.com")

    # Storage
    storage_backend: str = Field(default="local")
    upload_path: str = Field(default="./uploads")
    max_file_size_mb: int = Field(default=25)
    s3_bucket: Optional[str] = Field(default=None)
    s3_region: Optional[str] = Field(default=None)

    # Security
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    allowed_hosts: str = Field(default="*")
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)
    bcrypt_rounds: int = Field(default=12)

    # Business Rules
    max_po_amount_auto_approve: float = Field(default=5000.00)
    approval_timeout_hours: int = Field(default=72)
    notification_reminder_hours: int = Field(default=24)
    budget_alert_threshold_percent: int = Field(default=80)
    currency_default: str = Field(default="USD")

    # Observability
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="console")  # console | json

    # Celery
    celery_broker_url: str = Field(default="amqp://guest:guest@localhost:5672//")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # N8N
    n8n_webhook_url: Optional[str] = Field(default=None)
    n8n_api_key: Optional[str] = Field(default=None)



    @field_validator("jwt_secret_key", "secret_key", mode="before")
    @classmethod
    def validate_secret_not_default(cls, v: str, info) -> str:
        """Falla en startup si los secrets son los valores por defecto."""
        import os
        if os.getenv("APP_ENV", "development") == "production":
            dangerous = {"change-me", "change-me-in-production", "change-me-in-production-jwt-secret-key", "change-me-in-production-minimum-32-chars"}
            if any(v.lower().startswith(d) for d in dangerous):
                raise ValueError(
                    f"\n\n{'='*60}\n"
                    f"CRÍTICO: Secret key con valor por defecto en producción.\n"
                    f"Configura {info.field_name.upper()} en tu .env con un valor seguro.\n"
                    f"{'='*60}"
                )
        return v

    # Alias para compatibilidad (evita redefinir startup_security_check)
    _startup_security_check = True

    @field_validator("allowed_origins")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
