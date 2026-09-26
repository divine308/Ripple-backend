import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Ripple"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"

    MAX_UPLOAD_MB: int = 100
    MAX_FILES: int = 5000
    MAX_FILE_SIZE_MB: int = 5

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    RIPPLE_VERSION: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()