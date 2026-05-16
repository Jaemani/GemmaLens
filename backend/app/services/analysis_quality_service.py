from app.schemas.analysis_schema import AnalysisResult
from app.services.text_cleanup_service import normalize_pdf_ligatures


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
            if term.source_sentence and not self._source_in_text(term.source_sentence, text_lower):
                warnings.append(f"source_sentence_not_in_document:{term.term}")
            if not self._value_supported_by_source(term.term, term.source_sentence):
                warnings.append(f"term_not_in_source_sentence:{term.term}")
            if term.confidence < 0.4 and term.should_save:
                warnings.append(f"low_confidence_should_save:{term.term}")

        for phrase in result.phrases:
            if not phrase.explanation.strip():
                warnings.append(f"empty_phrase_explanation:{phrase.phrase}")
            if phrase.source_sentence and not self._source_in_text(phrase.source_sentence, text_lower):
                warnings.append(f"phrase_source_sentence_not_in_document:{phrase.phrase}")
            if phrase.phrase.lower() not in phrase.source_sentence.lower():
                warnings.append(f"phrase_not_in_source_sentence:{phrase.phrase}")

        return warnings

    def _source_in_text(self, source: str, text_lower: str) -> bool:
        source_lower = normalize_pdf_ligatures(source).lower()
        normalized_text = normalize_pdf_ligatures(text_lower).lower()
        if source_lower in normalized_text:
            return True
        trimmed = source_lower.strip(". ")
        if trimmed and trimmed in normalized_text:
            return True
        source_compact = " ".join(source_lower.split())
        text_compact = " ".join(normalized_text.split())
        return bool(source_compact and source_compact.strip(". ") in text_compact)

    def _value_supported_by_source(self, value: str, source: str) -> bool:
        value_lower = value.lower()
        source_lower = source.lower()
        if value_lower in source_lower:
            return True
        support_aliases = {
            "masked lm": "mask lm",
            "segment embedding": "learned embedding",
            "token embeddings": "token",
            "left-to-right language models": "left-to-right",
            "right-to-left language models": "right-to-left",
        }
        alias = support_aliases.get(value_lower)
        if alias and alias in source_lower:
            return True
        value_tokens = self._support_tokens(value_lower)
        source_tokens = self._support_tokens(source_lower)
        return bool(value_tokens) and value_tokens.issubset(source_tokens)

    def _support_tokens(self, value: str) -> set[str]:
        stopwords = {"the", "a", "an", "and", "or", "of", "on", "in", "to", "for", "by", "with", "set"}
        tokens = set()
        for token in value.replace("/", " ").replace("-", " ").split():
            cleaned = "".join(ch for ch in token if ch.isalnum()).lower()
            if not cleaned or cleaned in stopwords or len(cleaned) < 3:
                continue
            tokens.add(self._light_stem(cleaned))
        return tokens

    def _light_stem(self, token: str) -> str:
        if token.endswith("ally") and len(token) > 7:
            return f"{token[:-4]}al"
        for suffix in ("ing", "ed", "s"):
            if len(token) > len(suffix) + 3 and token.endswith(suffix):
                return token[: -len(suffix)]
        return token
