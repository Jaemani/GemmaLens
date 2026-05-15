from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.analysis_schema import AnalysisResult
from app.services.academic_text_service import AcademicTextService
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.analysis_pipeline_service import AnalysisPipelineService

router = APIRouter(prefix="/documents", tags=["analysis"])


@router.post("/{document_id}/analyze", response_model=AnalysisResult)
async def analyze_document(document_id: str, db: Session = Depends(get_db)):
    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db))
    profile = UserProfileRepository(db).get_or_create()
    try:
        result = await service.analyze(document_id, target_level=profile.target_level)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if not result:
        raise not_found("Document not found")
    return result


@router.get("/{document_id}/analysis", response_model=AnalysisResult)
def get_analysis(document_id: str, db: Session = Depends(get_db)):
    result = AnalysisRepository(db).get_result(document_id)
    if not result:
        raise not_found("Analysis not found")
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    readable_text = AcademicTextService().readable_section(document.content)
    normalized = AnalysisNormalizationService().normalize_result(result, readable_text)
    return normalized
