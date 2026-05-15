from fastapi import APIRouter, HTTPException, status

from app.schemas.translation_schema import TranslationRequest, TranslationResponse
from app.services.translation_service import TranslationService

router = APIRouter(prefix="/translate", tags=["translate"])


@router.post("", response_model=TranslationResponse)
async def translate_text(payload: TranslationRequest):
    try:
        return await TranslationService().translate(payload)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
