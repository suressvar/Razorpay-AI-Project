"""Configuration management for Recovery Autopilot using Pydantic Settings."""

from typing import List, Literal, Optional

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
    MODEL_PROVIDER: Literal["gemini", "openai", "ollama", "fake"] = "fake"

    # Payment Execution Mode: explicit 3-mode architecture
    # "synthetic": zero-dependency local simulation
    # "razorpay_test": genuine Razorpay test API calls using only rzp_test_ credentials
    # "production": disabled by default with dual explicit safety locks
    PAYMENT_EXECUTION_MODE: Literal["synthetic", "razorpay_test", "production"] = "synthetic"

    # Production Mode Double Safety Locks (Locked by default)
    ALLOW_PRODUCTION_MODE: bool = False
    CONFIRM_LIVE_FINANCIAL_TRANSACTIONS: bool = False

    # Emergency Kill Switch for Autonomous Executions
    KILL_SWITCH_ACTIVE: bool = False

    # Gemini Settings (Default: Gemini 3.7 Flash)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    # OpenAI Settings (Default: GPT-4o-mini)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_TIMEOUT_SECONDS: float = 30.0

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

    # Voice Recovery Agent Settings
    VOICE_ENABLED: bool = True
    VOICE_STT_PROVIDER: Literal["browser", "faster_whisper", "mock"] = "browser"
    VOICE_TTS_PROVIDER: Literal["browser", "local", "mock"] = "browser"
    VOICE_MIN_CONFIDENCE_THRESHOLD: float = 0.70
    VOICE_AUDIO_RETENTION_SECONDS: int = 0  # Zero raw audio retention by default
    VOICE_MAX_CLARIFICATION_ATTEMPTS: int = 2
    VOICE_SESSION_TIMEOUT_SECONDS: int = 300  # 5 minutes max per session

    def validate_execution_mode(self) -> None:
        """Validate safety constraints for active execution mode."""
        if self.PAYMENT_EXECUTION_MODE == "razorpay_test":
            if not self.RAZORPAY_KEY_ID.startswith("rzp_test_"):
                raise ValueError(
                    f"Invalid Razorpay Key ID for razorpay_test mode: '{self.RAZORPAY_KEY_ID[:8]}...'. "
                    "In test mode, keys MUST strictly start with 'rzp_test_'. Live credentials are prohibited."
                )
        elif self.PAYMENT_EXECUTION_MODE == "production":
            if not (self.ALLOW_PRODUCTION_MODE and self.CONFIRM_LIVE_FINANCIAL_TRANSACTIONS):
                raise ValueError(
                    "Production execution mode is locked. Live execution requires both "
                    "ALLOW_PRODUCTION_MODE=true and CONFIRM_LIVE_FINANCIAL_TRANSACTIONS=true."
                )


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


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings


def validate_execution_mode(app_settings: Optional[Settings] = None) -> str:
    """Validate safety constraints for active execution mode."""
    cfg = app_settings or settings
    cfg.validate_execution_mode()
    return cfg.PAYMENT_EXECUTION_MODE


