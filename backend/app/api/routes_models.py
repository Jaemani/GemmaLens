from fastapi import APIRouter

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
