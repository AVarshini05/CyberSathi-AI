import json
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "38b724f8d48416d8a23d6a2f7c0068a159feea6b4c10c0e86b3e70d44084f7b4"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    PROJECT_NAME: str = "Cyber Crime Reporting Management System (CCRMS)"

    # CORS origins setup
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return v
        raise ValueError(v)

    # AI Services Keys
    SARVAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Database setup (local PostgreSQL)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ccrms"

    # Local storage uploads
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=[
            # Try root directory .env relative to this file (4 levels up: backend/app/core/config.py)
            __import__("os").path.join(
                __import__("os").path.dirname(
                    __import__("os").path.dirname(
                        __import__("os").path.dirname(
                            __import__("os").path.dirname(
                                __import__("os").path.abspath(__file__)
                            )
                        )
                    )
                ),
                ".env"
            ),
            # Fallback to current working directory .env
            ".env"
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
