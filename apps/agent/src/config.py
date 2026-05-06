"""Agent-Firewall Agent — application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    # Proxy
    proxy_base_url: str = "http://localhost:8000/v1"

    # Agent identity (for centralized trace ingestion)
    agent_id: str = ""

    # Direct LLM access (used for full-context call after firewall scan)
    # LLM
    default_model: str = "deepseek-chat"
    default_model_prefix: str = "deepseek"
    default_policy: str = "strict"
    default_temperature: float = 0.3
    default_max_tokens: int = 1024
    litellm_log_level: str = "ERROR"
    deepseek_api_key: str = ""

    # OpenClaw tool provider
    openclaw_bin: str = "openclaw"
    openclaw_agent_id: str = "coder"
    openclaw_agent_local: bool = False
    openclaw_timeout_seconds: int = 120

    # Agent
    max_iterations: int = 3
    max_turns: int = 20
    max_sessions: int = 100

    # App
    mode: str = "dev"  # "dev" | "real"
    log_level: str = "INFO"
    app_version: str = "0.1.10"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
