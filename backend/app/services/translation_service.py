from fastapi import HTTPException, status

from app.llm.mlx_adapter import MLXAdapter
from app.schemas.translation_schema import TranslationRequest, TranslationResponse
from app.services.model_runtime_service import ModelRuntimeService


class TranslationService:
    async def translate(self, payload: TranslationRequest) -> TranslationResponse:
        runtime = ModelRuntimeService().provider_config()
        provider = runtime["provider"]

        if provider == "mlx":
            return await MLXAdapter().translate_text(
                source_language=payload.source_language,
                target_language=payload.target_language,
                text=payload.text,
            )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Translation requires an MLX model runtime in the current prototype.",
        )
