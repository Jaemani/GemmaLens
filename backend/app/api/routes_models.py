from time import perf_counter

from fastapi import APIRouter

from app.llm.mlx_adapter import MLXAdapter
from app.llm.remote_gemma_adapter import RemoteGemmaAdapter
from app.schemas.model_schema import ModelConfigUpdate, ModelPreset, ModelStatus
from app.services.model_runtime_service import ModelRuntimeService

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status", response_model=ModelStatus)
def model_status():
    return ModelRuntimeService().status()


@router.get("/presets", response_model=list[ModelPreset])
def model_presets():
    return ModelRuntimeService().presets()


@router.post("/config", response_model=ModelStatus)
def update_model_config(payload: ModelConfigUpdate):
    return ModelRuntimeService().update(payload)


@router.post("/warmup")
async def warmup_model():
    runtime = ModelRuntimeService().provider_config()
    start = perf_counter()
    if runtime["provider"] == "mlx":
        MLXAdapter().warmup()
        return {"status": "ready", "provider": "mlx", "elapsed_seconds": round(perf_counter() - start, 3)}
    if runtime["provider"] == "remote":
        health = await RemoteGemmaAdapter().warmup()
        return {
            "status": health.get("status", "ready"),
            "provider": "remote",
            "active_model": health.get("active_model", runtime["remote_gemma_model"]),
            "elapsed_seconds": round(perf_counter() - start, 3),
        }
    return {"status": "skipped", "provider": runtime["provider"], "elapsed_seconds": round(perf_counter() - start, 3)}
