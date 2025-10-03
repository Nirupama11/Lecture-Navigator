import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # environment
    ENV: str = Field(default="dev")

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # MongoDB
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB: str = Field(default="lecture_navigator")
    MONGODB_COLLECTION: str = Field(default="segments")

    # API Keys
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    # Models
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    LLM_MODEL: str = Field(default="gpt-4o-mini")

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton settings object
settings = Settings()
