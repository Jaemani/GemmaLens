from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.mock_adapter import MockModelAdapter
from app.llm.ollama_adapter import OllamaAdapter


def get_model_adapter() -> ModelAdapter:
    if get_settings().model_provider.lower() == "ollama":
        return OllamaAdapter()
    return MockModelAdapter()
