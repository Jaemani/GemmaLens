from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_pipeline_service import AnalysisPipelineService

router = APIRouter(prefix="/documents", tags=["analysis"])


@router.post("/{document_id}/analyze", response_model=AnalysisResult)
async def analyze_document(document_id: str, db: Session = Depends(get_db)):
    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db))
    result = await service.analyze(document_id)
    if not result:
        raise not_found("Document not found")
    return result


@router.get("/{document_id}/analysis", response_model=AnalysisResult)
def get_analysis(document_id: str, db: Session = Depends(get_db)):
    result = AnalysisRepository(db).get_result(document_id)
    if not result:
        raise not_found("Analysis not found")
    return result
