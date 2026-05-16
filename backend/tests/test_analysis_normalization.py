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


def test_resnet_highway_transition_section_keeps_reader_oriented():
    document = (
        "On the contrary, our formulation always learns residual functions; our identity shortcuts are never closed, "
        "and all information is always passed through, with additional residual functions to be learned. "
        "In addition, highway networks have not demonstrated accuracy gains with extremely increased depth. "
        "Residual Learning. Let us consider H(x) as an underlying mapping to be fit by a few stacked layers. "
        "If one hypothesizes that multiple nonlinear layers can asymptotically approximate complicated functions, "
        "then it is equivalent to hypothesize that they can asymptotically approximate the residual functions."
    )
    payload = {
        "terms": [{"term": "residual functions", "meaning": "functions learned relative to an identity reference"}],
        "concepts": [{"concept": "residual functions", "explanation": "core residual-learning target"}],
        "phrases": [],
        "summaries": {
            "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "simple": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "academic": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-highway-transition", document)
    phrases = {phrase.phrase for phrase in result.phrases}

    assert result.summaries.one_line == "This section contrasts ResNet with highway networks and then begins the residual-learning formulation."
    assert {"On the contrary", "In addition", "Let us consider"}.issubset(phrases)
    assert result.sentences[0].core_structure == "On the contrary, our A always does B; C are never D, and all E is passed through."
    assert "highway networks" in {term.term for term in result.terms}


def test_resnet_identity_shortcut_block_section_recovers_preconditioning_role():
    document = (
        "If the optimal function is closer to an identity mapping than to a zero mapping, it should be easier for the solver "
        "to find the perturbations with reference to an identity mapping, than to learn the function as a new one. "
        "We show by experiments that the learned residual functions in general have small responses, suggesting that identity mappings "
        "provide reasonable preconditioning. Identity Mapping by Shortcuts. We adopt residual learning to every few stacked layers. "
        "The shortcut connections in Eqn.(1) introduce neither extra parameter nor computation complexity. "
        "If this is not the case, we can perform a linear projection by the shortcut connections to match the dimensions."
    )
    payload = {
        "terms": [{"term": "Shortcuts We", "meaning": "heading glue artifact"}],
        "concepts": [{"concept": "Shortcuts We", "explanation": "heading glue artifact"}],
        "phrases": [],
        "summaries": {"one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-identity-shortcuts", document)
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "Shortcuts We" not in terms
    assert "Shortcuts We" not in {concept.concept for concept in result.concepts}
    assert {"identity mapping", "residual functions", "shortcut connections", "linear projection"}.issubset(terms)
    assert {"with reference to", "provide reasonable preconditioning", "neither extra parameter nor computation complexity"}.issubset(phrases)
    assert result.summaries.one_line == "This section explains why identity shortcuts help and defines the residual block computation."
    assert result.sentences[0].core_structure.startswith("If A is closer to B")


def test_resnet_network_architecture_section_separates_shortcut_options_from_baseline_design():
    document = (
        "But we will show by experiments that the identity mapping is sufficient for addressing the degradation problem and is economical, "
        "and thus Ws is only used when matching dimensions. The projection shortcut in Eqn.(2) is used to match dimensions. "
        "The form of the residual function F is flexible. "
        "We also note that although the above notations are about fully-connected layers for simplicity, they are applicable to convolutional layers. "
        "The element-wise addition is performed on two feature maps, channel by channel. Network Architectures. "
        "We have tested various plain/residual nets, and have observed consistent phenomena. To provide instances for discussion, "
        "we describe two models for ImageNet as follows. Plain Network. Our plain baselines are mainly inspired by the philosophy of VGG nets."
    )
    payload = {
        "terms": [
            {"term": "square matrix", "meaning": "too local"},
            {"term": "we describe two models", "meaning": "sentence fragment"},
        ],
        "concepts": [{"concept": "we describe two models", "explanation": "sentence fragment"}],
        "phrases": [{"phrase": "identity mapping is sufficient", "function": "result", "explanation": "identity is enough"}],
        "summaries": {
            "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "simple": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "academic": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-architecture", document)
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "square matrix" not in terms
    assert "we describe two models" not in terms
    assert "we describe two models" not in {concept.concept for concept in result.concepts}
    assert {"projection shortcut", "convolutional layers", "feature maps", "plain network", "VGG nets"}.issubset(terms)
    assert {"projection shortcut", "feature maps", "plain network", "VGG nets"}.issubset({concept.concept for concept in result.concepts})
    assert {"identity mapping is sufficient", "only used when matching dimensions", "To provide instances for discussion"}.issubset(phrases)
    assert result.summaries.one_line == "This section explains dimension matching and then introduces the ImageNet plain/residual network designs."
    assert result.sentences[0].core_structure == "We show that A is sufficient for B and economical; C is only used when D."


def test_resnet_shortcut_option_section_filters_training_hyperparameter_noise():
    document = (
        "Example network architectures for ImageNet. Left: the VGG-19 model as a reference. "
        "Middle: a plain network with 34 parameter layers. Right: a residual network with 34 parameter layers. "
        "The dotted shortcuts increase dimensions. Residual Network. Based on the above plain network, we insert shortcut connections "
        "which turn the network into its counterpart residual version. The identity shortcuts can be directly used when the input and output "
        "are of the same dimensions. When the dimensions increase, we consider two options: (A) The shortcut still performs identity mapping, "
        "with extra zero entries padded for increasing dimensions. This option introduces no extra parameter; "
        "(B) The projection shortcut is used to match dimensions, done by 1x1 convolutions. We adopt batch normalization right after each convolution. "
        "We use SGD with a mini-batch size of 256. The learning rate starts from 0.1."
    )
    payload = {
        "terms": [
            {"term": "Batch Normalization", "meaning": "training detail"},
            {"term": "mini-batch", "meaning": "training detail"},
            {"term": "learning rate", "meaning": "training detail"},
            {"term": "example network", "meaning": "caption fragment"},
            {"term": "Residual Network", "meaning": "residual counterpart"},
        ],
        "concepts": [
            {"concept": "Batch Normalization", "explanation": "training detail"},
            {"concept": "example network", "explanation": "caption fragment"},
            {"concept": "plain network", "explanation": "baseline architecture"},
        ],
        "phrases": [{"phrase": "residual network", "function": "general", "explanation": "too noun-like"}],
        "summaries": {
            "one_line": "Example network architectures for ImageNet.",
            "simple": "Example network architectures for ImageNet.",
            "academic": "Example network architectures for ImageNet.",
        },
        "sentences": [{"sentence": "The dotted shortcuts increase dimensions.", "core_structure": "Subject (shortcuts) + Verb (increase) + Object (dimensions)."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-shortcut-options", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "Batch Normalization" not in terms
    assert "mini-batch" not in terms
    assert "learning rate" not in terms
    assert "example network" not in terms
    assert "Batch Normalization" not in concepts
    assert "example network" not in concepts
    assert {"residual network", "dimensions increase", "zero entries padded", "projection shortcut", "1x1 convolutions"}.issubset(terms)
    assert {"residual network", "dimensions increase", "zero entries padded", "1x1 convolutions"}.issubset(concepts)
    assert {"Based on the above plain network", "When the dimensions increase", "introduces no extra parameter"}.issubset(phrases)
    assert "residual network" not in phrases
    assert result.summaries.one_line == "This section shows how the plain ImageNet baseline is converted into a residual network."
    assert result.sentences[0].core_structure == "Based on A, we insert B, which turn C into D."


def test_resnet_imagenet_plain_network_section_filters_heading_and_hyperparameter_noise():
    document = (
        "We use a weight decay of 0.0001 and a momentum of 0.9. "
        "4. Experiments 4.1. ImageNet Classification We evaluate our method on the ImageNet 2012 classification dataset "
        "that consists of 1000 classes. We evaluate both top-1 and top-5 error rates. "
        "Plain Networks. We first evaluate 18-layer and 34-layer plain nets. "
        "The results in Table 2 show that the deeper 34-layer plain net has higher validation error than the shallower 18-layer plain net. "
        "To reveal the reasons, in Fig. 4 we compare their training/validation errors during the training procedure. "
        "We have observed the degradation problem."
    )
    payload = {
        "terms": [
            {"term": "ImageNet Classification We", "meaning": "heading glue"},
            {"term": "Plain Networks", "meaning": "heading glue"},
            {"term": "we evaluate our method", "meaning": "sentence fragment"},
        ],
        "concepts": [
            {"concept": "ImageNet Classification We", "explanation": "heading glue"},
            {"concept": "Plain Networks", "explanation": "heading glue"},
        ],
        "phrases": [
            {
                "phrase": "weight decay of 0.0001 and a momentum of 0.9",
                "function": "general",
                "explanation": "hyperparameter noise",
            }
        ],
        "summaries": {
            "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "simple": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "academic": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-imagenet-plain", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "ImageNet Classification We" not in terms
    assert "Plain Networks" not in terms
    assert "we evaluate our method" not in terms
    assert "ImageNet Classification We" not in concepts
    assert "Plain Networks" not in concepts
    assert "weight decay of 0.0001 and a momentum of 0.9" not in phrases
    assert {"ImageNet 2012 classification dataset", "top-1 and top-5 error rates", "18-layer and 34-layer plain nets"}.issubset(terms)
    assert {"higher validation error", "training/validation errors", "degradation problem"}.issubset(concepts)
    assert {"We evaluate our method", "We first evaluate", "The results in Table 2 show that", "To reveal the reasons"}.issubset(phrases)
    assert "we compare" not in phrases
    assert result.summaries.one_line == "This section starts the ImageNet experiments and shows degradation in deeper plain networks."
    assert result.sentences[0].core_structure == "We evaluate our method on dataset X that consists of Y."


def test_resnet_plain_network_diagnosis_section_rejects_training_fragments():
    document = (
        "34-layer plain net has higher training error throughout the whole training procedure, even though the solution space "
        "of the 18-layer plain network is a subspace of that of the 34-layer one. "
        "We argue that this optimization difficulty is unlikely to be caused by vanishing gradients. "
        "These plain networks are trained with BN, which ensures forward propagated signals to have non-zero variances. "
        "We also verify that the backward propagated gradients exhibit healthy norms with BN. "
        "So neither forward nor backward signals vanish. "
        "We conjecture that the deep plain nets may have exponentially low convergence rates, which impact the reducing of the training error. "
        "Residual Networks. Next we evaluate 18-layer and 34-layer residual nets."
    )
    payload = {
        "terms": [
            {"term": "net has higher training", "meaning": "bad fragment"},
            {"term": "throughout the whole training", "meaning": "bad fragment"},
            {"term": "gradients", "meaning": "too broad"},
            {"term": "Residual Networks", "meaning": "heading glue"},
        ],
        "concepts": [
            {"concept": "net has higher training", "explanation": "bad fragment"},
            {"concept": "throughout the whole training", "explanation": "bad fragment"},
        ],
        "phrases": [],
        "summaries": {
            "one_line": "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth.",
            "simple": "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth.",
            "academic": "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-plain-diagnosis", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "net has higher training" not in terms
    assert "throughout the whole training" not in terms
    assert "gradients" not in terms
    assert "Residual Networks" not in terms
    assert "net has higher training" not in concepts
    assert {"higher training error", "vanishing gradients", "forward propagated signals", "backward propagated gradients", "convergence rates"}.issubset(terms)
    assert {"higher training error", "vanishing gradients", "convergence rates"}.issubset(concepts)
    assert {"unlikely to be caused by", "neither forward nor backward signals vanish", "may have exponentially low convergence rates", "Next we evaluate"}.issubset(phrases)
    assert result.summaries.one_line == "This section diagnoses plain-network degradation and then turns to residual-network experiments."
    assert result.sentences[0].core_structure == "We argue that X is unlikely to be caused by Y."


def test_resnet_projection_shortcut_option_section_rejects_table_fragments():
    document = (
        "Figure 5. A deeper residual function F for ImageNet. Left: a building block. "
        "We have shown that parameter-free, identity shortcuts help with training. "
        "Next we investigate projection shortcuts. In Table 3 we compare three options: "
        "(A) zero-padding shortcuts are used for increasing dimensions, and all shortcuts are parameter-free; "
        "(B) projection shortcuts are used for increasing dimensions, and other shortcuts are identity; "
        "and (C) all shortcuts are projections. Table 3 shows that all three options are considerably better than the plain counterpart. "
        "B is slightly better than A. C is marginally better than B. "
        "But the small differences among A/B/C indicate that projection shortcuts are not essential for addressing the degradation problem."
    )
    payload = {
        "terms": [
            {"term": "In Table", "meaning": "bad fragment"},
            {"term": "shortcuts help with training", "meaning": "bad fragment"},
            {"term": "residual function", "meaning": "figure-caption fragment"},
        ],
        "concepts": [
            {"concept": "In Table", "explanation": "bad fragment"},
            {"concept": "shortcuts help with training", "explanation": "bad fragment"},
        ],
        "phrases": [{"phrase": "we compare", "function": "method", "explanation": "too generic"}],
        "summaries": {
            "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "simple": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "academic": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-shortcut-ablation", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "In Table" not in terms
    assert "shortcuts help with training" not in terms
    assert "residual function" not in terms
    assert "In Table" not in concepts
    assert "we compare" not in phrases
    assert {"projection shortcut", "zero-padding shortcuts", "all shortcuts are parameter-free", "other shortcuts are identity", "all shortcuts are projections"}.issubset(terms)
    assert {"projection shortcuts", "zero-padding shortcuts", "all shortcuts are projections"}.issubset(concepts)
    assert {"Next we investigate", "we compare three options", "considerably better than", "not essential for addressing"}.issubset(phrases)
    assert result.summaries.one_line == "This section compares shortcut options and concludes projection shortcuts are useful but not essential."
    assert result.sentences[0].core_structure == "Next we investigate X."


def test_resnet_bottleneck_section_recovers_efficiency_argument():
    document = (
        "The three layers are 1x1, 3x3, and 1x1 convolutions, where the 1x1 layers are responsible for reducing and then increasing "
        "dimensions, leaving the 3x3 layer a bottleneck with smaller input/output dimensions. "
        "The parameter-free identity shortcuts are particularly important for the bottleneck architectures. "
        "If the identity shortcut is replaced with projection, one can show that the time complexity and model size are doubled. "
        "So identity shortcuts lead to more efficient models for the bottleneck designs. "
        "Deeper non-bottleneck ResNets also gain accuracy from increased depth, but are not as economical as the bottleneck ResNets. "
        "So the usage of bottleneck designs is mainly due to practical considerations."
    )
    payload = {
        "terms": [
            {"term": "time complexity and model", "meaning": "bad fragment"},
            {"term": "more efficient models", "meaning": "too broad"},
        ],
        "concepts": [
            {"concept": "time complexity and model", "explanation": "bad fragment"},
            {"concept": "more efficient models", "explanation": "too broad"},
        ],
        "phrases": [],
        "summaries": {"one_line": document.split(".")[0] + "."},
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-bottleneck", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "time complexity and model" not in terms
    assert "more efficient models" not in terms
    assert "time complexity and model" not in concepts
    assert {"bottleneck", "bottleneck architectures", "1x1 convolutions", "time complexity", "time complexity and model size", "practical considerations"}.issubset(terms)
    assert {"bottleneck", "bottleneck architectures", "practical considerations"}.issubset(concepts)
    assert {"are responsible for", "particularly important for", "lead to more efficient models", "mainly due to practical considerations"}.issubset(phrases)
    assert "show that" not in phrases
    assert result.summaries.one_line == "This section explains why bottleneck blocks make very deep ResNets computationally practical."
    assert result.sentences[0].core_structure == "The three layers are A, B, and C, where A is responsible for D."


def test_resnet_deep_bottleneck_results_section_recovers_imagenet_scaling_argument():
    document = (
        "34-layer net with this 3-layer bottleneck block, resulting in a 50-layer ResNet. "
        "101-layer and 152-layer ResNets: We construct 101-layer and 152-layer ResNets by using more 3-layer blocks. "
        "Remarkably, although the depth is significantly increased, the 152-layer ResNet still has lower complexity than VGG-16/19 nets. "
        "The 50/101/152-layer ResNets are more accurate than the 34-layer ones by considerable margins. "
        "We do not observe the degradation problem and thus enjoy significant accuracy gains from considerably increased depth. "
        "Comparisons with State-of-the-art Methods. Our baseline 34-layer ResNets have achieved very competitive accuracy. "
        "Our 152-layer ResNet has a single-model top-5 validation error of 4.49%. "
        "We combine six models of different depth to form an ensemble. This entry won the 1st place in ILSVRC 2015. "
        "CIFAR-10 and Analysis. Our focus is on the behaviors of extremely deep networks, but not on pushing the state-of-the-art results."
    )
    payload = {
        "terms": [
            {"term": "model", "meaning": "too generic"},
            {"term": "we combine six models", "meaning": "bad clause"},
        ],
        "concepts": [
            {"concept": "model", "explanation": "too generic"},
            {"concept": "we combine six models", "explanation": "bad clause"},
        ],
        "phrases": [{"phrase": "as follows", "function": "general", "explanation": "too generic here"}],
        "summaries": {
            "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "simple": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
            "academic": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
        },
        "sentences": [],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-deep-results", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "model" not in terms
    assert "we combine six models" not in terms
    assert "feature maps" not in terms
    assert "ResNet" not in terms
    assert "model" not in concepts
    assert "we combine six models" not in concepts
    assert {"50/101/152-layer ResNets", "single-model top-5 validation error", "ensemble", "ILSVRC 2015", "state-of-the-art methods"}.issubset(terms)
    assert {"lower complexity than VGG", "50/101/152-layer ResNets", "single-model top-5 validation error", "ensemble"}.issubset(concepts)
    assert {"lower complexity than", "more accurate than", "by considerable margins", "We do not observe", "form an ensemble", "won the 1st place", "Our focus is on"}.issubset(phrases)
    assert result.summaries.one_line == (
        "This section shows very deep bottleneck ResNets outperform shallower ResNets and reach state-of-the-art ImageNet results."
    )
    assert result.sentences[0].core_structure == "Although A is significantly increased, B still has lower complexity than C."


def test_resnet_cifar_architecture_section_filters_table_noise():
    document = (
        "The numbers of filters are {16, 32, 64} respectively. "
        "The subsampling is performed by convolutions with a stride of 2. "
        "The network ends with a global average pooling, a 10-way fully-connected layer, and softmax. "
        "There are totally 6n+2 stacked weighted layers. "
        "When shortcut connections are used, they are connected to the pairs of 3x3 layers, totally 3n shortcuts. "
        "On this dataset we use identity shortcuts in all cases, i.e., option A. "
        "method error Maxout NIN DSN FitNet Highway ResNet Classification error."
    )
    payload = {
        "terms": [
            {"term": "learning rate", "meaning": "not in this section"},
            {"term": "Dropout", "meaning": "table noise"},
            {"term": "For ResNet", "meaning": "fragment"},
            {"term": "network", "meaning": "too generic"},
        ],
        "concepts": [
            {"concept": "Dropout", "explanation": "table noise"},
            {"concept": "For ResNet", "explanation": "fragment"},
            {"concept": "network", "explanation": "too generic"},
        ],
        "phrases": [{"phrase": "subsampling is performed by convolutions with a stride of 2", "function": "method", "explanation": "useful"}],
        "summaries": {"one_line": "The numbers of filters are {16, 32, 64} respectively."},
        "sentences": [{"sentence": "The numbers of filters are {16, 32, 64} respectively.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-cifar-arch", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"learning rate", "Dropout", "For ResNet", "network"} & terms
    assert not {"Dropout", "For ResNet", "network"} & concepts
    assert {"stride of 2", "global average pooling", "10-way fully-connected layer", "6n+2 stacked weighted layers", "3n shortcuts"}.issubset(terms)
    assert {"CIFAR-10 architecture", "6n+2 stacked weighted layers", "stride of 2", "global average pooling", "identity shortcuts in all cases"}.issubset(concepts)
    assert {"subsampling is performed by", "network ends with", "There are totally", "When shortcut connections are used", "identity shortcuts in all cases"}.issubset(phrases)
    assert "subsampling is performed by convolutions with a stride of 2" not in phrases
    assert result.summaries.one_line == "This section defines the CIFAR-10 architecture used for controlled ResNet depth experiments."
    assert result.sentences[0].core_structure == "The subsampling is performed by A with B."


def test_resnet_cifar_depth_behavior_section_recovers_plain_vs_residual_contrast():
    document = (
        "We compare n = {3, 5, 7, 9}, leading to 20, 32, 44, and 56-layer networks. "
        "Fig. 6 shows the behaviors of the plain nets. The deep plain nets suffer from increased depth, and exhibit higher training error when going deeper. "
        "This phenomenon is similar to that on ImageNet and on MNIST, suggesting that such an optimization difficulty is a fundamental problem. "
        "Fig. 6 shows the behaviors of ResNets. Our ResNets manage to overcome the optimization difficulty and demonstrate accuracy gains when the depth increases. "
        "We further explore n = 18 that leads to a 110-layer ResNet. "
        "The initial learning rate of 0.1 is slightly too large to start converging. "
        "So we use 0.01 to warm up the training until the training error is below 80%, and then go back to 0.1 and continue training."
    )
    payload = {
        "terms": [
            {"term": "ResNets", "meaning": "too broad"},
            {"term": "layer networks", "meaning": "fragment"},
            {"term": "warm up the training", "meaning": "clause fragment"},
            {"term": "until the training", "meaning": "clause fragment"},
        ],
        "concepts": [
            {"concept": "ResNets", "explanation": "too broad"},
            {"concept": "layer networks", "explanation": "fragment"},
            {"concept": "warm up the training", "explanation": "clause fragment"},
        ],
        "phrases": [{"phrase": "suffer from increased depth", "function": "result", "explanation": "useful"}],
        "summaries": {"one_line": "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth."},
        "sentences": [{"sentence": "The deep plain nets suffer from increased depth.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-cifar-depth", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"ResNets", "layer networks", "warm up the training", "until the training"} & terms
    assert not {"ResNets", "layer networks", "warm up the training"} & concepts
    assert {"higher training error", "plain nets", "accuracy gains", "optimization difficulty", "110-layer ResNet"}.issubset(terms)
    assert {
        "plain-net depth degradation on CIFAR-10",
        "ResNet depth scaling on CIFAR-10",
        "optimization difficulty as a fundamental problem",
        "110-layer ResNet",
        "learning-rate warmup",
    }.issubset(concepts)
    assert {"suffer from increased depth", "manage to overcome", "demonstrate accuracy gains", "slightly too large to start converging"}.issubset(phrases)
    assert result.summaries.one_line == (
        "This section shows CIFAR-10 plain nets degrade with depth while ResNets overcome the optimization difficulty."
    )
    assert result.sentences[0].core_structure == "A suffer from B and exhibit C when D."


def test_resnet_over_1000_layers_section_recovers_optimization_vs_overfitting():
    document = (
        "When there are more layers, an individual layer of ResNets tends to modify the signal less. "
        "Exploring Over 1000 layers. We explore an aggressively deep model of over 1000 layers. "
        "We set n = 200 that leads to a 1202-layer network, which is trained as described above. "
        "Our method shows no optimization difficulty, and this 1202-layer network is able to achieve training error <0.1%. "
        "But there are still open problems on such aggressively deep models. "
        "The testing result of this 1202-layer network is worse than that of our 110-layer network, although both have similar training error. "
        "We argue that this is because of overfitting. The 1202-layer network may be unnecessarily large for this small dataset. "
        "Strong regularization such as maxout or dropout is applied to obtain the best results on this dataset. "
        "In this paper, we use no maxout/dropout and just simply impose regularization via deep and thin architectures by design, without distracting from the focus on the difficulties of optimization."
    )
    payload = {
        "terms": [
            {"term": "Dropout", "meaning": "too generic"},
            {"term": "ResNet", "meaning": "too broad"},
            {"term": "dashed lines denote training", "meaning": "figure artifact"},
        ],
        "concepts": [
            {"concept": "Dropout", "explanation": "too generic"},
            {"concept": "ResNet", "explanation": "too broad"},
            {"concept": "dashed lines denote training", "explanation": "figure artifact"},
        ],
        "phrases": [{"phrase": "Applied to", "function": "result", "explanation": "too generic"}],
        "summaries": {"one_line": "When there are more layers, an individual layer of ResNets tends to modify the signal less."},
        "sentences": [{"sentence": "When there are more layers, an individual layer of ResNets tends to modify the signal less.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-1202", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"Dropout", "ResNet", "dashed lines denote training"} & terms
    assert not {"Dropout", "ResNet", "dashed lines denote training"} & concepts
    assert {"1202-layer network", "overfitting", "strong regularization", "deep and thin architectures"}.issubset(terms)
    assert {"over-1000-layer stress test", "optimization success versus overfitting", "small-dataset overfitting", "regularization tradeoff"}.issubset(concepts)
    assert {"shows no optimization difficulty", "still open problems", "worse than that of", "because of overfitting", "unnecessarily large", "without distracting from"}.issubset(phrases)
    assert "Applied to" not in phrases
    assert "Exploring Over 1000 layers" not in phrases
    assert result.summaries.one_line == "This section stress-tests a 1202-layer ResNet and separates optimization success from overfitting."
    assert result.sentences[0].core_structure == "A shows no B, and C is able to achieve D."


def test_resnet_detection_transfer_section_recovers_representation_generalization():
    document = (
        "Here we are interested in the improvements of replacing VGG-16 with ResNet-101. "
        "The detection implementation of using both models is the same, so the gains can only be attributed to better networks. "
        "Most remarkably, on the challenging COCO dataset we obtain a 6.0% increase in COCO's standard metric (mAP@[.5, .95]), which is a 28% relative improvement. "
        "This gain is solely due to the learned representations. "
        "Based on deep residual nets, we won the 1st places in several tracks in ILSVRC & COCO 2015 competitions: ImageNet detection, ImageNet localization, COCO detection, and COCO segmentation."
    )
    payload = {
        "terms": [
            {"term": "VGG-16", "meaning": "baseline only"},
            {"term": "attributed to better networks", "meaning": "fragment"},
        ],
        "concepts": [
            {"concept": "VGG-16", "explanation": "baseline only"},
            {"concept": "attributed to better networks", "explanation": "fragment"},
        ],
        "phrases": [],
        "summaries": {"one_line": "Here we are interested in the improvements of replacing VGG-16 with ResNet-101."},
        "sentences": [{"sentence": "Here we are interested in the improvements of replacing VGG-16 with ResNet-101.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-transfer", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "VGG-16" not in terms
    assert "ImageNet" not in terms
    assert "attributed to better networks" not in terms
    assert "VGG-16" not in concepts
    assert "attributed to better networks" not in concepts
    assert {"ResNet-101", "detection implementation", "COCO dataset", "mAP@[.5, .95]", "learned representations", "ILSVRC & COCO 2015 competitions"}.issubset(terms)
    assert {"object-detection transfer", "representation quality attribution", "COCO relative improvement", "competition-level generalization"}.issubset(concepts)
    assert {"replacing VGG-16 with ResNet-101", "can only be attributed to", "Most remarkably", "relative improvement", "solely due to", "Based on deep residual nets"}.issubset(phrases)
    assert result.summaries.one_line == "This section shows ResNet-101 improves object detection by providing better learned representations."
    assert result.sentences[0].core_structure == "A can only be attributed to B."


def test_resnet_detection_baseline_section_recovers_appendix_implementation():
    document = (
        "A. Object Detection Baselines In this section we introduce our detection method based on the baseline Faster R-CNN system. "
        "The models are initialized by the ImageNet classification models, and then fine-tuned on the object detection data. "
        "We have experimented with ResNet-50/101 at the time of the ILSVRC & COCO 2015 detection competitions. "
        "Unlike VGG-16 used in Faster R-CNN, our ResNet has no hidden fc layers. "
        "We adopt the idea of Networks on Conv feature maps (NoC) to address this issue. "
        "We compute the full-image shared conv feature maps using layers whose strides on the image are no greater than 16 pixels."
    )
    payload = {
        "terms": [{"term": "ImageNet classification", "meaning": "too broad"}],
        "concepts": [{"concept": "ImageNet classification", "explanation": "too broad"}],
        "phrases": [],
        "summaries": {"one_line": "A."},
        "sentences": [{"sentence": "A.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-baseline", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert "ImageNet classification" not in terms
    assert "ImageNet classification" not in concepts
    assert "feature maps" not in concepts
    assert {"Faster R-CNN", "full-image shared conv feature maps"}.issubset(terms)
    assert "ImageNet" not in terms
    assert "feature maps" not in terms
    assert {"Faster R-CNN baseline adaptation", "ImageNet-to-detection fine-tuning", "ResNet without hidden fc layers", "shared convolutional feature maps"}.issubset(concepts)
    assert {"detection method based on", "initialized by", "fine-tuned on", "Unlike VGG-16", "adopt the idea of", "to address this issue"}.issubset(phrases)
    assert result.summaries.one_line == "This appendix section explains how ResNet classification backbones are adapted for Faster R-CNN detection."
    assert result.sentences[0].core_structure == "A are initialized by B and then fine-tuned on C."


def test_resnet_detection_evaluation_section_recovers_pascal_coco_metrics():
    document = (
        "PASCAL VOC Following prior work, for the PASCAL VOC 2007 test set we use VOC 2007 and VOC 2012 trainval images for training. "
        "The hyper-parameters for training Faster R-CNN are the same. ResNet-101 improves the mAP by >3% over VGG-16. "
        "This gain is solely because of the improved features learned by ResNet. "
        "MS COCO The MS COCO dataset involves 80 object categories. "
        "We evaluate the PASCAL VOC metric (mAP @ IoU = 0.5) and the standard COCO metric (mAP @ IoU = .5:.05:.95). "
        "ResNet-101 has a 6% increase of mAP@[.5, .95] over VGG-16, which is a 28% relative improvement, solely contributed by the features learned by the better network. "
        "This suggests that a deeper network can improve both recognition and localization."
    )
    payload = {
        "terms": [
            {"term": "mini-batch", "meaning": "training detail"},
            {"term": "learning rate", "meaning": "training detail"},
            {"term": "PASCAL VOC Following", "meaning": "heading glue"},
            {"term": "MS COCO The MS", "meaning": "heading glue"},
        ],
        "concepts": [
            {"concept": "mini-batch", "explanation": "training detail"},
            {"concept": "PASCAL VOC Following", "explanation": "heading glue"},
            {"concept": "MS COCO The MS", "explanation": "heading glue"},
        ],
        "phrases": [],
        "summaries": {"one_line": "PASCAL VOC Following prior work, for the PASCAL VOC 2007 test set we use VOC 2007 and VOC 2012 trainval images for training."},
        "sentences": [{"sentence": "PASCAL VOC Following prior work.", "core_structure": "Main claim + explanation."}],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-eval", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"mini-batch", "learning rate", "PASCAL VOC Following", "MS COCO The MS"} & terms
    assert not {"mini-batch", "PASCAL VOC Following", "MS COCO The MS"} & concepts
    assert {"PASCAL VOC", "mAP", "mAP @ IoU = 0.5", "mAP @ IoU = .5:.05:.95"}.issubset(terms)
    assert {"PASCAL and COCO evaluation setup", "ResNet feature gain attribution", "COCO metric comparison", "recognition and localization improvement"}.issubset(concepts)
    assert {"improves the mAP by", "solely because of", "standard COCO metric", "relative improvement", "improve both recognition and localization"}.issubset(phrases)
    assert result.summaries.one_line == "This appendix section evaluates ResNet-101 detection gains on PASCAL VOC and MS COCO."
    assert result.sentences[0].core_structure == "This gain is solely because of A."


def test_resnet_detection_improvements_section_recovers_method_recipe():
    document = (
        "Our box refinement partially follows the iterative localization in prior work. "
        "In Faster R-CNN, the final output is a regressed box that is different from its proposal box. "
        "Non-maximum suppression (NMS) is applied on the union set of predicted boxes using an IoU threshold of 0.3, followed by box voting. "
        "Global context. We combine global context in the Fast R-CNN step. "
        "Given the full-image conv feature map, global Spatial Pyramid Pooling can be implemented as RoI pooling using the entire image's bounding box as the RoI. "
        "This global feature is concatenated with the original per-region feature, followed by the sibling classification and box regression layers. "
        "This new structure is trained end-to-end. "
        "Multi-scale testing. We have not performed multi-scale training because of limited time."
    )
    payload = {
        "terms": [
            {"term": "feature maps", "meaning": "generic"},
            {"term": "mAP", "meaning": "wrong section emphasis"},
            {"term": "RPN step", "meaning": "not the main step"},
            {"term": "Global Spatial Pyramid Pooling", "meaning": "implementation detail"},
        ],
        "concepts": [
            {"concept": "feature maps", "explanation": "generic"},
            {"concept": "regressed box", "explanation": "too narrow"},
            {"concept": "Non-maximum suppression (NMS)", "explanation": "too narrow"},
            {"concept": "Global Spatial Pyramid Pooling", "explanation": "too narrow"},
        ],
        "phrases": [],
        "summaries": {"one_line": "Our box refinement partially follows the iterative localization in prior work."},
        "sentences": [{"sentence": "Our box refinement partially follows the iterative localization in prior work.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0", "analysis_mode:atomic_remote"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-improvements", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"feature maps", "mAP", "RPN step", "Global Spatial Pyramid Pooling"} & terms
    assert "feature maps" not in concepts
    assert {"box refinement", "regressed box", "Non-maximum suppression (NMS)", "box voting", "global context", "RoI pooling", "multi-scale testing"}.issubset(terms)
    assert {"box refinement pipeline", "global context feature", "multi-scale testing limitation"}.issubset(concepts)
    assert {"partially follows", "followed by", "is concatenated with", "trained end-to-end", "because of limited time"}.issubset(phrases)
    assert result.summaries.one_line == "This appendix section describes three detector improvements: box refinement, global context, and multi-scale testing."
    assert result.sentences[0].core_structure == "A is applied on B, followed by C."
    assert "analysis_mode:atomic_remote" in result.quality_warnings
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_resnet_detection_results_table_section_becomes_table_reading_guide():
    document = (
        "training data COCO train COCO trainval test data COCO val COCO test-dev mAP @.5 @[.5, .95] "
        "baseline Faster R-CNN (VGG-16) 41.5 21.2 baseline Faster R-CNN (ResNet-101) 48.4 27.2 "
        "+box refinement 49.9 29.9 +context 51.1 30.0 +multi-scale testing 53.8 32.5 ensemble 59.0 37. "
        "Object detection improvements on MS COCO using Faster R-CNN and ResNet-101. "
        "baseline+++ResNet-101 COCO+07+12 85.6 90.0 89.6. "
        "Detection results on the PASCAL VOC 2007 test set. The baseline is the Faster R-CNN system. "
        "The system baseline+++ include box refinement, context, and multi-scale testing in Table 9. "
        "Detection results on the PASCAL VOC 2012 test set."
    )
    payload = {
        "terms": [
            {"term": "mAP", "meaning": "metric"},
            {"term": "Faster R-CNN", "meaning": "detector"},
            {"term": "COCO", "meaning": "dataset"},
            {"term": "ensemble", "meaning": "combined model"},
        ],
        "concepts": [
            {"concept": "mAP", "explanation": "metric"},
            {"concept": "Faster R-CNN", "explanation": "detector"},
            {"concept": "COCO", "explanation": "dataset"},
            {"concept": "ensemble", "explanation": "combined model"},
        ],
        "phrases": [],
        "summaries": {"one_line": "training data COCO train COCO trainval test data COCO val COCO test-dev mAP @.5."},
        "sentences": [{"sentence": "training data COCO train COCO trainval test data COCO val COCO test-dev mAP @.5.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0", "term_not_in_source_sentence:mAP"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-table", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"mAP", "Faster R-CNN", "COCO"} & terms
    assert not {"mAP", "Faster R-CNN", "COCO", "ensemble"} & concepts
    assert {"baseline+++", "COCO test-dev", "PASCAL VOC 2007 test set", "PASCAL VOC 2012 test set", "ensemble"}.issubset(terms)
    assert {"detection result table reading", "baseline+++ system", "cross-benchmark detection validation"}.issubset(concepts)
    assert {"Object detection improvements on", "Detection results on", "The baseline is", "include box refinement"}.issubset(phrases)
    assert result.summaries.one_line == "This table section reports how ResNet-101 detector variants improve COCO and PASCAL VOC results."
    assert result.sentences[0].core_structure == "The baseline is A."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings
    assert "term_not_in_source_sentence:mAP" not in result.quality_warnings
    assert not any(warning.startswith("source_sentence_not_in_document:") for warning in result.quality_warnings)


def test_resnet_detection_result_narrative_recovers_protocol_and_transfer():
    document = (
        "The system baseline+++ include box refinement, context, and multi-scale testing in Table 9. "
        "Using validation data. Next we use the 80k+40k trainval set for training and the 20k test-dev set for evaluation. "
        "The test-dev set has no publicly available ground truth and the result is reported by the evaluation server. "
        "This is our single-model result. "
        "Ensemble. In Faster R-CNN, the system is designed to learn region proposals and also object classifiers, so an ensemble can be used to boost both tasks. "
        "We use an ensemble for proposing regions, and the union set of proposals are processed by an ensemble of per-region classifiers. "
        "This result won the 1st place in the detection task in COCO 2015. "
        "PASCAL VOC We revisit the PASCAL VOC dataset based on the above model. "
        "With the single model on the COCO dataset, we fine-tune this model on the PASCAL VOC sets. "
        "The result on PASCAL VOC 2012 is 10 points higher than the previous state-of-the-art result."
    )
    payload = {
        "terms": [
            {"term": "RoI pooling", "meaning": "wrong emphasis"},
            {"term": "mAP@.5", "meaning": "metric label"},
            {"term": "ensemble", "meaning": "too narrow alone"},
        ],
        "concepts": [
            {"concept": "RoI pooling", "explanation": "wrong emphasis"},
            {"concept": "mAP@.5", "explanation": "metric label"},
            {"concept": "ensemble", "explanation": "too narrow alone"},
        ],
        "phrases": [],
        "summaries": {"one_line": "The system baseline+++ include box refinement, context, and multi-scale testing in Table 9."},
        "sentences": [{"sentence": "The system baseline+++ include box refinement, context, and multi-scale testing in Table 9.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-detection-narrative", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"RoI pooling", "mAP@.5"} & terms
    assert not {"RoI pooling", "mAP@.5", "ensemble"} & concepts
    assert {"test-dev set", "evaluation server", "single-model result", "region proposals", "per-region classifiers", "state-of-the-art result"}.issubset(terms)
    assert {"hidden-label benchmark evaluation", "single model versus ensemble", "COCO-to-PASCAL fine-tuning", "competition result claim"}.issubset(concepts)
    assert {"no publicly available ground truth", "reported by the evaluation server", "single-model result", "boost both tasks", "fine-tune this model", "higher than the previous state-of-the-art"}.issubset(phrases)
    assert result.summaries.one_line == "This section explains COCO test-dev evaluation, ensemble gains, and COCO-to-PASCAL fine-tuning results."
    assert result.sentences[0].core_structure == "A has no B and the result is reported by C."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_resnet_imagenet_detection_setup_recovers_protocol():
    document = (
        "ImageNet Detection The ImageNet Detection (DET) task involves 200 object categories. "
        "The accuracy is evaluated by mAP@.5. "
        "Our object detection algorithm for ImageNet DET is the same as that for MS COCO in Table 9. "
        "The networks are pretrained on the 1000-class ImageNet classification set, and are fine-tuned on the DET data. "
        "We split the validation set into two parts (val1/val2) following prior work. "
        "We fine-tune the detection models using the DET training set and the val1 set. "
        "The val2 set is used for validation. We do not use other ILSVRC 2015 data."
    )
    payload = {
        "terms": [
            {"term": "ImageNet classification", "meaning": "too broad"},
            {"term": "mAP@.5", "meaning": "metric"},
            {"term": "fine-tuned", "meaning": "verb fragment"},
            {"term": "object categories", "meaning": "generic"},
        ],
        "concepts": [
            {"concept": "ImageNet classification", "explanation": "too broad"},
            {"concept": "mAP@.5", "explanation": "metric"},
            {"concept": "fine-tuned", "explanation": "verb fragment"},
            {"concept": "object categories", "explanation": "generic"},
        ],
        "phrases": [{"phrase": "is evaluated by mAP@.5", "explanation": "metric phrase"}],
        "summaries": {"one_line": "ImageNet Detection The ImageNet Detection (DET) task involves 200 object categories."},
        "sentences": [{"sentence": "ImageNet Detection The ImageNet Detection (DET) task involves 200 object categories.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:1"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-imagenet-det", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"ImageNet classification", "fine-tuned", "object categories"} & terms
    assert not {"ImageNet classification", "mAP@.5", "fine-tuned", "object categories"} & concepts
    assert {"ImageNet Detection (DET)", "mAP@.5", "ImageNet classification pretraining", "DET training set", "val1/val2 split", "ILSVRC 2015 data"}.issubset(terms)
    assert {"ImageNet DET benchmark setup", "classification-to-detection transfer", "val1/val2 validation protocol", "restricted competition data use"}.issubset(concepts)
    assert {"task involves", "is evaluated by", "is the same as that for", "are pretrained on", "are fine-tuned on", "We split the validation set", "is used for validation", "We do not use"}.issubset(phrases)
    assert result.summaries.one_line.startswith("This section defines the ImageNet DET setup")
    assert result.sentences[0].core_structure == "A is evaluated by B."
    assert "phrase_count_out_of_range:1" not in result.quality_warnings
    assert "term_not_in_source_sentence:ImageNet classification pretraining" not in result.quality_warnings
    assert "term_not_in_source_sentence:val1/val2 split" not in result.quality_warnings


def test_resnet_imagenet_localization_setup_recovers_task_and_rpn_adaptation():
    document = (
        "LOC method LOC network testing LOC error on GT CLS classification network top-5 LOC error on predicted CLS. "
        "Localization error (%) on the ImageNet validation. In the column of LOC error on GT class, the ground truth class is used. "
        "In the testing column, 1-crop denotes testing on a center crop and dense denotes fully convolutional and multi-scale testing. "
        "This result won the 1st place in the ImageNet detection task in ILSVRC 2015, surpassing the second place by 8.5 points. "
        "C. ImageNet Localization The ImageNet Localization (LOC) task requires to classify and localize the objects. "
        "Following prior work, we assume that the image-level classifiers are first adopted for predicting the class labels of an image, "
        "and the localization algorithm only accounts for predicting bounding boxes based on the predicted classes. "
        "We adopt the per-class regression (PCR) strategy, learning a bounding box regressor for each class. "
        "Unlike the way that is category-agnostic, our RPN for localization is designed in a per-class form. "
        "This RPN ends with two sibling 1x1 convolutional layers for binary classification and box regression."
    )
    payload = {
        "terms": [
            {"term": "ImageNet classification", "meaning": "wrong section"},
            {"term": "LOC", "meaning": "acronym alone"},
            {"term": "mAP", "meaning": "wrong metric emphasis"},
            {"term": "RPN", "meaning": "too broad alone"},
            {"term": "ensemble", "meaning": "previous result"},
            {"term": "convolutional layers", "meaning": "too generic"},
            {"term": "ResNet-101", "meaning": "too broad"},
        ],
        "concepts": [
            {"concept": "ImageNet classification", "explanation": "wrong section"},
            {"concept": "LOC", "explanation": "acronym alone"},
            {"concept": "mAP", "explanation": "wrong metric emphasis"},
            {"concept": "RPN", "explanation": "too broad alone"},
            {"concept": "convolutional layers", "explanation": "too generic"},
        ],
        "phrases": [],
        "summaries": {"one_line": "LOC method LOC network testing LOC error on GT CLS classification network top-5."},
        "sentences": [{"sentence": "LOC method LOC network testing LOC error on GT CLS classification network top-5.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-imagenet-loc", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"ImageNet classification", "LOC", "mAP", "RPN", "ensemble", "convolutional layers", "ResNet-101"} & terms
    assert not {"ImageNet classification", "LOC", "mAP", "RPN", "convolutional layers"} & concepts
    assert {"ImageNet Localization (LOC)", "localization error", "ground truth class", "predicted class", "per-class regression", "category-agnostic"}.issubset(terms)
    assert {"ImageNet LOC task framing", "classifier-then-localizer pipeline", "per-class regression strategy", "per-class RPN modification"}.issubset(concepts)
    assert {
        "requires to classify and localize",
        "only accounts for",
        "based on the predicted classes",
        "We adopt",
        "per-class regression",
        "Unlike the way",
        "is designed in a per-class form",
        "ends with two sibling",
        "surpassing the second place",
    }.issubset(phrases)
    assert result.summaries.one_line.startswith("This section transitions from ImageNet detection results")
    assert result.sentences[0].core_structure == "A requires to classify and localize B."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_resnet_imagenet_localization_details_recovers_anchor_and_testing_protocol():
    document = (
        "The cls and reg layers are both in a per-class form, in contrast to prior work. "
        "Specifically, the cls layer has a 1000-d output, and each dimension is binary logistic regression for predicting being or not being an object class; "
        "the reg layer has a 1000x4-d output consisting of box regressors for 1000 classes. "
        "Our bounding box regression is with reference to multiple translation-invariant anchor boxes at each position. "
        "We use a mini-batch size of 256 images for fine-tuning. "
        "To avoid negative samples being dominate, 8 anchors are randomly sampled for each image, where the sampled positive and negative anchors have a ratio of 1:1. "
        "For testing, the network is applied on the image fully-convolutionally. "
        "Following prior work, we first perform oracle testing using the ground truth class as the classification prediction. "
        "Under the same setting, our RPN method using ResNet-101 net significantly reduces the center-crop localization error to 13.3%."
    )
    payload = {
        "terms": [
            {"term": "mini-batch", "meaning": "training detail"},
            {"term": "ImageNet classification", "meaning": "wrong section"},
            {"term": "cls layer", "meaning": "too narrow alone"},
            {"term": "box regressors", "meaning": "too narrow alone"},
            {"term": "anchor boxes", "meaning": "important"},
            {"term": "state-of-the-art methods", "meaning": "previous table"},
            {"term": "Faster R-CNN", "meaning": "too broad here"},
            {"term": "multi-scale testing", "meaning": "previous detail"},
        ],
        "concepts": [
            {"concept": "mini-batch", "explanation": "training detail"},
            {"concept": "ImageNet classification", "explanation": "wrong section"},
            {"concept": "cls layer", "explanation": "too narrow alone"},
            {"concept": "box regressors", "explanation": "too narrow alone"},
            {"concept": "anchor boxes", "explanation": "too narrow alone"},
        ],
        "phrases": [],
        "summaries": {"one_line": "The cls and reg layers are both in a per-class form, in contrast to prior work."},
        "sentences": [{"sentence": "The cls and reg layers are both in a per-class form, in contrast to prior work.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0", "term_not_in_source_sentence:anchor boxes"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-imagenet-loc-detail", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"mini-batch", "ImageNet classification", "cls layer", "box regressors", "state-of-the-art methods", "Faster R-CNN", "multi-scale testing"} & terms
    assert not {"mini-batch", "ImageNet classification", "cls layer", "box regressors", "anchor boxes"} & concepts
    assert {"reg layer", "binary logistic regression", "anchor boxes", "positive and negative anchors", "oracle testing", "fully-convolutional testing"}.issubset(terms)
    assert {"per-class cls/reg heads", "anchor-based box regression", "balanced anchor sampling", "oracle and dense testing comparison"}.issubset(concepts)
    assert {
        "in contrast to",
        "Specifically",
        "consisting of",
        "with reference to",
        "To avoid",
        "are randomly sampled",
        "fully-convolutionally",
        "using the ground truth class",
        "Under the same setting",
        "significantly reduces",
    }.issubset(phrases)
    assert result.summaries.one_line.startswith("This section details the per-class localization RPN")
    assert result.sentences[0].core_structure == "A is with reference to B at each position."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings
    assert "term_not_in_source_sentence:anchor boxes" not in result.quality_warnings
    assert "term_not_in_source_sentence:fully-convolutional testing" not in result.quality_warnings


def test_resnet_imagenet_localization_rcnn_section_recovers_final_pipeline():
    document = (
        "One may use the detection network Fast R-CNN in Faster R-CNN to improve the results. "
        "But we notice that on this dataset, one image usually contains a single dominate object, and the proposal regions highly overlap with each other and thus have very similar RoI-pooled features. "
        "As a result, the image-centric training of Fast R-CNN generates samples of small variations, which may not be desired for stochastic training. "
        "Motivated by this, in our current experiment we use the original R-CNN that is RoI-centric, in place of Fast R-CNN. "
        "We apply the per-class RPN trained as above on the training images to predict bounding boxes for the ground truth class. "
        "These predicted boxes play a role of class-dependent proposals. "
        "For each training image, the highest scored 200 proposals are extracted as training samples to train an R-CNN classifier. "
        "The image region is cropped from a proposal, warped to 224x224 pixels, and fed into the classification network as in R-CNN. "
        "For testing, the RPN generates the highest scored 200 proposals for each predicted class, and the R-CNN network is used to update these proposals' scores and box positions. "
        "Using an ensemble of networks for both classification and localization, we achieve a top-5 localization error of 9.0% on the test set. "
        "This number significantly outperforms the ILSVRC 14 results, showing a 64% relative reduction of error. "
        "This result won the 1st place in the ImageNet localization task in ILSVRC 2015."
    )
    payload = {
        "terms": [
            {"term": "mini-batch", "meaning": "wrong emphasis"},
            {"term": "RoI-pooled features", "meaning": "symptom only"},
            {"term": "stochastic training", "meaning": "symptom only"},
            {"term": "per-class RPN", "meaning": "too broad alone"},
        ],
        "concepts": [
            {"concept": "mini-batch", "explanation": "wrong emphasis"},
            {"concept": "RoI-pooled features", "explanation": "symptom only"},
            {"concept": "stochastic training", "explanation": "symptom only"},
            {"concept": "per-class RPN", "explanation": "too broad alone"},
        ],
        "phrases": [],
        "summaries": {"one_line": "One may use the detection network Fast R-CNN in Faster R-CNN to improve the results."},
        "sentences": [{"sentence": "One may use the detection network Fast R-CNN in Faster R-CNN to improve the results.", "core_structure": "Main claim + explanation."}],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "resnet-imagenet-loc-rcnn", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert not {"mini-batch", "RoI-pooled features", "stochastic training", "per-class RPN"} & terms
    assert not {"mini-batch", "RoI-pooled features", "stochastic training", "per-class RPN"} & concepts
    assert {"RoI-centric", "class-dependent proposals", "highest scored proposals", "R-CNN classifier", "relative reduction of error"}.issubset(terms)
    assert {"Fast R-CNN limitation for LOC", "RoI-centric R-CNN choice", "class-dependent proposal workflow", "localization competition result"}.issubset(concepts)
    assert {
        "One may use",
        "But we notice that",
        "As a result",
        "Motivated by this",
        "in place of",
        "play a role of",
        "For each training image",
        "are extracted as training samples",
        "is cropped from",
        "used to update",
        "relative reduction of error",
    }.issubset(phrases)
    assert result.summaries.one_line.startswith("This final section explains why ImageNet localization uses RoI-centric R-CNN")
    assert result.sentences[0].core_structure == "Motivated by this, we use A in place of B."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_bert_feature_based_related_work_becomes_literature_map():
    document = (
        "1 Unsupervised Feature-based Approaches Learning widely applicable representations of words has been an active area of research for decades, "
        "including non-neural and neural methods. Pre-trained word embeddings are an integral part of modern NLP systems, offering significant improvements over embeddings learned from scratch. "
        "To pretrain word embedding vectors, left-to-right language modeling objectives have been used. "
        "These approaches have been generalized to coarser granularities, such as sentence embeddings or paragraph embeddings. "
        "ELMo and its predecessor generalize traditional word embedding research along a different dimension. "
        "They extract context-sensitive features from a left-to-right and a right-to-left language model. "
        "The contextual representation of each token is the concatenation of the left-to-right and right-to-left representations."
    )
    payload = {
        "terms": [
            {"term": "embeddings", "meaning": "too broad alone"},
            {"term": "language modeling objectives", "meaning": "too broad alone"},
            {"term": "context-sensitive features", "meaning": "important but too narrow alone"},
        ],
        "concepts": [
            {"concept": "embeddings", "explanation": "too broad alone"},
            {"concept": "language modeling objectives", "explanation": "too broad alone"},
            {"concept": "context-sensitive features", "explanation": "important but too narrow alone"},
        ],
        "phrases": [],
        "summaries": {"one_line": "1 Unsupervised Feature-based Approaches Learning widely applicable representations of words has been an active area of research for decades."},
        "sentences": [
            {
                "sentence": (
                    "1 Unsupervised Feature-based Approaches Learning widely applicable representations of words "
                    "has been an active area of research for decades."
                ),
                "core_structure": "Main claim + explanation.",
            }
        ],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "bert-related-work-feature", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"pre-trained word embeddings", "sentence embeddings", "paragraph embeddings", "ELMo", "context-sensitive features"}.issubset(terms)
    assert "embeddings" not in terms
    assert "feature-based" not in terms
    assert "language modeling objectives" not in terms
    assert {
        "feature-based representation history",
        "coarser-granularity embeddings",
        "ELMo contextual feature extraction",
        "directional representation concatenation",
    }.issubset(concepts)
    assert "embeddings" not in concepts
    assert "language modeling objectives" not in concepts
    assert {
        "has been an active area of research",
        "are an integral part of",
        "offering significant improvements over",
        "have been generalized to",
        "along a different dimension",
        "extract context-sensitive features",
        "is the concatenation of",
    }.issubset(phrases)
    assert result.summaries.one_line == "This related-work section traces feature-based representations from word embeddings to ELMo's contextual token features."
    assert result.sentences[0].core_structure == "Learning A has been an active area of research for B."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_bert_elmo_to_finetuning_transition_becomes_comparison_map():
    document = (
        "When integrating contextual word embeddings with existing task-specific architectures, ELMo advances the state of the art "
        "for several major NLP benchmarks including question answering and named entity recognition. "
        "Melamud et al. proposed learning contextual representations through a task to predict a single word from both left and right context using LSTMs. "
        "Similar to ELMo, their model is feature-based and not deeply bidirectional. "
        "Fedus et al. shows that the cloze task can be used to improve text generation models. "
        "2. 2 Unsupervised Fine-tuning Approaches As with the feature-based approaches, the first works in this direction only pre-trained word embedding parameters from unlabeled text. "
        "More recently, sentence or document encoders which produce contextual token representations have been pre-trained from unlabeled text and fine-tuned for a supervised downstream task. "
        "The advantage of these approaches is that few parameters need to be learned from scratch. "
        "At least partly due to this advantage, OpenAI GPT achieved previously state-of-the-art results on many sentence-level tasks from the GLUE benchmark."
    )
    payload = {
        "terms": [
            {"term": "contextual word embeddings", "meaning": "contextual embeddings"},
            {"term": "bidirectional", "meaning": "too broad alone"},
            {"term": "cloze task", "meaning": "missing-word prediction"},
        ],
        "concepts": [
            {"concept": "contextual word embeddings", "explanation": "term duplicated as concept"},
            {"concept": "bidirectional", "explanation": "too broad alone"},
            {"concept": "cloze task", "explanation": "term duplicated as concept"},
        ],
        "phrases": [],
        "summaries": {"one_line": "When integrating contextual word embeddings with existing task-specific architectures, ELMo advances the state of the art for several major NLP benchmarks."},
        "sentences": [
            {
                "sentence": (
                    "When integrating contextual word embeddings with existing task-specific architectures, "
                    "ELMo advances the state of the art for several major NLP benchmarks."
                ),
                "core_structure": "Main claim + explanation.",
            }
        ],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "bert-elmo-gpt-transition", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {
        "contextual word embeddings",
        "cloze task",
        "fine-tuning approaches",
        "contextual token representations",
        "supervised downstream task",
        "OpenAI GPT",
        "GLUE benchmark",
    }.issubset(terms)
    assert "bidirectional" not in terms
    assert {
        "ELMo benchmark integration",
        "shallow bidirectionality limitation",
        "cloze-style context prediction",
        "unsupervised fine-tuning approach",
        "parameter-efficient transfer",
        "GPT as fine-tuning baseline",
    }.issubset(concepts)
    assert "contextual word embeddings" not in concepts
    assert "bidirectional" not in concepts
    assert {
        "advances the state of the art",
        "when integrating",
        "proposed learning contextual representations through",
        "Similar to ELMo",
        "not deeply bidirectional",
        "As with the feature-based approaches",
        "fine-tuned for a supervised downstream task",
        "few parameters need to be learned from scratch",
    }.issubset(phrases)
    assert result.summaries.one_line == "This transition section compares ELMo-style feature integration with GPT-style unsupervised fine-tuning."
    assert result.sentences[0].core_structure == "When integrating A with B, C advances the state of the art for D."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings


def test_bert_pretraining_finetuning_figure_becomes_workflow_lesson():
    document = (
        "TokM Masked Sentence A Masked Sentence B Pre-training Fine-Tuning NSP Mask LM Mask LM Unlabeled Sentence A and B Pair "
        "SQuAD Question Answer Pair NERMNLI Figure 1: Overall pre-training and fine-tuning procedures for BERT. "
        "Apart from output layers, the same architectures are used in both pre-training and fine-tuning. "
        "The same pre-trained model parameters are used to initialize models for different downstream tasks. "
        "During fine-tuning, all parameters are fine-tuned. "
        "[CLS] is a special symbol added in front of every input example, and [SEP] is a special separator token. "
        "2. 3 Transfer Learning from Supervised Data There has also been work showing effective transfer from supervised tasks with large datasets."
    )
    payload = {
        "terms": [
            {"term": "pre-training", "meaning": "first stage"},
            {"term": "fine-tuning", "meaning": "second stage"},
            {"term": "[CLS]", "meaning": "special token"},
        ],
        "concepts": [
            {"concept": "pre-training", "explanation": "term duplicated as concept"},
            {"concept": "fine-tuning", "explanation": "term duplicated as concept"},
            {"concept": "[CLS]", "explanation": "term duplicated as concept"},
        ],
        "phrases": [],
        "summaries": {"one_line": "TokM Masked Sentence A Masked Sentence B Pre-training Fine-Tuning NSP Mask LM Mask LM."},
        "sentences": [
            {
                "sentence": "TokM Masked Sentence A Masked Sentence B Pre-training Fine-Tuning NSP Mask LM Mask LM.",
                "core_structure": "Main claim + explanation.",
            }
        ],
        "quality_warnings": ["phrase_count_out_of_range:0"],
    }

    result = AnalysisNormalizationService().normalize_payload(payload, "bert-workflow-figure", document)
    terms = {term.term for term in result.terms}
    concepts = {concept.concept for concept in result.concepts}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {
        "pre-training",
        "fine-tuning",
        "output layers",
        "pre-trained model parameters",
        "[CLS]",
        "[SEP]",
        "supervised transfer",
    }.issubset(terms)
    assert "BERT" not in terms
    assert {
        "shared pre-training/fine-tuning architecture",
        "parameter initialization for downstream tasks",
        "full-model fine-tuning",
        "BERT input formatting",
        "supervised transfer background",
    }.issubset(concepts)
    assert "pre-training" not in concepts
    assert "fine-tuning" not in concepts
    assert "[CLS]" not in concepts
    assert "BERT" not in concepts
    assert {
        "Apart from output layers",
        "are used to initialize",
        "During fine-tuning",
        "is a special symbol added",
        "is a special separator token",
        "There has also been work showing",
        "effective transfer from",
    }.issubset(phrases)
    assert "We introduce" not in phrases
    assert result.summaries.one_line == "This section explains BERT's pre-training to fine-tuning workflow and input-format tokens."
    assert result.sentences[0].core_structure == "Apart from A, the same B are used in C and D."
    assert "phrase_count_out_of_range:0" not in result.quality_warnings
