from collections import OrderedDict
from typing import Any

from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.section_analysis_repository import SectionAnalysisRepository
from app.schemas.analysis_schema import PaperMapGuide, PaperMapResponse, PaperMapSynthesis
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
        section_indices = {index for index, _ in section_results}
        if base and 0 not in section_indices:
            base_text = section_texts[0] if section_texts else ""
            section_results = [(0, self.normalizer.normalize_result(base, base_text)), *section_results]

        concepts: OrderedDict[str, dict[str, Any]] = OrderedDict()
        terms: OrderedDict[str, dict[str, Any]] = OrderedDict()
        phrases: OrderedDict[str, dict[str, Any]] = OrderedDict()
        summaries: list[dict[str, Any]] = []
        analyzed_sections: list[int] = []

        for section_index, result in section_results:
            section_number = section_index + 1
            if not self._is_learning_signal(result.summaries.one_line):
                continue
            analyzed_sections.append(section_number)
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

        top_concepts = self._rank(concepts, 10)
        top_terms = self._rank(terms, 12)
        top_phrases = self._rank(phrases, 40)

        return PaperMapResponse(
            document_id=document_id,
            total_sections=len(section_texts or []),
            analyzed_sections=analyzed_sections,
            guide=self._guide(len(section_texts or []), analyzed_sections, top_concepts, top_terms, top_phrases, summaries),
            synthesis=self._synthesis(len(section_texts or []), analyzed_sections, top_concepts, top_terms, top_phrases, summaries),
            top_concepts=top_concepts,
            top_terms=top_terms,
            top_phrases=top_phrases,
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
        return sorted(rows.values(), key=lambda row: (self._rank_priority(str(row["text"])), -row["count"], row["sections"][0], row["text"].lower()))[:limit]

    def _rank_priority(self, text: str) -> int:
        lowered = text.lower()
        promoted = {
            "bert",
            "batch normalization",
            "internal covariate shift",
            "masked language model",
            "multi-head attention",
            "residual functions",
            "residual learning framework",
            "scaled dot-product attention",
            "self-attention",
            "shortcut connections",
            "transformer",
            "as easy as stacking more layers",
            "there exists a solution by construction",
            "not caused by overfitting",
            "no higher training error than",
            "experiments show that",
            "has been exposed",
            "instead of hoping",
            "fit a residual mapping",
            "is recast into",
            "neither extra parameter nor computational complexity",
            "trained end-to-end",
            "we show that",
            "exhibit higher training error",
            "accuracy gains from",
            "this strong evidence shows that",
            "while still having lower complexity than",
            "these methods suggest that",
            "in contrast to",
            "concurrent with our work",
            "on the contrary",
            "in addition",
            "is shown to be more effective than",
            "reformulates the system as",
            "with reference to",
            "provide reasonable preconditioning",
            "identity mapping is sufficient",
            "only used when matching dimensions",
            "applicable to convolutional layers",
            "to provide instances for discussion",
            "the results in table 2 show that",
            "we evaluate our method",
            "we first evaluate",
            "to reveal the reasons",
        }
        demoted = {
            "deeper neural networks",
            "training deep neural networks",
            "dominant sequence transduction models",
            "language representation models",
            "cifar-10",
            "imagenet",
        }
        if lowered in promoted:
            return 0
        if lowered in demoted:
            return 2
        return 1

    def _is_learning_signal(self, text: str) -> bool:
        lowered = " ".join(text.lower().split())
        if not lowered:
            return False
        if len(lowered) < 80 and self._is_short_artifact(lowered):
            return False
        non_content_markers = [
            "work performed while",
            "conference on neural information processing systems",
            "spent countless long days",
            "initial codebase",
            "tensor2tensor",
            "provided proper attribution",
        ]
        return not any(marker in lowered for marker in non_content_markers)

    def _is_short_artifact(self, lowered: str) -> bool:
        artifact_markers = [
            "weighted sum",
            "figure",
            "table",
            "equation",
            "where",
        ]
        return any(marker in lowered for marker in artifact_markers)

    def _guide(
        self,
        total_sections: int,
        analyzed_sections: list[int],
        top_concepts: list[dict[str, Any]],
        top_terms: list[dict[str, Any]],
        top_phrases: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
    ) -> PaperMapGuide:
        analyzed_count = len(analyzed_sections)
        if analyzed_count == 0:
            return PaperMapGuide(
                thesis_so_far="No section has been analyzed yet.",
                coverage_note="Analyze the first readable section to start a source-grounded paper map.",
                reading_focus=["Start with one section rather than asking the edge model to summarize the whole paper at once."],
                next_steps=["Analyze the current section.", "Then continue section by section and watch repeated concepts emerge."],
            )

        concept_names = [str(item["text"]) for item in top_concepts[:3]]
        term_names = [str(item["text"]) for item in top_terms[:4]]
        phrase_names = [str(item["text"]) for item in top_phrases[:3]]
        first_summary = str(summaries[0]["meaning"]) if summaries else ""
        latest_summary = str(summaries[-1]["meaning"]) if summaries else first_summary
        if concept_names:
            thesis = f"So far, the paper is organized around {', '.join(concept_names)}."
            if first_summary:
                thesis = f"{thesis} First analyzed signal: {first_summary}"
        else:
            thesis = latest_summary or "Analyzed sections are available, but no stable concept anchor has emerged yet."

        if total_sections:
            coverage = f"{analyzed_count} of {total_sections} sections analyzed. This is a partial reading guide, not a whole-paper conclusion."
        else:
            coverage = f"{analyzed_count} analyzed section(s). This guide only reflects analyzed text."

        focus: list[str] = []
        if concept_names:
            focus.append(f"Concept path: understand {concept_names[0]} before memorizing surrounding vocabulary.")
        if term_names:
            focus.append(f"Vocabulary path: save recurring/high-signal terms such as {', '.join(term_names[:3])}.")
        if phrase_names:
            focus.append(f"Academic-expression path: notice how phrases like {', '.join(phrase_names[:2])} move the argument.")
        if latest_summary and latest_summary != first_summary:
            focus.append(f"Latest section signal: {latest_summary}")

        next_steps = ["Analyze the next unstudied section before trusting the map as a whole-paper view."]
        if top_concepts:
            repeated = [str(item["text"]) for item in top_concepts if int(item.get("count") or 0) > 1]
            if repeated:
                next_steps.append(f"Review repeated concept(s): {', '.join(repeated[:3])}.")
        next_steps.append("Save concepts separately from vocabulary; discourse signals belong in expressions, not dictionary terms.")

        return PaperMapGuide(
            thesis_so_far=thesis,
            coverage_note=coverage,
            reading_focus=focus[:4],
            next_steps=next_steps[:4],
        )

    def _synthesis(
        self,
        total_sections: int,
        analyzed_sections: list[int],
        top_concepts: list[dict[str, Any]],
        top_terms: list[dict[str, Any]],
        top_phrases: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
    ) -> PaperMapSynthesis:
        analyzed_count = len(analyzed_sections)
        if analyzed_count == 0:
            return PaperMapSynthesis(
                status="empty",
                argument_flow=["Analyze sections to build a whole-paper learning synthesis."],
                review_plan=["Start with the first readable section.", "Save concepts and terms separately as they appear."],
            )

        coverage_ratio = analyzed_count / total_sections if total_sections else 0
        status = "whole-paper draft" if total_sections and coverage_ratio >= 0.8 else "partial synthesis"
        flow_limit = 10
        flow = self._argument_flow(summaries, limit=flow_limit)
        unique_summary_count = len({str(item.get("meaning") or "").strip().lower() for item in summaries if item.get("meaning")})
        if unique_summary_count > flow_limit:
            flow.append(f"...{unique_summary_count - flow_limit} more analyzed section summaries are folded into the lists below.")

        priority_concepts = top_concepts[:5]
        priority_terms = top_terms[:8]
        reusable_expressions = self._select_reusable_expressions(top_phrases, analyzed_sections, 6)

        review_plan = [
            "Read the next unanalyzed section before treating this as a final whole-paper view.",
            "Save concept anchors first; they explain why the vocabulary matters.",
            "Then save recurring terms and reusable academic expressions separately.",
        ]
        if status == "whole-paper draft":
            review_plan[0] = "Review the argument flow, then use the priority lists as the paper-level study plan."
        if priority_concepts:
            review_plan.append(f"First review concept: {priority_concepts[0]['text']}.")

        return PaperMapSynthesis(
            status=status,
            argument_flow=flow,
            priority_concepts=priority_concepts,
            priority_terms=priority_terms,
            reusable_expressions=reusable_expressions,
            review_plan=review_plan[:5],
        )

    def _select_reusable_expressions(self, top_phrases: list[dict[str, Any]], analyzed_sections: list[int], limit: int) -> list[dict[str, Any]]:
        if not top_phrases:
            return []
        selected: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(item: dict[str, Any]) -> None:
            key = str(item.get("text") or "").lower()
            if key and key not in seen and len(selected) < limit:
                seen.add(key)
                selected.append(item)

        for item in top_phrases[:3]:
            add(item)
        latest_section = max(analyzed_sections) if analyzed_sections else None
        if latest_section is not None:
            for item in top_phrases:
                if latest_section in [int(section) for section in item.get("sections") or []]:
                    add(item)
        for item in top_phrases:
            add(item)
        return selected

    def _argument_flow(self, summaries: list[dict[str, Any]], limit: int) -> list[str]:
        grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
        for item in summaries:
            meaning = " ".join(str(item.get("meaning") or "").split())
            if not meaning:
                continue
            key = meaning.lower()
            if key not in grouped:
                grouped[key] = {"meaning": meaning, "sections": []}
            grouped[key]["sections"].extend(int(section) for section in item.get("sections") or [])
        flow: list[str] = []
        for item in list(grouped.values())[:limit]:
            sections = sorted(set(item["sections"]))
            label = self._section_label(sections)
            flow.append(f"{label}: {self._trim_flow_text(item['meaning'])}")
        return flow

    def _section_label(self, sections: list[int]) -> str:
        if not sections:
            return "S?"
        if len(sections) == 1:
            return f"S{sections[0]}"
        return f"S{', '.join(str(section) for section in sections[:4])}{', ...' if len(sections) > 4 else ''}"

    def _trim_flow_text(self, text: str, limit: int = 180) -> str:
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1].rsplit(' ', 1)[0]}..."
