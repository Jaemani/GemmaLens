import re

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


def test_normalizer_trims_long_transcript_source_context():
    transcript = (
        "hello and welcome to this long tutorial about sequence models " * 10
        + "now we explain Transformer attention and why it replaced many recurrent neural networks "
        + "then we continue with many extra words " * 20
    )
    payload = {
        "terms": [
            {
                "term": "Transformer attention",
                "meaning": "attention mechanism used in transformer models",
                "domain_relevance": "high",
                "source_sentence": transcript,
            }
        ],
        "concepts": [
            {
                "concept": "Transformer attention",
                "explanation": "A core idea in transformer models.",
                "source_sentence": transcript,
            }
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "video-1", transcript)

    assert len(result.terms[0].source_sentence) <= 430
    assert "Transformer attention" in result.terms[0].source_sentence
    assert len(result.concepts[0].source_sentence) <= 430


def test_normalizer_drops_generic_model_phrases_from_terms_and_concepts():
    document = (
        "The best performing models also connect the encoder and decoder through an attention mechanism. "
        "Dominant sequence transduction models are based on complex recurrent or convolutional neural networks."
    )
    payload = {
        "terms": [
            {"term": "the best performing models", "meaning": "generic phrase"},
            {"term": "or convolutional neural networks", "meaning": "technical architecture"},
            {"term": "Introduction Recurrent", "meaning": "section artifact"},
        ],
        "concepts": [
            {"concept": "the best performing models", "explanation": "generic phrase"},
            {"concept": "dominant sequence transduction models", "explanation": "model family for sequence tasks"},
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "doc-6", document)

    assert [term.term for term in result.terms] == ["convolutional neural networks"]
    assert [concept.concept for concept in result.concepts] == ["sequence transduction models"]


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


def test_academic_text_service_repairs_pdf_hyphen_fragments():
    raw_text = """
Abstract
We introduce a new language representa- tion model called BERT.
Unlike recent language repre- sentation models, BERT is designed to pre- train deep bidirectional representations.
"""

    readable = AcademicTextService().readable_section(raw_text)

    assert "representation model" in readable
    assert "representation models" in readable
    assert "pretrain" in readable
    assert not re.search(r"\btion model\b", readable)
    assert not re.search(r"\bsentation models\b", readable)


def test_batch_norm_real_paper_snippet_keeps_concepts_and_fragments_separate():
    document = (
        "Training Deep Neural Networks is complicated by the fact that the distribution of each layer's inputs changes during training, "
        "as the parameters of the previous layers change. We refer to this phenomenon as internal covariate shift, and address the problem "
        "by normalizing layer inputs. Batch Normalization allows us to use much higher learning rates and be less careful about initialization."
    )
    payload = {
        "terms": [
            {"term": "Training Deep Neural Networks", "meaning": "generic title-like fragment"},
            {"term": "inputs changes during training", "meaning": "bad noun fragment"},
            {"term": "Batch Normalization", "meaning": "normalizes layer inputs"},
        ],
        "concepts": [
            {"concept": "Training Deep Neural Networks", "explanation": "generic title-like fragment"},
            {"concept": "inputs changes during training", "explanation": "bad noun fragment"},
            {"concept": "internal covariate shift", "explanation": "layer input distributions change during training"},
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "batch-norm", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}

    assert "Training Deep Neural Networks" not in terms
    assert "inputs changes during training" not in terms
    assert "Training Deep Neural Networks" not in concepts
    assert "inputs changes during training" not in concepts
    assert "Batch Normalization" in terms
    assert "internal covariate shift" in concepts


def test_bert_real_paper_snippet_drops_pdf_artifacts_and_unhelpful_model_terms():
    document = (
        "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. "
        "Unlike recent language representation models, BERT is designed to pretrain deep bidirectional representations from unlabeled text by jointly "
        "conditioning on both left and right context in all layers. The pre-trained BERT model can be fine-tuned with just one additional output layer."
    )
    payload = {
        "terms": [
            {"term": "tion model", "meaning": "PDF split artifact"},
            {"term": "sentation models", "meaning": "PDF split artifact"},
            {"term": "pre-trained bert model", "meaning": "generic local noun phrase"},
            {"term": "BERT", "meaning": "Bidirectional Encoder Representations from Transformers"},
        ],
        "concepts": [
            {"concept": "new language representation model", "explanation": "generic local noun phrase"},
            {"concept": "Bidirectional Encoder Representations", "explanation": "partial expansion"},
            {"concept": "BERT", "explanation": "bidirectional Transformer representation model"},
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "bert", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}

    assert "tion model" not in terms
    assert "sentation models" not in terms
    assert "pre-trained bert model" not in terms
    assert "new language representation model" not in concepts
    assert "BERT" in terms
    assert "BERT" in concepts
