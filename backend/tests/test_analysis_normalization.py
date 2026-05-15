from app.llm.json_utils import extract_json_object
from app.services.academic_text_service import AcademicTextService
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
    assert result.summaries.simple.startswith("Although previous studies")


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


def test_normalizer_scales_decimal_difficulty_scores():
    payload = {
        "difficulty": {
            "overall_level": "C1",
            "lexical_difficulty": 0.7,
            "syntax_difficulty": 0.8,
            "domain_difficulty": 0.9,
            "reason": "decimal scores from model",
        }
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "doc-3", DOCUMENT_TEXT)

    assert result.difficulty.lexical_difficulty == 7
    assert result.difficulty.syntax_difficulty == 8
    assert result.difficulty.domain_difficulty == 9
    assert result.summaries.one_line.startswith("Although previous studies")


def test_normalizer_discards_items_not_grounded_in_source():
    payload = {
        "terms": [
            {"term": "sleep deprivation", "meaning": "not enough sleep"},
            {"term": "Stochastic Gradient Descent", "meaning": "not in this passage"},
            {"term": "string", "meaning": "placeholder"},
        ],
        "phrases": [
            {"phrase": "remains unclear", "explanation": "marks uncertainty"},
            {"phrase": "to summarize the above", "explanation": "not in this passage"},
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "doc-4", DOCUMENT_TEXT)

    assert [term.term for term in result.terms] == ["sleep deprivation"]
    assert [phrase.phrase for phrase in result.phrases] == ["remains unclear"]


def test_normalizer_keeps_source_grounded_concepts():
    payload = {
        "terms": [{"term": "cognitive performance", "meaning": "mental task performance", "domain_relevance": "high"}],
        "concepts": [
            {
                "concept": "cognitive performance",
                "explanation": "A concept needed to understand what sleep loss may affect.",
                "source_sentence": "wrong sentence",
                "related_terms": ["sleep deprivation"],
                "why_it_matters": "It connects the paper's topic to measurable learning outcomes.",
                "references": [],
            },
            {"concept": "invented construct", "explanation": "not grounded"},
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "doc-5", DOCUMENT_TEXT)

    assert [concept.concept for concept in result.concepts] == ["cognitive performance"]
    assert result.concepts[0].source_sentence.startswith("Although previous studies")


def test_academic_text_service_starts_after_front_matter_abstract():
    raw_text = """
arXiv:1502.03167v3 [cs.LG] 2 Mar 2015
Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift
Sergey Ioffe Google Inc., sioffe@google.com
Christian Szegedy Google Inc., szegedy@google.com
Abstract
Training Deep Neural Networks is complicated by the fact that the distribution of each layer's inputs changes during training.
1 Introduction
Deep learning has dramatically advanced.
"""

    readable = AcademicTextService().readable_section(raw_text)

    assert readable.startswith("Training Deep Neural Networks")
    assert "sioffe@google.com" not in readable
    assert not readable.startswith("arXiv")
