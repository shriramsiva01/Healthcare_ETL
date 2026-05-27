"""
Application settings — loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "healthcare_etl"

    # ── Paths ─────────────────────────────────────────────────
    RAW_DATA_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "raw")
    PROCESSED_DATA_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "processed")
    LOG_DIR: str = str(Path(__file__).resolve().parent.parent / "logs")

    # ── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
