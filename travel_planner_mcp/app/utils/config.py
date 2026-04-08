from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:7b-instruct", alias="OLLAMA_MODEL")
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")
    serpapi_api_key: str = Field(default="", alias="SERPAPI_API_KEY")
    hotel_provider: str = Field(default="serpapi", alias="HOTEL_PROVIDER")
    maps_provider: str = Field(default="google", alias="MAPS_PROVIDER")
    fastapi_host: str = Field(default="0.0.0.0", alias="FASTAPI_HOST")
    fastapi_port: int = Field(default=8000, alias="FASTAPI_PORT")
    fastapi_url: str = Field(default="http://localhost:8000", alias="FASTAPI_URL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
