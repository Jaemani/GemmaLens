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

    async def analyze(
        self,
        document_id: str,
        target_level: str | None = None,
        support_language: str = "Korean",
        learning_language: str = "English",
    ) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        readable_text = self.academic_text.readable_section(document.content)
        chunks = self.chunker.chunk(readable_text)
        analysis_text = self._analysis_text(readable_text)
        analysis_chunks = chunks[: self.settings.analysis_model_max_chunks]
        result = await self.adapter.analyze_document(document.id, analysis_text, analysis_chunks, support_language, learning_language, target_level)
        result = self.normalizer.normalize_result(result, analysis_text, support_language=support_language, target_level=target_level)
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

    async def analyze_section(
        self,
        document_id: str,
        section_index: int,
        target_level: str | None = None,
        support_language: str = "Korean",
        learning_language: str = "English",
        force: bool = False,
    ) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        readable_text = self.academic_text.readable_section(document.content)
        section = self.sections.section(readable_text, section_index)
        if not section:
            return None
        section_text, section_count = section
        if self.section_analyses and not force:
            cached = self.section_analyses.get_result(document_id, section_index)
            if cached:
                normalized_cached = self.normalizer.normalize_result(cached, section_text, support_language=support_language, target_level=target_level)
                if target_level and target_level != "unknown" and not normalized_cached.difficulty.reason.startswith("Calibrated against your"):
                    normalized_cached = normalized_cached.model_copy(
                        update={
                            "difficulty": normalized_cached.difficulty.model_copy(
                                update={
                                    "overall_level": target_level,
                                    "reason": f"Calibrated against your {target_level} reading setting. {normalized_cached.difficulty.reason}",
                                }
                            )
                        }
                    )
                normalized_cached.quality_warnings = [warning for warning in normalized_cached.quality_warnings if not warning.startswith("section:")]
                normalized_cached.quality_warnings.append(f"section:{section_index + 1}/{section_count}")
                self.section_analyses.upsert(section_index, normalized_cached)
                return normalized_cached
        chunks = self.chunker.chunk(section_text)
        result = await self.adapter.analyze_document(
            document.id,
            section_text,
            chunks[: self.settings.analysis_model_max_chunks],
            support_language,
            learning_language,
            target_level,
        )
        result = self.normalizer.normalize_result(result, section_text, support_language=support_language, target_level=target_level)
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

    async def analyze_page_sections(
        self,
        document_id: str,
        page_number: int,
        target_level: str | None = None,
        support_language: str = "Korean",
        learning_language: str = "English",
    ) -> list[tuple[int, AnalysisResult]] | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        readable_text = self.academic_text.readable_section(document.content)
        labeled_sections = self.sections.split_with_labels(readable_text)
        page_sections = [
            (index, section)
            for index, section in enumerate(labeled_sections)
            if section.source_label == f"PDF page {page_number}" or (page_number == 1 and section.source_label is None)
        ]
        if not page_sections:
            return []

        results: list[tuple[int, AnalysisResult]] = []
        missing_sections: list[tuple[int, object]] = []
        if self.section_analyses:
            for index, section in page_sections:
                cached = self.section_analyses.get_result(document_id, index)
                if cached:
                    normalized_cached = self.normalizer.normalize_result(cached, section.text, support_language=support_language, target_level=target_level)
                    normalized_cached.quality_warnings = [warning for warning in normalized_cached.quality_warnings if not warning.startswith("section:")]
                    normalized_cached.quality_warnings.append(f"section:{index + 1}/{len(labeled_sections)}")
                    if "analysis_mode:page_batch" not in normalized_cached.quality_warnings:
                        normalized_cached.quality_warnings.append("analysis_mode:page_batch")
                    self.section_analyses.upsert(index, normalized_cached)
                    results.append((index, normalized_cached))
                else:
                    missing_sections.append((index, section))
        else:
            missing_sections = page_sections

        if not missing_sections:
            return results

        page_text = "\n\n".join(section.text for _, section in missing_sections)
        chunks = self.chunker.chunk(page_text)
        page_result = await self.adapter.analyze_document(
            document.id,
            page_text,
            chunks[: self.settings.analysis_model_max_chunks],
            support_language,
            learning_language,
            target_level,
        )

        for index, section in missing_sections:
            section_result = self.normalizer.normalize_result(page_result, section.text, support_language=support_language, target_level=target_level)
            section_result.quality_warnings = [
                warning
                for warning in section_result.quality_warnings
                if not warning.startswith("section:") and warning != "analysis_mode:page_batch"
            ]
            section_result.quality_warnings.append(f"section:{index + 1}/{len(labeled_sections)}")
            section_result.quality_warnings.append("analysis_mode:page_batch")
            if target_level and target_level != "unknown":
                section_result = section_result.model_copy(
                    update={
                        "difficulty": section_result.difficulty.model_copy(
                            update={
                                "overall_level": target_level,
                                "reason": f"Calibrated against your {target_level} reading setting. {section_result.difficulty.reason}",
                            }
                        )
                    }
                )
            if self.section_analyses:
                self.section_analyses.upsert(index, section_result)
            results.append((index, section_result))

        return sorted(results, key=lambda item: item[0])

    def _analysis_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= self.settings.analysis_model_input_chars:
            return normalized
        return normalized[: self.settings.analysis_model_input_chars].rsplit(" ", 1)[0]
