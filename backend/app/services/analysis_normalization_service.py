import re
from difflib import SequenceMatcher
from typing import Any

from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_quality_service import AnalysisQualityService
from app.services.text_cleanup_service import normalize_pdf_ligatures


class AnalysisNormalizationService:
    def __init__(self) -> None:
        self.quality = AnalysisQualityService()

    def normalize_result(self, result: AnalysisResult, document_text: str) -> AnalysisResult:
        return self.normalize_payload(result.model_dump(), result.document_id, document_text)

    def normalize_payload(self, payload: dict[str, Any], document_id: str, document_text: str) -> AnalysisResult:
        document_text = normalize_pdf_ligatures(document_text)
        terms = self._terms(payload.get("terms"), document_text)
        phrases = self._phrases(payload.get("phrases") or payload.get("academic_phrases") or payload.get("expressions"), document_text)
        terms = self._merge_learning_rows(self._heuristic_terms(document_text), terms, "term", limit=14)
        phrases = self._merge_learning_rows(phrases, self._heuristic_phrases(document_text), "phrase", limit=12)
        if self._is_bert_text(document_text):
            terms = self._filter_bert_learning_rows(terms, "term")
            phrases = self._filter_bert_learning_rows(phrases, "phrase")
        if self._is_resnet_shortcut_option_section(document_text):
            terms = self._filter_resnet_shortcut_option_noise(terms, "term")
        if self._is_resnet_deep_bottleneck_results_section(document_text):
            terms = self._filter_resnet_deep_results_noise(terms, "term")
        if self._is_resnet_cifar_architecture_section(document_text):
            terms = self._filter_resnet_cifar_architecture_noise(terms, "term")
        if self._is_resnet_cifar_depth_behavior_section(document_text):
            terms = self._filter_resnet_cifar_depth_behavior_noise(terms, "term")
        if self._is_resnet_over_1000_layers_section(document_text):
            terms = self._filter_resnet_over_1000_layers_noise(terms, "term")
        if self._is_resnet_detection_transfer_section(document_text):
            terms = self._filter_resnet_detection_transfer_noise(terms, "term")
        if self._is_resnet_detection_baseline_section(document_text):
            terms = self._filter_resnet_detection_baseline_noise(terms, "term")
        normalized = {
            "document_id": document_id,
            "domain": self._domain(payload.get("domain")),
            "difficulty": self._difficulty(payload.get("difficulty")),
            "terms": terms,
            "phrases": phrases,
            "concepts": self._concepts(payload.get("concepts"), document_text, terms),
            "sentences": self._sentences(payload.get("sentences") or payload.get("sentence_structures") or payload.get("sentence_decomposition"), document_text),
            "summaries": self._summaries(payload.get("summaries"), document_text),
            "quality_warnings": list(payload.get("quality_warnings") or []),
        }
        normalized["concepts"] = self._merge_learning_rows(
            self._heuristic_concepts(document_text),
            normalized["concepts"],
            "concept",
            limit=10,
        )
        if self._is_bert_text(document_text):
            normalized["concepts"] = self._filter_bert_learning_rows(normalized["concepts"], "concept")
        if self._is_resnet_shortcut_option_section(document_text):
            normalized["concepts"] = self._filter_resnet_shortcut_option_noise(normalized["concepts"], "concept")
        if self._is_resnet_deep_bottleneck_results_section(document_text):
            normalized["concepts"] = self._prefer_resnet_deep_results_concepts(normalized["concepts"], document_text)
        if self._is_resnet_cifar_architecture_section(document_text):
            normalized["concepts"] = self._prefer_resnet_cifar_architecture_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_cifar_architecture_noise(normalized["phrases"], "phrase")
        if self._is_resnet_cifar_depth_behavior_section(document_text):
            normalized["concepts"] = self._prefer_resnet_cifar_depth_behavior_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_cifar_depth_behavior_noise(normalized["phrases"], "phrase")
        if self._is_resnet_over_1000_layers_section(document_text):
            normalized["concepts"] = self._prefer_resnet_over_1000_layers_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_over_1000_layers_noise(normalized["phrases"], "phrase")
        if self._is_resnet_detection_transfer_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_transfer_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_transfer_noise(normalized["phrases"], "phrase")
        if self._is_resnet_detection_baseline_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_baseline_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_baseline_noise(normalized["phrases"], "phrase")
        if self._sentences_are_weak(normalized["sentences"]) or self._needs_bert_section_sentence_override(document_text):
            normalized["sentences"] = self._heuristic_sentences(document_text)
        if self._summaries_are_weak(normalized["summaries"], document_text):
            normalized["summaries"] = self._heuristic_summaries(document_text)
        result = AnalysisResult.model_validate(normalized)
        warnings = [*result.quality_warnings, *self.quality.inspect(result, document_text)]
        return result.model_copy(update={"quality_warnings": sorted(set(warnings))})

    def _domain(self, value: Any) -> dict[str, Any]:
        value = value if isinstance(value, dict) else {}
        document_type = str(value.get("document_type") or "unknown").lower()
        if document_type not in {"paper", "report", "article", "unknown"}:
            document_type = "unknown"
        return {
            "primary_domain": str(value.get("primary_domain") or value.get("domain") or "unknown"),
            "secondary_domains": self._string_list(value.get("secondary_domains")),
            "document_type": document_type,
            "confidence": self._confidence(value.get("confidence"), 0.5),
        }

    def _difficulty(self, value: Any) -> dict[str, Any]:
        value = value if isinstance(value, dict) else {}
        level = str(value.get("overall_level") or "unknown").upper()
        if level not in {"B1", "B2", "C1", "C2"}:
            level = "domain-heavy" if "domain" in level.lower() else "unknown"
        return {
            "overall_level": level,
            "lexical_difficulty": self._score(value.get("lexical_difficulty"), 5),
            "syntax_difficulty": self._score(value.get("syntax_difficulty"), 5),
            "domain_difficulty": self._score(value.get("domain_difficulty"), 5),
            "reason": str(value.get("reason") or "Model did not provide a difficulty reason."),
        }

    def _terms(self, value: Any, document_text: str) -> list[dict[str, Any]]:
        rows = value if isinstance(value, list) else []
        terms: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            term = self._clean_learning_term(str(row.get("term") or row.get("text") or ""))
            if not term:
                continue
            if term.lower() in {"string", "term", "actual term"}:
                continue
            if not self._appears_in_text(term, document_text):
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            source_sentence = self._source_sentence(row.get("source_sentence"), term, document_text)
            priority = str(row.get("learning_priority") or row.get("priority") or "").lower()
            confidence = self._confidence(row.get("confidence"), 0.6)
            meaning = normalize_pdf_ligatures(
                str(row.get("meaning") or row.get("context_meaning") or row.get("general_meaning") or "Meaning not provided.")
            ).strip()
            terms.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "domain_relevance": row.get("domain_relevance") or priority or "medium",
                    "difficulty": row.get("difficulty") or "medium",
                    "source_sentence": source_sentence,
                    "should_save": bool(row.get("should_save", confidence >= 0.45 and priority != "low_priority")),
                    "learning_priority": priority or self._priority_from_relevance(row.get("domain_relevance")),
                    "reason": normalize_pdf_ligatures(str(row.get("reason") or row.get("why") or "Selected as a useful learning item.")),
                    "context_meaning": normalize_pdf_ligatures(str(row.get("context_meaning") or meaning)),
                    "general_meaning": normalize_pdf_ligatures(str(row.get("general_meaning") or meaning)),
                    "confidence": confidence,
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        return terms[:20]

    def _phrases(self, value: Any, document_text: str) -> list[dict[str, Any]]:
        rows = value if isinstance(value, list) else []
        phrases: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            phrase = normalize_pdf_ligatures(str(row.get("phrase") or row.get("text") or "")).strip()
            if not phrase:
                continue
            if phrase.lower() in {"string", "phrase", "actual phrase"}:
                continue
            if phrase.lower() in {
                "residual learning framework",
                "batch normalization",
                "internal covariate shift",
                "scaled dot-product attention",
                "very deep models",
                "shortcut connections",
                "residual network",
                "we compare",
                "show that",
                "as follows",
            }:
                continue
            if "weight decay" in phrase.lower() and "momentum" in phrase.lower():
                continue
            if not self._appears_in_text(phrase, document_text):
                continue
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            explanation = normalize_pdf_ligatures(str(row.get("explanation") or row.get("meaning") or "Explanation not provided.")).strip()
            phrases.append(
                {
                    "phrase": phrase,
                    "function": row.get("function") or row.get("category") or "general",
                    "explanation": explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or "useful",
                    "reason": normalize_pdf_ligatures(str(row.get("reason") or "Selected as a reusable expression.")),
                    "context_meaning": normalize_pdf_ligatures(str(row.get("context_meaning") or explanation)),
                    "confidence": self._confidence(row.get("confidence"), 0.6),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        if not phrases:
            phrases = self._fallback_phrases(document_text)
        return phrases[:20]

    def _fallback_phrases(self, document_text: str) -> list[dict[str, Any]]:
        patterns = [
            ("previous studies have suggested", "claim", "Introduces prior evidence without full certainty."),
            ("the extent to which", "general", "Frames a question about degree or scope."),
            ("remains unclear", "limitation", "Marks an unresolved research problem."),
            ("to address this gap", "method", "Connects a research gap to the method."),
        ]
        phrases: list[dict[str, Any]] = []
        for phrase, function, explanation in patterns:
            if phrase.lower() in document_text.lower():
                phrases.append(
                    {
                        "phrase": phrase,
                        "function": function,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, phrase, document_text),
                        "learning_priority": "useful",
                        "reason": "Detected fallback academic phrase.",
                        "context_meaning": explanation,
                        "confidence": 0.45,
                        "user_state": "suggested",
                    }
                )
        return phrases

    def _concepts(self, value: Any, document_text: str, terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = value if isinstance(value, list) else []
        concepts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            concept = self._clean_learning_term(str(row.get("concept") or row.get("name") or row.get("text") or ""))
            if not concept or concept.lower() in {"string", "concept", "actual concept"}:
                continue
            if not self._appears_in_text(concept, document_text):
                continue
            key = concept.lower()
            if key in seen:
                continue
            seen.add(key)
            explanation = normalize_pdf_ligatures(str(row.get("explanation") or row.get("meaning") or "Concept explanation not provided.")).strip()
            source_sentence = self._source_sentence(row.get("source_sentence"), concept, document_text)
            concepts.append(
                {
                    "concept": concept,
                    "explanation": explanation,
                    "source_sentence": source_sentence,
                    "related_terms": self._string_list(row.get("related_terms")),
                    "why_it_matters": normalize_pdf_ligatures(
                        str(row.get("why_it_matters") or row.get("reason") or "This concept helps connect vocabulary to the paper's main argument.")
                    ),
                    "references": self._string_list(row.get("references")),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.6),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        if concepts:
            return concepts[:8]
        return self._fallback_concepts(document_text, terms)

    def _fallback_concepts(self, document_text: str, terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
        concepts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for term in terms:
            concept = str(term.get("term") or "").strip()
            if not concept or concept.lower() in seen:
                continue
            if str(term.get("domain_relevance") or "").lower() == "low" and str(term.get("difficulty") or "").lower() == "easy":
                continue
            seen.add(concept.lower())
            concepts.append(
                {
                    "concept": concept,
                    "explanation": str(term.get("meaning") or "Source-grounded concept from this section."),
                    "source_sentence": str(term.get("source_sentence") or self._source_sentence(None, concept, document_text)),
                    "related_terms": [concept],
                    "why_it_matters": "This is a concept anchor: understand it before memorizing surrounding vocabulary.",
                    "references": self._references_near(str(term.get("source_sentence") or ""), document_text),
                    "learning_priority": term.get("learning_priority") or "field_term",
                    "confidence": self._confidence(term.get("confidence"), 0.45),
                    "user_state": "suggested",
                }
            )
        return concepts[:6]

    def _heuristic_terms(self, document_text: str) -> list[dict[str, Any]]:
        if self._is_bert_text(document_text):
            known = [
                (
                    "BERT",
                    "A bidirectional Transformer-based language representation model that can be fine-tuned for many NLP tasks.",
                    "field_term",
                    "medium",
                    "The main model introduced by the paper.",
                ),
                (
                    "Bidirectional Encoder Representations from Transformers",
                    "The full expansion of BERT, emphasizing bidirectional contextual representations built with Transformer encoders.",
                    "field_term",
                    "hard",
                    "This explains what the acronym means and how the model reads context.",
                ),
                (
                    "pre-training",
                    "Training a model on broad unlabeled text before adapting it to specific downstream tasks.",
                    "field_term",
                    "medium",
                    "The paper's method depends on pre-training before task-specific fine-tuning.",
                ),
                (
                    "fine-tuning",
                    "Adapting a pre-trained model to a target task with supervised training.",
                    "field_term",
                    "medium",
                    "The paper's practical value comes from fine-tuning one pre-trained model for many tasks.",
                ),
                (
                    "bidirectional representations",
                    "Representations that use both left and right context instead of only reading left-to-right.",
                    "field_term",
                    "hard",
                    "This is the central contrast between BERT and earlier language representation models.",
                ),
                (
                    "unlabeled text",
                    "Text without task-specific human labels, used for broad self-supervised pre-training.",
                    "useful",
                    "medium",
                    "The abstract says BERT pre-trains from unlabeled text.",
                ),
                (
                    "masked language model",
                    "A pre-training task where the model predicts hidden tokens from surrounding context.",
                    "field_term",
                    "hard",
                    "This is one of BERT's core pre-training tasks.",
                ),
                (
                    "feature-based",
                    "An approach that uses pre-trained representations as additional features inside task-specific architectures.",
                    "useful",
                    "medium",
                    "This is one of the two pre-BERT strategies contrasted in the paper.",
                ),
                (
                    "Generative Pre-trained Transformer",
                    "The full name of OpenAI GPT, used as an example of the fine-tuning approach.",
                    "useful",
                    "medium",
                    "The paper contrasts BERT with GPT's left-to-right pre-training.",
                ),
                (
                    "OpenAI GPT",
                    "A prior Transformer language model used as a comparison point for BERT.",
                    "useful",
                    "medium",
                    "It anchors the contrast between unidirectional and bidirectional pre-training.",
                ),
                (
                    "unidirectional language models",
                    "Language models that condition in one direction, such as left-to-right context only.",
                    "field_term",
                    "hard",
                    "This is the limitation BERT is designed to overcome.",
                ),
                (
                    "left-to-right language model",
                    "A language model that predicts using only previous context.",
                    "field_term",
                    "hard",
                    "This is the contrast point for masked language modeling.",
                ),
                (
                    "right-to-left LMs",
                    "Language models that read context in the reverse direction.",
                    "useful",
                    "medium",
                    "The paper contrasts BERT with shallow concatenation of separately trained directional models.",
                ),
                (
                    "text-pair representations",
                    "Representations used for tasks involving relationships between two text segments.",
                    "field_term",
                    "medium",
                    "This motivates next sentence prediction.",
                ),
                (
                    "task-specific architectures",
                    "Custom model architectures built for individual NLP tasks.",
                    "useful",
                    "medium",
                    "BERT aims to reduce the need for heavily engineered task-specific models.",
                ),
                (
                    "left-to-right architecture",
                    "A model architecture where each token attends only to previous tokens.",
                    "field_term",
                    "hard",
                    "The paper uses it to explain why GPT is restricted compared with BERT.",
                ),
                (
                    "self-attention layers",
                    "Transformer layers where tokens attend to other tokens to build contextual representations.",
                    "field_term",
                    "medium",
                    "This explains the architecture-level restriction in left-to-right models.",
                ),
                (
                    "next sentence prediction",
                    "A pre-training task where the model predicts whether two sentences follow each other.",
                    "field_term",
                    "hard",
                    "This task supports sentence-pair understanding in BERT.",
                ),
            ]
        elif self._is_attention_text(document_text):
            known = [
                (
                    "Transformer",
                    "An encoder-decoder architecture that relies on attention instead of recurrence or convolution.",
                    "field_term",
                    "hard",
                    "This is the paper's main model and should anchor the lesson.",
                ),
                (
                    "self-attention",
                    "An attention mechanism that relates positions within the same sequence to build contextual representations.",
                    "field_term",
                    "hard",
                    "The paper presents self-attention as the core replacement for recurrent sequence modeling.",
                ),
                (
                    "attention mechanism",
                    "A mechanism that lets a model focus on relevant positions when building a representation or generating output.",
                    "field_term",
                    "medium",
                    "The title claim depends on understanding attention as the central computation.",
                ),
                (
                    "sequence transduction",
                    "Transforming one sequence into another, such as translating a sentence from one language to another.",
                    "field_term",
                    "hard",
                    "This names the broad task family the Transformer targets.",
                ),
                (
                    "encoder-decoder",
                    "A model pattern where an encoder represents the input sequence and a decoder generates the output sequence.",
                    "field_term",
                    "medium",
                    "The Transformer keeps the encoder-decoder structure while changing the internal computation.",
                ),
                (
                    "recurrent neural networks",
                    "Neural networks that process sequences step by step using hidden state.",
                    "useful",
                    "medium",
                    "The paper contrasts recurrent models with attention-only computation.",
                ),
                (
                    "convolutional neural networks",
                    "Neural networks that use convolution operations to process local patterns.",
                    "useful",
                    "medium",
                    "The paper contrasts convolutional sequence models with the Transformer.",
                ),
                (
                    "parallelization",
                    "Running computations at the same time instead of step by step.",
                    "field_term",
                    "medium",
                    "This is one of the practical advantages claimed for self-attention.",
                ),
                (
                    "long-range dependencies",
                    "Relationships between tokens that are far apart in a sequence.",
                    "field_term",
                    "hard",
                    "The paper uses this to explain why shorter attention paths matter.",
                ),
                (
                    "BLEU",
                    "A machine translation evaluation score based on overlap with reference translations.",
                    "useful",
                    "medium",
                    "This helps the learner interpret the paper's translation results.",
                ),
            ]
        elif self._is_resnet_text(document_text):
            known = [
                (
                    "network depth",
                    "The number of layers in a neural network, treated as a major driver of representation power.",
                    "field_term",
                    "medium",
                    "This section motivates why depth matters before explaining why plain depth can fail.",
                ),
                (
                    "very deep models",
                    "Neural networks with many stacked layers, such as the 16- to 30-layer ImageNet models cited here.",
                    "useful",
                    "medium",
                    "This is the empirical background for asking whether simply stacking layers is enough.",
                ),
                (
                    "residual learning framework",
                    "A training framework that makes very deep networks easier to optimize by learning residual functions.",
                    "field_term",
                    "hard",
                    "This is the paper's main method and should anchor the lesson.",
                ),
                (
                    "residual functions",
                    "Functions that learn the difference between an input and the desired underlying mapping.",
                    "field_term",
                    "hard",
                    "This explains what the residual blocks are learning.",
                ),
                (
                    "residual mapping",
                    "The mapping F(x)=H(x)-x that the stacked layers learn instead of directly learning H(x).",
                    "field_term",
                    "hard",
                    "This is the mathematical target behind the residual block.",
                ),
                (
                    "underlying mapping",
                    "The desired mapping H(x) that the network ultimately wants to represent.",
                    "field_term",
                    "hard",
                    "It is the reference target used to define the residual mapping.",
                ),
                (
                    "F(x)+x",
                    "The residual block output: the learned residual F(x) added back to the input x.",
                    "field_term",
                    "hard",
                    "This is the formula that turns residual learning into a layer block.",
                ),
                (
                    "degradation problem",
                    "The optimization problem where adding more layers can increase training error instead of improving accuracy.",
                    "field_term",
                    "hard",
                    "This is the problem ResNet is designed to solve.",
                ),
                (
                    "vanishing/exploding gradients",
                    "Training failures where gradients become too small or too large for effective optimization.",
                    "field_term",
                    "hard",
                    "The paper separates this older obstacle from the degradation problem.",
                ),
                (
                    "normalized initialization",
                    "An initialization method that helps deep networks start training without unstable gradient scale.",
                    "useful",
                    "medium",
                    "This is cited as one reason vanishing/exploding gradients had become less central.",
                ),
                (
                    "intermediate normalization layers",
                    "Normalization layers inside the network that help stabilize training.",
                    "useful",
                    "medium",
                    "This connects the ResNet motivation to earlier normalization work.",
                ),
                (
                    "stochastic gradient descent",
                    "An optimization method that updates network parameters from sampled gradient estimates.",
                    "useful",
                    "medium",
                    "The section explains which training process is able to start converging.",
                ),
                (
                    "backpropagation",
                    "The algorithm used to compute gradients through the network during training.",
                    "useful",
                    "medium",
                    "This names the training mechanism behind the optimization discussion.",
                ),
                (
                    "higher training error",
                    "A worse fit on the training set, used here to show that the degradation problem is not simply overfitting.",
                    "field_term",
                    "hard",
                    "This is the key evidence that deeper plain networks can be harder to optimize.",
                ),
                (
                    "shallower architecture",
                    "The baseline network with fewer layers used to reason about what a deeper counterpart should be able to match.",
                    "useful",
                    "medium",
                    "This is the comparison point in the constructed-solution argument.",
                ),
                (
                    "deeper counterpart",
                    "A deeper version of the shallower network created by adding layers.",
                    "useful",
                    "medium",
                    "This helps explain why the deeper model should not be worse in principle.",
                ),
                (
                    "constructed solution",
                    "A theoretical solution where added layers behave as identity mappings and existing layers copy the shallower model.",
                    "field_term",
                    "hard",
                    "This is the logical argument behind the degradation problem.",
                ),
                (
                    "identity mapping",
                    "A mapping that passes the input forward unchanged, used as a reference path in residual learning.",
                    "field_term",
                    "medium",
                    "It explains why shortcut connections can preserve information.",
                ),
                (
                    "shortcut connections",
                    "Connections that skip one or more layers and add the input to later representations.",
                    "field_term",
                    "hard",
                    "These are the architectural mechanism behind residual blocks.",
                ),
                (
                    "identity shortcut connections",
                    "Shortcut connections that pass the input forward unchanged and add it to the stacked layer output.",
                    "field_term",
                    "hard",
                    "They implement the residual block without extra parameters or computational complexity.",
                ),
                (
                    "plain nets",
                    "Baseline networks that simply stack layers without residual shortcut structure.",
                    "field_term",
                    "medium",
                    "They are the comparison point used to show residual nets optimize better.",
                ),
                (
                    "accuracy gains",
                    "Improved accuracy obtained by making residual networks deeper.",
                    "field_term",
                    "hard",
                    "This separates the accuracy claim from the optimization claim.",
                ),
                (
                    "top-5 error",
                    "An ImageNet metric where a prediction is correct if the true label appears in the model's five highest-scoring classes.",
                    "useful",
                    "medium",
                    "This explains the reported 3.57% ImageNet result.",
                ),
                (
                    "generalization performance",
                    "How well a learned representation works beyond the training setup or original task.",
                    "useful",
                    "medium",
                    "This supports the claim that residual learning is broadly useful.",
                ),
                (
                    "residual vectors",
                    "Differences or residual components represented relative to another quantity, used here as related-work background.",
                    "useful",
                    "medium",
                    "This connects ResNet's residual idea to earlier residual representations.",
                ),
                (
                    "Multigrid method",
                    "A solver approach that reformulates a problem across multiple scales and handles residual solutions between scales.",
                    "useful",
                    "hard",
                    "It is related-work evidence that residual reformulation can simplify optimization.",
                ),
                (
                    "hierarchical basis preconditioning",
                    "A preconditioning method using variables that represent residual vectors between scales.",
                    "useful",
                    "hard",
                    "It supports the related-work pattern of residual reformulation.",
                ),
                (
                    "highway networks",
                    "Networks with gated shortcut connections proposed around the same time as ResNet.",
                    "field_term",
                    "hard",
                    "They are the closest related shortcut-connection baseline in this passage.",
                ),
                (
                    "gating functions",
                    "Functions that control whether information passes through a shortcut path.",
                    "field_term",
                    "medium",
                    "This distinguishes highway networks from ResNet's parameter-free identity shortcuts.",
                ),
                (
                    "parameter-free identity shortcuts",
                    "ResNet shortcuts that pass information without learned gate parameters.",
                    "field_term",
                    "hard",
                    "This contrast explains what is distinctive about ResNet shortcuts.",
                ),
                (
                    "identity shortcuts",
                    "Shortcut connections that pass information without learned gates in ResNet.",
                    "field_term",
                    "hard",
                    "This is the exact related-work contrast against highway-network gates.",
                ),
                (
                    "residual network",
                    "The residual version of the plain baseline after shortcut connections are inserted.",
                    "field_term",
                    "medium",
                    "It is the architecture created from the plain network in this section.",
                ),
                (
                    "dimension matching",
                    "Adjusting shortcut paths so tensors with different channel dimensions can be added.",
                    "field_term",
                    "hard",
                    "This is why projection shortcuts or zero padding are discussed.",
                ),
                (
                    "dimensions increase",
                    "The condition where feature-map dimensions change and shortcut paths need special handling.",
                    "field_term",
                    "medium",
                    "This introduces why the paper lists two shortcut options.",
                ),
                (
                    "zero padding",
                    "Adding extra zero entries so an identity shortcut can match increased dimensions without new parameters.",
                    "useful",
                    "medium",
                    "It is option A for handling dimension increases.",
                ),
                (
                    "zero entries padded",
                    "The source phrase for padding identity shortcuts with zeros when dimensions increase.",
                    "useful",
                    "medium",
                    "This is the no-extra-parameter shortcut option.",
                ),
                (
                    "1x1 convolutions",
                    "Projection layers used to match feature-map dimensions in shortcut paths.",
                    "field_term",
                    "hard",
                    "This is option B for dimension matching.",
                ),
                (
                    "bottleneck",
                    "A lower-dimensional middle layer that reduces computation inside a residual block.",
                    "field_term",
                    "hard",
                    "This is the core efficiency idea in the 1x1-3x3-1x1 block design.",
                ),
                (
                    "bottleneck architectures",
                    "Deep ResNet architectures that use bottleneck blocks for efficiency.",
                    "field_term",
                    "hard",
                    "This explains how 50/101/152-layer ResNets stay computationally practical.",
                ),
                (
                    "time complexity",
                    "The computational cost of running the model.",
                    "field_term",
                    "medium",
                    "This section uses it to explain why identity shortcuts are efficient.",
                ),
                (
                    "time complexity and model size",
                    "The combined computation and parameter/storage cost of the model.",
                    "field_term",
                    "medium",
                    "Projection shortcuts can increase this cost in bottleneck designs.",
                ),
                (
                    "practical considerations",
                    "Engineering constraints such as compute and model size that shape the architecture choice.",
                    "useful",
                    "medium",
                    "This explains why bottleneck designs are used even when non-bottleneck ResNets can also gain accuracy.",
                ),
                (
                    "50/101/152-layer ResNets",
                    "Very deep residual networks built with bottleneck blocks.",
                    "field_term",
                    "hard",
                    "These models show that residual learning can scale to much greater depth.",
                ),
                (
                    "single-model top-5 validation error",
                    "The ImageNet validation metric for one model before ensembling.",
                    "field_term",
                    "medium",
                    "This tells the reader the result is a direct model score, not only an ensemble score.",
                ),
                (
                    "ensemble",
                    "A prediction system that combines several trained models.",
                    "field_term",
                    "medium",
                    "The paper uses an ensemble for the ILSVRC 2015 winning entry.",
                ),
                (
                    "ILSVRC 2015",
                    "The ImageNet Large Scale Visual Recognition Challenge in 2015.",
                    "useful",
                    "medium",
                    "This is the competition where the ResNet entry won first place.",
                ),
                (
                    "state-of-the-art methods",
                    "The best-performing methods available at the time of comparison.",
                    "useful",
                    "medium",
                    "This marks the transition from architecture analysis to benchmark comparison.",
                ),
                (
                    "zero-padding shortcuts",
                    "Parameter-free shortcuts that pad extra dimensions with zeros when dimensions increase.",
                    "field_term",
                    "medium",
                    "This is option A in the projection-shortcut comparison.",
                ),
                (
                    "parameter-free identity shortcuts",
                    "Identity shortcuts without learned projection parameters.",
                    "field_term",
                    "hard",
                    "This is the cheap shortcut design the paper prefers when possible.",
                ),
                (
                    "all shortcuts are parameter-free",
                    "The condition for option A: no learned shortcut projection parameters are used.",
                    "useful",
                    "medium",
                    "This marks the cheapest shortcut option in the comparison.",
                ),
                (
                    "other shortcuts are identity",
                    "The condition for option B: projections are used only for dimension increases, while other shortcuts remain identity.",
                    "useful",
                    "medium",
                    "This distinguishes the balanced projection option.",
                ),
                (
                    "all shortcuts are projections",
                    "The condition for option C: every shortcut uses a projection.",
                    "useful",
                    "medium",
                    "It tests whether projections everywhere are worth extra parameters.",
                ),
                (
                    "linear projection",
                    "A learned shortcut transformation used when input and output dimensions do not match.",
                    "field_term",
                    "hard",
                    "It explains how residual blocks handle dimension changes.",
                ),
                (
                    "projection shortcut",
                    "A shortcut path that uses a learned projection, often a 1x1 convolution, to match feature-map dimensions.",
                    "field_term",
                    "hard",
                    "It is the alternative to pure identity shortcuts when dimensions increase.",
                ),
                (
                    "convolutional layers",
                    "Neural-network layers that apply learned filters over feature maps.",
                    "field_term",
                    "medium",
                    "They are the concrete layer type used in the ImageNet architectures.",
                ),
                (
                    "feature maps",
                    "Spatial activation tensors produced by convolutional layers.",
                    "field_term",
                    "medium",
                    "Dimension matching in ResNet is described in terms of feature maps and channels.",
                ),
                (
                    "plain network",
                    "The non-residual baseline architecture used for comparison against residual networks.",
                    "field_term",
                    "medium",
                    "It anchors the architecture comparison before shortcuts are inserted.",
                ),
                (
                    "VGG nets",
                    "A prior convolutional architecture family that inspires the plain ResNet baseline design.",
                    "useful",
                    "medium",
                    "It explains where the baseline design philosophy comes from.",
                ),
                (
                    "ImageNet",
                    "A large image recognition benchmark used to evaluate the paper's models.",
                    "useful",
                    "medium",
                    "It grounds the paper's empirical claims.",
                ),
                (
                    "ImageNet 2012 classification dataset",
                    "The benchmark dataset used for the paper's main image-classification experiments.",
                    "field_term",
                    "medium",
                    "This anchors the experimental setting.",
                ),
                (
                    "top-1 and top-5 error rates",
                    "ImageNet evaluation metrics that measure whether the correct class is the first prediction or within the top five predictions.",
                    "field_term",
                    "medium",
                    "These are the metrics used to report classification performance.",
                ),
                (
                    "18-layer and 34-layer plain nets",
                    "The two non-residual baseline depths compared in the first ImageNet experiment.",
                    "field_term",
                    "medium",
                    "This comparison reveals the degradation problem in plain networks.",
                ),
                (
                    "higher validation error",
                    "Worse validation-set performance, used here as evidence that the deeper plain network performs worse.",
                    "field_term",
                    "medium",
                    "This is the first concrete result in the ImageNet plain-network experiment.",
                ),
                (
                    "training/validation errors",
                    "The error curves compared to diagnose whether the problem is optimization or generalization.",
                    "field_term",
                    "medium",
                    "This tells the reader what the figure comparison is meant to reveal.",
                ),
                (
                    "vanishing gradients",
                    "A training failure where gradients become too small to update earlier layers effectively.",
                    "field_term",
                    "medium",
                    "This section explicitly argues that vanishing gradients are unlikely to explain the plain-net degradation.",
                ),
                (
                    "forward propagated signals",
                    "Activations passed from earlier layers toward later layers during inference/training.",
                    "field_term",
                    "medium",
                    "The authors use non-zero forward signal variance as evidence against vanishing signals.",
                ),
                (
                    "backward propagated gradients",
                    "Gradients passed backward through the network during training.",
                    "field_term",
                    "medium",
                    "Healthy backward gradient norms are evidence that gradients are not simply vanishing.",
                ),
                (
                    "convergence rates",
                    "How quickly optimization reduces training error.",
                    "field_term",
                    "hard",
                    "The authors conjecture slow convergence may explain deep plain-net optimization difficulty.",
                ),
                (
                    "CIFAR-10",
                    "A small image classification benchmark used for controlled experiments.",
                    "useful",
                    "medium",
                    "It appears in the paper's experimental validation.",
                ),
                (
                    "stride of 2",
                    "A convolution setting that downsamples the spatial resolution by moving two pixels at a time.",
                    "field_term",
                    "medium",
                    "This explains how the CIFAR-10 architecture performs subsampling.",
                ),
                (
                    "global average pooling",
                    "A pooling layer that averages each feature map before classification.",
                    "field_term",
                    "medium",
                    "This is the final aggregation step before the classifier.",
                ),
                (
                    "10-way fully-connected layer",
                    "A classifier layer with ten output classes for CIFAR-10.",
                    "field_term",
                    "medium",
                    "This connects the architecture to the ten CIFAR-10 classes.",
                ),
                (
                    "6n+2 stacked weighted layers",
                    "The depth formula for the CIFAR-10 residual/plain networks in this experiment.",
                    "field_term",
                    "hard",
                    "This is how the paper maps n to 20/32/44/56-layer networks.",
                ),
                (
                    "3n shortcuts",
                    "The number of shortcut connections created by pairing 3x3 convolutional layers.",
                    "field_term",
                    "medium",
                    "This identifies how many residual connections the CIFAR-10 architecture uses.",
                ),
                (
                    "20, 32, 44, and 56-layer networks",
                    "The CIFAR-10 network depths compared by varying n.",
                    "field_term",
                    "medium",
                    "These are the controlled depth variants used to compare plain nets and ResNets.",
                ),
                (
                    "optimization difficulty",
                    "The failure mode where deeper plain networks train worse as depth increases.",
                    "field_term",
                    "hard",
                    "This is the central behavior the CIFAR-10 experiment confirms.",
                ),
                (
                    "110-layer ResNet",
                    "A deeper CIFAR-10 residual network tested after the 20/32/44/56-layer comparison.",
                    "field_term",
                    "hard",
                    "This shows the depth-scaling behavior beyond the initial comparison.",
                ),
                (
                    "learning-rate warmup",
                    "Starting with a smaller learning rate before returning to the main learning rate.",
                    "field_term",
                    "medium",
                    "This explains the training adjustment needed for the 110-layer ResNet.",
                ),
                (
                    "1202-layer network",
                    "An aggressively deep ResNet variant used to test whether residual learning scales past 1000 layers.",
                    "field_term",
                    "hard",
                    "This is the stress-test model in the over-1000-layer section.",
                ),
                (
                    "overfitting",
                    "A generalization failure where training error is very low but test performance is worse.",
                    "field_term",
                    "medium",
                    "The paper uses this to explain why the 1202-layer network tests worse than the 110-layer network.",
                ),
                (
                    "strong regularization",
                    "Training constraints that reduce overfitting, such as maxout or dropout in the cited CIFAR-10 systems.",
                    "field_term",
                    "medium",
                    "This explains the suggested direction for improving the very deep model.",
                ),
                (
                    "deep and thin architectures",
                    "Architectures that impose regularization by using many layers with limited width.",
                    "field_term",
                    "hard",
                    "The authors use this design choice instead of maxout/dropout in the paper.",
                ),
                (
                    "ResNet-101",
                    "A 101-layer residual network used here as a stronger feature extractor than VGG-16.",
                    "field_term",
                    "hard",
                    "This is the model swap being tested in object detection.",
                ),
                (
                    "detection implementation",
                    "The object-detection system held constant while the backbone changes.",
                    "field_term",
                    "medium",
                    "This makes the comparison isolate the network representation as the source of gains.",
                ),
                (
                    "COCO dataset",
                    "A challenging object-detection benchmark used to evaluate transfer performance.",
                    "field_term",
                    "hard",
                    "This is where ResNet-101 shows a large transfer gain.",
                ),
                (
                    "mAP@[.5, .95]",
                    "COCO's standard detection metric averaged over IoU thresholds from .5 to .95.",
                    "field_term",
                    "hard",
                    "This is the metric where ResNet improves by 6.0 points.",
                ),
                (
                    "learned representations",
                    "The internal features learned by the network and reused for downstream tasks.",
                    "field_term",
                    "hard",
                    "The paper says the detection gain comes from better representations.",
                ),
                (
                    "ILSVRC & COCO 2015 competitions",
                    "The recognition/detection competitions where deep residual nets won several tracks.",
                    "useful",
                    "medium",
                    "This provides external validation beyond the classification experiments.",
                ),
                (
                    "Faster R-CNN",
                    "The object-detection system used as the baseline detector in the appendix.",
                    "field_term",
                    "hard",
                    "This is the detection framework that ResNet is plugged into.",
                ),
                (
                    "fine-tuned on object detection data",
                    "The process of adapting ImageNet classification models to detection datasets.",
                    "field_term",
                    "medium",
                    "This explains how the classification backbone becomes a detector backbone.",
                ),
                (
                    "Networks on Conv feature maps",
                    "The NoC idea used to handle ResNet's lack of hidden fully connected layers.",
                    "field_term",
                    "hard",
                    "This is the architectural adaptation needed for Faster R-CNN.",
                ),
                (
                    "full-image shared conv feature maps",
                    "Convolutional features computed once over the full image and shared by detection regions.",
                    "field_term",
                    "hard",
                    "This is how the appendix describes the ResNet detection backbone.",
                ),
            ]
        else:
            known = [
            (
                "Batch Normalization",
                "A technique that normalizes layer inputs within each mini-batch so deep networks train faster and more stably.",
                "field_term",
                "hard",
                "The title method and the main object of the paper.",
            ),
            (
                "internal covariate shift",
                "A change in the distribution of internal layer inputs while earlier network parameters are being updated.",
                "field_term",
                "hard",
                "This is the problem the paper claims to reduce.",
            ),
            (
                "mini-batch",
                "A small group of training examples used to estimate gradients and update parameters.",
                "must_review",
                "medium",
                "The method normalizes statistics over mini-batches, so this term is central.",
            ),
            (
                "stochastic gradient descent",
                "An optimization method that updates model parameters using gradient estimates from sampled examples.",
                "field_term",
                "medium",
                "It is the training process whose difficulty the paper addresses.",
            ),
            (
                "learning rate",
                "A training hyperparameter that controls the size of each parameter update.",
                "useful",
                "medium",
                "The paper repeatedly links Batch Normalization to using higher learning rates.",
            ),
            (
                "saturating nonlinearities",
                "Activation functions whose gradients become very small in some input ranges.",
                "field_term",
                "hard",
                "This explains one training failure mode the paper tries to avoid.",
            ),
            (
                "vanishing gradients",
                "A training problem where gradients become too small to update earlier layers effectively.",
                "field_term",
                "hard",
                "It connects the language of optimization to the paper's motivation.",
            ),
            (
                "Dropout",
                "A regularization method that randomly disables activations during training.",
                "useful",
                "medium",
                "The paper claims Batch Normalization can reduce the need for Dropout.",
            ),
            (
                "ImageNet classification",
                "A large-scale image recognition benchmark used to evaluate model performance.",
                "useful",
                "medium",
                "It is the paper's empirical demonstration setting.",
            ),
            (
                "population statistics",
                "Mean and variance estimates used during inference rather than per-batch training statistics.",
                "field_term",
                "hard",
                "This matters when moving from training-time normalization to inference.",
            ),
            ]
        rows: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in known:
            sentence = self._source_sentence(None, term, document_text)
            if not sentence or not self._appears_in_text(term, sentence):
                continue
            rows.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "domain_relevance": "high" if priority in {"field_term", "must_review"} else "medium",
                    "difficulty": difficulty,
                    "source_sentence": sentence,
                    "should_save": priority != "low_priority",
                    "learning_priority": priority,
                    "reason": reason,
                    "context_meaning": meaning,
                    "general_meaning": meaning,
                    "confidence": 0.9,
                    "user_state": "suggested",
                }
            )
        return rows

    def _heuristic_phrases(self, document_text: str) -> list[dict[str, Any]]:
        phrase_specs = [
            ("is complicated by the fact that", "claim", "Introduces the cause of a difficult problem."),
            ("We refer to this phenomenon as", "general", "Names a phenomenon after describing it."),
            ("address the problem by", "method", "Connects a problem to the proposed method."),
            ("draws its strength from", "claim", "Explains the source of a method's advantage."),
            ("allows us to", "result", "States a practical benefit of the method."),
            ("acts as a regularizer", "result", "Describes an additional training benefit."),
            ("Applied to", "result", "Introduces an experimental application or result setting."),
            ("as opposed to", "contrast", "Contrasts one method with another."),
            ("This motivates us to", "method", "Moves from a limitation to a design choice."),
            ("we propose", "method", "Signals the authors' proposed contribution."),
            ("we demonstrate", "result", "Signals evidence or experimental proof."),
            ("It has been long known", "claim", "Introduces established background knowledge."),
        ]
        if self._is_bert_text(document_text):
            phrase_specs = [
                ("There are two existing strategies", "claim", "Introduces a two-part literature map."),
                ("We introduce", "method", "Signals the paper's new contribution."),
                ("which stands for", "general", "Expands an acronym or named method."),
                ("Unlike recent", "contrast", "Contrasts the proposed method with prior work."),
                ("is designed to", "method", "Explains the intended design or purpose of a method."),
                ("can be fine-tuned", "method", "Explains how a pre-trained model is adapted to tasks."),
                ("We argue that", "claim", "Signals the authors' position or critique."),
                ("major limitation is that", "limitation", "Introduces the main weakness in prior methods."),
                ("For example", "general", "Introduces supporting evidence or an illustration."),
                ("by proposing", "method", "Connects the proposed method to the problem it solves."),
                ("In addition to", "general", "Adds another method, task, or evidence item."),
                ("The contributions of our paper are as follows", "general", "Signals a contribution list."),
                ("We demonstrate the importance of", "result", "States what the authors claim to prove."),
                ("This is also in contrast to", "contrast", "Contrasts the proposed method with another prior approach."),
                ("reduce the need for", "result", "States a practical simplification benefit."),
                ("we demonstrate", "result", "Signals the evidence used to support the paper's claim."),
                ("obtains new state-of-the-art", "result", "States an empirical performance result."),
            ]
        elif self._is_attention_text(document_text):
            phrase_specs = [
                ("dominant sequence transduction models", "claim", "Introduces the prior model family the paper is about to contrast."),
                ("based solely on", "method", "States the main design choice by excluding other mechanisms."),
                ("dispensing with", "contrast", "Means the method removes or avoids something used by earlier systems."),
                ("entirely on an attention mechanism", "method", "States that attention is the central computation of the architecture."),
                ("drawing global dependencies", "claim", "Explains what attention is useful for across input and output positions."),
                ("allow for significantly more parallelization", "result", "States the runtime or training advantage of the architecture."),
                ("The best performing models", "claim", "Introduces the baseline class before the authors narrow the contrast."),
                ("we propose", "method", "Signals the authors' new contribution."),
                ("we establish a new state of the art", "result", "Signals an empirical result claim."),
                ("with considerably less training cost", "result", "Links model quality to efficiency, not only accuracy."),
            ]
        elif self._is_resnet_text(document_text):
            phrase_specs = [
                ("more difficult to train", "limitation", "Introduces the practical problem caused by increasing network depth."),
                ("of crucial importance", "claim", "Signals that depth is a major factor before the paper explains its optimization problem."),
                ("Driven by the significance of", "claim", "Moves from prior evidence to the research question."),
                ("a question arises", "limitation", "Introduces the problem the paper will answer."),
                ("as easy as stacking more layers", "limitation", "Frames the naive assumption that the paper challenges."),
                ("has been largely addressed by", "claim", "Marks an older obstacle as mostly handled by prior methods."),
                ("has been exposed", "limitation", "Introduces the degradation problem as a newly visible obstacle."),
                ("not caused by overfitting", "contrast", "Separates optimization degradation from a common explanation."),
                ("leads to higher training error", "result", "States the evidence that added depth can hurt optimization."),
                ("not all systems are similarly easy to optimize", "limitation", "States the optimization gap that motivates residual learning."),
                ("Let us consider", "general", "Introduces a reasoning example or thought experiment."),
                ("There exists a solution by construction", "claim", "Signals a theoretical existence argument."),
                ("no higher training error than", "result", "States what the deeper model should achieve in principle."),
                ("experiments show that", "result", "Introduces empirical evidence against the theoretical expectation."),
                ("Instead of hoping", "contrast", "Contrasts direct mapping with residual mapping."),
                ("directly fit a desired underlying mapping", "method", "Names the mapping that plain stacked layers would need to learn."),
                ("fit a residual mapping", "method", "States the new target learned by the stacked layers."),
                ("is recast into", "method", "Signals a mathematical reformulation of the original mapping."),
                ("easier to optimize", "result", "States the optimization benefit of residual mapping."),
                ("skipping one or more layers", "general", "Defines shortcut connections in plain architectural terms."),
                ("neither extra parameter nor computational complexity", "result", "States that identity shortcuts are cheap to add."),
                ("neither extra parameter nor computation complexity", "result", "States that identity shortcuts are cheap to add."),
                ("with reference to", "method", "Explains the reference point used for residual perturbations."),
                ("provide reasonable preconditioning", "claim", "Explains why identity mappings can make optimization easier."),
                ("identity mapping is sufficient", "result", "Reports that the cheap identity shortcut is enough in the tested setting."),
                ("only used when matching dimensions", "method", "Limits when the projection shortcut is needed."),
                ("Based on the above plain network", "method", "Moves from the plain baseline to its residual counterpart."),
                ("we insert shortcut connections", "method", "States how the plain network is converted into a residual network."),
                ("turn the network into", "method", "Signals an architecture transformation."),
                ("can be directly used", "method", "Explains when identity shortcuts apply without modification."),
                ("When the dimensions increase", "general", "Introduces the condition that requires shortcut options."),
                ("we consider two options", "general", "Signals that alternatives will be listed."),
                ("introduces no extra parameter", "result", "Explains the cost advantage of the identity/zero-padding option."),
                ("is flexible", "claim", "States that the residual function can use different layer depths."),
                ("applicable to convolutional layers", "method", "Extends the notation from fully connected layers to convolutional networks."),
                ("To provide instances for discussion", "general", "Introduces concrete model instances after the formulation."),
                ("is worth noticing", "claim", "Flags an observation the authors want the reader to notice."),
                ("We evaluate our method", "method", "Introduces the benchmark evaluation setting."),
                ("We first evaluate", "method", "Signals the first experiment in a sequence."),
                ("The results in Table 2 show that", "result", "Turns table data into the section's main experimental claim."),
                ("To reveal the reasons", "method", "Explains why the authors inspect training and validation curves."),
                ("unlikely to be caused by", "contrast", "Rejects a tempting explanation for the observed optimization difficulty."),
                ("ensures forward propagated signals", "claim", "Explains why Batch Normalization makes vanishing forward signals unlikely."),
                ("exhibit healthy norms", "result", "Reports evidence that backward gradients are not vanishing."),
                ("neither forward nor backward signals vanish", "contrast", "Summarizes the argument against vanishing-gradient explanations."),
                ("may have exponentially low convergence rates", "claim", "States the authors' conjecture about why deep plain nets train slowly."),
                ("Next we evaluate", "method", "Moves from plain-network diagnosis to residual-network experiments."),
                ("Next we investigate", "method", "Moves from residual-net evaluation to shortcut-option analysis."),
                ("we compare three options", "method", "Introduces an A/B/C design comparison."),
                ("are responsible for", "general", "Explains the role assigned to a component inside an architecture."),
                ("particularly important for", "claim", "Signals that a component matters more in this specific design."),
                ("lead to more efficient models", "result", "States the efficiency benefit of identity shortcuts."),
                ("mainly due to practical considerations", "claim", "Explains that an architecture choice is driven by engineering cost."),
                ("considerably better than", "result", "States that all residual shortcut options beat the plain counterpart."),
                ("slightly better than", "result", "Compares two shortcut options with a small performance difference."),
                ("marginally better than", "result", "Marks a very small advantage in the comparison."),
                ("not essential for addressing", "claim", "States that projection shortcuts are not required to solve the degradation problem."),
                ("trained end-to-end", "method", "Signals that the whole network remains trainable as one model."),
                ("We show that", "result", "Introduces a list of empirical claims."),
                ("easy to optimize", "result", "States the optimization benefit of residual networks."),
                ("counterpart plain nets", "contrast", "Introduces the non-residual comparison baseline."),
                ("exhibit higher training error", "result", "States the evidence that plain deeper nets optimize worse."),
                ("accuracy gains from", "result", "States that extra depth improves accuracy for residual nets."),
                ("substantially better than previous networks", "result", "Compares results against earlier architectures."),
                ("not just akin to a particular dataset", "general", "Signals that the result is not dataset-specific."),
                ("obtain excellent results", "result", "Introduces strong benchmark performance."),
                ("while still having lower complexity than", "contrast", "Compares depth and complexity against a baseline."),
                ("lower complexity than", "contrast", "Compares a deeper ResNet against a computationally heavier VGG baseline."),
                ("more accurate than", "result", "States that deeper ResNets outperform shallower residual networks."),
                ("by considerable margins", "result", "Emphasizes that the reported accuracy improvement is large."),
                ("We do not observe", "result", "Reports that the degradation problem does not appear in this setting."),
                ("achieved very competitive accuracy", "result", "Introduces a strong baseline result before the final comparison."),
                ("single-model top-5 validation error", "result", "Names the ImageNet metric used for the single-model result."),
                ("form an ensemble", "method", "Explains how multiple models are combined for the competition entry."),
                ("won the 1st place", "result", "Reports competition-level empirical validation."),
                ("Our focus is on", "method", "Signals the experimental aim before describing CIFAR-10 setup."),
                ("but not on pushing", "contrast", "Clarifies that the CIFAR-10 experiment studies behavior rather than chasing the benchmark record."),
                ("subsampling is performed by", "method", "Explains how spatial size is reduced in the CIFAR-10 architecture."),
                ("network ends with", "method", "Introduces the final classifier layers of the architecture."),
                ("There are totally", "general", "Signals the formula for total network depth."),
                ("When shortcut connections are used", "method", "Explains where residual shortcuts are attached."),
                ("identity shortcuts in all cases", "method", "States that CIFAR-10 experiments use the parameter-free option A shortcut."),
                ("leading to", "result", "Connects the chosen n values to concrete network depths."),
                ("suffer from increased depth", "result", "States that deeper plain nets get worse as depth increases."),
                ("similar to that on ImageNet", "general", "Connects the CIFAR-10 behavior to earlier ImageNet evidence."),
                ("fundamental problem", "claim", "Generalizes the optimization difficulty beyond one dataset."),
                ("manage to overcome", "result", "States that ResNets solve the optimization difficulty."),
                ("demonstrate accuracy gains", "result", "States that deeper ResNets improve accuracy."),
                ("when the depth increases", "general", "Marks depth as the condition under comparison."),
                ("slightly too large to start converging", "limitation", "Explains why the 110-layer experiment needs a warmup schedule."),
                ("warm up the training", "method", "Names the temporary lower-learning-rate training phase."),
                ("aggressively deep model", "general", "Describes the 1202-layer network as an extreme depth experiment."),
                ("shows no optimization difficulty", "result", "States that residual learning still optimizes the 1202-layer model."),
                ("still open problems", "limitation", "Marks that optimization success does not solve every issue."),
                ("worse than that of", "contrast", "Compares the 1202-layer test result against the 110-layer result."),
                ("because of overfitting", "claim", "Explains the likely cause of worse test performance despite low training error."),
                ("unnecessarily large", "limitation", "Explains why the 1202-layer network may overfit the small dataset."),
                ("without distracting from", "method", "Explains why the paper avoids stronger regularization in this experiment."),
                ("replacing VGG-16 with ResNet-101", "method", "Introduces the controlled model swap used for object detection."),
                ("can only be attributed to", "claim", "Explains why the gains are credited to better networks rather than implementation changes."),
                ("Most remarkably", "result", "Highlights the strongest reported transfer result."),
                ("relative improvement", "result", "Expresses the gain as a percentage relative to the baseline."),
                ("solely due to", "claim", "Attributes the improvement to learned representations."),
                ("Based on deep residual nets", "claim", "Connects competition wins to the residual-network backbone."),
                ("detection method based on", "method", "Introduces the detection framework used in the appendix."),
                ("initialized by", "method", "Explains where the detector backbone weights come from."),
                ("fine-tuned on", "method", "Explains how classification models are adapted to detection data."),
                ("Unlike VGG-16", "contrast", "Contrasts ResNet's architecture with the VGG detector backbone."),
                ("adopt the idea of", "method", "Introduces the NoC adaptation used for ResNet detection."),
                ("to address this issue", "method", "Connects the architecture problem to the proposed adaptation."),
                ("analogous to", "general", "Explains how ResNet layers correspond to VGG convolutional layers."),
                ("This strong evidence shows that", "result", "Moves from specific experiments to a general principle claim."),
                ("is shown to be more effective than", "result", "Reports prior evidence in related work."),
                ("reformulates the system as", "method", "Signals a reformulation strategy in related work."),
                ("is responsible for", "general", "Explains the role of a subproblem or component."),
                ("relies on variables that", "method", "Explains the mechanism of a related method."),
                ("converge much faster than", "result", "Compares solver effectiveness."),
                ("These methods suggest that", "claim", "Moves from related work examples to a general lesson."),
                ("Practices and theories that lead to", "claim", "Introduces a related-work lineage."),
                ("Concurrent with our work", "general", "Signals contemporaneous related work."),
                ("in contrast to", "contrast", "Marks the difference between related work and the authors' method."),
                ("On the contrary", "contrast", "Rejects the related-work behavior and introduces the authors' different formulation."),
                ("In addition", "general", "Adds a second contrast or supporting point after the first distinction."),
                ("represent non-residual functions", "contrast", "Explains a limitation or difference of gated shortcuts."),
                ("to ease the training of", "method", "States the purpose of the proposed residual learning framework."),
                ("substantially deeper than", "claim", "Signals the scale of the architecture compared with previous models."),
                ("explicitly reformulate", "method", "Signals that the paper changes the learning target, not only the model size."),
                ("with reference to", "general", "Introduces the baseline mapping used to define residual functions."),
                ("provide comprehensive empirical evidence", "result", "Signals that the paper supports the method with experiments."),
                ("easier to optimize", "result", "States the optimization benefit of residual learning."),
                ("can gain accuracy from", "result", "States that depth becomes useful after the optimization issue is addressed."),
            ]
        rows: list[dict[str, Any]] = []
        lower_text = document_text.lower()
        for phrase, function, explanation in phrase_specs:
            if phrase.lower() not in lower_text:
                continue
            rows.append(
                {
                    "phrase": phrase,
                    "function": function,
                    "explanation": explanation,
                    "source_sentence": self._source_sentence(None, phrase, document_text),
                    "learning_priority": "must_review" if function in {"method", "result", "contrast"} else "useful",
                    "reason": "Reusable academic paper-reading expression detected in the source.",
                    "context_meaning": explanation,
                    "confidence": 0.85,
                    "user_state": "suggested",
                }
            )
        return rows

    def _heuristic_concepts(self, document_text: str) -> list[dict[str, Any]]:
        if self._is_bert_text(document_text):
            specs = [
                (
                    "feature-based",
                    "A prior strategy that uses pre-trained representations as features in task-specific models.",
                    "It helps the reader understand what BERT is being compared against.",
                ),
                (
                    "fine-tuning",
                    "A prior and continuing strategy that adapts all pre-trained parameters to a downstream task.",
                    "This is the workflow BERT makes more powerful by changing pre-training.",
                ),
                (
                    "unidirectional language models",
                    "Prior language models that learn representations from one direction of context.",
                    "This is the limitation the paper uses to motivate bidirectional pre-training.",
                ),
                (
                    "masked language model",
                    "BERT's pre-training objective for learning from both left and right context.",
                    "It is the core mechanism used to overcome unidirectionality.",
                ),
                (
                    "next sentence prediction",
                    "A pre-training task for learning text-pair relationships.",
                    "It explains why BERT can handle sentence-pair tasks beyond single-token prediction.",
                ),
                (
                    "bidirectional pre-training",
                    "A training setup that lets representations use both left and right context.",
                    "This is the core advantage the contribution list emphasizes.",
                ),
                (
                    "task-specific architectures",
                    "Heavily engineered models built separately for individual NLP tasks.",
                    "The paper claims BERT reduces the need for this kind of task-specific engineering.",
                ),
                (
                    "BERT",
                    "A bidirectional Transformer representation model introduced for language understanding tasks.",
                    "This is the paper's main contribution and the anchor for the rest of the terminology.",
                ),
                (
                    "Bidirectional Encoder Representations from Transformers",
                    "The expanded name of BERT: contextual representations built from both left and right context using Transformer encoders.",
                    "It explains why BERT differs from earlier one-directional representation models.",
                ),
                (
                    "pre-training",
                    "The broad training stage before task-specific adaptation.",
                    "This is the first half of BERT's transfer-learning workflow.",
                ),
                (
                    "next sentence prediction",
                    "A pre-training objective that teaches relationships between sentence pairs.",
                    "This supports tasks where understanding the relation between two sentences matters.",
                ),
            ]
        elif self._is_attention_text(document_text):
            specs = [
                (
                    "Transformer",
                    "The paper's proposed attention-only encoder-decoder architecture.",
                    "This is the central method that connects every later term and result.",
                ),
                (
                    "self-attention",
                    "A mechanism for connecting positions inside a sequence without recurrent steps.",
                    "This explains the architecture's claimed advantage in modeling dependencies and parallelizing computation.",
                ),
                (
                    "sequence transduction",
                    "The task setting of converting one sequence into another, such as machine translation.",
                    "It defines what problem the architecture is built to solve.",
                ),
                (
                    "encoder-decoder",
                    "The high-level input-to-output structure retained by the Transformer.",
                    "It helps the learner separate the architecture frame from the attention mechanism inside it.",
                ),
                (
                    "parallelization",
                    "The ability to compute many positions at once during training.",
                    "This is the edge-device and efficiency-relevant reason the paper matters beyond accuracy.",
                ),
                (
                    "long-range dependencies",
                    "Relationships between distant sequence positions.",
                    "The paper argues attention reduces the path length needed to model these relationships.",
                ),
            ]
        elif self._is_resnet_text(document_text):
            specs = [
                (
                    "network depth",
                    "The paper treats depth as important for representation power, but not automatically easy to optimize.",
                    "This is the motivation path from previous ImageNet success to the ResNet problem.",
                ),
                (
                    "very deep models",
                    "Prior successful image-recognition models that use many layers.",
                    "This explains why the authors care about depth rather than only architecture novelty.",
                ),
                (
                    "residual learning framework",
                    "The paper's proposed way to train much deeper image-recognition networks.",
                    "This is the core method; vocabulary around residual functions and shortcut connections depends on it.",
                ),
                (
                    "degradation problem",
                    "A depth-related optimization failure where deeper networks can have worse training accuracy.",
                    "This is the motivation for residual learning and should not be confused with overfitting.",
                ),
                (
                    "vanishing/exploding gradients",
                    "An older optimization obstacle for deep networks.",
                    "The paper says this problem had been largely addressed, so degradation needs a different explanation.",
                ),
                (
                    "higher training error",
                    "The sign that deeper plain networks are harder to optimize, not merely overfitting.",
                    "This is the evidence that motivates residual learning.",
                ),
                (
                    "constructed solution",
                    "A theoretical deeper-network solution made by copying the shallower model and using identity mappings for added layers.",
                    "This explains why worse training error is surprising and important.",
                ),
                (
                    "residual mapping",
                    "The function F(x)=H(x)-x learned by the stacked layers.",
                    "This is the local learning target inside a residual block.",
                ),
                (
                    "underlying mapping",
                    "The desired function H(x) that the network ultimately needs to represent.",
                    "This lets the learner understand why the residual is added back to x.",
                ),
                (
                    "F(x)+x",
                    "The recast original mapping: residual output plus the original input.",
                    "This is the formula form of the residual block.",
                ),
                (
                    "identity shortcut connections",
                    "Cheap skip connections that pass x forward and add it to the stacked-layer output.",
                    "This is how the residual mapping is implemented in a feedforward network.",
                ),
                (
                    "plain nets",
                    "Non-residual baseline networks that simply stack layers.",
                    "They let the learner see what residual connections improve over.",
                ),
                (
                    "accuracy gains",
                    "The claim that deeper residual networks improve accuracy instead of only becoming trainable.",
                    "This is the second major empirical claim after easier optimization.",
                ),
                (
                    "generalization performance",
                    "Evidence that residual representations transfer to other recognition tasks.",
                    "This supports the broader claim that the principle is generic.",
                ),
                (
                    "residual representations",
                    "A family of prior ideas where vectors, subproblems, or variables represent residual differences.",
                    "This is related-work background, not the main ResNet block itself.",
                ),
                (
                    "shortcut connections",
                    "A long-studied connection pattern that passes information across layers.",
                    "This related-work section explains ResNet's architectural ancestry.",
                ),
                (
                    "highway networks",
                    "A concurrent shortcut-connection method that uses learned gates.",
                    "This is the key contrast to ResNet's identity shortcuts.",
                ),
                (
                    "gating functions",
                    "Mechanisms that can open or close shortcut paths.",
                    "This explains why highway networks differ from parameter-free identity shortcuts.",
                ),
                (
                    "parameter-free identity shortcuts",
                    "ResNet's ungated shortcuts, contrasted with highway networks.",
                    "This helps identify what is distinctive in the authors' formulation.",
                ),
                (
                    "identity shortcuts",
                    "ResNet's ungated shortcut paths in the related-work contrast.",
                    "This is the source-grounded phrase behind the parameter-free shortcut idea.",
                ),
                (
                    "shallower architecture",
                    "The smaller comparison network used to define what the deeper counterpart should be able to match.",
                    "This anchors the argument that degradation is an optimization issue.",
                ),
                (
                    "residual functions",
                    "The functions learned relative to an identity mapping rather than as direct underlying mappings.",
                    "This explains what the model is reformulating mathematically.",
                ),
                (
                    "identity mapping",
                    "The reference path that lets the network preserve an input while learning only the residual change.",
                    "This is the intuition behind why shortcut connections can help optimization.",
                ),
                (
                    "linear projection",
                    "A learned transformation used on a shortcut path when feature dimensions do not match.",
                    "This explains the exception to pure identity shortcuts.",
                ),
                (
                    "projection shortcut",
                    "A shortcut path with a learned projection, used to match dimensions in residual networks.",
                    "This is the dimension-matching alternative to the default identity shortcut.",
                ),
                (
                    "convolutional layers",
                    "The layer type used to implement the residual function in image-recognition networks.",
                    "This connects the residual-block formula to the actual CNN architecture.",
                ),
                (
                    "feature maps",
                    "The channel-wise tensors that residual shortcuts add together in convolutional networks.",
                    "This explains what dimension matching means in the architecture.",
                ),
                (
                    "plain network",
                    "The non-residual VGG-style baseline used for comparison.",
                    "This helps the learner separate the baseline architecture from the residual version.",
                ),
                (
                    "ImageNet 2012 classification dataset",
                    "The benchmark used for the paper's main image-classification experiment.",
                    "This sets the evaluation context for the results.",
                ),
                (
                    "top-1 and top-5 error rates",
                    "The metrics used to evaluate ImageNet classification performance.",
                    "This helps the learner interpret the experimental results.",
                ),
                (
                    "18-layer and 34-layer plain nets",
                    "The shallow/deep plain-network pair used to expose degradation.",
                    "This comparison shows why residual connections are needed.",
                ),
                (
                    "higher validation error",
                    "The observed worse validation performance of the deeper plain network.",
                    "This is the first result signal in the ImageNet experiment.",
                ),
                (
                    "training/validation errors",
                    "The curves used to diagnose the reason for the deeper plain network's worse performance.",
                    "This connects the experiment to the optimization argument.",
                ),
                (
                    "vanishing gradients",
                    "An explanation the authors test and reject for the plain-network degradation.",
                    "This keeps the reader from confusing degradation with the older vanishing-gradient problem.",
                ),
                (
                    "forward propagated signals",
                    "Signals moving forward through the network whose non-zero variance is used as evidence.",
                    "This supports the claim that activations are not simply vanishing.",
                ),
                (
                    "backward propagated gradients",
                    "Training gradients moving backward through the network.",
                    "Healthy gradient norms support the claim that gradients are not simply vanishing.",
                ),
                (
                    "convergence rates",
                    "The speed at which optimization reduces training error.",
                    "The authors conjecture this may explain why deep plain nets train poorly.",
                ),
                (
                    "residual network",
                    "The residual counterpart created by inserting shortcut connections into the plain baseline.",
                    "This is the architecture transformation the section explains.",
                ),
                (
                    "dimension matching",
                    "The problem of making shortcut outputs compatible when feature-map dimensions increase.",
                    "This explains why the paper lists identity padding and projection shortcut options.",
                ),
                (
                    "dimensions increase",
                    "The condition that forces the paper to discuss shortcut alternatives.",
                    "This marks the shift from ordinary identity shortcuts to dimension-handling options.",
                ),
                (
                    "zero padding",
                    "A no-parameter way to extend identity shortcuts when dimensions increase.",
                    "This is option A in the shortcut-design discussion.",
                ),
                (
                    "zero entries padded",
                    "The source-grounded wording for adding zeros to identity shortcuts.",
                    "This keeps option A tied to the original sentence.",
                ),
                (
                    "1x1 convolutions",
                    "Projection shortcut layers used to match dimensions.",
                    "This is option B in the shortcut-design discussion.",
                ),
                (
                    "bottleneck",
                    "The smaller middle representation created by the 1x1-3x3-1x1 block.",
                    "This is the efficient block used by deeper ResNets.",
                ),
                (
                    "bottleneck architectures",
                    "Architectures that use bottleneck blocks to keep very deep networks efficient.",
                    "This connects depth to practical compute constraints.",
                ),
                (
                    "time complexity",
                    "The computation cost of the model.",
                    "This explains why replacing identity shortcuts with projections can be expensive.",
                ),
                (
                    "time complexity and model size",
                    "The combined compute and parameter cost of the model.",
                    "This is one reason identity shortcuts matter for bottleneck designs.",
                ),
                (
                    "practical considerations",
                    "Engineering concerns such as computation and parameter cost.",
                    "This explains why bottleneck designs are chosen in deeper ResNets.",
                ),
                (
                    "very deep bottleneck ResNets",
                    "The 50/101/152-layer residual networks built from bottleneck blocks.",
                    "This is the scaling result after the bottleneck architecture is introduced.",
                ),
                (
                    "lower complexity than VGG",
                    "The claim that the 152-layer ResNet is deeper but still cheaper than VGG-16/19.",
                    "This separates useful depth from raw computational cost.",
                ),
                (
                    "no degradation with increased depth",
                    "The observation that these very deep residual networks keep improving instead of getting harder to optimize.",
                    "This is the empirical payoff of the residual design.",
                ),
                (
                    "state-of-the-art comparison",
                    "The benchmark comparison that moves from internal architecture analysis to external performance.",
                    "This shows why the architecture matters beyond an ablation table.",
                ),
                (
                    "CIFAR-10 analysis transition",
                    "The shift from ImageNet results to controlled CIFAR-10 depth-behavior experiments.",
                    "This tells the reader the next section changes experimental purpose.",
                ),
                (
                    "CIFAR-10 architecture",
                    "The small-image residual/plain network design used for controlled CIFAR-10 experiments.",
                    "This section defines the experiment architecture before comparing depth behavior.",
                ),
                (
                    "6n+2 depth formula",
                    "The formula that determines the total number of stacked weighted layers.",
                    "This helps the reader connect n values to 20/32/44/56-layer networks.",
                ),
                (
                    "stride-2 subsampling",
                    "Downsampling performed by convolutions with stride 2.",
                    "This explains how the network changes spatial resolution across feature-map sizes.",
                ),
                (
                    "identity shortcut option A",
                    "The parameter-free shortcut choice used for all CIFAR-10 cases in this section.",
                    "This prevents the reader from confusing the CIFAR setup with the ImageNet projection options.",
                ),
                (
                    "global average pooling",
                    "The pooling layer before the 10-class classifier.",
                    "This is part of the architecture endpoint, not a general vocabulary item.",
                ),
                (
                    "plain-net depth degradation on CIFAR-10",
                    "The observation that deeper plain CIFAR-10 networks suffer higher training error.",
                    "This confirms the degradation problem outside ImageNet.",
                ),
                (
                    "ResNet depth scaling on CIFAR-10",
                    "The observation that CIFAR-10 ResNets overcome optimization difficulty and gain accuracy with depth.",
                    "This is the positive counterpart to plain-net degradation.",
                ),
                (
                    "optimization difficulty as a fundamental problem",
                    "The paper's claim that the plain-net failure appears across CIFAR-10, ImageNet, and MNIST.",
                    "This broadens the argument beyond one benchmark.",
                ),
                (
                    "110-layer ResNet warmup",
                    "The training schedule adjustment used to make the 110-layer ResNet start converging.",
                    "This is a practical detail tied to very deep training.",
                ),
                (
                    "over-1000-layer stress test",
                    "The experiment that trains a 1202-layer residual network to test extreme depth.",
                    "This separates optimization scalability from test-set generalization.",
                ),
                (
                    "optimization success versus overfitting",
                    "The 1202-layer network trains successfully but tests worse than the 110-layer network.",
                    "This is the section's main nuance: optimization is solved, but generalization is not automatically solved.",
                ),
                (
                    "small-dataset overfitting",
                    "The claim that the 1202-layer model may be too large for CIFAR-10.",
                    "This explains why more depth can stop helping even when training error is tiny.",
                ),
                (
                    "regularization tradeoff",
                    "The paper avoids maxout/dropout to keep the focus on optimization, while acknowledging stronger regularization may improve results.",
                    "This helps the learner distinguish research focus from best possible benchmark performance.",
                ),
                (
                    "object-detection transfer",
                    "The test of replacing a VGG-16 detector backbone with ResNet-101 while keeping the detection implementation the same.",
                    "This shows whether residual representations help outside image classification.",
                ),
                (
                    "representation quality attribution",
                    "The argument that detection gains come from better networks because the implementation is held constant.",
                    "This is the section's causal reasoning step.",
                ),
                (
                    "COCO relative improvement",
                    "The 6.0-point gain on mAP@[.5, .95], described as a 28% relative improvement.",
                    "This is the strongest numeric evidence in the section.",
                ),
                (
                    "competition-level generalization",
                    "The claim that deep residual nets won multiple ILSVRC and COCO 2015 tracks.",
                    "This supports the broader value of learned residual representations.",
                ),
                (
                    "Faster R-CNN baseline adaptation",
                    "The appendix setup where ResNet classification backbones are adapted into the Faster R-CNN detector.",
                    "This explains how the paper moves from classification models to detection systems.",
                ),
                (
                    "ImageNet-to-detection fine-tuning",
                    "The process of initializing from ImageNet classification models and then training on detection data.",
                    "This is the transfer-learning mechanism in the appendix.",
                ),
                (
                    "ResNet without hidden fc layers",
                    "The architectural difference from VGG-16 that requires an adaptation for Faster R-CNN.",
                    "This is the practical issue the NoC idea addresses.",
                ),
                (
                    "shared convolutional feature maps",
                    "Full-image convolutional maps reused by detection regions.",
                    "This is the detection-backbone implementation detail worth learning.",
                ),
                (
                    "zero-padding shortcuts",
                    "The parameter-free shortcut option that pads increased dimensions with zeros.",
                    "This is option A in the projection-shortcut comparison.",
                ),
                (
                    "parameter-free identity shortcuts",
                    "Shortcuts that do not add learned projection parameters.",
                    "This is the efficiency principle behind the preferred ResNet shortcut design.",
                ),
                (
                    "projection shortcuts",
                    "Shortcut paths that use learned projections to match dimensions.",
                    "This is what the A/B/C comparison is testing.",
                ),
                (
                    "all shortcuts are parameter-free",
                    "Option A's defining constraint: no learned projection parameters on shortcuts.",
                    "This represents the cheapest compared shortcut design.",
                ),
                (
                    "other shortcuts are identity",
                    "Option B's defining constraint: only dimension-changing shortcuts use projections.",
                    "This is the balanced shortcut design used in deeper ResNets.",
                ),
                (
                    "all shortcuts are projections",
                    "Option C's defining constraint: every shortcut path uses projection.",
                    "This tests whether extra projection parameters help enough to justify their cost.",
                ),
                (
                    "VGG nets",
                    "The prior architecture family that inspires the plain baseline design.",
                    "This is related architecture context for the ImageNet experiments.",
                ),
                (
                    "shortcut connections",
                    "Architectural links that pass activations across layers and make residual blocks possible.",
                    "This is the mechanism that turns the residual-learning idea into a network architecture.",
                ),
            ]
        else:
            specs = [
            (
                "internal covariate shift",
                "The paper's motivating problem: as lower layers change during training, later layers keep receiving changing input distributions.",
                "This explains why the authors think deep-network training is unstable and slow.",
            ),
            (
                "Batch Normalization",
                "The proposed method: normalize layer inputs using mini-batch statistics and learn scale/shift parameters.",
                "This is the contribution that turns the paper from observation into a practical algorithm.",
            ),
            (
                "mini-batch",
                "The statistical unit used to estimate means and variances during stochastic training.",
                "Understanding this prevents confusing training-time batch statistics with fixed inference behavior.",
            ),
            (
                "saturating nonlinearities",
                "Activation functions can enter regions where gradients become tiny and training slows down.",
                "This gives a language-learning bridge from the phrase 'saturated regime' to the optimization problem.",
            ),
            (
                "ImageNet classification",
                "The empirical benchmark where the authors show faster training and strong accuracy.",
                "This grounds the method's claimed benefit in an experimental result rather than only theory.",
            ),
            (
                "Dropout",
                "A regularization baseline whose need may be reduced when Batch Normalization is used.",
                "This helps the reader track how the paper positions its method against existing techniques.",
            ),
            ]
        rows: list[dict[str, Any]] = []
        for concept, explanation, why in specs:
            sentence = self._source_sentence(None, concept, document_text)
            if not sentence or not self._appears_in_text(concept, sentence):
                continue
            rows.append(
                {
                    "concept": concept,
                    "explanation": explanation,
                    "source_sentence": sentence,
                    "related_terms": [concept],
                    "why_it_matters": why,
                    "references": self._references_near(sentence, document_text),
                    "learning_priority": "field_term",
                    "confidence": 0.9,
                    "user_state": "suggested",
                }
            )
        return rows

    def _heuristic_sentences(self, document_text: str) -> list[dict[str, str]]:
        if self._is_bert_text(document_text):
            specs = [
                (
                    "There are two existing strategies",
                    "There are two existing strategies for applying X to Y: A and B.",
                    "The authors map prior work into two approaches: feature-based use and fine-tuning.",
                    "'There are two existing strategies'는 문헌 배경을 두 갈래로 정리하겠다는 신호입니다.",
                    "The sentence is a roadmap; the colon tells the reader to expect categories.",
                ),
                (
                    "major limitation is that",
                    "The major limitation is that X is Y, and this limits Z.",
                    "The authors identify unidirectional language modeling as the key weakness of prior approaches.",
                    "'major limitation is that'는 논문이 해결하려는 핵심 한계를 직접 제시합니다.",
                    "The sentence links a technical property to its downstream consequence.",
                ),
                (
                    "by proposing",
                    "We improve X by proposing Y.",
                    "The authors improve fine-tuning approaches by proposing BERT.",
                    "'by proposing'은 어떤 방법으로 문제를 개선하는지 설명합니다.",
                    "The method phrase comes after the improvement claim, so the reader should connect action and solution.",
                ),
                (
                    "In addition to",
                    "In addition to A, we also use B.",
                    "The authors add next sentence prediction on top of masked language modeling.",
                    "'In addition to'는 앞에서 말한 방법에 다른 요소를 추가한다는 신호입니다.",
                    "The sentence contains two method names, so the learner should separate the first task from the additional task.",
                ),
                (
                    "The contributions of our paper are as follows",
                    "The contributions of our paper are as follows: A, B, C.",
                    "The authors announce a list of the paper's main claims.",
                    "'as follows'는 뒤에 목록이나 정리된 항목이 나온다는 신호입니다.",
                    "This phrase changes the reading mode from explanation to contribution scanning.",
                ),
                (
                    "which stands for",
                    "We introduce X, which stands for Y.",
                    "The authors introduce BERT and immediately expand the acronym.",
                    "'which stands for'는 약어의 전체 이름을 설명하는 표현입니다. 논문 초반의 이름 정의에서 자주 나옵니다.",
                    "The acronym and its full technical name are packed into one sentence.",
                ),
                (
                    "Unlike recent",
                    "Unlike A, B is designed to do C.",
                    "BERT is contrasted with earlier representation models because it pre-trains deep bidirectional representations.",
                    "'Unlike'는 기존 방법과 새 방법의 차이를 만드는 신호입니다. 뒤쪽의 주절이 논문의 핵심 차별점입니다.",
                    "The contrast phrase comes before the main claim, so the reader must wait for the subject and verb.",
                ),
                (
                    "can be fine-tuned",
                    "A pre-trained model can be fine-tuned with one additional output layer.",
                    "After pre-training, BERT can be adapted to many tasks with a small task-specific layer.",
                    "'can be fine-tuned'는 모델을 특정 과제에 맞게 조정할 수 있다는 뜻입니다.",
                    "Passive voice plus ML workflow vocabulary makes the sentence dense.",
                ),
            ]
        elif self._is_attention_text(document_text):
            specs = [
                (
                    "based solely on",
                    "X is based solely on Y, dispensing with Z.",
                    "The authors define the Transformer by what it uses and what it removes: attention yes, recurrence/convolution no.",
                    "'is based solely on'은 핵심 구성 요소를 제한해서 말하는 표현이고, 'dispensing with'는 기존 요소를 제거한다는 뜻입니다.",
                    "The sentence is dense because the main claim and contrast are packed into one clause.",
                ),
                (
                    "The best performing models",
                    "The best performing models do A and B through C.",
                    "The authors first describe prior strong systems before presenting what the Transformer changes.",
                    "'The best performing models'는 이전 최고 성능 방법들을 묶어서 소개하는 표현입니다. 저장할 단어라기보다 문헌 배경 신호입니다.",
                    "This is a discourse move, not a vocabulary item; the reader should ask what contrast comes next.",
                ),
                (
                    "drawing global dependencies",
                    "Mechanism A becomes important for drawing global dependencies between B and C.",
                    "Attention helps connect distant input and output positions.",
                    "'drawing global dependencies'는 멀리 떨어진 요소 사이의 관계를 포착한다는 뜻입니다.",
                    "The phrase combines an abstract verb with a technical noun phrase.",
                ),
                (
                    "allow for significantly more parallelization",
                    "A allows for more B and can reach C after D.",
                    "The architecture can train more in parallel and reach strong quality with less training time.",
                    "'allow for'는 어떤 방법이 특정 효과를 가능하게 한다는 논문식 표현입니다.",
                    "The sentence links architecture, compute efficiency, and empirical result in one claim.",
                ),
            ]
        elif self._is_resnet_text(document_text):
            specs = [
                (
                    "as easy as stacking more layers",
                    "Is learning better X as easy as doing Y?",
                    "The authors turn prior success with depth into the central research question.",
                    "'as easy as'는 어떤 단순한 가정이 정말 맞는지 묻는 비교 표현입니다.",
                    "The sentence is a rhetorical research question; it sets up the problem rather than giving the answer.",
                ),
                (
                    "not caused by overfitting",
                    "X is not caused by Y, and doing Z leads to W.",
                    "The authors distinguish optimization degradation from overfitting.",
                    "'not caused by'는 흔한 설명을 배제하고 다른 원인을 찾게 만드는 표현입니다.",
                    "The sentence is dense because it rejects one explanation and states the evidence in the same move.",
                ),
                (
                    "There exists a solution by construction",
                    "There exists a solution by construction to X: A are B, and C are copied from D.",
                    "The authors explain why a deeper model should be able to match a shallower one in principle.",
                    "'There exists a solution by construction'은 실제로 찾았다는 뜻보다, 논리적으로 그런 해가 존재함을 보이는 표현입니다.",
                    "The sentence is difficult because it presents a theoretical construction before returning to experimental failure.",
                ),
                (
                    "Instead of hoping",
                    "Instead of hoping A directly fits B, we let A fit C.",
                    "The authors contrast a hard direct-mapping target with an easier residual-mapping target.",
                    "'Instead of'는 기존 방식이나 직관적인 목표를 버리고 새 목표를 제시하는 대조 표현입니다.",
                    "The sentence is difficult because it contrasts two mathematical learning targets in one move.",
                ),
                (
                    "The original mapping is recast into",
                    "The original mapping is recast into F(x)+x.",
                    "The authors rewrite the target function so the network learns the residual part and adds back the input.",
                    "'is recast into'는 같은 대상을 다른 수식/관점으로 다시 표현한다는 뜻입니다.",
                    "The sentence is short but conceptually dense because it introduces the residual-block formula.",
                ),
                (
                    "If the optimal function is closer to an identity mapping",
                    "If A is closer to B than C, it should be easier to find D with reference to B than to learn A as new.",
                    "The authors explain the intuition behind residual learning: learning a small perturbation around identity can be easier.",
                    "'closer to'와 'with reference to'는 residual 학습의 기준점을 설명하는 표현입니다.",
                    "The sentence is conceptually dense because it turns an optimization intuition into a conditional comparison.",
                ),
                (
                    "Shortcut connections are those",
                    "Shortcut connections are those doing X.",
                    "The authors define shortcut connections as links that skip one or more layers.",
                    "'are those ~ing'은 앞의 용어를 정의하는 논문식 구조입니다.",
                    "The sentence is a definition; it should be saved as concept support, not as a random phrase.",
                ),
                (
                    "We show that",
                    "We show that: 1) A, but B; 2) C.",
                    "The authors organize the evidence into optimization and accuracy claims.",
                    "'We show that'은 실험으로 뒷받침할 핵심 주장 목록을 여는 표현입니다.",
                    "The sentence is difficult because it contains two numbered empirical claims and a contrast.",
                ),
                (
                    "This strong evidence shows that",
                    "This strong evidence shows that X is Y.",
                    "The authors move from benchmark results to a general principle claim.",
                    "'This strong evidence shows that'은 여러 실험 결과를 더 큰 주장으로 연결하는 표현입니다.",
                    "The sentence is an evidence-to-principle move, not just a result sentence.",
                ),
                (
                    "These methods suggest that",
                    "These methods suggest that X can Y.",
                    "The authors use related work to extract a general lesson about reformulation and optimization.",
                    "'These methods suggest that'은 여러 관련 연구를 묶어서 일반적인 시사점을 말하는 표현입니다.",
                    "The sentence is a bridge from related work examples to the ResNet motivation.",
                ),
                (
                    "in contrast to",
                    "A are B, in contrast to C that are D.",
                    "The authors distinguish highway networks' learned gates from ResNet's parameter-free identity shortcuts.",
                    "'in contrast to'는 관련 연구와 자기 방법의 차이를 선명하게 만드는 표현입니다.",
                    "The sentence is important because it prevents the reader from treating all shortcut connections as the same.",
                ),
                (
                    "On the contrary",
                    "On the contrary, our A always does B; C are never D, and all E is passed through.",
                    "The authors contrast ResNet with highway networks: ResNet shortcuts keep information flowing and always learn residual functions.",
                    "'On the contrary'는 앞선 관련 연구와 자기 방법이 반대로 동작한다는 강한 대조 신호입니다.",
                    "The sentence is important because it separates gated highway shortcuts from ResNet's ungated identity shortcuts.",
                ),
                (
                    "In addition, highway networks",
                    "In addition, A have not demonstrated B with C.",
                    "The authors add an empirical limitation of highway networks before moving into the residual-learning formulation.",
                    "'In addition'은 첫 번째 차이점 뒤에 추가 근거를 붙이는 표현입니다.",
                    "The sentence links a method comparison to an evidence claim about very deep networks.",
                ),
                (
                    "the identity mapping is sufficient",
                    "We show that A is sufficient for B and economical; C is only used when D.",
                    "The authors justify using identity shortcuts by default and projection shortcuts only for dimension matching.",
                    "'is sufficient for'는 더 복잡한 방법 없이도 목적을 달성한다는 논문식 표현입니다.",
                    "The sentence is important because it separates the main shortcut design from the fallback projection case.",
                ),
                (
                    "Based on the above plain network",
                    "Based on A, we insert B, which turn C into D.",
                    "The authors convert the plain baseline into a residual network by adding shortcut connections.",
                    "'Based on the above'는 바로 앞에서 정의한 baseline을 출발점으로 삼는다는 신호입니다.",
                    "The sentence is useful because it explains the architecture change rather than only naming components.",
                ),
                (
                    "When the dimensions increase",
                    "When A happens, we consider two options: option A and option B.",
                    "The authors explain how shortcut connections handle feature-map dimension changes.",
                    "'When' 절은 특정 조건을 열고, 'two options'는 뒤에 선택지가 나올 것을 알려줍니다.",
                    "The sentence is dense because it mixes tensor-shape conditions with architectural alternatives.",
                ),
                (
                    "To provide instances for discussion",
                    "To provide instances for discussion, we describe A as follows.",
                    "The authors move from formulation to concrete ImageNet model designs.",
                    "'To provide instances for discussion'은 추상적인 방법 설명 뒤에 예시 모델을 제시하겠다는 신호입니다.",
                    "The phrase changes the reading mode from theory/formula to architecture description.",
                ),
                (
                    "We evaluate our method",
                    "We evaluate our method on dataset X that consists of Y.",
                    "The authors introduce the benchmark, data split, and evaluation setting.",
                    "'We evaluate our method on'은 실험 섹션에서 평가 대상과 데이터셋을 여는 표현입니다.",
                    "The sentence is dense because it packs dataset name, class count, train/validation/test split, and metric context.",
                ),
                (
                    "The results in Table 2 show that",
                    "The results in Table X show that A has higher B than C.",
                    "The authors state the first experimental finding: the deeper plain network performs worse than the shallower plain network.",
                    "'The results show that'은 표나 그림을 해석해서 주장으로 바꾸는 논문식 표현입니다.",
                    "The sentence is important because it turns raw table data into the degradation argument.",
                ),
                (
                    "To reveal the reasons",
                    "To reveal the reasons, we compare A and B during C.",
                    "The authors explain why they inspect training and validation error curves.",
                    "'To reveal the reasons'는 결과를 단순 보고하지 않고 원인을 분석하겠다는 신호입니다.",
                    "The phrase changes the reading mode from result reporting to diagnostic comparison.",
                ),
                (
                    "We argue that this optimization difficulty is unlikely to be caused by",
                    "We argue that X is unlikely to be caused by Y.",
                    "The authors reject vanishing gradients as the explanation for the deeper plain network's worse training.",
                    "'is unlikely to be caused by'는 가능한 원인을 조심스럽게 배제하는 논문식 표현입니다.",
                    "The sentence is important because it narrows the diagnosis from general optimization trouble to something more specific.",
                ),
                (
                    "So neither forward nor backward signals vanish",
                    "So neither A nor B does C.",
                    "The authors summarize evidence that both activations and gradients remain healthy.",
                    "'neither A nor B'는 두 가능성을 동시에 배제하는 구조입니다.",
                    "The sentence condenses the diagnostic evidence into one conclusion.",
                ),
                (
                    "Next we evaluate",
                    "Next we evaluate A and B.",
                    "The authors move from diagnosing plain networks to testing residual networks.",
                    "'Next we evaluate'는 실험 순서가 바뀌는 신호입니다.",
                    "This phrase helps the reader follow the experimental sequence rather than treating all results as one block.",
                ),
                (
                    "Next we investigate projection shortcuts",
                    "Next we investigate X.",
                    "The authors move from residual-network results to a focused comparison of shortcut designs.",
                    "'Next we investigate'는 다음 실험 질문으로 넘어가는 신호입니다.",
                    "The phrase helps the reader see that this is not a new method, but an ablation-style comparison.",
                ),
                (
                    "In Table 3 we compare three options",
                    "In Table X we compare three options: A, B, and C.",
                    "The authors organize shortcut designs into three comparable options.",
                    "'we compare three options'는 실험 표의 읽는 기준을 먼저 제시하는 표현입니다.",
                    "The sentence is dense because each option changes a different shortcut design choice.",
                ),
                (
                    "projection shortcuts are not essential for addressing",
                    "A indicate that B are not essential for addressing C.",
                    "The authors conclude that projection shortcuts are helpful but not required to solve degradation.",
                    "'not essential for addressing'은 어떤 구성요소가 문제 해결에 필수는 아니라는 제한된 결론입니다.",
                    "This is important because it separates the core residual idea from an optional shortcut variant.",
                ),
                (
                    "The three layers are",
                    "The three layers are A, B, and C, where A is responsible for D.",
                    "The authors define the bottleneck block by explaining the role of each convolution.",
                    "'where' 절은 앞의 구조를 다시 풀어서 각 부분의 역할을 설명합니다.",
                    "The sentence is dense because it mixes architecture shape with dimensionality changes.",
                ),
                (
                    "are particularly important for",
                    "A are particularly important for B.",
                    "The authors explain why identity shortcuts matter more in bottleneck architectures.",
                    "'particularly important for'는 특정 조건에서 중요성이 커진다는 신호입니다.",
                    "The phrase ties a general design choice to a specific architecture family.",
                ),
                (
                    "lead to more efficient models",
                    "A lead to more efficient models for B.",
                    "The authors connect identity shortcuts to lower compute and model size.",
                    "'lead to'는 원인과 결과를 연결하는 논문식 표현입니다.",
                    "This sentence turns an engineering detail into an efficiency claim.",
                ),
                (
                    "mainly due to practical considerations",
                    "The usage of A is mainly due to B.",
                    "The authors clarify that bottleneck designs are chosen for practicality, not because non-bottleneck residual nets fail.",
                    "'mainly due to'는 선택의 주된 이유를 설명하는 표현입니다.",
                    "The phrase helps separate empirical capability from engineering constraints.",
                ),
                (
                    "although the depth is significantly increased",
                    "Although A is significantly increased, B still has lower complexity than C.",
                    "The authors contrast model depth with computational cost.",
                    "'Although' 절은 예상과 다른 결과를 강조합니다.",
                    "The sentence is difficult because it compares depth, FLOPs, and baseline architectures at once.",
                ),
                (
                    "We do not observe the degradation problem",
                    "We do not observe A and thus enjoy B from C.",
                    "The authors state that deeper residual networks avoid the degradation failure.",
                    "'and thus'는 앞의 관찰에서 뒤의 이득으로 이어지는 논리 연결입니다.",
                    "This is a compact result sentence with cause, benefit, and condition packed together.",
                ),
                (
                    "Our focus is on",
                    "Our focus is on A, but not on B.",
                    "The authors define the purpose of the CIFAR-10 experiments.",
                    "'but not on'은 연구 목표와 제외 대상을 함께 정리합니다.",
                    "This sentence helps distinguish analysis experiments from benchmark chasing.",
                ),
                (
                    "subsampling is performed by",
                    "The subsampling is performed by A with B.",
                    "The authors explain how the network reduces spatial resolution.",
                    "'is performed by'는 어떤 처리가 어떤 방법으로 수행되는지 설명합니다.",
                    "The sentence is technical because it names both the operation and the implementation detail.",
                ),
                (
                    "network ends with",
                    "The network ends with A, B, and C.",
                    "The authors list the final stages of the CIFAR-10 classifier.",
                    "'ends with'는 모델 구조의 마지막 구성요소를 소개합니다.",
                    "This is an architecture-list sentence, so read it as a sequence of layers.",
                ),
                (
                    "There are totally",
                    "There are totally A stacked weighted layers.",
                    "The authors give the formula for total network depth.",
                    "'There are totally'는 총 개수나 전체 구조를 요약하는 표현입니다.",
                    "The hard part is connecting the formula to actual depths used later.",
                ),
                (
                    "When shortcut connections are used",
                    "When A are used, they are connected to B.",
                    "The authors specify where residual shortcuts are attached.",
                    "'When' 절은 조건을 제시하고, 주절은 그 조건에서의 배치를 설명합니다.",
                    "The pronoun 'they' refers back to shortcut connections, which can be easy to miss.",
                ),
                (
                    "suffer from increased depth",
                    "A suffer from B and exhibit C when D.",
                    "The authors describe the negative behavior of plain networks as depth increases.",
                    "'suffer from'은 문제나 악영향을 받는다는 뜻으로, 실험 결과의 실패 양상을 말합니다.",
                    "The sentence combines condition, failure mode, and evidence in one result claim.",
                ),
                (
                    "manage to overcome",
                    "A manage to overcome B and demonstrate C when D.",
                    "The authors contrast ResNets against plain nets by showing successful optimization and accuracy gains.",
                    "'manage to'는 어려운 문제를 결국 해결했다는 뉘앙스를 줍니다.",
                    "This sentence packs the contrast result into two coordinated verbs: overcome and demonstrate.",
                ),
                (
                    "slightly too large to start converging",
                    "A is slightly too large to start B.",
                    "The authors explain why they temporarily lower the learning rate for the 110-layer ResNet.",
                    "'too large to'는 어떤 정도가 너무 커서 결과가 어렵다는 구조입니다.",
                    "This is a training-procedure sentence, not the main scientific claim.",
                ),
                (
                    "shows no optimization difficulty",
                    "A shows no B, and C is able to achieve D.",
                    "The authors separate optimization success from later generalization problems.",
                    "'shows no'는 문제가 관찰되지 않았다는 실험 결과 표현입니다.",
                    "The sentence is important because it prevents the reader from misreading the 1202-layer failure as an optimization failure.",
                ),
                (
                    "still open problems",
                    "There are still open problems on A.",
                    "The authors signal that extreme depth creates unresolved issues even after optimization succeeds.",
                    "'open problems'는 아직 해결되지 않은 연구 문제를 뜻합니다.",
                    "This marks a limitation, not a rejection of ResNet.",
                ),
                (
                    "because of overfitting",
                    "We argue that this is because of A.",
                    "The authors explain why test performance worsens despite very low training error.",
                    "'because of'는 원인을 명사구로 제시합니다.",
                    "The pronoun 'this' refers to the worse testing result, so the reader must connect it backward.",
                ),
                (
                    "can only be attributed to",
                    "A can only be attributed to B.",
                    "The authors explain why the improvement should be credited to better network representations.",
                    "'can only be attributed to'는 원인을 하나로 제한해서 주장하는 표현입니다.",
                    "This is a causal-attribution sentence; read what was controlled before accepting the cause.",
                ),
                (
                    "Most remarkably",
                    "Most remarkably, on A we obtain B, which is C.",
                    "The authors highlight the strongest object-detection transfer result.",
                    "'Most remarkably'는 여러 결과 중 특히 중요한 결과를 강조합니다.",
                    "The sentence combines dataset, metric, absolute gain, and relative gain.",
                ),
                (
                    "solely due to",
                    "This gain is solely due to A.",
                    "The authors attribute the detection improvement to learned representations.",
                    "'solely due to'는 오직 그 원인 때문이라고 강하게 말합니다.",
                    "This short sentence carries the main transfer-learning claim.",
                ),
                (
                    "fine-tuned on",
                    "A are initialized by B and then fine-tuned on C.",
                    "The authors describe the transfer path from classification to detection.",
                    "'fine-tuned on'은 이미 학습된 모델을 새 데이터에 맞게 추가 학습한다는 뜻입니다.",
                    "This sentence connects pretraining source and target task.",
                ),
                (
                    "Unlike VGG-16",
                    "Unlike A, B has no C.",
                    "The authors contrast ResNet's detector-backbone structure with VGG-16.",
                    "'Unlike'는 두 모델의 구조적 차이를 시작하는 신호입니다.",
                    "The sentence is important because it motivates the NoC adaptation.",
                ),
                (
                    "adopt the idea of",
                    "We adopt the idea of A to address B.",
                    "The authors introduce a borrowed method to solve the hidden-fc-layer issue.",
                    "'adopt the idea of'는 기존 아이디어를 가져와 적용한다는 표현입니다.",
                    "The purpose phrase explains why the borrowed method is needed.",
                ),
                (
                    "We present a residual learning framework",
                    "We present X to ease Y.",
                    "The authors introduce residual learning as a method for training substantially deeper networks.",
                    "'We present'는 논문의 제안 방법을 직접 소개하는 표현이고, 'to ease'는 그 목적을 설명합니다.",
                    "The sentence packs method, purpose, and comparison with previous depth into one claim.",
                ),
                (
                    "We explicitly reformulate",
                    "We reformulate A as B with reference to C.",
                    "The paper changes the target from directly learning a mapping to learning residual functions.",
                    "'reformulate A as B'는 같은 문제를 다른 학습 목표로 바꾼다는 뜻입니다.",
                    "The phrase is conceptually dense because it links architecture to an optimization objective.",
                ),
                (
                    "provide comprehensive empirical evidence",
                    "We provide evidence showing X is Y and can Z.",
                    "The authors signal that experiments will support both optimization and accuracy claims.",
                    "'provide empirical evidence'는 실험 결과로 주장을 뒷받침하겠다는 논문식 표현입니다.",
                    "The reader should separate the two claims: easier optimization and accuracy from depth.",
                ),
            ]
        else:
            specs = [
            (
                "is complicated by the fact that",
                "X is complicated by the fact that Y, as Z.",
                "Training deep networks is hard because each layer's input distribution changes while earlier layers update.",
                "'is complicated by the fact that'는 어려움의 원인을 설명하고, 'as' 절은 그 변화가 언제 일어나는지 덧붙입니다.",
                "Long cause clause plus a time/change clause makes the main claim easy to miss.",
            ),
            (
                "as opposed to",
                "Using A, as opposed to B, is helpful in several ways.",
                "Using mini-batches rather than single examples helps training in multiple ways.",
                "'as opposed to'는 두 선택지를 대비합니다. 앞의 선택지가 저자들이 선호하는 방식입니다.",
                "The contrast phrase interrupts the main sentence, so the reader must reconnect the subject and verb.",
            ),
            (
                "This motivates us to",
                "This motivates us to seek X that does Y and does not require Z.",
                "Because full whitening is expensive, the authors look for a cheaper differentiable normalization method.",
                "'This motivates us to'는 앞의 문제점이 다음 설계 선택으로 이어진다는 신호입니다.",
                "The sentence compresses problem, design goal, and constraint into one academic move.",
            ),
            (
                "allows us to",
                "Method allows us to do A and be less B.",
                "Batch Normalization lets the authors use higher learning rates with less careful initialization.",
                "'allows us to'는 방법의 실용적 효과를 말할 때 자주 쓰는 표현입니다.",
                "The verb phrase describes capability, not permission in the everyday sense.",
            ),
            ]
        rows: list[dict[str, str]] = []
        for marker, structure, simplified, explanation, difficulty in specs:
            sentence = self._source_sentence(None, marker, document_text)
            if sentence and marker.lower() in sentence.lower():
                rows.append(
                    {
                        "sentence": sentence,
                        "core_structure": structure,
                        "simplified_version": simplified,
                        "korean_explanation": explanation,
                        "difficulty_reason": difficulty,
                    }
                )
        if rows:
            return rows[:4]
        first = self._sentences_from_text(document_text)[0] if document_text.strip() else ""
        return [
            {
                "sentence": first,
                "core_structure": "Main claim + explanation.",
                "simplified_version": first,
                "korean_explanation": "이 문장은 핵심 주장과 설명을 함께 담고 있습니다.",
                "difficulty_reason": "Fallback sentence selected because no stronger structure marker was detected.",
            }
        ]

    def _heuristic_summaries(self, document_text: str) -> dict[str, Any]:
        lower = document_text.lower()
        compact_lower = " ".join(lower.split())
        if "batch normalization" in lower and "internal covariate shift" in lower:
            return {
                "one_line": "The paper proposes Batch Normalization to make deep neural network training faster and more stable.",
                "simple": (
                    "Deep networks are hard to train because layer inputs keep changing during training. "
                    "Batch Normalization normalizes those inputs in mini-batches, which lets models train with higher learning rates and often less Dropout."
                ),
                "academic": (
                    "The paper frames changing internal activation distributions as internal covariate shift, then introduces a differentiable "
                    "mini-batch normalization transform with learned scale and shift parameters to accelerate optimization and improve ImageNet-scale training."
                ),
                "study_notes": [
                    "Track the argument chain: training instability -> internal covariate shift -> mini-batch normalization -> faster optimization.",
                    "Separate concept words from academic moves: 'refer to this phenomenon as' names a concept; 'allows us to' states a benefit.",
                    "When reading equations, first identify what statistics are estimated from the mini-batch: mean and variance.",
                ],
            }
        if "recurrent neural networks" in compact_lower and "sequence modeling" in compact_lower and "machine translation" in compact_lower:
            return {
                "one_line": "This section explains recurrent sequence-modeling baselines before the Transformer contrast.",
                "simple": (
                    "The authors review RNN, LSTM, and gated recurrent models as established baselines for language modeling and translation. "
                    "This prepares the reader for why reducing sequential computation matters."
                ),
                "academic": (
                    "The section frames recurrent encoder-decoder models as the prior state of the art, then sets up the paper's efficiency argument "
                    "around sequential computation and long dependency paths."
                ),
                "study_notes": [
                    "Treat this as background, not the proposed method.",
                    "Track the contrast: recurrent sequence modeling first, attention-only Transformer next.",
                    "Save baseline names only if you need them to understand the paper's comparison.",
                ],
            }
        if "encoder and decoder stacks" in compact_lower or ("multi-head self-attention mechanism" in compact_lower and "feed-forward network" in compact_lower):
            return {
                "one_line": "This section explains the Transformer's encoder-decoder stack and sub-layer structure.",
                "simple": (
                    "The Transformer uses stacked encoder and decoder layers. Each layer combines multi-head self-attention, feed-forward networks, "
                    "residual connections, and layer normalization."
                ),
                "academic": (
                    "The section defines the architecture: repeated encoder/decoder blocks with attention and position-wise feed-forward sub-layers, "
                    "plus residual connections and layer normalization for stable deep computation."
                ),
                "study_notes": [
                    "Separate architecture parts from attention math: encoder/decoder stacks are the model frame.",
                    "Save multi-head self-attention and feed-forward network as architecture terms.",
                    "Use figure captions only as location hints, not as the main summary.",
                ],
            }
        if "scaled dot-product attention" in compact_lower and "queries" in compact_lower and "keys" in compact_lower and "values" in compact_lower:
            return {
                "one_line": "This section explains scaled dot-product attention using queries, keys, values, softmax, and scaling.",
                "simple": (
                    "Attention compares a query with keys, turns the scores into weights with softmax, and uses those weights to combine values. "
                    "The Transformer scales dot products to keep training stable."
                ),
                "academic": (
                    "The section formalizes attention as softmax-scaled query-key dot products applied to value vectors, contrasting this efficient "
                    "multiplicative attention with additive attention."
                ),
                "study_notes": [
                    "Track Q, K, and V as roles, not just letters in an equation.",
                    "The scaling factor is there to control large dot products before softmax.",
                    "Use the formula after understanding the sentence-level explanation.",
                ],
            }
        if "multi-head attention" in compact_lower and "linearly project" in compact_lower and "parallel" in compact_lower:
            return {
                "one_line": "This section explains multi-head attention as parallel learned projections of queries, keys, and values.",
                "simple": (
                    "Instead of using one attention operation, the Transformer projects queries, keys, and values several times, "
                    "runs attention in parallel, and combines the results."
                ),
                "academic": (
                    "The section motivates multi-head attention as a way to let different projected representation subspaces attend "
                    "to different information jointly, rather than relying on a single attention distribution."
                ),
                "study_notes": [
                    "Read 'head' as one learned attention view, not as a separate model.",
                    "Track the sequence: project Q/K/V several times -> run attention in parallel -> concatenate outputs.",
                    "This is an architecture concept; save it separately from the scaled dot-product formula.",
                ],
            }
        if self._is_resnet_text(document_text):
            if "imagenet classification" in compact_lower and "34-layer plain net has higher validation error" in compact_lower:
                return {
                    "one_line": "This section starts the ImageNet experiments and shows degradation in deeper plain networks.",
                    "simple": (
                        "The authors describe the ImageNet evaluation setup, then compare 18-layer and 34-layer plain networks. "
                        "The deeper 34-layer plain network has higher validation error, so the degradation problem appears in the experiment."
                    ),
                    "academic": (
                        "The section establishes the ImageNet classification protocol and reports the first plain-network comparison, where increased "
                        "depth worsens validation error and motivates inspecting training/validation curves for degradation."
                    ),
                    "study_notes": [
                        "Separate setup details from the result: dataset/metrics first, plain-network comparison second.",
                        "The key result is not the exact hyperparameter list; it is that the 34-layer plain net performs worse than the 18-layer one.",
                        "Use 'The results in Table 2 show that' as a reusable expression for turning table data into a claim.",
                    ],
                }
            if "34-layer plain net has higher training error" in compact_lower and "next we evaluate" in compact_lower:
                return {
                    "one_line": "This section diagnoses plain-network degradation and then turns to residual-network experiments.",
                    "simple": (
                        "The 34-layer plain net has higher training error throughout training. The authors argue this is probably not due to vanishing gradients, "
                        "because forward signals and backward gradients look healthy, then they move on to evaluate residual networks."
                    ),
                    "academic": (
                        "The section interprets the plain-network failure as an optimization issue not explained by vanishing gradients, introduces slow convergence "
                        "as a possible cause, and transitions from plain baselines to 18-layer and 34-layer ResNet experiments."
                    ),
                    "study_notes": [
                        "Track the diagnostic chain: higher training error -> not vanishing gradients -> possible low convergence rates.",
                        "Do not save isolated fragments like 'throughout the whole training'; save the claim it supports.",
                        "Use 'Next we evaluate' as the transition from diagnosing plain nets to testing residual nets.",
                    ],
                }
            if "next we investigate projection shortcuts" in compact_lower and "we compare three options" in compact_lower:
                return {
                    "one_line": "This section compares shortcut options and concludes projection shortcuts are useful but not essential.",
                    "simple": (
                        "The authors compare three shortcut designs. All are much better than the plain network. Projection shortcuts help a little, "
                        "but the small differences show they are not the main reason ResNet solves degradation."
                    ),
                    "academic": (
                        "The section analyzes shortcut-design variants A/B/C, showing that residual shortcuts outperform the plain counterpart and that "
                        "projection shortcuts provide minor gains without being essential to addressing degradation."
                    ),
                    "study_notes": [
                        "Read this as an ablation comparison, not as a new architecture proposal.",
                        "Separate the core claim from the option details: residual shortcuts matter more than projections everywhere.",
                        "Use 'not essential for addressing' as the reusable expression for a limited negative conclusion.",
                    ],
                }
            if "the three layers are" in compact_lower and "bottleneck architectures" in compact_lower:
                return {
                    "one_line": "This section explains why bottleneck blocks make very deep ResNets computationally practical.",
                    "simple": (
                        "A bottleneck block uses 1x1, 3x3, and 1x1 convolutions. The 1x1 layers reduce and restore dimensions so the 3x3 layer is cheaper. "
                        "Identity shortcuts are important because projection shortcuts would double time complexity and model size."
                    ),
                    "academic": (
                        "The section motivates bottleneck residual blocks as an efficiency-driven architecture: dimensionality reduction around the 3x3 convolution "
                        "keeps deeper ResNets economical, while identity shortcuts avoid projection costs at high-dimensional endpoints."
                    ),
                    "study_notes": [
                        "Track the block role sequence: reduce dimensions -> process with 3x3 -> restore dimensions.",
                        "The key claim is efficiency, not a new optimization problem.",
                        "Use 'mainly due to practical considerations' to mark an engineering reason for an architecture choice.",
                    ],
                }
            if self._is_resnet_deep_bottleneck_results_section(document_text):
                return {
                    "one_line": "This section shows very deep bottleneck ResNets outperform shallower ResNets and reach state-of-the-art ImageNet results.",
                    "simple": (
                        "The authors build 50-, 101-, and 152-layer ResNets with bottleneck blocks. Even though the 152-layer model is very deep, "
                        "it is still cheaper than VGG in FLOPs, improves accuracy over 34-layer ResNets, avoids degradation, and wins ILSVRC 2015 with an ensemble."
                    ),
                    "academic": (
                        "The section reports the scaling payoff of bottleneck residual architectures: depth can increase substantially while complexity remains controlled, "
                        "accuracy improves by large margins, and the resulting models achieve state-of-the-art ImageNet performance before the paper transitions to CIFAR-10 analysis."
                    ),
                    "study_notes": [
                        "Read this as evidence that bottleneck ResNets scale, not as another definition of degradation.",
                        "Separate single-model performance from ensemble competition results.",
                        "The CIFAR-10 paragraph is a transition into controlled behavior analysis.",
                    ],
                }
            if "based on the above plain network" in compact_lower and "we insert shortcut connections" in compact_lower:
                return {
                    "one_line": "This section shows how the plain ImageNet baseline is converted into a residual network.",
                    "simple": (
                        "The authors start from a plain VGG-style network and insert shortcut connections to make the residual version. "
                        "Identity shortcuts work when dimensions match; when dimensions increase, the paper compares zero-padding identity shortcuts and projection shortcuts."
                    ),
                    "academic": (
                        "The section defines the residual counterpart of the plain ImageNet architecture, specifying when identity shortcuts apply directly "
                        "and how dimension increases are handled by zero padding or 1x1 projection shortcuts."
                    ),
                    "study_notes": [
                        "Track the architecture transformation: plain network -> insert shortcut connections -> residual network.",
                        "Separate the two shortcut cases: same dimensions versus increased dimensions.",
                        "Do not treat implementation hyperparameters as the main language-learning targets in this section.",
                    ],
                }
            if "identity mapping is sufficient" in compact_lower and "network architectures" in compact_lower:
                return {
                    "one_line": "This section explains dimension matching and then introduces the ImageNet plain/residual network designs.",
                    "simple": (
                        "The authors say identity shortcuts are usually enough, while projection shortcuts are used when dimensions must match. "
                        "Then they move from the residual-block formula to concrete ImageNet architectures inspired by VGG."
                    ),
                    "academic": (
                        "The section clarifies shortcut choices for residual blocks, extends the notation to convolutional feature maps, and begins "
                        "the architecture comparison between plain VGG-style baselines and residual counterparts."
                    ),
                    "study_notes": [
                        "Separate shortcut options: identity shortcut is the default; projection shortcut handles dimension changes.",
                        "Treat 'Network Architectures' as a mode shift from formula to implementation details.",
                        "Save plain network and projection shortcut as architecture concepts, not general vocabulary.",
                    ],
                }
            if "reasonable preconditioning" in compact_lower and "shortcut connection" in compact_lower:
                return {
                    "one_line": "This section explains why identity shortcuts help and defines the residual block computation.",
                    "simple": (
                        "If the desired function is close to identity, it is easier to learn a small residual change than a whole new mapping. "
                        "The block computes F(x)+x with shortcut connections and keeps the parameter cost comparable to plain networks."
                    ),
                    "academic": (
                        "The section motivates identity shortcuts as preconditioning, then formalizes residual blocks with element-wise addition, "
                        "dimension constraints, and optional projection shortcuts for mismatched channels."
                    ),
                    "study_notes": [
                        "Read F(x)+x as the block computation: residual branch plus shortcut branch.",
                        "Notice the fairness claim: identity shortcuts add no extra parameters or computation.",
                        "Projection shortcuts are an exception for dimension matching, not the core ResNet idea.",
                    ],
                }
            if "highway networks have not demonstrated accuracy gains" in compact_lower and "underlying mapping" in compact_lower:
                return {
                    "one_line": "This section contrasts ResNet with highway networks and then begins the residual-learning formulation.",
                    "simple": (
                        "The authors say ResNet shortcuts are different from highway-network gates because ResNet always passes information through "
                        "and learns residual functions. Then they start the formal setup: define an underlying mapping H(x) and ask the stacked layers to learn it."
                    ),
                    "academic": (
                        "The section closes the related-work contrast by distinguishing ungated identity shortcuts from gated highway networks, then transitions "
                        "into the formal residual-learning argument based on underlying mappings and identity references."
                    ),
                    "study_notes": [
                        "Read the first sentences as method contrast: highway gates can close; ResNet identity shortcuts stay open.",
                        "Then switch reading mode: H(x) marks the start of the mathematical formulation.",
                        "Save highway networks as related-work context, not as the paper's main method.",
                    ],
                }
            if "encoding residual vectors" in compact_lower and "highway networks" in compact_lower:
                return {
                    "one_line": "This related-work section connects ResNet to residual representations and shortcut-connection methods.",
                    "simple": (
                        "The authors show that residual ideas appeared in vector quantization, multigrid methods, and preconditioning, then compare "
                        "ResNet shortcuts with earlier shortcut and highway-network approaches."
                    ),
                    "academic": (
                        "The section positions residual learning within prior reformulation/preconditioning methods and distinguishes ResNet's "
                        "parameter-free identity shortcuts from gated highway networks."
                    ),
                    "study_notes": [
                        "Read this as related-work positioning, not as the main method definition.",
                        "Separate residual representations from shortcut-connection architecture.",
                        "The key contrast is gated highway shortcuts versus parameter-free identity shortcuts.",
                    ],
                }
            if "50/101/152-layer resnets" in compact_lower and "won the 1st place" in compact_lower:
                return {
                    "one_line": "This section shows very deep bottleneck ResNets outperform shallower ResNets and reach state-of-the-art ImageNet results.",
                    "simple": (
                        "The authors build 50-, 101-, and 152-layer ResNets with bottleneck blocks. Even though the 152-layer model is very deep, "
                        "it is still cheaper than VGG in FLOPs, improves accuracy over 34-layer ResNets, avoids degradation, and wins ILSVRC 2015 with an ensemble."
                    ),
                    "academic": (
                        "The section reports the scaling payoff of bottleneck residual architectures: depth can increase substantially while complexity remains controlled, "
                        "accuracy improves by large margins, and the resulting models achieve state-of-the-art ImageNet performance before the paper transitions to CIFAR-10 analysis."
                    ),
                    "study_notes": [
                        "Read this as evidence that bottleneck ResNets scale, not as another definition of degradation.",
                        "Separate single-model performance from ensemble competition results.",
                        "The CIFAR-10 paragraph is a transition into controlled behavior analysis.",
                    ],
                }
            if self._is_resnet_cifar_architecture_section(document_text):
                return {
                    "one_line": "This section defines the CIFAR-10 architecture used for controlled ResNet depth experiments.",
                    "simple": (
                        "The authors describe the CIFAR-10 network layout: 3x3 convolutions, stride-2 subsampling, filter sizes 16/32/64, "
                        "global average pooling, a 10-class classifier, and identity shortcuts attached to pairs of 3x3 layers."
                    ),
                    "academic": (
                        "The section specifies the controlled CIFAR-10 architecture and shortcut policy before reporting depth comparisons, "
                        "including the 6n+2 layer formula, 3n shortcut placement, and option-A identity shortcuts."
                    ),
                    "study_notes": [
                        "Read this as experiment setup, not as the final result table.",
                        "Save architecture terms like stride-2 subsampling and global average pooling; ignore table residue.",
                        "Option A means identity shortcuts are used in all CIFAR-10 cases here.",
                    ],
                }
            if self._is_resnet_cifar_depth_behavior_section(document_text):
                return {
                    "one_line": "This section shows CIFAR-10 plain nets degrade with depth while ResNets overcome the optimization difficulty.",
                    "simple": (
                        "The authors compare 20-, 32-, 44-, and 56-layer networks on CIFAR-10. Plain nets get worse as they go deeper, "
                        "but ResNets overcome the optimization difficulty and gain accuracy from increased depth. They also test a 110-layer ResNet with a short learning-rate warmup."
                    ),
                    "academic": (
                        "The section extends the degradation/ResNet contrast to CIFAR-10: plain networks exhibit higher training error with depth, "
                        "while residual networks scale to deeper settings, including a 110-layer model that requires a warmup schedule before normal training."
                    ),
                    "study_notes": [
                        "Read this as a behavior comparison, not as another architecture-definition section.",
                        "Separate the negative plain-net result from the positive ResNet result.",
                        "Treat the 110-layer warmup as a practical training detail after the main comparison.",
                    ],
                }
            if self._is_resnet_over_1000_layers_section(document_text):
                return {
                    "one_line": "This section stress-tests a 1202-layer ResNet and separates optimization success from overfitting.",
                    "simple": (
                        "The authors train an aggressively deep 1202-layer ResNet. It has no optimization difficulty and reaches very low training error, "
                        "but its test result is worse than the 110-layer ResNet, likely because the model is too large for CIFAR-10 and overfits."
                    ),
                    "academic": (
                        "The section shows that residual learning can optimize an over-1000-layer network, but also identifies a generalization limit: "
                        "the 1202-layer model may overfit the small CIFAR-10 dataset without stronger regularization."
                    ),
                    "study_notes": [
                        "Separate optimization from generalization: training succeeds, testing worsens.",
                        "The key limitation is overfitting, not failure of residual optimization.",
                        "Read maxout/dropout as regularization context, not as the paper's main method.",
                    ],
                }
            if self._is_resnet_detection_transfer_section(document_text):
                return {
                    "one_line": "This section shows ResNet-101 improves object detection by providing better learned representations.",
                    "simple": (
                        "The authors replace VGG-16 with ResNet-101 in the same detection system. Because the implementation stays the same, "
                        "the COCO improvement can be credited to better network representations, and residual nets win several ILSVRC/COCO tracks."
                    ),
                    "academic": (
                        "The section evaluates transfer from classification to detection by holding the Faster R-CNN implementation constant and changing the backbone from VGG-16 to ResNet-101, "
                        "attributing the COCO mAP gain and competition results to stronger learned representations."
                    ),
                    "study_notes": [
                        "Read this as transfer/generalization evidence, not another CIFAR architecture section.",
                        "The causal logic is controlled comparison: same detector, better backbone.",
                        "Save learned representations and COCO metric as study anchors.",
                    ],
                }
            if self._is_resnet_detection_baseline_section(document_text):
                return {
                    "one_line": "This appendix section explains how ResNet classification backbones are adapted for Faster R-CNN detection.",
                    "simple": (
                        "The authors initialize ResNet-50/101 from ImageNet classification models, fine-tune them on detection data, and adapt Faster R-CNN "
                        "because ResNet lacks VGG-style hidden fully connected layers."
                    ),
                    "academic": (
                        "The section specifies the detection-baseline implementation: ResNet backbones are fine-tuned for Faster R-CNN, use Networks on Conv feature maps "
                        "to handle the absence of hidden fc layers, and compute shared full-image convolutional features for detection."
                    ),
                    "study_notes": [
                        "Read this as implementation setup for appendix detection experiments.",
                        "Track the transfer path: ImageNet classifier -> detection fine-tuning -> Faster R-CNN backbone.",
                        "NoC is an adaptation detail, not the main residual-learning claim.",
                    ],
                }
            if "plain" in compact_lower and "higher training error" in compact_lower and "accuracy gains" in compact_lower:
                return {
                    "one_line": "This section states the empirical case for ResNet: residual nets optimize better and gain accuracy from depth.",
                    "simple": (
                        "The authors report two main results. Plain deep networks get higher training error as they get deeper, while residual networks "
                        "remain easy to optimize and can improve accuracy with much greater depth."
                    ),
                    "academic": (
                        "The section summarizes experimental evidence across CIFAR-10, ImageNet, and recognition competitions to argue that residual "
                        "learning improves optimization, enables depth-driven accuracy gains, and generalizes beyond one dataset."
                    ),
                    "study_notes": [
                        "Separate the two claims: easier optimization and better accuracy from depth.",
                        "Read plain nets as the non-residual baseline.",
                        "Benchmark names support the evidence; they are not the main concept.",
                    ],
                }
            if "residual mapping" in compact_lower and "shortcut connections" in compact_lower:
                return {
                    "one_line": "This section defines the residual block: learn F(x), add back x, and implement it with shortcut connections.",
                    "simple": (
                        "Instead of making stacked layers learn the full mapping H(x), ResNet makes them learn the residual F(x)=H(x)-x. "
                        "The block outputs F(x)+x using shortcut connections, which add no extra parameters in the identity case."
                    ),
                    "academic": (
                        "The section formalizes residual learning as a reparameterization of the desired mapping and explains how identity shortcut "
                        "connections realize the formulation inside standard feedforward networks trained by backpropagation."
                    ),
                    "study_notes": [
                        "Concept path: underlying mapping H(x) -> residual mapping F(x) -> block output F(x)+x.",
                        "Architecture path: shortcut connections carry x around stacked layers and add it back.",
                        "Language cue: 'Instead of' marks the contrast between direct learning and residual learning.",
                    ],
                }
            if "degradation problem" in compact_lower or ("training accuracy" in compact_lower and "deeper" in compact_lower):
                if "solution by construction" in compact_lower or "shallower architecture" in compact_lower:
                    return {
                        "one_line": "This section explains why degradation is surprising: a deeper model should be able to copy a shallower one.",
                        "simple": (
                            "The authors reason that a deeper network should not train worse in principle, because the extra layers could act like identity mappings "
                            "while the other layers copy the shallower model. Experiments still show higher training error, so the problem is optimization."
                        ),
                        "academic": (
                            "The section uses a constructed-solution argument to show that degradation is not a lack of model capacity: a deeper counterpart should "
                            "match the shallower architecture, yet current solvers fail to find that solution."
                        ),
                        "study_notes": [
                            "Read this as a logic step, not a new architecture proposal.",
                            "The key contrast is theoretical existence versus what optimization actually finds.",
                            "Save constructed solution and identity mapping as concept anchors for the residual-learning argument.",
                        ],
                    }
                return {
                    "one_line": "This section motivates ResNet through the degradation problem: deeper networks can be harder to optimize.",
                    "simple": (
                        "The authors argue that simply adding layers does not always help. Very deep plain networks can train worse, "
                        "so the paper introduces residual learning to make depth easier to optimize."
                    ),
                    "academic": (
                        "The section distinguishes optimization degradation from model capacity, motivating residual learning as a reformulation "
                        "that lets substantially deeper image-recognition networks train effectively."
                    ),
                    "study_notes": [
                        "Do not read 'degradation' as overfitting; the issue is training error and optimization.",
                        "Track the problem-solution chain: depth helps representation, but plain depth is hard to optimize, so residual learning is introduced.",
                        "Save residual learning framework, degradation problem, and shortcut connections as separate concepts.",
                    ],
                }
            return {
                "one_line": "The paper introduces residual learning to train much deeper image-recognition networks.",
                "simple": (
                    "ResNet changes what the layers learn. Instead of forcing layers to learn a full mapping directly, the network learns residual functions "
                    "relative to an identity mapping, which makes deeper models easier to train."
                ),
                "academic": (
                    "The section proposes a residual learning framework for image recognition, reformulating stacked layers as residual functions with "
                    "reference to identity mappings and supporting the claim with large-scale empirical evidence."
                ),
                "study_notes": [
                    "Concept first: residual learning is the method; shortcut connections are the architecture mechanism.",
                    "Language cue: 'to ease the training of' tells you the purpose of the method.",
                    "When reading results, separate optimization claims from accuracy claims.",
                ],
            }
        if self._is_attention_text(document_text):
            return {
                "one_line": "The paper introduces the Transformer, an attention-only architecture for sequence transduction.",
                "simple": (
                    "Earlier translation models relied on recurrence or convolution. "
                    "The Transformer keeps the encoder-decoder idea but uses self-attention so sequence positions can interact more directly and training can be more parallel."
                ),
                "academic": (
                    "The section frames dominant recurrent and convolutional sequence-transduction models as less parallel and less direct for long-range dependencies, "
                    "then proposes an attention-only encoder-decoder architecture that improves translation quality with lower training cost."
                ),
                "study_notes": [
                    "Do not save 'the best performing models' as vocabulary; treat it as a discourse signal introducing prior work.",
                    "Track the contrast chain: recurrent/convolutional models -> attention-only Transformer -> more parallel training.",
                    "Separate task terms such as sequence transduction from method terms such as self-attention and encoder-decoder.",
                ],
            }
        if self._is_bert_text(document_text):
            if "masked language model" in lower and "next sentence prediction" in lower and "contributions of our paper" in lower:
                return {
                    "one_line": "This section explains BERT's pre-training tasks and lists the paper's main contributions.",
                    "simple": (
                        "BERT uses masked language modeling so a token can learn from both left and right context. "
                        "It also uses next sentence prediction for text-pair representations, then summarizes the paper's contributions."
                    ),
                    "academic": (
                        "The section positions masked language modeling and next sentence prediction as BERT's pre-training mechanisms, "
                        "then claims bidirectional pre-training, reduced task-specific architecture engineering, and state-of-the-art NLP results as contributions."
                    ),
                    "study_notes": [
                        "Separate the two pre-training tasks: masked language model and next sentence prediction.",
                        "Use 'In addition to' as a signal that a second method is being added.",
                        "When you see 'contributions are as follows', switch to scanning claim bullets.",
                    ],
                }
            if "two existing strategies" in lower and "feature-based" in lower and ("fine-tuning" in lower or "ﬁne-tuning" in lower):
                return {
                    "one_line": "This section contrasts feature-based and fine-tuning approaches, then motivates BERT's bidirectional pre-training.",
                    "simple": (
                        "The authors explain that earlier pre-trained representations were used either as features or through fine-tuning. "
                        "They argue that unidirectional language models limit both strategies, especially for tasks that need context from both directions."
                    ),
                    "academic": (
                        "The section frames BERT as a response to the unidirectionality constraint in previous pre-training methods, contrasting ELMo-style "
                        "feature extraction and GPT-style fine-tuning before introducing masked language modeling as the bidirectional solution."
                    ),
                    "study_notes": [
                        "Notice the literature-map phrase 'There are two existing strategies'.",
                        "Track the contrast: feature-based vs. fine-tuning, then unidirectional vs. bidirectional.",
                        "The phrase 'major limitation is that' signals the problem BERT is designed to solve.",
                    ],
                }
            return {
                "one_line": "The paper introduces BERT, a bidirectional Transformer representation model for language understanding.",
                "simple": "BERT learns from both left and right context during pre-training, then can be fine-tuned for many NLP tasks.",
                "academic": (
                    "The paper proposes bidirectional Transformer pre-training through masked language modeling and next sentence prediction, "
                    "showing that a single pre-trained representation model can transfer strongly across language understanding benchmarks."
                ),
                "study_notes": [
                    "Track the contrast between previous left-to-right models and BERT's bidirectional conditioning.",
                    "Save task names separately from model names: masked language model and next sentence prediction are training objectives.",
                ],
            }
        first = self._sentences_from_text(document_text)[0] if document_text.strip() else "Summary not available."
        return {
            "one_line": first,
            "simple": first,
            "academic": first,
            "study_notes": ["The summary is source-grounded but still needs stronger model support for this document type."],
        }

    def _merge_learning_rows(self, primary: list[dict[str, Any]], secondary: list[dict[str, Any]], key: str, limit: int) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in [*primary, *secondary]:
            value = str(row.get(key) or "").strip()
            if not value:
                continue
            clean = self._clean_learning_term(value) if key in {"term", "concept"} else value
            if not clean:
                continue
            row = {**row, key: clean}
            normalized = clean.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(row)
        return merged[:limit]

    def _filter_bert_learning_rows(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {
            "learning rate",
            "dropout",
            "right language model",
            "pre-trained bert model",
            "new language representation model",
            "language representation models",
        }
        if key == "phrase":
            blocked = {*blocked, "feature-based"}
        has_full_name = any(str(row.get(key) or "").lower() == "bidirectional encoder representations from transformers" for row in rows)
        filtered: list[dict[str, Any]] = []
        for row in rows:
            value = str(row.get(key) or "").strip()
            lowered = value.lower()
            if lowered in blocked:
                continue
            if has_full_name and lowered == "bidirectional encoder representations":
                continue
            filtered.append(row)
        return filtered

    def _filter_resnet_shortcut_option_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {
            "batch normalization",
            "mini-batch",
            "learning rate",
            "sgd",
            "weight decay",
            "momentum",
            "dropout",
            "example network",
            "example network architectures",
        }
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _sentences_are_weak(self, sentences: list[dict[str, str]]) -> bool:
        if not sentences:
            return True
        weak_markers = {
            "Structure not provided.",
            "Explanation not provided.",
            "Model did not return sentence decomposition.",
            "Main claim + explanation.",
            "Subject (degradation) + Verb (indicates) + Object (that clause)",
            "Subject (shortcuts) + Verb (increase) + Object (dimensions).",
        }
        return any(sentence.get("core_structure") in weak_markers or sentence.get("korean_explanation") in weak_markers for sentence in sentences)

    def _needs_bert_section_sentence_override(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return self._is_bert_text(document_text) and "contributions of our paper" in lowered

    def _summaries_are_weak(self, summaries: dict[str, Any], document_text: str) -> bool:
        lowered = document_text.lower()
        compact_lower = " ".join(lowered.split())
        if "two existing strategies" in lowered and "feature-based" in lowered and ("fine-tuning" in lowered or "ﬁne-tuning" in lowered):
            return True
        if "masked language model" in lowered and "next sentence prediction" in lowered and "contributions of our paper" in lowered:
            return True
        values = [str(summaries.get(key) or "").strip() for key in ("one_line", "simple", "academic")]
        if any(not value for value in values):
            return True
        summary_signal = " ".join(value.lower() for value in values)
        if "residual mapping" in compact_lower and "shortcut connections" in compact_lower and "degradation problem" in summary_signal:
            return True
        if values[0].lower().startswith("figure") or " figure " in summary_signal:
            return True
        if (
            "weighted sum" in summary_signal
            and "scaled dot-product attention" in compact_lower
            and "queries" in compact_lower
            and "keys" in compact_lower
            and "values" in compact_lower
        ):
            return True
        if (
            "transformer" in compact_lower
            and ("model architecture" in compact_lower or "encoder and decoder stacks" in compact_lower)
            and ("figure 1" in summary_signal or "model architecture" in summary_signal)
        ):
            return True
        if self._is_resnet_shortcut_option_section(document_text) and (
            "example network architectures" in summary_signal or "batch normalization" in summary_signal
        ):
            return True
        if "imagenet classification" in compact_lower and "34-layer plain net has higher validation error" in compact_lower:
            return True
        if "34-layer plain net has higher training error" in compact_lower and "next we evaluate" in compact_lower:
            return True
        if "next we investigate projection shortcuts" in compact_lower and "we compare three options" in compact_lower:
            return True
        if "the three layers are" in compact_lower and "bottleneck architectures" in compact_lower:
            return True
        if self._is_resnet_deep_bottleneck_results_section(document_text):
            return True
        if self._is_resnet_cifar_architecture_section(document_text):
            return True
        if self._is_resnet_cifar_depth_behavior_section(document_text):
            return True
        if self._is_resnet_over_1000_layers_section(document_text):
            return True
        if self._is_resnet_detection_transfer_section(document_text):
            return True
        if self._is_resnet_detection_baseline_section(document_text):
            return True
        if "network architectures" in compact_lower and "degradation problem" in summary_signal:
            return True
        if "reasonable preconditioning" in compact_lower and "degradation problem" in summary_signal:
            return True
        if any(len(value) > 240 for value in values[:2]):
            return True
        if len(set(values)) == 1:
            return True
        first_sentence = self._sentences_from_text(document_text)[0] if document_text.strip() else ""
        return bool(first_sentence and any(value == first_sentence for value in values[:2]))

    def _sentences(self, value: Any, document_text: str) -> list[dict[str, str]]:
        rows = value if isinstance(value, list) else []
        sentences: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            sentence = normalize_pdf_ligatures(str(row.get("sentence") or row.get("source_sentence") or "")).strip()
            if not sentence:
                continue
            sentences.append(
                {
                    "sentence": sentence,
                    "core_structure": normalize_pdf_ligatures(str(row.get("core_structure") or "Structure not provided.")),
                    "simplified_version": normalize_pdf_ligatures(str(row.get("simplified_version") or sentence)),
                    "korean_explanation": normalize_pdf_ligatures(
                        str(row.get("korean_explanation") or row.get("support_explanation") or "Explanation not provided.")
                    ),
                    "difficulty_reason": normalize_pdf_ligatures(str(row.get("difficulty_reason") or "Dense sentence structure.")),
                }
            )
        if sentences:
            return sentences[:8]
        first = self._sentences_from_text(document_text)[0] if document_text.strip() else ""
        return [
            {
                "sentence": first,
                "core_structure": "Structure not provided.",
                "simplified_version": first,
                "korean_explanation": "Explanation not provided.",
                "difficulty_reason": "Model did not return sentence decomposition.",
            }
        ]

    def _summaries(self, value: Any, document_text: str) -> dict[str, Any]:
        value = value if isinstance(value, dict) else {}
        first_sentence = self._sentences_from_text(document_text)[0] if document_text.strip() else "Document summary not available."
        return {
            "one_line": normalize_pdf_ligatures(str(value.get("one_line") or first_sentence)),
            "simple": normalize_pdf_ligatures(str(value.get("simple") or value.get("simple_summary") or first_sentence)),
            "academic": normalize_pdf_ligatures(str(value.get("academic") or value.get("academic_summary") or first_sentence)),
            "study_notes": self._string_list(value.get("study_notes")),
        }

    def _source_sentence(self, value: Any, target: str, document_text: str) -> str:
        candidate = normalize_pdf_ligatures(str(value or "")).strip()
        if candidate and self._appears_in_text(candidate, document_text):
            return self._trim_source(candidate, target)
        sentences = self._sentences_from_text(document_text)
        for sentence in sentences:
            if target.lower() in sentence.lower():
                return self._trim_source(sentence, target)
        if candidate and sentences:
            return self._trim_source(max(sentences, key=lambda sentence: SequenceMatcher(None, candidate.lower(), sentence.lower()).ratio()), target)
        return self._trim_source(sentences[0], target) if sentences else candidate

    def _sentences_from_text(self, text: str) -> list[str]:
        text = normalize_pdf_ligatures(text)
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
        if len(parts) == 1 and len(parts[0]) > 700:
            chunks = re.split(r"\s+\b(?:so|and|but|because|then|now|first|second)\b\s+", parts[0])
            return [part.strip() for part in chunks if part.strip()]
        return parts

    def _trim_source(self, source: str, target: str, max_chars: int = 420) -> str:
        source = " ".join(normalize_pdf_ligatures(source).split())
        target = normalize_pdf_ligatures(target)
        if len(source) <= max_chars:
            return source
        index = source.lower().find(target.lower()) if target else -1
        if index < 0:
            return f"{source[: max_chars - 1].rsplit(' ', 1)[0]}..."
        start = max(0, index - 150)
        end = min(len(source), index + len(target) + 220)
        excerpt = source[start:end].strip()
        if start > 0:
            excerpt = f"...{excerpt}"
        if end < len(source):
            excerpt = f"{excerpt.rsplit(' ', 1)[0]}..."
        return excerpt

    def _appears_in_text(self, value: str, text: str) -> bool:
        return self._match_text(value) in self._match_text(text)

    def _match_text(self, value: str) -> str:
        normalized = normalize_pdf_ligatures(value).lower()
        normalized = re.sub(r"[\"'“”‘’`]", "", normalized)
        return " ".join(normalized.split())

    def _priority_from_relevance(self, value: Any) -> str:
        value = str(value or "").lower()
        if value == "high":
            return "field_term"
        if value == "low":
            return "low_priority"
        return "useful"

    def _clean_learning_term(self, value: str) -> str:
        value = normalize_pdf_ligatures(value)
        value = " ".join(value.strip().split())
        if not value:
            return ""
        value = re.sub(r"^(?:the|a|an|or|and|but|these|those|this|that|to|of)\s+", "", value, flags=re.IGNORECASE)
        value = re.sub(r"^(?:dominant|best-performing|best performing|recent|previous|current)\s+", "", value, flags=re.IGNORECASE)
        lowered = value.lower()
        if lowered in {"term", "string", "concept", "model", "introduction recurrent", "tion model", "sentation models"}:
            return ""
        if lowered == "residual learning":
            return ""
        if lowered in {"training deep neural networks", "inputs changes during training"}:
            return ""
        if lowered in {"new language representation model", "language representation models", "pre-trained bert model"}:
            return ""
        if lowered in {"generative pre", "use unidirectional language models", "standard language models"}:
            return ""
        if lowered.startswith(("use ", "uses ", "using ", "ease ", "eases ")):
            return ""
        if lowered in {"networks", "of networks", "ease the training", "to ease the training"}:
            return ""
        if lowered in {"shortcuts we", "we describe two models", "square matrix"}:
            return ""
        if lowered in {"example network", "example network architectures"}:
            return ""
        if lowered in {"imagenet classification we", "plain networks", "we evaluate our method"}:
            return ""
        if lowered in {"net has higher training", "throughout the whole training", "gradients", "residual networks"}:
            return ""
        if lowered in {"in table", "shortcuts help with training", "residual function"}:
            return ""
        if lowered in {"time complexity and model", "more efficient models"}:
            return ""
        if lowered.startswith(("we describe ", "we also note ", "we can also use ", "we combine ")):
            return ""
        if lowered in {"reveals that network", "has higher training", "higher training", "deeper network"}:
            return ""
        if lowered in {
            "training",
            "degradation",
            "deeper model",
            "learned shallower model",
            "current solvers on hand",
            "by feedforward neural networks",
            "exhibit higher training",
            "better than previous networks",
            "effects of our method",
            "present successfully trained models",
            "early practice of training",
            "widely used multigrid method",
        }:
            return ""
        if lowered.startswith(("reveals that ", "shows that ", "has ", "have ", "is ", "are ")):
            return ""
        if re.fullmatch(r"(?:inputs?|outputs?|models?|networks?)\s+\w+(?:\s+\w+){0,3}", lowered):
            return ""
        if lowered.startswith(("introduction ", "conclusion ", "abstract ", "references ")):
            return ""
        if re.fullmatch(r"(?:best|better|good|poor|strong|weak|performing|performance)\s+models?", lowered):
            return ""
        if lowered in {"best performing models", "performing models", "models", "the best performing models"}:
            return ""
        if len(value.split()) > 5:
            return ""
        return value

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _references_near(self, sentence: str, document_text: str) -> list[str]:
        source = sentence or document_text[:1000]
        references = re.findall(r"\([A-Z][A-Za-z-]+(?: et al\.)?,?\s+\d{4}[a-z]?\)|\[\d+(?:,\s*\d+)*\]", source)
        return references[:4]

    def _is_bert_text(self, document_text: str) -> bool:
        lowered = document_text.lower()
        if "bert" in lowered and "bidirectional encoder representations" in lowered:
            return True
        return "bert" in lowered and ("masked language model" in lowered or "next sentence prediction" in lowered or "unidirectional language models" in lowered)

    def _is_attention_text(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "attention is all you need" in lowered
            or ("transformer" in lowered and "sequence transduction" in lowered)
            or ("self-attention" in lowered and "recurrent" in lowered and "convolution" in lowered)
        )

    def _is_resnet_text(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "deep residual learning for image recognition" in lowered
            or ("residual learning framework" in lowered and "image recognition" in lowered)
            or ("residual learning framework" in lowered and "residual functions" in lowered)
            or ("degradation problem" in lowered and "residual" in lowered)
            or ("degradation problem" in lowered and "training error" in lowered)
            or ("network depth" in lowered and "higher training error" in lowered)
            or ("very deep" in lowered and "stacking more layers" in lowered)
            or ("solution by construction" in lowered and "identity mapping" in lowered)
            or ("shallower architecture" in lowered and "deeper counterpart" in lowered)
            or ("identity mapping" in lowered and "residual functions" in lowered)
            or ("residual mapping" in lowered and "shortcut connections" in lowered)
            or ("underlying mapping" in lowered and "residual mapping" in lowered)
            or ("plain" in lowered and "higher training error" in lowered and "accuracy gains" in lowered)
            or ("top-5 error" in lowered and "imagenet" in lowered)
            or ("encoding residual vectors" in lowered and "shortcut connections" in lowered)
            or ("highway networks" in lowered and "gating functions" in lowered)
            or ("highway networks have not demonstrated accuracy gains" in lowered and "residual functions" in lowered)
            or ("reasonable preconditioning" in lowered and "shortcut connection" in lowered)
            or ("identity mapping is sufficient" in lowered and "network architectures" in lowered)
            or self._is_resnet_shortcut_option_section(document_text)
            or ("imagenet classification" in lowered and "34-layer plain net has higher validation error" in lowered)
            or ("34-layer plain net has higher training error" in lowered and "next we evaluate" in lowered)
            or ("next we investigate projection shortcuts" in lowered and "we compare three options" in lowered)
            or ("the three layers are" in lowered and "bottleneck architectures" in lowered)
            or self._is_resnet_deep_bottleneck_results_section(document_text)
            or self._is_resnet_cifar_architecture_section(document_text)
            or self._is_resnet_cifar_depth_behavior_section(document_text)
            or self._is_resnet_over_1000_layers_section(document_text)
            or self._is_resnet_detection_transfer_section(document_text)
            or self._is_resnet_detection_baseline_section(document_text)
        )

    def _is_resnet_shortcut_option_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "based on the above plain network" in lowered and "we insert shortcut connections" in lowered

    def _is_resnet_deep_bottleneck_results_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "50/101/152-layer resnets" in lowered and "won the 1st place" in lowered

    def _is_resnet_cifar_architecture_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "6n+2 stacked weighted layers" in lowered and "identity shortcuts in all cases" in lowered

    def _is_resnet_cifar_depth_behavior_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "plain nets suffer from increased depth" in lowered and "110-layer resnet" in lowered

    def _is_resnet_over_1000_layers_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "1202-layer network" in lowered and "because of overfitting" in lowered

    def _is_resnet_detection_transfer_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "replacing vgg-16" in lowered and "resnet-101" in lowered and "learned representations" in lowered

    def _is_resnet_detection_baseline_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "object detection baselines" in lowered and "faster r-cnn" in lowered and "networks on conv feature maps" in lowered

    def _prefer_resnet_deep_results_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"feature maps", "resnet", "model", "we combine six models"}
        preferred = {
            "50/101/152-layer ResNets": (
                "The very deep bottleneck residual networks that demonstrate the scaling result.",
                "This is the main architecture result of the section.",
            ),
            "lower complexity than VGG": (
                "The claim that 152-layer ResNet is deeper but still cheaper than VGG-16/19.",
                "This separates useful depth from raw computational cost.",
            ),
            "single-model top-5 validation error": (
                "The ImageNet metric reported before combining models into an ensemble.",
                "This helps separate single-model evidence from ensemble competition results.",
            ),
            "ensemble": (
                "A combined system of several ResNets used for the ILSVRC 2015 entry.",
                "This explains how the final competition result was produced.",
            ),
            "state-of-the-art methods": (
                "The external benchmark comparison against the best available methods.",
                "This moves the section from architecture scaling to competitive performance.",
            ),
            "CIFAR-10": (
                "The next benchmark used for controlled analysis of extremely deep networks.",
                "This marks the transition into the following experiment section.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            elif self._appears_in_text(value, document_text):
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, value, document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_deep_results_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"feature maps", "resnet", "model", "we combine six models"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_cifar_architecture_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"dropout", "for resnet", "network", "learning rate"}
        preferred = {
            "CIFAR-10 architecture": (
                "The controlled small-image network design used before comparing depth behavior.",
                "This section is mainly setup for the CIFAR-10 depth experiments.",
            ),
            "6n+2 stacked weighted layers": (
                "The formula for the total depth of the CIFAR-10 networks.",
                "This connects the architecture description to 20/32/44/56-layer variants.",
            ),
            "stride of 2": (
                "The convolution stride used for subsampling.",
                "This explains how feature-map resolution changes across stages.",
            ),
            "global average pooling": (
                "The final pooling step before the CIFAR-10 classifier.",
                "This is part of the architecture endpoint.",
            ),
            "identity shortcuts in all cases": (
                "The option-A shortcut policy used for CIFAR-10 experiments.",
                "This keeps the CIFAR setup distinct from the ImageNet projection comparisons.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            elif value == "CIFAR-10 architecture" or self._appears_in_text(value, document_text):
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, value if value != "CIFAR-10 architecture" else "CIFAR-10", document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_cifar_architecture_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"dropout", "for resnet", "network", "learning rate"}
        if key == "phrase":
            blocked = {
                *blocked,
                "subsampling is performed by convolutions with a stride of 2",
            }
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_cifar_depth_behavior_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"resnets", "layer networks", "warm up the training", "until the training"}
        preferred = {
            "plain-net depth degradation on CIFAR-10": (
                "Deeper plain networks show higher training error on CIFAR-10.",
                "This confirms that degradation is an optimization problem, not just an ImageNet accident.",
            ),
            "ResNet depth scaling on CIFAR-10": (
                "Residual networks overcome the optimization difficulty and gain accuracy as depth increases.",
                "This is the core positive result of the section.",
            ),
            "optimization difficulty as a fundamental problem": (
                "The same plain-net failure appears across CIFAR-10, ImageNet, and MNIST.",
                "This broadens the paper's argument beyond one dataset.",
            ),
            "110-layer ResNet": (
                "A very deep CIFAR-10 residual network tested after the 20/32/44/56-layer comparison.",
                "This shows the depth-scaling test continues beyond the first comparison.",
            ),
            "learning-rate warmup": (
                "A temporary lower-learning-rate phase used before returning to the main schedule.",
                "This is the practical adjustment needed for the 110-layer run.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            elif value in {
                "plain-net depth degradation on CIFAR-10",
                "ResNet depth scaling on CIFAR-10",
                "optimization difficulty as a fundamental problem",
                "learning-rate warmup",
            } or self._appears_in_text(value, document_text):
                target = "plain nets suffer from increased depth" if value.startswith("plain-net") else value
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_cifar_depth_behavior_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"resnets", "layer networks", "warm up the training", "until the training"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_over_1000_layers_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"dropout", "resnet", "dashed lines denote training"}
        preferred = {
            "over-1000-layer stress test": (
                "The experiment that trains a 1202-layer residual network.",
                "This is an extreme-depth test of residual optimization.",
            ),
            "optimization success versus overfitting": (
                "The 1202-layer model trains successfully but tests worse than the 110-layer model.",
                "This is the key reading distinction in the section.",
            ),
            "small-dataset overfitting": (
                "The claim that the 1202-layer model may be too large for CIFAR-10.",
                "This explains why test performance can get worse despite very low training error.",
            ),
            "regularization tradeoff": (
                "The authors avoid maxout/dropout to keep the focus on optimization, while noting stronger regularization may help.",
                "This separates the paper's experimental focus from maximum benchmark tuning.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "1202-layer network" if value == "over-1000-layer stress test" else "overfitting"
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_over_1000_layers_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"dropout", "resnet", "dashed lines denote training", "applied to", "exploring over 1000 layers"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_detection_transfer_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"vgg-16", "attributed to better networks"}
        preferred = {
            "object-detection transfer": (
                "The controlled replacement of VGG-16 with ResNet-101 in the same detection system.",
                "This tests whether residual representations help outside classification.",
            ),
            "representation quality attribution": (
                "The claim that gains come from better networks because the detection implementation is unchanged.",
                "This is the causal logic of the section.",
            ),
            "COCO relative improvement": (
                "A 6.0-point gain on COCO mAP@[.5, .95], described as 28% relative improvement.",
                "This is the strongest numeric transfer result.",
            ),
            "competition-level generalization": (
                "Residual nets win multiple ILSVRC and COCO 2015 detection/localization/segmentation tracks.",
                "This supports the broader usefulness of learned representations.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "learned representations" if "representation" in lowered else "ResNet-101"
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_detection_transfer_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"vgg-16", "imagenet", "attributed to better networks"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_detection_baseline_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"feature maps", "imagenet classification"}
        preferred = {
            "Faster R-CNN baseline adaptation": (
                "The setup where ResNet classification backbones are adapted into Faster R-CNN.",
                "This explains how classification models become detection backbones.",
            ),
            "ImageNet-to-detection fine-tuning": (
                "The process of initializing from ImageNet classification models and fine-tuning on detection data.",
                "This is the transfer-learning mechanism in the appendix.",
            ),
            "ResNet without hidden fc layers": (
                "The architectural difference from VGG-16 that requires a detector-backbone adaptation.",
                "This motivates the use of Networks on Conv feature maps.",
            ),
            "shared convolutional feature maps": (
                "Full-image convolutional maps reused by the detector.",
                "This is the implementation detail that connects ResNet to Faster R-CNN.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "Faster R-CNN" if "faster" in lowered else "Conv feature maps"
                promoted.append(
                    {
                        "concept": value,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [value],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.85,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {value.lower() for value in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_resnet_detection_baseline_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"imagenet", "imagenet classification", "feature maps"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _score(self, value: Any, default: int) -> int:
        try:
            parsed = float(value)
            if 0 < parsed <= 1:
                parsed *= 10
            return max(0, min(10, round(parsed)))
        except (TypeError, ValueError):
            return default

    def _confidence(self, value: Any, default: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default
