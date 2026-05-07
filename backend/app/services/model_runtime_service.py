import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.model_schema import ModelConfigUpdate, ModelPreset, ModelStatus


PRESETS: dict[str, dict[str, str]] = {
    "mock": {
        "label": "Mock analysis",
        "provider": "mock",
        "size": "Instant",
        "speed": "Fastest",
        "description": "Deterministic output for testing without a local model.",
    },
    "gemma4-e2b-mlx": {
        "label": "Gemma 4 E2B (MLX bf16)",
        "provider": "mlx",
        "mlx_model_path": "~/Models/mlx/gemma-4-e2b-it-bf16",
        "size": "E2B",
        "speed": "Fast",
        "description": "Full-precision bf16 instruction model for local analysis on Apple Silicon.",
    },
    "gemma4-e4b-mlx": {
        "label": "Gemma 4 E4B (MLX bf16)",
        "provider": "mlx",
        "mlx_model_path": "~/Models/mlx/gemma-4-e4b-it-bf16",
        "size": "E4B",
        "speed": "Best local quality",
        "description": "Full-precision bf16 Gemma 4 E4B. M1 Max 32 GB can hold it.",
    },
    "gemma4-e4b-ollama": {
        "label": "Gemma 4 E4B (Ollama)",
        "provider": "ollama",
        "ollama_model": "gemma4:e4b",
        "size": "E4B",
        "speed": "External",
        "description": "Use Ollama on localhost. Requires `ollama pull gemma4:e4b`.",
    },
}


class ModelRuntimeService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.config_path = Path("model_runtime.json")

    def status(self) -> ModelStatus:
        config = self._merged_config()
        mlx_path = Path(config["mlx_model_path"]).expanduser()
        preset_id = config["preset_id"]
        preset = PRESETS[preset_id]
        return ModelStatus(
            provider=config["provider"],
            preset_id=preset_id,
            preset_label=preset["label"],
            ollama_model=config["ollama_model"],
            ollama_base_url=config["ollama_base_url"],
            mlx_model_path=str(mlx_path),
            mlx_model_available=mlx_path.exists(),
        )

    def update(self, payload: ModelConfigUpdate) -> ModelStatus:
        current = self._merged_config()
        updates = payload.model_dump(exclude_none=True)
        if preset_id := updates.pop("preset_id", None):
            current.update(self._preset_config(preset_id))
        current.update(updates)
        self.config_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return self.status()

    def presets(self) -> list[ModelPreset]:
        current = self._merged_config()
        presets: list[ModelPreset] = []
        for preset_id, preset in PRESETS.items():
            runtime = preset["provider"]
            availability = "external" if runtime == "ollama" else "ready"
            if runtime == "mlx":
                path = Path(preset["mlx_model_path"]).expanduser()
                availability = "ready" if path.exists() else "missing"
            presets.append(
                ModelPreset(
                    id=preset_id,
                    label=preset["label"],
                    runtime=runtime,
                    size=preset["size"],
                    speed=preset["speed"],
                    availability=availability,
                    description=preset["description"],
                )
            )
        if current["preset_id"] not in PRESETS:
            current["preset_id"] = "mock"
        return presets

    def provider_config(self) -> dict[str, Any]:
        return self._merged_config()

    def _merged_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "preset_id": "mock",
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
        if config["provider"] == "mlx" and (
            "OptiQ" in config["mlx_model_path"] or "4bit" in config["mlx_model_path"] or "4-bit" in config["mlx_model_path"]
        ):
            config.update(self._preset_config("gemma4-e4b-mlx"))
        elif config["preset_id"] == "mock" and config["provider"] == "mlx":
            config.update(self._preset_config("gemma4-e4b-mlx"))
        elif config["preset_id"] == "mock" and config["provider"] == "ollama":
            config.update(self._preset_config("gemma4-e4b-ollama"))
        return config

    def _preset_config(self, preset_id: str) -> dict[str, Any]:
        preset = PRESETS[preset_id]
        return {
            "preset_id": preset_id,
            "provider": preset["provider"],
            "ollama_model": preset.get("ollama_model", self.settings.ollama_model),
            "ollama_base_url": self.settings.ollama_base_url,
            "mlx_model_path": preset.get("mlx_model_path", self.settings.mlx_model_path),
        }
