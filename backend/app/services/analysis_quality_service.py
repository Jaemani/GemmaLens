from app.schemas.analysis_schema import AnalysisResult


class AnalysisQualityService:
    def inspect(self, result: AnalysisResult, document_text: str) -> list[str]:
        warnings: list[str] = []
        text_lower = document_text.lower()

        if not (3 <= len(result.terms) <= 20):
            warnings.append(f"term_count_out_of_range:{len(result.terms)}")
        if not (2 <= len(result.phrases) <= 20):
            warnings.append(f"phrase_count_out_of_range:{len(result.phrases)}")
        if result.summaries.one_line == "Summary not provided.":
            warnings.append("missing_one_line_summary")
        if result.summaries.simple == "Simple summary not provided.":
            warnings.append("missing_simple_summary")
        if result.summaries.academic == "Academic summary not provided.":
            warnings.append("missing_academic_summary")

        seen_terms: set[str] = set()
        for term in result.terms:
            key = term.term.lower().strip()
            if key in seen_terms:
                warnings.append(f"duplicate_term:{term.term}")
            seen_terms.add(key)
            if not term.meaning.strip():
                warnings.append(f"empty_term_meaning:{term.term}")
            if term.source_sentence and term.source_sentence.lower() not in text_lower:
                warnings.append(f"source_sentence_not_in_document:{term.term}")
            if term.term.lower() not in term.source_sentence.lower():
                warnings.append(f"term_not_in_source_sentence:{term.term}")
            if term.confidence < 0.4 and term.should_save:
                warnings.append(f"low_confidence_should_save:{term.term}")

        for phrase in result.phrases:
            if not phrase.explanation.strip():
                warnings.append(f"empty_phrase_explanation:{phrase.phrase}")
            if phrase.source_sentence and phrase.source_sentence.lower() not in text_lower:
                warnings.append(f"phrase_source_sentence_not_in_document:{phrase.phrase}")
            if phrase.phrase.lower() not in phrase.source_sentence.lower():
                warnings.append(f"phrase_not_in_source_sentence:{phrase.phrase}")

        return warnings
