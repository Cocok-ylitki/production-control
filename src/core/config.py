from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/production_control"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/production_control"

    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "production-control"
    minio_secure: bool = False
    minio_reports_prefix: str = "reports"
    minio_imports_prefix: str = "imports"
    minio_exports_prefix: str = "exports"
    # Имена бакетов (можно переопределить в .env)
    minio_bucket_reports: str = "reports"
    minio_bucket_exports: str = "exports"
    minio_bucket_imports: str = "imports"
    redis_url: str = "redis://localhost:6379/1"

    @property
    def minio_buckets(self) -> dict[str, str]:
        """Бакеты для инициализации: имя -> описание."""
        return {
            self.minio_bucket_reports: "Сгенерированные отчеты",
            self.minio_bucket_exports: "Экспортированные данные",
            self.minio_bucket_imports: "Загруженные файлы для импорта",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
