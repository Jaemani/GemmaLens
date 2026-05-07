import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.model_schema import ModelConfigUpdate, ModelStatus


class ModelRuntimeService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.config_path = Path("model_runtime.json")

    def status(self) -> ModelStatus:
        config = self._merged_config()
        mlx_path = Path(config["mlx_model_path"]).expanduser()
        return ModelStatus(
            provider=config["provider"],
            ollama_model=config["ollama_model"],
            ollama_base_url=config["ollama_base_url"],
            mlx_model_path=str(mlx_path),
            mlx_model_available=mlx_path.exists(),
        )

    def update(self, payload: ModelConfigUpdate) -> ModelStatus:
        current = self._merged_config()
        updates = payload.model_dump(exclude_none=True)
        current.update(updates)
        self.config_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return self.status()

    def provider_config(self) -> dict[str, Any]:
        return self._merged_config()

    def _merged_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "provider": self.settings.model_provider,
            "ollama_model": self.settings.ollama_model,
            "ollama_base_url": self.settings.ollama_base_url,
            "mlx_model_path": self.settings.mlx_model_path,
        }
        if self.config_path.exists():
            try:
                persisted = json.loads(self.config_path.read_text(encoding="utf-8"))
                config.update({k: v for k, v in persisted.items() if v is not None})
            except json.JSONDecodeError:
                pass
        return config
