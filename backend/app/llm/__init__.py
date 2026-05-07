from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.mlx_adapter import MLXAdapter
from app.llm.mock_adapter import MockModelAdapter
from app.llm.ollama_adapter import OllamaAdapter
from app.services.model_runtime_service import ModelRuntimeService


def get_model_adapter() -> ModelAdapter:
    provider = ModelRuntimeService().provider_config()["provider"].lower()
    if provider == "ollama":
        return OllamaAdapter()
    if provider == "mlx":
        return MLXAdapter()
    return MockModelAdapter()
