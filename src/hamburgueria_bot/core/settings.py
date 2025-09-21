
"""Configurações Pydantic Settings para a aplicação."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Configurações da aplicação. Carrega de env e .env.

    Todas as credenciais devem vir via env. Nunca hardcode.
    """
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HB_", case_sensitive=False)

    # Flask
    flask_debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # DB
    database_url: str = Field(..., description="URL do Postgres, ex: postgresql+psycopg://user:pass@db:5432/app")

    # WhatsApp Cloud API
    whatsapp_token: str = Field(...)
    whatsapp_phone_number_id: str = Field(...)
    app_secret: str = Field(..., description="APP_SECRET para assinar Webhook")
    verify_token: str = Field(..., description="VERIFY_TOKEN para verificação do hub.challenge")

    # Coalescência
    coalesce_window_ms: int = Field(default=1200)

    # LLM / LiteLLM
    litellm_base_url: str = Field(..., description="URL do gateway LiteLLM")
    litellm_model_primary: str = Field(default="gpt-4o-mini")
    litellm_model_fallback: str = Field(default="gpt-4o-mini")
    litellm_timeout_s: int = Field(default=12)
    litellm_max_tokens: int = Field(default=300)
    litellm_temperature: float = Field(default=0.1)

    # Outros
    ctx_summary_threshold: int = Field(default=30)
