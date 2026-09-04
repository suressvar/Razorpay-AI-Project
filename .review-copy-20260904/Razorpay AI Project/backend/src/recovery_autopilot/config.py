"""Configuration management for Recovery Autopilot using Pydantic Settings."""

from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Config
    APP_NAME: str = "Recovery Autopilot"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database Configuration (Postgres or SQLite fallback)
    DATABASE_URL: str = "sqlite+aiosqlite:///./recovery_autopilot.db"

    # Background Tasks & Queues
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_IN_PROCESS_WORKER: bool = True

    # Model Provider Selection
    MODEL_PROVIDER: Literal["gemini", "ollama", "fake"] = "fake"

    # Gemini Settings (Default: Gemini 3.7 Flash)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    # Ollama Settings (Default: Qwen3 8B)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0

    # Razorpay Test Mode Credentials
    RAZORPAY_KEY_ID: str = "rzp_test_simulation_key"
    RAZORPAY_KEY_SECRET: str = "rzp_test_simulation_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "rzp_whsec_simulation_key"

    # Operational Safety & Guardrails
    SYNTHETIC_MODE: bool = True
    SIMULATE_NOTIFICATIONS: bool = True
    HUMAN_REVIEW_THRESHOLD_INR: float = 15000.0
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    MAX_CONTACT_ATTEMPTS: int = 3
    MIN_HOURS_BETWEEN_CONTACTS: int = 24
    MAX_CONTACTS_PER_WEEK: int = 3
    MAX_RETRY_DELAY_MINUTES: int = 10080  # 7 days max delay

    # Security & CORS
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
    )


# Singleton settings instance
settings = Settings()
