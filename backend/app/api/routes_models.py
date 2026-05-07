from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
def model_status():
    settings = get_settings()
    mlx_path = Path(settings.mlx_model_path).expanduser()
    return {
        "provider": settings.model_provider,
        "ollama_model": settings.ollama_model,
        "ollama_base_url": settings.ollama_base_url,
        "mlx_model_path": str(mlx_path),
        "mlx_model_available": mlx_path.exists(),
        "mock_fallback": True,
    }
