from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # GitHub
    GITHUB_APP_ID: int | None = None
    GITHUB_PRIVATE_KEY: str | None = None
    GITHUB_TOKEN: str | None = None

    # Security
    WEBHOOK_SECRET: str

    # LLM (via LiteLLM)
    LITELLM_MODEL: str = "ollama/llama3.2"

    # Storage & runtime
    DATA_DIR: str = "data"

    # Redis event bus
    REDIS_URL: str = "redis://localhost:6379/0"

    # Observability (OpenTelemetry)
    OTLP_ENDPOINT: str = "http://localhost:4317"

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
