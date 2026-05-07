from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PaperLens Core"
    database_url: str = "sqlite:///./paperlens.db"
    model_provider: str = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
