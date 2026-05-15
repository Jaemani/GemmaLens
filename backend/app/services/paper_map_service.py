from collections import OrderedDict
from typing import Any

from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.section_analysis_repository import SectionAnalysisRepository
from app.schemas.analysis_schema import PaperMapResponse
from app.services.analysis_normalization_service import AnalysisNormalizationService


class PaperMapService:
    def __init__(self, analyses: AnalysisRepository, section_analyses: SectionAnalysisRepository):
        self.analyses = analyses
        self.section_analyses = section_analyses
        self.normalizer = AnalysisNormalizationService()

    def build(self, document_id: str, section_texts: list[str] | None = None) -> PaperMapResponse:
        section_results = self.section_analyses.list_results(document_id)
        if section_texts:
            section_results = [
                (index, self.normalizer.normalize_result(result, section_texts[index]))
                for index, result in section_results
                if 0 <= index < len(section_texts)
            ]
        base = self.analyses.get_result(document_id)
        if base and not section_results:
            base_text = section_texts[0] if section_texts else ""
            section_results = [(0, self.normalizer.normalize_result(base, base_text))]

        concepts: OrderedDict[str, dict[str, Any]] = OrderedDict()
        terms: OrderedDict[str, dict[str, Any]] = OrderedDict()
        phrases: OrderedDict[str, dict[str, Any]] = OrderedDict()
        summaries: list[dict[str, Any]] = []

        for section_index, result in section_results:
            section_number = section_index + 1
            summaries.append(
                {
                    "text": f"Section {section_number}",
                    "meaning": result.summaries.one_line,
                    "sections": [section_number],
                    "count": 1,
                }
            )
            for concept in result.concepts:
                self._add(
                    concepts,
                    concept.concept,
                    concept.explanation or concept.why_it_matters,
                    section_number,
                )
            for term in result.terms:
                self._add(terms, term.term, term.meaning, section_number)
            for phrase in result.phrases:
                self._add(phrases, phrase.phrase, phrase.explanation, section_number)

        return PaperMapResponse(
            document_id=document_id,
            total_sections=len(section_texts or []),
            analyzed_sections=[index + 1 for index, _ in section_results],
            top_concepts=self._rank(concepts, 10),
            top_terms=self._rank(terms, 12),
            top_phrases=self._rank(phrases, 12),
            section_summaries=summaries[:20],
        )

    def _add(self, rows: OrderedDict[str, dict[str, Any]], text: str, meaning: str, section_number: int) -> None:
        text = " ".join(text.split())
        if not text:
            return
        key = text.lower()
        if key not in rows:
            rows[key] = {"text": text, "meaning": meaning, "sections": [], "count": 0}
        rows[key]["count"] += 1
        if section_number not in rows[key]["sections"]:
            rows[key]["sections"].append(section_number)
        if not rows[key]["meaning"] and meaning:
            rows[key]["meaning"] = meaning

    def _rank(self, rows: OrderedDict[str, dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        return sorted(rows.values(), key=lambda row: (-row["count"], row["sections"][0], row["text"].lower()))[:limit]
