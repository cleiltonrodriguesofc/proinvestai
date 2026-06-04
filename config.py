import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    SECURITY: DATABASE_URL and SECRET_KEY have no safe defaults.
    They MUST be set via .env or environment variables.
    """

    APP_NAME: str = "ProInvestAI"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./proinvestai.db"
    SECRET_KEY: str = "CHANGE-ME-BEFORE-DEPLOY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # External APIs
    GEMINI_API_KEY: str = ""
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    BRAPI_TOKEN: str = ""
    BCB_API_URL: str = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Prevent deployment with insecure defaults."""
        insecure_keys = {"secret", "CHANGE-ME-BEFORE-DEPLOY", ""}
        if not self.DEBUG and self.SECRET_KEY in insecure_keys:
            raise ValueError(
                "SECRET_KEY must be set to a secure random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if not self.DEBUG and "password" in self.DATABASE_URL:
            logger.warning(
                "DATABASE_URL appears to contain a default password. "
                "Ensure production credentials are set via environment variables."
            )
        return self


@lru_cache()
def get_settings():
    """Return cached application settings singleton."""
    return Settings()
