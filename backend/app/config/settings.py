"""Application settings loaded from environment variables. No hardcoded secrets."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Google Cloud
    google_cloud_project: str = "demo-project"
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = True

    gemini_model: str = "gemini-3.5-pro"

    firestore_database: str = "(default)"

    pubsub_project_id: str | None = None
    pubsub_topic: str = "founder-shortcut-jobs"

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_refresh_token: str | None = None
    google_calendar_id: str = "primary"

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None

    email_provider_api_key: str | None = None

    storage_bucket: str | None = None

    demo_mode: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8080
    frontend_origin: str = "http://localhost:3000"

    @property
    def project(self) -> str:
        return self.google_cloud_project


@lru_cache
def get_settings() -> Settings:
    return Settings()
