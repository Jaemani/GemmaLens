from typing import Literal

from pydantic import BaseModel, Field


class ModelStatus(BaseModel):
    provider: Literal["mock", "mlx", "ollama"]
    ollama_model: str
    ollama_base_url: str
    mlx_model_path: str
    mlx_model_available: bool
    mock_fallback: bool = True


class ModelConfigUpdate(BaseModel):
    provider: Literal["mock", "mlx", "ollama"] | None = None
    ollama_model: str | None = Field(default=None, min_length=1)
    ollama_base_url: str | None = Field(default=None, min_length=1)
    mlx_model_path: str | None = Field(default=None, min_length=1)
