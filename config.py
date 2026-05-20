from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "ProInvestAI"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/proinvestai"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External APIs
    OPENAI_API_KEY: str = ""
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    BRAPI_TOKEN: str = ""
    BCB_API_URL: str = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
