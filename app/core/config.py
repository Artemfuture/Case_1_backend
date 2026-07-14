from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Document Checks API"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@db:5432/checks_db")
    database_echo: bool = False

    max_file_size_mb: int = 20
    uploads_dir: Path = Field(default=Path("uploads"))

    server_host: str = "0.0.0.0"
    server_port: int = 8000

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
