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


def test_academic_text_service_repairs_short_pdf_hyphen_fragments():
    raw_text = """
Abstract
In- stead of fitting the full mapping, residual networks fit a residual mapping.
"""

    readable = AcademicTextService().readable_section(raw_text)

    assert "Instead of fitting" in readable
    assert "In- stead" not in readable


def test_academic_text_service_repairs_pdf_ligatures():
    raw_text = """
Abstract
Deeper neural networks are more difﬁcult to train.
We provide comprehensive empirical evidence showing the beneﬁt of residual functions.
"""

    readable = AcademicTextService().readable_section(raw_text)

    assert "difficult" in readable
    assert "benefit" in readable
    assert "difﬁcult" not in readable
    assert "beneﬁt" not in readable


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


def test_attention_paper_snippet_keeps_discourse_signals_out_of_terms():
    document = (
        "The best performing models also connect the encoder and decoder through an attention mechanism. "
        "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, "
        "dispensing with recurrence and convolutions entirely. In these models, self-attention is used to compute "
        "representations of sequence transduction inputs and outputs. This allows for significantly more parallelization "
        "and helps draw global dependencies between input and output."
    )
    payload = {
        "terms": [
            {"term": "the best performing models", "meaning": "generic discourse signal"},
            {"term": "Transformer", "meaning": "attention-only architecture"},
        ],
        "concepts": [
            {"concept": "the best performing models", "explanation": "generic discourse signal"},
            {"concept": "self-attention", "explanation": "connects sequence positions"},
        ],
        "sentences": [],
        "summaries": {"one_line": document.split(".")[0] + ".", "simple": document.split(".")[0] + ".", "academic": document.split(".")[0] + "."},
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "attention", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "the best performing models" not in {item.lower() for item in terms}
    assert "the best performing models" not in {item.lower() for item in concepts}
    assert {"Transformer", "self-attention", "sequence transduction"}.issubset(terms)
    assert {"Transformer", "self-attention", "sequence transduction"}.issubset(concepts)
    assert "based solely on" in phrases
    assert result.summaries.one_line.startswith("The paper introduces the Transformer")
    assert result.sentences[0].core_structure == "X is based solely on Y, dispensing with Z."


def test_attention_intro_summary_replaces_long_first_sentence_copy():
    document = (
        "1 Introduction Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular, "
        "have been firmly established as state of the art approaches in sequence modeling and transduction problems such as "
        "language modeling and machine translation. Recurrent models typically factor computation along the symbol positions."
    )
    payload = {
        "terms": [],
        "phrases": [],
        "sentences": [],
        "summaries": {
            "one_line": document.split(".")[0] + ".",
            "simple": document.split(".")[0] + ".",
            "academic": document.split(".")[0] + ".",
        },
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "attention-intro", document)

    assert result.summaries.one_line == "This section explains recurrent sequence-modeling baselines before the Transformer contrast."
    assert "background" in result.summaries.study_notes[0].lower()


def test_attention_architecture_summary_replaces_figure_caption_copy():
    document = (
        "Figure 1: The Transformer - model architecture. The encoder is composed of a stack of 6 identical layers. "
        "Each layer has two sub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, "
        "position-wise fully connected feed-forward network. We employ a residual connection around each of the two sub-layers, "
        "followed by layer normalization. The decoder is also composed of a stack of 6 identical layers."
    )
    payload = {
        "terms": [],
        "phrases": [],
        "sentences": [],
        "summaries": {
            "one_line": "Figure 1: The Transformer - model architecture.",
            "simple": "Figure 1: The Transformer - model architecture.",
            "academic": "Figure 1: The Transformer - model architecture.",
        },
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "attention-architecture", document)

    assert result.summaries.one_line == "This section explains the Transformer's encoder-decoder stack and sub-layer structure."
    assert "architecture parts" in result.summaries.study_notes[0]


def test_attention_formula_summary_replaces_equation_fragment_copy():
    document = (
        "Scaled Dot-Product Attention. The input consists of queries and keys of dimension dk, and values of dimension dv. "
        "We compute the dot products of the query with all keys, divide each by sqrt(dk), and apply a softmax function to obtain "
        "the weights on the values. In practice, we compute the attention function on a set of queries simultaneously."
    )
    payload = {
        "terms": [],
        "phrases": [],
        "sentences": [],
        "summaries": {
            "one_line": "The output is computed as a weighted sum 3",
            "simple": "The output is computed as a weighted sum 3",
            "academic": "The output is computed as a weighted sum 3",
        },
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "attention-formula", document)

    assert result.summaries.one_line == "This section explains scaled dot-product attention using queries, keys, values, softmax, and scaling."
    assert "Q, K, and V" in result.summaries.study_notes[0]


def test_multi_head_attention_summary_replaces_formula_lead_sentence():
    document = (
        "To counteract this effect, we scale the dot products by 1/sqrt(dk). "
        "Multi-Head Attention. Instead of performing a single attention function with dmodel-dimensional keys, values and queries, "
        "we found it beneficial to linearly project the queries, keys and values h times with different, learned linear projections. "
        "On each of these projected versions of queries, keys and values we then perform the attention function in parallel."
    )
    payload = {
        "terms": [],
        "phrases": [],
        "sentences": [],
        "summaries": {
            "one_line": "To counteract this effect, we scale the dot products by 1/sqrt(dk).",
            "simple": "To counteract this effect, we scale the dot products by 1/sqrt(dk).",
            "academic": "To counteract this effect, we scale the dot products by 1/sqrt(dk).",
        },
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "multi-head", document)

    assert result.summaries.one_line == "This section explains multi-head attention as parallel learned projections of queries, keys, and values."
    assert "architecture concept" in result.summaries.study_notes[2]


def test_resnet_real_paper_snippet_repairs_fragments_and_summary():
    document = (
        "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks "
        "that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions "
        "with reference to the layer inputs, instead of learning unreferenced functions. We provide comprehensive empirical evidence "
        "showing that these residual networks are easier to optimize, and can gain accuracy from considerably increased depth."
    )
    payload = {
        "terms": [
            {"term": "residual learning framework", "meaning": "method for deeper networks"},
            {"term": "to ease the training", "meaning": "bad verb fragment"},
            {"term": "of networks", "meaning": "bad prepositional fragment"},
        ],
        "concepts": [
            {"concept": "residual learning framework", "explanation": "main method"},
            {"concept": "to ease the training", "explanation": "bad verb fragment"},
            {"concept": "of networks", "explanation": "bad prepositional fragment"},
        ],
        "sentences": [],
        "summaries": {
            "one_line": "Deeper neural networks are more difficult to train.",
            "simple": "Deeper neural networks are more difficult to train.",
            "academic": "Deeper neural networks are more difficult to train.",
        },
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}

    assert "to ease the training" not in terms
    assert "of networks" not in terms
    assert "to ease the training" not in concepts
    assert "of networks" not in concepts
    assert {"residual learning framework", "residual functions"}.issubset(terms)
    assert {"residual learning framework", "residual functions"}.issubset(concepts)
    assert "residual learning framework" not in {phrase.phrase for phrase in result.phrases}
    assert "to ease the training of" in {phrase.phrase for phrase in result.phrases}
    assert result.summaries.one_line == "The paper introduces residual learning to train much deeper image-recognition networks."
    assert result.sentences[0].core_structure == "We present X to ease Y."


def test_resnet_ligature_phrase_is_normalized_for_learning_output():
    document = (
        "Deeper neural networks are more difﬁcult to train. "
        "We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously."
    )
    payload = {
        "phrases": [{"phrase": "more difﬁcult to train", "explanation": "bad ligature should be normalized"}],
        "terms": [{"term": "residual learning framework", "meaning": "method for deeper networks"}],
        "concepts": [{"concept": "residual learning framework", "explanation": "main method"}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-ligature", document)

    assert "more difficult to train" in {phrase.phrase for phrase in result.phrases}
    assert "more difﬁcult to train" not in {phrase.phrase for phrase in result.phrases}
    assert all("ﬁ" not in term.source_sentence for term in result.terms)


def test_resnet_depth_motivation_section_rejects_fragments():
    document = (
        "Recent evidence reveals that network depth is of crucial importance, and the leading results on the challenging ImageNet dataset "
        "all exploit very deep models. Driven by the significance of depth, a question arises: Is learning better networks as easy as stacking "
        "more layers? An obstacle to answering this question was the notorious problem of vanishing/exploding gradients, which hamper convergence "
        "from the beginning. This problem, however, has been largely addressed by normalized initialization and intermediate normalization layers, "
        "which enable networks with tens of layers to start converging for stochastic gradient descent (SGD) with backpropagation. When deeper "
        "networks are able to start converging, a degradation problem has been exposed: with the network depth increasing, accuracy gets saturated "
        "and then degrades rapidly. Unexpectedly, such degradation is not caused by overfitting, and adding more layers to a suitably deep model "
        "leads to higher training error."
    )
    payload = {
        "terms": [
            {"term": "reveals that network", "meaning": "bad fragment"},
            {"term": "deeper network", "meaning": "bad fragment"},
            {"term": "has higher training", "meaning": "bad fragment"},
        ],
        "concepts": [
            {"concept": "reveals that network", "explanation": "bad fragment"},
            {"concept": "has higher training", "explanation": "bad fragment"},
        ],
        "summaries": {"one_line": document.split(".")[0] + ".", "simple": document.split(".")[0] + ".", "academic": document.split(".")[0] + "."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-depth", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "reveals that network" not in terms
    assert "deeper network" not in terms
    assert "has higher training" not in terms
    assert "reveals that network" not in concepts
    assert "has higher training" not in concepts
    assert {"very deep models", "degradation problem", "vanishing/exploding gradients", "higher training error"}.issubset(terms)
    assert {"very deep models", "degradation problem", "higher training error"}.issubset(concepts)
    assert {"as easy as stacking more layers", "not caused by overfitting", "leads to higher training error"}.issubset(phrases)
    assert "very deep models" not in phrases
    assert result.summaries.one_line == "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize."
    assert result.sentences[0].core_structure == "Is learning better X as easy as doing Y?"


def test_resnet_constructed_solution_section_rejects_fragments():
    document = (
        "The degradation of training accuracy indicates that not all systems are similarly easy to optimize. "
        "Let us consider a shallower architecture and its deeper counterpart that adds more layers onto it. "
        "There exists a solution by construction to the deeper model: the added layers are identity mapping, "
        "and the other layers are copied from the learned shallower model. The existence of this constructed solution "
        "indicates that a deeper model should produce no higher training error than its shallower counterpart. "
        "But experiments show that our current solvers on hand are unable to find solutions."
    )
    payload = {
        "terms": [
            {"term": "degradation", "meaning": "bad short fragment"},
            {"term": "training", "meaning": "too broad"},
            {"term": "deeper model", "meaning": "generic fragment"},
            {"term": "learned shallower model", "meaning": "local fragment"},
        ],
        "concepts": [
            {"concept": "degradation", "explanation": "bad short fragment"},
            {"concept": "training", "explanation": "too broad"},
            {"concept": "deeper model", "explanation": "generic fragment"},
        ],
        "summaries": {"one_line": document.split(".")[0] + ".", "simple": document.split(".")[0] + ".", "academic": document.split(".")[0] + "."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-construct", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "degradation" not in terms
    assert "training" not in terms
    assert "deeper model" not in terms
    assert "learned shallower model" not in terms
    assert "deeper model" not in concepts
    assert {"constructed solution", "shallower architecture", "identity mapping", "higher training error"}.issubset(terms)
    assert {"constructed solution", "shallower architecture"}.issubset(concepts)
    assert {"There exists a solution by construction", "no higher training error than", "experiments show that"}.issubset(phrases)
    assert result.summaries.one_line == "This section explains why degradation is surprising: a deeper model should be able to copy a shallower one."
    assert result.sentences[0].core_structure == "There exists a solution by construction to X: A are B, and C are copied from D."


def test_resnet_residual_block_section_recovers_method_structure():
    document = (
        "In this paper, we address the degradation problem by introducing a deep residual learning framework. "
        "Instead of hoping each few stacked layers directly fit a desired underlying mapping, we explicitly let these layers fit a residual mapping. "
        "Formally, denoting the desired underlying mapping as H(x), we let the stacked nonlinear layers fit another mapping of F(x) := H(x)-x. "
        "The original mapping is recast into F(x)+x. We hypothesize that it is easier to optimize the residual mapping than to optimize the original, "
        "unreferenced mapping. The formulation of F(x)+x can be realized by feedforward neural networks with shortcut connections. "
        "Shortcut connections are those skipping one or more layers. In our case, the shortcut connections simply perform identity mapping, "
        "and their outputs are added to the outputs of the stacked layers. Identity shortcut connections add neither extra parameter nor computational complexity."
    )
    payload = {
        "terms": [
            {"term": "by feedforward neural networks", "meaning": "bad prepositional fragment"},
            {"term": "Residual learning", "meaning": "heading-level duplicate"},
        ],
        "concepts": [{"concept": "by feedforward neural networks", "explanation": "bad prepositional fragment"}],
        "phrases": [],
        "summaries": {"one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize."},
        "sentences": [
            {
                "sentence": "Instead of hoping each few stacked layers directly fit a desired underlying mapping, we explicitly let these layers fit a residual mapping.",
                "core_structure": "Main claim + explanation.",
            }
        ],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-block", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "by feedforward neural networks" not in terms
    assert "by feedforward neural networks" not in concepts
    assert "Residual learning" not in terms
    assert {"residual mapping", "underlying mapping", "F(x)+x", "shortcut connections", "identity shortcut connections"}.issubset(terms)
    assert {"residual mapping", "underlying mapping", "F(x)+x", "identity shortcut connections"}.issubset(concepts)
    assert {"fit a residual mapping", "is recast into", "neither extra parameter nor computational complexity"}.issubset(phrases)
    assert "shortcut connections" not in phrases
    assert result.summaries.one_line == "This section defines the residual block: learn F(x), add back x, and implement it with shortcut connections."
    assert result.sentences[0].core_structure == "Instead of hoping A directly fits B, we let A fit C."


def test_resnet_experiment_claim_section_rejects_fragments():
    document = (
        "We show that: 1) Our extremely deep residual nets are easy to optimize, but the counterpart “plain” nets exhibit higher training error "
        "when the depth increases; 2) Our deep residual nets can easily enjoy accuracy gains from greatly increased depth, producing results "
        "substantially better than previous networks. Similar phenomena are also shown on the CIFAR-10 set, suggesting that the optimization "
        "difficulties and the effects of our method are not just akin to a particular dataset. On the ImageNet classification dataset, we obtain "
        "excellent results by extremely deep residual nets. Our 152-layer residual net is the deepest network ever presented on ImageNet, while "
        "still having lower complexity than VGG nets. Our ensemble has 3.57% top-5 error on the ImageNet test set. This strong evidence shows "
        "that the residual learning principle is generic and has excellent generalization performance."
    )
    payload = {
        "terms": [
            {"term": "exhibit higher training", "meaning": "bad fragment"},
            {"term": "better than previous networks", "meaning": "bad fragment"},
            {"term": "effects of our method", "meaning": "bad fragment"},
            {"term": "present successfully trained models", "meaning": "bad fragment"},
        ],
        "concepts": [
            {"concept": "exhibit higher training", "explanation": "bad fragment"},
            {"concept": "effects of our method", "explanation": "bad fragment"},
        ],
        "phrases": [],
        "summaries": {"one_line": document.split(".")[0] + "."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-results", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "exhibit higher training" not in terms
    assert "better than previous networks" not in terms
    assert "effects of our method" not in concepts
    assert {"plain nets", "accuracy gains", "top-5 error", "generalization performance"}.issubset(terms)
    assert {"plain nets", "accuracy gains", "generalization performance"}.issubset(concepts)
    assert {"We show that", "exhibit higher training error", "accuracy gains from", "This strong evidence shows that"}.issubset(phrases)
    assert result.summaries.one_line == "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth."
    assert result.sentences[0].core_structure == "We show that: 1) A, but B; 2) C."


def test_resnet_related_work_section_separates_background_from_method():
    document = (
        "For vector quantization, encoding residual vectors is shown to be more effective than encoding original vectors. "
        "For solving Partial Differential Equations, the widely used Multigrid method reformulates the system as subproblems at multiple scales, "
        "where each subproblem is responsible for the residual solution between a coarser and a finer scale. "
        "An alternative to Multigrid is hierarchical basis preconditioning, which relies on variables that represent residual vectors between two scales. "
        "These methods suggest that a good reformulation or preconditioning can simplify the optimization. "
        "Shortcut Connections. Practices and theories that lead to shortcut connections have been studied for a long time. "
        "Concurrent with our work, highway networks present shortcut connections with gating functions. "
        "These gates are data-dependent and have parameters, in contrast to our identity shortcuts that are parameter-free. "
        "When a gated shortcut is closed, the layers in highway networks represent non-residual functions."
    )
    payload = {
        "terms": [
            {"term": "widely used multigrid method", "meaning": "bad adjective-heavy fragment"},
            {"term": "early practice of training", "meaning": "bad local fragment"},
        ],
        "concepts": [{"concept": "widely used multigrid method", "explanation": "bad adjective-heavy fragment"}],
        "phrases": [{"phrase": "encoding residual vectors", "function": "method", "explanation": "too narrow as only phrase"}],
        "summaries": {"one_line": "For vector quantization, encoding residual vectors is shown to be more effective than encoding original vectors."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-related", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "widely used multigrid method" not in terms
    assert "early practice of training" not in terms
    assert {"residual vectors", "Multigrid method", "hierarchical basis preconditioning", "highway networks", "gating functions"}.issubset(terms)
    assert {"residual vectors", "shortcut connections", "highway networks", "identity shortcuts"}.issubset(concepts)
    assert {"These methods suggest that", "Concurrent with our work", "in contrast to"}.issubset(phrases)
    assert result.summaries.one_line == "This related-work section connects ResNet to residual representations and shortcut-connection methods."
    assert result.sentences[0].core_structure == "These methods suggest that X can Y."
