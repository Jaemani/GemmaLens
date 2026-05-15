from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GemmaLens Core"
    database_url: str = "sqlite:///./gemmalens.db"
    app_demo_mode: bool = False
    model_provider: str = "mlx"
    model_switching_enabled: bool = True
    model_runtime_config_path: str = "model_runtime.json"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    mlx_model_path: str = "~/Models/mlx/gemma-4-e4b-it-bf16"
    mlx_max_tokens: int = 768
    mlx_temperature: float = 0.1
    analysis_model_input_chars: int = 2500
    analysis_model_max_chunks: int = 3
    raw_model_output_path: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_origin_regex: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
