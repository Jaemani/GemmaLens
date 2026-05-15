from typing import Literal

from pydantic import BaseModel, Field

ModelPresetId = Literal[
    "mock",
    "gemma4-e2b-mlx",
    "gemma4-e4b-mlx",
    "gemma4-e4b-ollama",
    "gemma4-e2b-thinkpad",
    "gemma4-e4b-thinkpad",
]


class ModelPreset(BaseModel):
    id: ModelPresetId
    label: str
    runtime: Literal["mock", "mlx", "ollama", "remote"]
    size: str
    speed: str
    availability: Literal["ready", "missing", "external"]
    description: str


class ModelStatus(BaseModel):
    provider: Literal["mock", "mlx", "ollama", "remote"]
    preset_id: ModelPresetId
    preset_label: str
    ollama_model: str
    ollama_base_url: str
    remote_gemma_model: str
    remote_gemma_base_url: str
    mlx_model_path: str
    mlx_model_available: bool
    mock_fallback: bool = False
    demo_mode: bool = False


class ModelConfigUpdate(BaseModel):
    preset_id: ModelPresetId | None = None
    provider: Literal["mock", "mlx", "ollama", "remote"] | None = None
    ollama_model: str | None = Field(default=None, min_length=1)
    ollama_base_url: str | None = Field(default=None, min_length=1)
    remote_gemma_model: str | None = Field(default=None, min_length=1)
    remote_gemma_base_url: str | None = Field(default=None, min_length=1)
    mlx_model_path: str | None = Field(default=None, min_length=1)
