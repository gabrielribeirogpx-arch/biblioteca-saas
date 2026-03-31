import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/library"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ALLOW_ORIGINS: list[str] = [
        "https://front-biblioteca-saas.vercel.app",
        "http://localhost:3000",
    ]
    CORS_ALLOW_ORIGIN_REGEX: str = r"^https://.*\.vercel\.app$"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_async_database_url(cls, value: str) -> str:
        if value.startswith("postgresql+asyncpg://"):
            suffix = value[len("postgresql+asyncpg://") :]
            if suffix.startswith("postgresql://"):
                suffix = suffix[len("postgresql://") :]
            if suffix.startswith("postgresql+asyncpg://"):
                suffix = suffix[len("postgresql+asyncpg://") :]
            return f"postgresql+asyncpg://{suffix}"
        if value.startswith("postgresql://postgresql://"):
            value = value.replace("postgresql://postgresql://", "postgresql://", 1)
        if value.startswith("postgresql://postgresql+asyncpg://"):
            value = value.replace("postgresql://postgresql+asyncpg://", "postgresql://", 1)
        if value.startswith("postgresql://"):
            suffix = value[len("postgresql://") :]
            if suffix.startswith("postgresql://"):
                suffix = suffix[len("postgresql://") :]
            if suffix.startswith("postgresql+asyncpg://"):
                suffix = suffix[len("postgresql+asyncpg://") :]
            return f"postgresql+asyncpg://{suffix}"
        raise ValueError("DATABASE_URL must use postgresql:// or postgresql+asyncpg:// format")

    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            trimmed = value.strip()

            if trimmed.startswith("["):
                try:
                    parsed_value = json.loads(trimmed)
                except json.JSONDecodeError:
                    parsed_value = None
                else:
                    if isinstance(parsed_value, list):
                        return [str(origin).strip() for origin in parsed_value if str(origin).strip()]

            normalized = trimmed.strip("[]")
            return [
                origin.strip().strip("\"'").strip()
                for origin in normalized.split(",")
                if origin.strip().strip("\"'").strip()
            ]
        return value


settings = Settings()
