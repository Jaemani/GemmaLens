from app.core.config import get_settings
from app.llm import get_model_adapter
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.section_analysis_repository import SectionAnalysisRepository
from app.schemas.analysis_schema import AnalysisResult
from app.services.academic_text_service import AcademicTextService
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.chunking_service import ChunkingService
from app.services.document_section_service import DocumentSectionService


class AnalysisPipelineService:
    def __init__(self, documents: DocumentRepository, analyses: AnalysisRepository, section_analyses: SectionAnalysisRepository | None = None):
        self.documents = documents
        self.analyses = analyses
        self.section_analyses = section_analyses
        self.settings = get_settings()
        self.chunker = ChunkingService()
        self.adapter = get_model_adapter()
        self.normalizer = AnalysisNormalizationService()
        self.academic_text = AcademicTextService()
        self.sections = DocumentSectionService()

    async def analyze(self, document_id: str, target_level: str | None = None) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        readable_text = self.academic_text.readable_section(document.content)
        chunks = self.chunker.chunk(readable_text)
        analysis_text = self._analysis_text(readable_text)
        analysis_chunks = chunks[: self.settings.analysis_model_max_chunks]
        result = await self.adapter.analyze_document(document.id, analysis_text, analysis_chunks)
        result = self.normalizer.normalize_result(result, analysis_text)
        if target_level and target_level != "unknown":
            result = result.model_copy(
                update={
                    "difficulty": result.difficulty.model_copy(
                        update={
                            "overall_level": target_level,
                            "reason": f"Calibrated against your {target_level} reading setting. {result.difficulty.reason}",
                        }
                    )
                }
            )
        if len(" ".join(readable_text.split())) > len(analysis_text):
            result.quality_warnings.append(
                "This is a section-level analysis from the first readable section. Full-document staged analysis is not implemented yet."
            )
        self.analyses.upsert(result)
        return result

    async def analyze_section(self, document_id: str, section_index: int, target_level: str | None = None) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        readable_text = self.academic_text.readable_section(document.content)
        section = self.sections.section(readable_text, section_index)
        if not section:
            return None
        if self.section_analyses:
            cached = self.section_analyses.get_result(document_id, section_index)
            if cached:
                return cached
        section_text, section_count = section
        chunks = self.chunker.chunk(section_text)
        result = await self.adapter.analyze_document(document.id, section_text, chunks[: self.settings.analysis_model_max_chunks])
        result = self.normalizer.normalize_result(result, section_text)
        result.quality_warnings.append(f"section:{section_index + 1}/{section_count}")
        if target_level and target_level != "unknown":
            result = result.model_copy(
                update={
                    "difficulty": result.difficulty.model_copy(
                        update={
                            "overall_level": target_level,
                            "reason": f"Calibrated against your {target_level} reading setting. {result.difficulty.reason}",
                        }
                    )
                }
            )
        if self.section_analyses:
            self.section_analyses.upsert(section_index, result)
        return result

    def _analysis_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= self.settings.analysis_model_input_chars:
            return normalized
        return normalized[: self.settings.analysis_model_input_chars].rsplit(" ", 1)[0]
