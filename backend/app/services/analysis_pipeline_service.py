from app.llm import get_model_adapter
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.chunking_service import ChunkingService


class AnalysisPipelineService:
    def __init__(self, documents: DocumentRepository, analyses: AnalysisRepository):
        self.documents = documents
        self.analyses = analyses
        self.chunker = ChunkingService()
        self.adapter = get_model_adapter()
        self.normalizer = AnalysisNormalizationService()

    async def analyze(self, document_id: str) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        chunks = self.chunker.chunk(document.content)
        result = await self.adapter.analyze_document(document.id, document.content, chunks)
        result = self.normalizer.normalize_result(result, document.content)
        self.analyses.upsert(result)
        return result
