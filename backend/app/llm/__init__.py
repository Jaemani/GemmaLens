from fastapi import HTTPException

from app.llm.base import ModelAdapter
from app.llm.mlx_adapter import MLXAdapter
from app.llm.mock_adapter import MockModelAdapter
from app.llm.ollama_adapter import OllamaAdapter
from app.llm.remote_gemma_adapter import RemoteGemmaAdapter
from app.services.model_runtime_service import ModelRuntimeService


def get_model_adapter() -> ModelAdapter:
    provider = ModelRuntimeService().provider_config()["provider"].lower()
    if provider == "ollama":
        return OllamaAdapter()
    if provider == "mlx":
        return MLXAdapter()
    if provider == "remote":
        return RemoteGemmaAdapter()
    if provider == "mock":
        return MockModelAdapter()
    raise HTTPException(status_code=503, detail="No model runtime configured. Select an explicit provider before requesting analysis.")
