from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "backend" / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = "FOLLOWUAI_API_KEY_SEGURA_2026"

    DB_PATH: str = str(PROJECT_ROOT / "database" / "followuai.db")
    SCHEMA_PATH: str = str(PROJECT_ROOT / "database" / "schema.sql")

    LOG_LEVEL: str = "INFO"
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8000
    INTERVALO_MIN_ENVIO_MINUTOS: int = 5

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.DB_PATH}"


settings = Settings()
