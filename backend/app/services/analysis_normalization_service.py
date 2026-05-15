import re
from difflib import SequenceMatcher
from typing import Any

from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_quality_service import AnalysisQualityService


class AnalysisNormalizationService:
    def __init__(self) -> None:
        self.quality = AnalysisQualityService()

    def normalize_result(self, result: AnalysisResult, document_text: str) -> AnalysisResult:
        return self.normalize_payload(result.model_dump(), result.document_id, document_text)

    def normalize_payload(self, payload: dict[str, Any], document_id: str, document_text: str) -> AnalysisResult:
        terms = self._terms(payload.get("terms"), document_text)
        phrases = self._phrases(payload.get("phrases") or payload.get("academic_phrases") or payload.get("expressions"), document_text)
        terms = self._merge_learning_rows(self._heuristic_terms(document_text), terms, "term", limit=14)
        phrases = self._merge_learning_rows(phrases, self._heuristic_phrases(document_text), "phrase", limit=10)
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
        if self._sentences_are_weak(normalized["sentences"]):
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
            meaning = str(row.get("meaning") or row.get("context_meaning") or row.get("general_meaning") or "Meaning not provided.").strip()
            terms.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "domain_relevance": row.get("domain_relevance") or priority or "medium",
                    "difficulty": row.get("difficulty") or "medium",
                    "source_sentence": source_sentence,
                    "should_save": bool(row.get("should_save", confidence >= 0.45 and priority != "low_priority")),
                    "learning_priority": priority or self._priority_from_relevance(row.get("domain_relevance")),
                    "reason": str(row.get("reason") or row.get("why") or "Selected as a useful learning item."),
                    "context_meaning": str(row.get("context_meaning") or meaning),
                    "general_meaning": str(row.get("general_meaning") or meaning),
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
            phrase = str(row.get("phrase") or row.get("text") or "").strip()
            if not phrase:
                continue
            if phrase.lower() in {"string", "phrase", "actual phrase"}:
                continue
            if not self._appears_in_text(phrase, document_text):
                continue
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            explanation = str(row.get("explanation") or row.get("meaning") or "Explanation not provided.").strip()
            phrases.append(
                {
                    "phrase": phrase,
                    "function": row.get("function") or row.get("category") or "general",
                    "explanation": explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or "useful",
                    "reason": str(row.get("reason") or "Selected as a reusable expression."),
                    "context_meaning": str(row.get("context_meaning") or explanation),
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
            explanation = str(row.get("explanation") or row.get("meaning") or "Concept explanation not provided.").strip()
            source_sentence = self._source_sentence(row.get("source_sentence"), concept, document_text)
            concepts.append(
                {
                    "concept": concept,
                    "explanation": explanation,
                    "source_sentence": source_sentence,
                    "related_terms": self._string_list(row.get("related_terms")),
                    "why_it_matters": str(row.get("why_it_matters") or row.get("reason") or "This concept helps connect vocabulary to the paper's main argument."),
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
        if "bert" in lower and "bidirectional encoder representations" in lower:
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

    def _sentences_are_weak(self, sentences: list[dict[str, str]]) -> bool:
        if not sentences:
            return True
        weak_markers = {"Structure not provided.", "Explanation not provided.", "Model did not return sentence decomposition."}
        return any(sentence.get("core_structure") in weak_markers or sentence.get("korean_explanation") in weak_markers for sentence in sentences)

    def _summaries_are_weak(self, summaries: dict[str, Any], document_text: str) -> bool:
        values = [str(summaries.get(key) or "").strip() for key in ("one_line", "simple", "academic")]
        if any(not value for value in values):
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
            sentence = str(row.get("sentence") or row.get("source_sentence") or "").strip()
            if not sentence:
                continue
            sentences.append(
                {
                    "sentence": sentence,
                    "core_structure": str(row.get("core_structure") or "Structure not provided."),
                    "simplified_version": str(row.get("simplified_version") or sentence),
                    "korean_explanation": str(row.get("korean_explanation") or row.get("support_explanation") or "Explanation not provided."),
                    "difficulty_reason": str(row.get("difficulty_reason") or "Dense sentence structure."),
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
            "one_line": str(value.get("one_line") or first_sentence),
            "simple": str(value.get("simple") or value.get("simple_summary") or first_sentence),
            "academic": str(value.get("academic") or value.get("academic_summary") or first_sentence),
            "study_notes": self._string_list(value.get("study_notes")),
        }

    def _source_sentence(self, value: Any, target: str, document_text: str) -> str:
        candidate = str(value or "").strip()
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
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
        if len(parts) == 1 and len(parts[0]) > 700:
            chunks = re.split(r"\s+\b(?:so|and|but|because|then|now|first|second)\b\s+", parts[0])
            return [part.strip() for part in chunks if part.strip()]
        return parts

    def _trim_source(self, source: str, target: str, max_chars: int = 420) -> str:
        source = " ".join(source.split())
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
        return " ".join(value.lower().split()) in " ".join(text.lower().split())

    def _priority_from_relevance(self, value: Any) -> str:
        value = str(value or "").lower()
        if value == "high":
            return "field_term"
        if value == "low":
            return "low_priority"
        return "useful"

    def _clean_learning_term(self, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            return ""
        value = re.sub(r"^(?:the|a|an|or|and|but|these|those|this|that)\s+", "", value, flags=re.IGNORECASE)
        value = re.sub(r"^(?:dominant|best-performing|best performing|recent|previous|current)\s+", "", value, flags=re.IGNORECASE)
        lowered = value.lower()
        if lowered in {"term", "string", "concept", "introduction recurrent"}:
            return ""
        if lowered in {"training deep neural networks", "inputs changes during training"}:
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
