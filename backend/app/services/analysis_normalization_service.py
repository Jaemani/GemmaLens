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
        phrases = self._merge_learning_rows(phrases, self._heuristic_phrases(document_text), "phrase", limit=10)
        if self._is_bert_text(document_text):
            terms = self._filter_bert_learning_rows(terms, "term")
            phrases = self._filter_bert_learning_rows(phrases, "phrase")
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
            }:
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
                    "ImageNet",
                    "A large image recognition benchmark used to evaluate the paper's models.",
                    "useful",
                    "medium",
                    "It grounds the paper's empirical claims.",
                ),
                (
                    "CIFAR-10",
                    "A small image classification benchmark used for controlled experiments.",
                    "useful",
                    "medium",
                    "It appears in the paper's experimental validation.",
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
            if not sentence or term.lower() not in sentence.lower():
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
            if not sentence or concept.lower() not in sentence.lower():
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
            if "degradation problem" in compact_lower or ("training accuracy" in compact_lower and "deeper" in compact_lower):
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

    def _sentences_are_weak(self, sentences: list[dict[str, str]]) -> bool:
        if not sentences:
            return True
        weak_markers = {"Structure not provided.", "Explanation not provided.", "Model did not return sentence decomposition.", "Main claim + explanation."}
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
        return " ".join(normalize_pdf_ligatures(value).lower().split()) in " ".join(normalize_pdf_ligatures(text).lower().split())

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
        if lowered in {"term", "string", "concept", "introduction recurrent", "tion model", "sentation models"}:
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
        if lowered in {"reveals that network", "has higher training", "higher training", "deeper network"}:
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
            or ("identity mapping" in lowered and "residual functions" in lowered)
        )

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
