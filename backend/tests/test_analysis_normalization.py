from app.llm.json_utils import extract_json_object
from app.services.analysis_normalization_service import AnalysisNormalizationService

DOCUMENT_TEXT = (
    "Although previous studies have suggested a correlation between sleep deprivation "
    "and reduced cognitive performance, the extent to which these findings generalize "
    "across real-world learning environments remains unclear. To address this gap, "
    "we analyze longitudinal study logs collected from undergraduate students over a "
    "six-week period."
)


def test_normalizer_repairs_common_model_output_typos():
    payload = {
        "domain": {"domain": "education", "document_type": "study", "confidence": "0.9"},
        "difficulty": {
            "overall_level": "c1",
            "lexical_difficulty": "7",
            "syntax_difficulty": 11,
            "domain_difficulty": "bad",
            "reason": "dense syntax",
        },
        "terms": [
            {
                "text": "sleep deprivation",
                "meaning": "not enough sleep",
                "domain_relevance": "important",
                "difficulty": "moderate",
                "source_sentence": "wrong sentence",
                "priority": "must know",
                "confidence": "0.83",
            },
            {
                "term": "sleep deprivation",
                "meaning": "duplicate should be removed",
            },
            {
                "term": "generalize",
                "context_meaning": "apply findings beyond the original setting",
                "domain_relevance": "medium",
                "difficulty": "advanced",
            },
        ],
        "phrases": [
            {
                "phrase": "to address this gap",
                "function": "purpose",
                "meaning": "connects the gap to the method",
                "confidence": 0.7,
            }
        ],
        "sentences": [
            {
                "sentence": "To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.",
                "core_structure": "To address X, we analyze Y.",
            }
        ],
        "summaries": {"one_line": "A study about sleep and learning."},
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "doc-1", DOCUMENT_TEXT)

    assert result.document_id == "doc-1"
    assert result.domain.primary_domain == "education"
    assert result.domain.document_type == "unknown"
    assert result.difficulty.overall_level == "C1"
    assert result.difficulty.syntax_difficulty == 10
    assert result.difficulty.domain_difficulty == 5
    assert [term.term for term in result.terms] == ["sleep deprivation", "generalize"]
    assert result.terms[0].source_sentence.startswith("Although previous studies")
    assert result.terms[0].learning_priority == "must_review"
    assert result.terms[1].difficulty == "hard"
    assert result.phrases[0].function == "method"
    assert result.summaries.simple == "Simple summary not provided."


def test_markdown_wrapped_json_can_be_extracted_and_normalized():
    raw = """
```json
{
  "terms": [{"term": "longitudinal study", "meaning": "observing the same subjects over time"}],
  "phrases": [{"phrase": "remains unclear", "function": "gap", "explanation": "marks uncertainty"}],
  "sentences": [],
  "summaries": {"academic_summary": "The passage frames a research gap and method."}
}
```
"""
    payload = extract_json_object(raw)
    result = AnalysisNormalizationService().normalize_payload(payload, "doc-2", DOCUMENT_TEXT)

    assert result.terms[0].term == "longitudinal study"
    assert result.terms[0].source_sentence.startswith("To address this gap")
    assert result.phrases[0].function == "limitation"
    assert result.sentences[0].sentence.startswith("Although previous studies")
    assert "term_count_out_of_range:1" in result.quality_warnings
