from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://codeforge:password@db:5432/codeforge"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Sandbox defaults
    sandbox_memory_limit: str = "128m"
    sandbox_cpu_limit: float = 0.5
    sandbox_default_timeout: int = 10
    sandbox_tmpfs_size: str = "16m"
    sandbox_pids_limit: int = 64
    sandbox_ulimit_nofile: int = 64

    # Docker
    docker_host: str = "unix:///var/run/docker.sock"

    # AI Tutor
    gemini_api_key: str = ""


settings = Settings()
