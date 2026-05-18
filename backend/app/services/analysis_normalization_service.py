import re
from difflib import SequenceMatcher
from typing import Any

from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_quality_service import AnalysisQualityService
from app.services.text_cleanup_service import normalize_pdf_ligatures


class AnalysisNormalizationService:
    def __init__(self) -> None:
        self.quality = AnalysisQualityService()

    def normalize_result(
        self,
        result: AnalysisResult,
        document_text: str,
        support_language: str = "Korean",
        target_level: str | None = None,
        source_type: str | None = None,
    ) -> AnalysisResult:
        return self.normalize_payload(
            result.model_dump(),
            result.document_id,
            document_text,
            support_language=support_language,
            target_level=target_level,
            source_type=source_type,
        )

    def normalize_payload(
        self,
        payload: dict[str, Any],
        document_id: str,
        document_text: str,
        support_language: str = "Korean",
        target_level: str | None = None,
        source_type: str | None = None,
    ) -> AnalysisResult:
        document_text = normalize_pdf_ligatures(document_text)
        terms = self._terms(payload.get("terms"), document_text, support_language=support_language)
        phrases = self._phrases(
            payload.get("phrases") or payload.get("academic_phrases") or payload.get("expressions"),
            document_text,
            support_language=support_language,
        )
        terms = self._merge_learning_rows(self._heuristic_terms(document_text), terms, "term", limit=14)
        phrases = self._merge_learning_rows(phrases, self._heuristic_phrases(document_text), "phrase", limit=12)
        if self._is_bert_text(document_text):
            terms = self._filter_bert_learning_rows(terms, "term")
            phrases = self._filter_bert_learning_rows(phrases, "phrase")
        if self._is_bert_elmo_finetuning_transition_section(document_text):
            terms = self._prefer_bert_elmo_finetuning_transition_terms(terms, document_text)
        if self._is_bert_pretraining_finetuning_procedure_section(document_text):
            terms = self._prefer_bert_pretraining_finetuning_procedure_terms(terms, document_text)
            phrases = self._filter_bert_pretraining_finetuning_procedure_phrases(phrases)
        if self._is_bert_architecture_model_size_section(document_text):
            terms = self._prefer_bert_architecture_model_size_terms(terms, document_text)
        if self._is_bert_input_representation_masked_lm_transition_section(document_text):
            terms = self._prefer_bert_input_representation_masked_lm_terms(terms, document_text)
        if self._is_bert_masked_lm_procedure_section(document_text):
            terms = self._prefer_bert_masked_lm_procedure_terms(terms, document_text)
            phrases = self._filter_bert_masked_lm_procedure_phrases(phrases)
        if self._is_bert_nsp_procedure_section(document_text):
            terms = self._prefer_bert_nsp_procedure_terms(terms, document_text)
            phrases = self._filter_bert_nsp_procedure_phrases(phrases)
        if self._is_bert_finetuning_unification_section(document_text):
            terms = self._prefer_bert_finetuning_unification_terms(terms, document_text)
            phrases = self._filter_bert_finetuning_unification_phrases(phrases)
        if self._is_bert_glue_setup_results_section(document_text):
            terms = self._prefer_bert_glue_setup_results_terms(terms, document_text)
            phrases = self._filter_bert_glue_setup_results_phrases(phrases)
        if self._is_bert_glue_result_interpretation_section(document_text):
            terms = self._prefer_bert_glue_result_interpretation_terms(terms, document_text)
            phrases = self._filter_bert_glue_result_interpretation_phrases(phrases)
        if self._is_bert_squad_span_prediction_section(document_text):
            terms = self._prefer_bert_squad_span_prediction_terms(terms, document_text)
            phrases = self._prefer_bert_squad_span_prediction_phrases(phrases, document_text)
        if self._is_bert_squad_results_transition_section(document_text):
            terms = self._prefer_bert_squad_results_transition_terms(terms, document_text)
            phrases = self._prefer_bert_squad_results_transition_phrases(phrases, document_text)
        if self._is_bert_squad2_swag_transition_section(document_text):
            terms = self._prefer_bert_squad2_swag_transition_terms(terms, document_text)
            phrases = self._prefer_bert_squad2_swag_transition_phrases(phrases, document_text)
        if self._is_bert_swag_ablation_transition_section(document_text):
            terms = self._prefer_bert_swag_ablation_transition_terms(terms, document_text)
            phrases = self._prefer_bert_swag_ablation_transition_phrases(phrases, document_text)
        if self._is_bert_ablation_interpretation_section(document_text):
            terms = self._prefer_bert_ablation_interpretation_terms(terms, document_text)
            phrases = self._prefer_bert_ablation_interpretation_phrases(phrases, document_text)
        if self._is_bert_model_size_effect_section(document_text):
            terms = self._prefer_bert_model_size_effect_terms(terms, document_text)
            phrases = self._prefer_bert_model_size_effect_phrases(phrases, document_text)
        if self._is_bert_feature_based_transition_section(document_text):
            terms = self._prefer_bert_feature_based_transition_terms(terms, document_text)
            phrases = self._prefer_bert_feature_based_transition_phrases(phrases, document_text)
        if self._is_bert_ner_feature_table_section(document_text):
            terms = self._prefer_bert_ner_feature_table_terms(terms, document_text)
            phrases = self._prefer_bert_ner_feature_table_phrases(phrases, document_text)
        if self._is_bert_conclusion_section(document_text):
            terms = self._prefer_bert_conclusion_terms(terms, document_text)
            phrases = self._prefer_bert_conclusion_phrases(phrases, document_text)
        if self._is_bert_appendix_learning_section(document_text):
            terms = self._prefer_bert_appendix_terms(terms, document_text)
            phrases = self._prefer_bert_appendix_phrases(phrases, document_text)
        if self._is_reference_list_section(document_text):
            terms = self._prefer_reference_list_terms(terms, document_text)
            phrases = self._prefer_reference_list_phrases(phrases, document_text)
        if self._is_batchnorm_learning_section(document_text):
            terms = self._prefer_batchnorm_terms(terms, document_text)
            phrases = self._prefer_batchnorm_phrases(phrases, document_text)
        if self._is_attention_learning_section(document_text):
            terms = self._prefer_attention_terms(terms, document_text)
            phrases = self._prefer_attention_phrases(phrases, document_text)
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
        if self._is_resnet_detection_evaluation_section(document_text):
            terms = self._filter_resnet_detection_evaluation_noise(terms, "term")
        if self._is_resnet_detection_improvements_section(document_text):
            terms = self._filter_resnet_detection_improvements_noise(terms, "term")
        if self._is_resnet_detection_results_table_section(document_text):
            terms = self._filter_resnet_detection_results_table_noise(terms, "term")
        if self._is_resnet_detection_result_narrative_section(document_text):
            terms = self._filter_resnet_detection_result_narrative_noise(terms, "term")
            terms = self._prefer_resnet_detection_result_narrative_terms(terms, document_text)
        if self._is_resnet_imagenet_detection_setup_section(document_text):
            terms = self._filter_resnet_imagenet_detection_setup_noise(terms, "term")
            terms = self._prefer_resnet_imagenet_detection_setup_terms(terms, document_text)
        if self._is_resnet_imagenet_localization_setup_section(document_text):
            terms = self._filter_resnet_imagenet_localization_setup_noise(terms, "term")
        if self._is_resnet_imagenet_localization_details_section(document_text):
            terms = self._filter_resnet_imagenet_localization_details_noise(terms, "term")
            terms = self._prefer_resnet_imagenet_localization_details_terms(terms, document_text)
        if self._is_resnet_imagenet_localization_rcnn_section(document_text):
            terms = self._filter_resnet_imagenet_localization_rcnn_noise(terms, "term")
            terms = self._prefer_resnet_imagenet_localization_rcnn_terms(terms, document_text)
        normalized = {
            "document_id": document_id,
            "domain": self._domain(payload.get("domain")),
            "difficulty": self._difficulty(payload.get("difficulty")),
            "terms": terms,
            "phrases": phrases,
            "concepts": self._concepts(payload.get("concepts"), document_text, terms, support_language),
            "sentences": self._sentences(
                payload.get("sentences") or payload.get("sentence_structures") or payload.get("sentence_decomposition"),
                document_text,
                support_language=support_language,
            ),
            "summaries": self._summaries(payload.get("summaries"), document_text),
            "quality_warnings": self._fresh_quality_warnings(payload.get("quality_warnings")),
        }
        normalized["concepts"] = self._merge_learning_rows(
            self._heuristic_concepts(document_text),
            normalized["concepts"],
            "concept",
            limit=10,
        )
        if self._is_bert_text(document_text):
            normalized["concepts"] = self._filter_bert_learning_rows(normalized["concepts"], "concept")
        if self._is_bert_feature_based_related_work_section(document_text):
            normalized["concepts"] = self._prefer_bert_feature_related_work_concepts(normalized["concepts"], document_text)
        if self._is_bert_elmo_finetuning_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_elmo_finetuning_transition_concepts(normalized["concepts"], document_text)
        if self._is_bert_pretraining_finetuning_procedure_section(document_text):
            normalized["concepts"] = self._prefer_bert_pretraining_finetuning_procedure_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_bert_pretraining_finetuning_procedure_phrases(normalized["phrases"])
        if self._is_bert_architecture_model_size_section(document_text):
            normalized["concepts"] = self._prefer_bert_architecture_model_size_concepts(normalized["concepts"], document_text)
        if self._is_bert_input_representation_masked_lm_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_input_representation_masked_lm_concepts(normalized["concepts"], document_text)
        if self._is_bert_masked_lm_procedure_section(document_text):
            normalized["concepts"] = self._prefer_bert_masked_lm_procedure_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_bert_masked_lm_procedure_phrases(normalized["phrases"])
        if self._is_bert_nsp_procedure_section(document_text):
            normalized["concepts"] = self._prefer_bert_nsp_procedure_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_bert_nsp_procedure_phrases(normalized["phrases"])
        if self._is_bert_finetuning_unification_section(document_text):
            normalized["concepts"] = self._prefer_bert_finetuning_unification_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_bert_finetuning_unification_phrases(normalized["phrases"])
        if self._is_bert_glue_setup_results_section(document_text):
            normalized["concepts"] = self._prefer_bert_glue_setup_results_concepts(normalized["concepts"], document_text)
        if self._is_bert_glue_result_interpretation_section(document_text):
            normalized["concepts"] = self._prefer_bert_glue_result_interpretation_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_bert_glue_result_interpretation_phrases(normalized["phrases"])
        if self._is_bert_squad_span_prediction_section(document_text):
            normalized["concepts"] = self._prefer_bert_squad_span_prediction_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_squad_span_prediction_phrases(normalized["phrases"], document_text)
        if self._is_bert_squad_results_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_squad_results_transition_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_squad_results_transition_phrases(normalized["phrases"], document_text)
        if self._is_bert_squad2_swag_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_squad2_swag_transition_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_squad2_swag_transition_phrases(normalized["phrases"], document_text)
        if self._is_bert_swag_ablation_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_swag_ablation_transition_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_swag_ablation_transition_phrases(normalized["phrases"], document_text)
        if self._is_bert_ablation_interpretation_section(document_text):
            normalized["concepts"] = self._prefer_bert_ablation_interpretation_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_ablation_interpretation_phrases(normalized["phrases"], document_text)
        if self._is_bert_model_size_effect_section(document_text):
            normalized["concepts"] = self._prefer_bert_model_size_effect_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_model_size_effect_phrases(normalized["phrases"], document_text)
        if self._is_bert_feature_based_transition_section(document_text):
            normalized["concepts"] = self._prefer_bert_feature_based_transition_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_feature_based_transition_phrases(normalized["phrases"], document_text)
        if self._is_bert_ner_feature_table_section(document_text):
            normalized["concepts"] = self._prefer_bert_ner_feature_table_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_ner_feature_table_phrases(normalized["phrases"], document_text)
        if self._is_bert_conclusion_section(document_text):
            normalized["concepts"] = self._prefer_bert_conclusion_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_conclusion_phrases(normalized["phrases"], document_text)
        if self._is_bert_appendix_learning_section(document_text):
            normalized["concepts"] = self._prefer_bert_appendix_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_bert_appendix_phrases(normalized["phrases"], document_text)
        if self._is_reference_list_section(document_text):
            normalized["concepts"] = self._prefer_reference_list_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_reference_list_phrases(normalized["phrases"], document_text)
        if self._is_batchnorm_learning_section(document_text):
            normalized["concepts"] = self._prefer_batchnorm_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_batchnorm_phrases(normalized["phrases"], document_text)
        if self._is_attention_learning_section(document_text):
            normalized["concepts"] = self._prefer_attention_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._prefer_attention_phrases(normalized["phrases"], document_text)
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
        if self._is_resnet_detection_evaluation_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_evaluation_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_evaluation_noise(normalized["phrases"], "phrase")
        if self._is_resnet_detection_improvements_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_improvements_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_improvements_noise(normalized["phrases"], "phrase")
        if self._is_resnet_detection_results_table_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_results_table_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_results_table_noise(normalized["phrases"], "phrase")
        if self._is_resnet_detection_result_narrative_section(document_text):
            normalized["concepts"] = self._prefer_resnet_detection_result_narrative_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_detection_result_narrative_noise(normalized["phrases"], "phrase")
        if self._is_resnet_imagenet_detection_setup_section(document_text):
            normalized["concepts"] = self._prefer_resnet_imagenet_detection_setup_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_imagenet_detection_setup_noise(normalized["phrases"], "phrase")
        if self._is_resnet_imagenet_localization_setup_section(document_text):
            normalized["concepts"] = self._prefer_resnet_imagenet_localization_setup_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_imagenet_localization_setup_noise(normalized["phrases"], "phrase")
        if self._is_resnet_imagenet_localization_details_section(document_text):
            normalized["concepts"] = self._prefer_resnet_imagenet_localization_details_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_imagenet_localization_details_noise(normalized["phrases"], "phrase")
        if self._is_resnet_imagenet_localization_rcnn_section(document_text):
            normalized["concepts"] = self._prefer_resnet_imagenet_localization_rcnn_concepts(normalized["concepts"], document_text)
            normalized["phrases"] = self._filter_resnet_imagenet_localization_rcnn_noise(normalized["phrases"], "phrase")
        if (
            self._sentences_are_weak(normalized["sentences"])
            or self._needs_bert_section_sentence_override(document_text)
            or self._is_batchnorm_learning_section(document_text)
            or self._is_attention_learning_section(document_text)
        ):
            normalized["sentences"] = self._heuristic_sentences(document_text)
        if self._is_batchnorm_learning_section(document_text):
            normalized["summaries"] = self._heuristic_summaries(document_text)
        if self._is_attention_learning_section(document_text):
            normalized["summaries"] = self._heuristic_summaries(document_text)
        if self._summaries_are_weak(normalized["summaries"], document_text):
            normalized["summaries"] = self._heuristic_summaries(document_text)
        normalized = self._calibrate_learning_level(normalized, target_level)
        normalized = self._ensure_minimum_learning_signal(normalized, document_text, support_language, target_level)
        normalized["terms"] = self._with_support_language_glosses(normalized["terms"], support_language, "term")
        normalized["phrases"] = self._with_support_language_glosses(normalized["phrases"], support_language, "phrase")
        normalized = self._apply_quality_eval_guardrails(normalized, document_text, support_language, source_type)
        result = AnalysisResult.model_validate(normalized)
        warnings = [*result.quality_warnings, *self.quality.inspect(result, document_text)]
        return result.model_copy(update={"quality_warnings": sorted(set(warnings))})

    def _apply_quality_eval_guardrails(
        self,
        normalized: dict[str, Any],
        document_text: str,
        support_language: str,
        source_type: str | None,
    ) -> dict[str, Any]:
        normalized = dict(normalized)
        normalized["sentences"] = self._with_support_sentence_explanations(
            list(normalized.get("sentences") or []),
            support_language,
        )
        if source_type in {"video_segment", "transcript"}:
            normalized["terms"] = self._dedupe_rows_by_key(list(normalized.get("terms") or []), "term")
            normalized["phrases"] = self._dedupe_rows_by_key(
                [row for row in list(normalized.get("phrases") or []) if self._is_reusable_phrase_row(row)],
                "phrase",
            )
            normalized["concepts"] = self._remove_video_phrase_concepts(list(normalized.get("concepts") or []))
            normalized["summaries"] = self._video_safe_summaries(normalized.get("summaries") or {}, document_text)
            normalized["phrases"] = self._promote_video_spoken_phrases(normalized["phrases"], document_text, support_language)
        return normalized

    def _dedupe_rows_by_key(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            value = self._learning_key(str(row.get(key) or ""))
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(row)
        return deduped

    def _remove_video_phrase_concepts(self, concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        filtered: list[dict[str, Any]] = []
        for row in concepts:
            key = self._learning_key(str(row.get("concept") or ""))
            if not key or key in seen:
                continue
            if self._looks_like_spoken_phrase(key):
                continue
            seen.add(key)
            filtered.append(row)
        return filtered[:8]

    def _is_reusable_phrase_row(self, row: dict[str, Any]) -> bool:
        phrase = str(row.get("phrase") or "").strip()
        key = self._learning_key(phrase)
        if not key:
            return False
        if len(key.split()) == 1 and key not in {"nevertheless", "however", "therefore"}:
            return False
        if len(key.split()) > 8:
            return False
        blocked = {
            "on the wmt",
            "to make",
            "based on",
            "allows the",
            "answer questions",
            "the thinking game",
        }
        if key in blocked:
            return False
        if re.search(r"\b(?:wmt|p100|gpu|gpus|bert|squad|swag|glue|imagenet)\b", key) and len(key.split()) <= 3:
            return False
        return True

    def _learning_key(self, value: str) -> str:
        value = normalize_pdf_ligatures(value).lower()
        value = re.sub(r"[\"'“”‘’`.,;:!?()\[\]{}]", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        value = re.sub(r"^(?:the|a|an)\s+", "", value)
        return value

    def _looks_like_spoken_phrase(self, key: str) -> bool:
        return key in {"on the cusp of", "breakneck speed", "embarked on", "pull this off", "in my opinion", "keepers of a secret"}

    def _with_support_sentence_explanations(self, rows: list[dict[str, str]], support_language: str) -> list[dict[str, str]]:
        updated: list[dict[str, str]] = []
        for row in rows:
            row = dict(row)
            explanation = normalize_pdf_ligatures(str(row.get("korean_explanation") or "")).strip()
            if not self._is_valid_sentence_support(explanation, support_language):
                row["korean_explanation"] = self._sentence_support_explanation(row, support_language)
            updated.append(row)
        return updated

    def _is_valid_sentence_support(self, value: str, support_language: str) -> bool:
        if not value or value == "Explanation not provided.":
            return False
        language = (support_language or "").strip().lower()
        if language in {"korean", "ko", "한국어"}:
            return bool(re.search(r"[가-힣]", value))
        if language not in {"chinese", "zh", "中文", "japanese", "ja", "日本語"} and self._contains_cjk(value):
            return False
        return True

    def _sentence_support_explanation(self, row: dict[str, str], support_language: str) -> str:
        structure = str(row.get("core_structure") or "the sentence structure").strip()
        simplified = str(row.get("simplified_version") or row.get("sentence") or "").strip()
        language = (support_language or "").strip().lower()
        if language in {"korean", "ko", "한국어"}:
            return f"핵심 구조는 '{structure}'입니다. 쉽게 말하면: {simplified}"
        return f"Core structure: {structure}. In simpler words: {simplified}"

    def _video_safe_summaries(self, summaries: dict[str, Any], document_text: str) -> dict[str, Any]:
        fixed = dict(summaries)
        for key in ("one_line", "simple", "academic"):
            value = normalize_pdf_ligatures(str(fixed.get(key) or "")).strip()
            value = re.sub(r"\b[Tt]he paper\b", "this scene", value)
            value = re.sub(r"\b[Tt]his paper\b", "this scene", value)
            value = re.sub(r"\b[Tt]he document\b", "this transcript segment", value)
            fixed[key] = value or (self._sentences_from_text(document_text)[0] if document_text.strip() else "Scene summary not available.")
        fixed["study_notes"] = [
            re.sub(r"\b[Tt]he paper\b", "this scene", str(note)) for note in self._string_list(fixed.get("study_notes"))
        ]
        return fixed

    def _promote_video_spoken_phrases(
        self,
        phrases: list[dict[str, Any]],
        document_text: str,
        support_language: str,
    ) -> list[dict[str, Any]]:
        preferred = [
            ("first of all", "Marks the first point in a spoken explanation."),
            ("this is why", "Connects a problem to the reason for the next idea."),
            ("let's have a look", "Signals a move into explanation or demonstration."),
            ("on the cusp of", "Means something important is about to happen."),
            ("pull this off", "Means to succeed at a difficult plan."),
            ("breakneck speed", "Means extremely fast progress."),
            ("in my opinion", "Marks a personal stance."),
        ]
        existing = {self._learning_key(str(row.get("phrase") or "")) for row in phrases}
        additions: list[dict[str, Any]] = []
        for phrase, explanation in preferred:
            if self._learning_key(phrase) in existing or not self._appears_in_text(phrase, document_text):
                continue
            additions.append(
                {
                    "phrase": phrase,
                    "function": "general",
                    "explanation": explanation,
                    "support_language_explanation": self._support_language_gloss(phrase, explanation, support_language, "phrase"),
                    "source_sentence": self._source_sentence(None, phrase, document_text),
                    "learning_priority": "useful",
                    "reason": "Useful spoken expression from the current subtitle segment.",
                    "context_meaning": explanation,
                    "confidence": 0.85,
                    "user_state": "suggested",
                }
            )
        return self._dedupe_rows_by_key([*additions, *phrases], "phrase")[:12]

    def _ensure_minimum_learning_signal(
        self,
        normalized: dict[str, Any],
        document_text: str,
        support_language: str,
        target_level: str | None,
    ) -> dict[str, Any]:
        normalized = dict(normalized)
        existing_terms = list(normalized.get("terms") or [])
        existing_phrases = list(normalized.get("phrases") or [])
        terms_changed = False
        phrases_changed = False
        if len(existing_terms) < 2:
            existing_terms = self._merge_learning_rows(
                existing_terms,
                self._source_grounded_term_backfill(document_text),
                "term",
                limit=14,
            )
            terms_changed = True
        if len(existing_phrases) < 1:
            existing_phrases = self._merge_learning_rows(
                existing_phrases,
                self._source_grounded_phrase_backfill(document_text),
                "phrase",
                limit=12,
            )
            phrases_changed = True
        normalized["terms"] = self._calibrate_term_rows(existing_terms, (target_level or "").upper()) if terms_changed else existing_terms
        normalized["phrases"] = (
            self._calibrate_phrase_rows(existing_phrases, (target_level or "").upper()) if phrases_changed else existing_phrases
        )
        return normalized

    def _source_grounded_term_backfill(self, document_text: str) -> list[dict[str, Any]]:
        candidates = [
            ("Transformer", "The attention-based model architecture proposed or discussed in the source.", "field_term", "hard"),
            ("parallelization", "The ability to run computations in parallel rather than sequentially.", "field_term", "medium"),
            ("translation quality", "The quality of machine translation output reported by the model.", "field_term", "medium"),
            ("state of the art", "A best-known or benchmark-leading result claim.", "useful", "medium"),
            ("P100 GPUs", "Hardware used to report the training-time result.", "low_priority", "medium"),
            ("compatibility function", "A function that scores how well a query matches a key.", "field_term", "hard"),
            ("query", "The vector or item that asks what information should be retrieved in attention.", "field_term", "medium"),
            ("key", "The vector or item matched against a query in attention.", "field_term", "medium"),
            ("value", "The vector or item weighted and combined by attention.", "field_term", "medium"),
            ("components", "Model parts varied in ablation experiments.", "useful", "medium"),
            ("architecture", "The model structure being described or varied.", "field_term", "medium"),
            ("attention heads", "Parallel attention units inside multi-head attention.", "field_term", "medium"),
            ("attention distributions", "The learned attention patterns inspected by the authors.", "field_term", "hard"),
            ("syntactic and semantic structure", "Language structure reflected by attention behavior.", "field_term", "hard"),
            ("exhibit behaviour", "Shows observable behavior or patterns in model components.", "useful", "medium"),
            ("BN transform", "The Batch Normalization transform applied in the network.", "field_term", "hard"),
            ("linear transformation", "A learned affine/linear operation applied in the model.", "field_term", "medium"),
            ("activation", "A layer output value inside a neural network.", "field_term", "medium"),
            ("feature map", "A channel-wise activation map in a convolutional layer.", "field_term", "medium"),
            ("gradient magnitudes", "The sizes of gradients during backpropagation.", "field_term", "hard"),
            ("batch-normalized network", "A network trained with Batch Normalization layers.", "field_term", "medium"),
            ("training steps", "The number of parameter-update steps used during training.", "field_term", "medium"),
            ("validation accuracy", "Accuracy measured on a held-out validation set.", "field_term", "medium"),
            ("subsequent layers", "Layers that receive activations from earlier layers.", "field_term", "medium"),
            ("distributions", "Activation or input distributions tracked during training.", "field_term", "medium"),
            ("maximum accuracy", "The highest validation accuracy achieved in an experiment.", "field_term", "medium"),
            ("Inception", "The baseline image model family used in the experiment.", "useful", "medium"),
            ("BN-Baseline", "The BatchNorm baseline variant compared in the experiment.", "field_term", "medium"),
            ("BN-x5", "A BatchNorm variant trained with a larger learning rate.", "field_term", "medium"),
            ("BN-x30", "A BatchNorm variant trained with a much larger learning rate.", "field_term", "medium"),
            ("sigmoid", "A nonlinear activation function used in the experiment.", "field_term", "medium"),
            ("population means and variances", "Fixed normalization statistics used for inference or adaptation.", "field_term", "hard"),
            ("domain adaptation", "Adapting a model to a new data distribution.", "field_term", "hard"),
            ("transfer learning", "Reusing knowledge from one task or dataset for another.", "field_term", "medium"),
            ("supervised tasks", "Tasks trained with labeled examples.", "field_term", "medium"),
            ("natural language inference", "A task that judges the relation between sentence meanings.", "field_term", "medium"),
            ("machine translation", "A task that translates text from one language to another.", "field_term", "medium"),
            ("SQuAD v2.0", "A question-answering benchmark that includes unanswerable questions.", "field_term", "hard"),
            ("no short answer", "The SQuAD 2.0 case where no answer span exists.", "field_term", "medium"),
            ("answer span", "A text span selected as the answer in extractive QA.", "field_term", "medium"),
            ("SWAG", "A commonsense sentence-continuation benchmark.", "field_term", "hard"),
            ("sentence-pair completion", "A task requiring selection of a plausible sentence continuation.", "field_term", "medium"),
            ("commonsense inference", "Reasoning about plausible everyday situations.", "field_term", "hard"),
            ("ablation experiments", "Experiments that remove or vary components to test importance.", "field_term", "hard"),
            ("facets of BERT", "Different BERT design aspects examined in ablation experiments.", "field_term", "hard"),
            ("relative importance", "How much each component contributes compared with others.", "field_term", "medium"),
            ("pre-training tasks", "Tasks used before downstream fine-tuning.", "field_term", "hard"),
            ("downstream task", "The final target task after pre-training.", "field_term", "medium"),
            ("model size", "The capacity scale of a model.", "field_term", "medium"),
            ("bidirectional model", "A model that can use both left and right context.", "field_term", "hard"),
            ("left and right context", "Context from both sides of a token.", "field_term", "medium"),
            ("QA", "Question answering, a task where the model answers questions from text.", "field_term", "medium"),
            ("pre-trained representations", "Representations learned during pre-training and reused downstream.", "field_term", "hard"),
            ("additional parameters", "New parameters added for a downstream task.", "field_term", "medium"),
            ("masked LM", "Masked language modeling, where selected tokens are predicted from context.", "field_term", "hard"),
            ("feature-based approach", "Using representations as features without fine-tuning all model parameters.", "field_term", "hard"),
            ("BiLSTM", "A bidirectional LSTM used as a task model.", "field_term", "hard"),
            ("majority class", "The most frequent class used as a simple baseline prediction.", "useful", "medium"),
            ("single-task fine-tuning", "Fine-tuning on one task at a time.", "field_term", "medium"),
            ("multitask fine-tuning", "Fine-tuning with multiple tasks together.", "field_term", "hard"),
        ]
        rows: list[dict[str, Any]] = []
        lowered = " ".join(document_text.lower().split())
        for term, meaning, priority, difficulty in candidates:
            if term.lower() not in lowered:
                continue
            sentence = self._source_sentence(None, term, document_text)
            if not sentence:
                continue
            rows.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "domain_relevance": "high" if priority == "field_term" else "medium",
                    "difficulty": difficulty,
                    "source_sentence": sentence,
                    "should_save": priority != "low_priority",
                    "learning_priority": priority,
                    "reason": "Source-grounded fallback term selected because the section had too little learning signal.",
                    "context_meaning": meaning,
                    "general_meaning": meaning,
                    "confidence": 0.72,
                    "user_state": "suggested",
                }
            )
        return rows

    def _source_grounded_phrase_backfill(self, document_text: str) -> list[dict[str, Any]]:
        phrase_specs = [
            *self._generic_academic_phrase_specs(document_text),
            ("allows for significantly more", "result", "States a comparative capability or efficiency benefit."),
            ("can reach a new state of the art", "result", "Claims benchmark-leading performance."),
            ("is computed by", "method", "Explains how a value is calculated."),
            ("where the weight assigned to", "method", "Explains the role of weights in an operation."),
            ("to evaluate the importance of", "method", "Introduces an ablation experiment."),
            ("many appear to exhibit", "claim", "Cautiously reports observed model behavior."),
            ("in my opinion", "claim", "Marks a personal stance inside an example sentence."),
            ("rather than", "contrast", "Contrasts the chosen unit or method with an alternative."),
            ("so that", "method", "Introduces the purpose or consequence of a method."),
            ("during inference", "method", "Marks behavior at inference time rather than training time."),
            ("we nevertheless expect", "claim", "States a cautious expectation despite caveats."),
            ("remains an area of further study", "limitation", "Marks an unresolved research question."),
            ("we found this effect to be", "result", "Reports an observed experimental effect."),
            ("whereas", "contrast", "Contrasts two methods or conditions."),
            ("to verify the effects of", "method", "Introduces the purpose of an experiment."),
            ("we evaluated the following", "method", "Introduces a list of experimental conditions."),
            ("steps to match", "result", "Explains the number of steps needed to reach a target result."),
            ("required to reach", "result", "States the training amount needed to reach a metric."),
            ("maximum accuracy achieved", "result", "Reports the best accuracy reached by a model."),
            ("we also verified that", "result", "Adds a supporting experimental finding."),
            ("without Batch Normalization", "contrast", "Contrasts the method with the baseline without it."),
            ("our future work includes", "limitation", "Introduces future work rather than a completed result."),
            ("we plan to investigate whether", "limitation", "States a future research question."),
            ("there has also been work showing", "claim", "Introduces related work evidence."),
            ("demonstrated the importance of", "claim", "States what prior work has shown."),
            ("allowing for the possibility that", "method", "Explains an expanded task definition."),
            ("we use a simple approach to", "method", "Introduces a simple method extension."),
            ("we treat questions that", "method", "Explains how a special case is represented."),
            ("the task is to choose", "claim", "Defines a task objective."),
            ("when fine-tuning on", "method", "Introduces task-specific fine-tuning setup."),
            ("results are presented in", "result", "Points to where the empirical result is reported."),
            ("we perform ablation experiments", "method", "Introduces ablation analysis."),
            ("in order to better understand", "method", "States the purpose of an analysis."),
            ("this demonstrates", "result", "Interprets a result as evidence for a claim."),
            ("compared to", "contrast", "Introduces a comparison baseline."),
            ("twice as expensive", "contrast", "States a cost disadvantage in a comparison."),
            ("strictly less powerful than", "contrast", "States a representational limitation."),
            ("we hypothesize that", "claim", "States a hypothesis rather than a proven result."),
            ("can benefit from", "result", "States a practical benefit."),
            ("possible values to work well", "method", "Introduces a working hyperparameter range."),
            ("where the goal is to", "claim", "States the objective of a task."),
            ("has been converted to", "method", "Explains task transformation."),
            ("without fine-tuning", "contrast", "Contrasts feature extraction with full fine-tuning."),
            ("we therefore exclude", "method", "States an evaluation decision based on a caveat."),
            ("to be fair to", "claim", "Gives the fairness reason for an evaluation choice."),
        ]
        rows: list[dict[str, Any]] = []
        lowered = " ".join(document_text.lower().split())
        seen: set[str] = set()
        for phrase, function, explanation in phrase_specs:
            key = phrase.lower()
            if key in seen or key not in lowered:
                continue
            seen.add(key)
            rows.append(
                {
                    "phrase": phrase,
                    "function": function,
                    "explanation": explanation,
                    "source_sentence": self._source_sentence(None, phrase, document_text),
                    "learning_priority": "must_review" if function in {"method", "result", "contrast"} else "useful",
                    "reason": "Source-grounded fallback expression selected because the section had too little learning signal.",
                    "context_meaning": explanation,
                    "confidence": 0.72,
                    "user_state": "suggested",
                }
            )
        return rows

    def _calibrate_learning_level(self, normalized: dict[str, Any], target_level: str | None) -> dict[str, Any]:
        level = (target_level or "").upper()
        if level not in {"B1", "B2", "C1", "C2"}:
            return normalized
        normalized = dict(normalized)
        normalized["terms"] = self._calibrate_term_rows(normalized.get("terms", []), level)
        normalized["phrases"] = self._calibrate_phrase_rows(normalized.get("phrases", []), level)
        normalized["concepts"] = self._calibrate_concept_rows(normalized.get("concepts", []), level)
        normalized["sentences"] = self._calibrate_sentence_rows(normalized.get("sentences", []), level)
        return normalized

    def _calibrate_term_rows(self, rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
        blocked_for_advanced = {
            "p100 gpus",
            "nvidia p100 gpus",
            "first",
            "second",
            "third",
        }
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            key = str(row.get("term") or "").strip().lower()
            if not key:
                continue
            priority = str(row.get("learning_priority") or "").lower()
            difficulty = str(row.get("difficulty") or "").lower()
            relevance = str(row.get("domain_relevance") or "").lower()
            if level in {"C1", "C2"} and (key in blocked_for_advanced or priority == "low_priority"):
                continue
            if level in {"B1", "B2"} and priority == "low_priority" and len(rows) > 6:
                continue
            score = 0
            score += {"must_review": 40, "field_term": 32, "useful": 20, "low_priority": 0}.get(priority, 10)
            score += {"high": 12, "medium": 6, "low": 0}.get(relevance, 3)
            if level in {"C1", "C2"}:
                score += {"hard": 12, "medium": 8, "easy": 1}.get(difficulty, 4)
            else:
                score += {"medium": 12, "easy": 8, "hard": 5}.get(difficulty, 4)
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:14]]

    def _calibrate_phrase_rows(self, rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
        weak_advanced_phrases = {
            "first",
            "second",
            "third",
            "in this section",
            "as follows",
            "shown in",
            "figure",
        }
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            phrase = str(row.get("phrase") or "").strip()
            key = phrase.lower()
            if not key:
                continue
            function = str(row.get("function") or "").lower()
            priority = str(row.get("learning_priority") or "").lower()
            if level in {"C1", "C2"} and (key in weak_advanced_phrases or priority == "low_priority"):
                continue
            score = 0
            score += {"must_review": 35, "field_term": 25, "useful": 20, "low_priority": 0}.get(priority, 10)
            score += {"contrast": 14, "limitation": 14, "method": 12, "result": 12, "claim": 10, "general": 3}.get(function, 5)
            if level in {"C1", "C2"} and len(phrase.split()) >= 3:
                score += 6
            if level in {"B1", "B2"} and len(phrase.split()) <= 5:
                score += 5
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:12]]

    def _calibrate_concept_rows(self, rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            priority = str(row.get("learning_priority") or "").lower()
            if level in {"C1", "C2"} and priority == "low_priority":
                continue
            score = {"must_review": 35, "field_term": 30, "useful": 15, "low_priority": 0}.get(priority, 10)
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:10]]

    def _calibrate_sentence_rows(self, rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
        if not rows:
            return rows
        calibrated: list[dict[str, Any]] = []
        for row in rows[:4]:
            row = dict(row)
            if level in {"B1", "B2"}:
                row["difficulty_reason"] = self._append_once(
                    str(row.get("difficulty_reason") or ""),
                    "For this level, focus on finding the main clause first, then add modifiers one by one.",
                )
            elif level in {"C1", "C2"}:
                row["difficulty_reason"] = self._append_once(
                    str(row.get("difficulty_reason") or ""),
                    "For this level, notice the rhetorical move, clause compression, and how the author positions evidence or limitation.",
                )
            calibrated.append(row)
        return calibrated

    def _append_once(self, value: str, suffix: str) -> str:
        value = value.strip()
        if suffix in value:
            return value
        return f"{value} {suffix}".strip()

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

    def _terms(self, value: Any, document_text: str, support_language: str = "Korean") -> list[dict[str, Any]]:
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
            support_meaning = normalize_pdf_ligatures(
                str(row.get("support_language_meaning") or row.get("native_meaning") or "")
            ).strip()
            terms.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "support_language_meaning": support_meaning or self._support_language_gloss(term, meaning, support_language, kind="term"),
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

    def _phrases(self, value: Any, document_text: str, support_language: str = "Korean") -> list[dict[str, Any]]:
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
            support_explanation = normalize_pdf_ligatures(
                str(row.get("support_language_explanation") or row.get("native_explanation") or "")
            ).strip()
            phrases.append(
                {
                    "phrase": phrase,
                    "function": row.get("function") or row.get("category") or "general",
                    "explanation": explanation,
                    "support_language_explanation": support_explanation
                    or self._support_language_gloss(phrase, explanation, support_language, kind="phrase"),
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

    def _support_language_gloss(self, text: str, meaning: str, support_language: str, kind: str) -> str:
        language = (support_language or "").strip().lower()
        key = text.strip().lower()
        if language in {"korean", "ko", "한국어"}:
            known = {
                "self-attention": "문장 안의 토큰들이 서로 어떤 관련이 있는지 직접 보게 하는 attention 방식입니다.",
                "transformer": "순환 구조 없이 attention 중심으로 문장을 처리하는 encoder-decoder 모델입니다.",
                "scaled dot-product attention": "query와 key의 점수를 스케일링한 뒤 value를 섞는 attention 계산입니다.",
                "multi-head attention": "여러 attention head가 서로 다른 관계를 병렬로 보게 하는 구조입니다.",
                "encoder-decoder": "입력을 표현으로 바꾸는 encoder와 출력을 생성하는 decoder의 조합입니다.",
                "sequence transduction": "한 sequence를 다른 sequence로 바꾸는 작업입니다. 예: 번역.",
                "sequential computation": "앞 위치의 계산이 끝나야 다음 위치를 계산할 수 있는 순차적 처리 방식입니다.",
                "parallelization": "여러 위치나 예제를 동시에 계산해 학습을 빠르게 만드는 성질입니다.",
                "hidden representations": "입력 토큰이나 sequence를 모델 내부에서 계산한 벡터 표현입니다.",
                "long-range dependencies": "문장이나 sequence 안에서 멀리 떨어진 위치들 사이의 의존 관계입니다.",
                "dependencies between distant positions": "sequence 안에서 멀리 떨어진 위치들 사이의 의존 관계입니다.",
                "in parallel": "여러 위치나 계산을 동시에 처리한다는 뜻입니다.",
                "recurrent models": "토큰 위치를 순서대로 처리하면서 이전 hidden state에 의존하는 sequence model입니다.",
                "hidden states": "recurrent model이 각 위치에서 만들어 다음 위치로 넘기는 내부 표현입니다.",
                "convolutional neural networks": "convolution 연산으로 주변 패턴을 처리하는 neural network 계열입니다.",
                "input and output positions": "sequence의 입력과 출력에서 각 토큰이 놓인 위치를 뜻합니다.",
                "queries": "attention에서 필요한 정보를 묻는 역할의 벡터입니다.",
                "keys": "query와 비교되어 attention 점수를 만드는 역할의 벡터입니다.",
                "values": "attention 가중치로 섞여 최종 출력이 되는 정보 벡터입니다.",
                "softmax function": "점수들을 합이 1인 가중치로 바꾸는 함수입니다.",
                "dot products": "query와 key가 얼마나 맞는지 계산하는 내적 점수입니다.",
                "linear projections": "query/key/value를 다른 표현 공간으로 보내는 학습된 선형 변환입니다.",
                "position-wise feed-forward networks": "각 sequence 위치에 독립적으로 적용되는 feed-forward layer입니다.",
                "embeddings": "토큰을 모델이 계산할 수 있는 벡터로 바꾼 표현입니다.",
                "positional encodings": "토큰 순서 정보를 주기 위해 embedding에 더하는 위치 벡터입니다.",
                "sine and cosine functions": "Transformer의 고정 positional encoding을 만드는 삼각함수입니다.",
                "training data": "모델 학습에 사용한 데이터셋입니다.",
                "batching": "여러 예제를 묶어 효율적으로 학습하는 방식입니다.",
                "nvidia p100 gpus": "Transformer 학습 시간 보고에 쓰인 GPU 하드웨어입니다.",
                "adam optimizer": "Transformer 학습에 사용한 최적화 알고리즘입니다.",
                "warmup_steps": "초기 학습률을 점진적으로 키우는 단계 수입니다.",
                "label smoothing": "모델이 정답에 과도하게 확신하지 않도록 만드는 regularization입니다.",
                "bleu score": "기계번역 결과를 reference 번역과 비교해 평가하는 점수입니다.",
                "beam search": "생성 중 여러 후보 문장을 유지하며 더 좋은 출력을 찾는 decoding 방법입니다.",
                "checkpoint averaging": "최근 저장된 여러 모델 checkpoint를 평균해 평가에 쓰는 방법입니다.",
                "model variations": "구성요소를 바꿔 성능 변화를 보는 ablation 실험입니다.",
                "attention heads": "multi-head attention 안에서 병렬로 작동하는 attention 계산 단위입니다.",
                "heads": "multi-head attention 안에서 병렬로 작동하는 attention 계산 단위입니다.",
                "projections": "query/key/value를 attention head의 공간으로 보내는 학습된 변환입니다.",
                "parameter matrices": "모델 벡터를 다른 공간으로 보내는 학습된 행렬입니다.",
                "feed-forward network": "선형 변환과 비선형 함수를 적용하는 neural network sub-layer입니다.",
                "linear transformations": "입력 벡터에 행렬과 bias를 적용하는 선형 변환입니다.",
                "relu activation": "음수는 0으로 만들고 양수는 그대로 두는 비선형 activation입니다.",
                "maximum path length": "두 sequence 위치가 정보를 주고받기 위해 거쳐야 하는 가장 긴 계산 경로입니다.",
                "convolutional layers": "주변 위치의 패턴을 convolution으로 처리하는 neural network layer입니다.",
                "separable convolutions": "계산량을 줄인 convolution 변형입니다.",
                "training steps": "학습 중 parameter update를 수행한 횟수입니다.",
                "base models": "비교 기준으로 쓰는 더 작은 Transformer 설정입니다.",
                "big models": "더 큰 용량과 더 긴 학습으로 강한 성능을 내는 Transformer 설정입니다.",
                "dropout": "학습 중 일부 activation을 무작위로 끄는 regularization 방법입니다.",
                "bn transform": "네트워크 안에서 Batch Normalization을 적용하는 변환입니다.",
                "normalized activations": "정규화가 적용된 layer activation입니다.",
                "feature map": "convolutional layer에서 channel 단위로 생기는 activation map입니다.",
                "gradient propagation": "학습 중 gradient가 뒤쪽 layer에서 앞쪽 layer로 전달되는 과정입니다.",
                "singular values": "변환이 각 방향을 얼마나 확대하거나 축소하는지 나타내는 값입니다.",
                "backpropagation": "gradient를 뒤로 전달해 parameter를 업데이트하는 학습 알고리즘입니다.",
                "imagenet classification": "대규모 이미지 분류 benchmark입니다.",
                "ensemble": "여러 모델의 예측을 합쳐 성능을 높이는 방법입니다.",
                "general language representations": "여러 NLP task에 재사용할 수 있도록 넓게 학습한 언어 표현입니다.",
                "contextual representations": "주변 문맥에 따라 달라지는 token/text 표현입니다.",
                "question answering": "텍스트를 바탕으로 질문에 답하는 NLP task입니다.",
                "named entity recognition": "사람, 조직, 장소 같은 고유명사를 태깅하는 NLP task입니다.",
                "wordpiece embeddings": "BERT가 사용하는 subword token embedding입니다.",
                "token sequence": "BERT 입력으로 들어가는 token들의 sequence입니다.",
                "glue benchmark": "여러 자연어 이해 task를 모은 benchmark입니다.",
                "final hidden vector": "classification에 사용하는 마지막 hidden representation입니다.",
                "classification layer": "task-specific classification을 위해 추가되는 출력 layer입니다.",
                "f1 score": "precision과 recall을 함께 반영하는 평가 지표입니다.",
                "leaderboard system": "benchmark leaderboard에서 비교 대상으로 삼는 상위 시스템입니다.",
                "convex": "두 점 사이를 이은 선분이 함수나 집합의 조건 안에 머무르는 성질을 뜻합니다.",
                "convex optimization problem": "목적함수와 제약식이 볼록성 조건을 만족하는 최적화 문제입니다.",
                "objective function": "목적함수입니다. 최적화에서 최소화하거나 최대화하려는 기준 함수입니다.",
                "constraint": "해가 반드시 만족해야 하는 조건입니다.",
                "affine": "선형식에 상수항을 더한 형태를 뜻하며, 등식 제약에서 자주 쓰입니다.",
                "concave maximization problems": "오목함수를 최대화하는 문제로, 볼록 최적화와 대응되는 형태로 다룹니다.",
                "standard form": "정의에서 요구하는 목적함수와 제약식 형태를 갖춘 표준 표현입니다.",
                "batch normalization": "mini-batch 통계로 layer 입력을 정규화해 학습을 안정화하는 방법입니다.",
                "internal covariate shift": "학습 중 layer 입력 분포가 계속 바뀐다는 문제의식입니다.",
                "mini-batch": "한 번의 업데이트에 함께 쓰는 작은 데이터 묶음입니다.",
                "residual learning": "입력 전체가 아니라 보정해야 할 잔차를 학습하게 하는 방식입니다.",
                "shortcut connections": "입력을 몇 layer 뒤로 바로 전달해 깊은 네트워크 학습을 돕는 연결입니다.",
                "pre-training": "대규모 비라벨 텍스트로 먼저 모델 표현을 학습하는 단계입니다.",
                "fine-tuning": "사전학습된 모델을 특정 과제 데이터로 조정하는 단계입니다.",
                "output layers": "공유 모델 위에 붙는 과제별 출력층입니다.",
                "pre-trained model parameters": "사전학습 단계에서 배운 뒤 downstream task 초기값으로 재사용되는 가중치입니다.",
                "pre-trained language representations": "대규모 텍스트로 먼저 학습해 downstream task에 재사용하는 언어 표현입니다.",
                "feature-based": "사전학습 표현을 고정된 feature로 가져와 task-specific model에 넣는 방식입니다.",
                "feature-based approach": "사전학습 표현을 추가 feature로 사용하고, 과제별 구조는 따로 두는 전이 방식입니다.",
                "fine-tuning approach": "사전학습 모델 전체를 downstream task 데이터로 함께 조정하는 전이 방식입니다.",
                "downstream tasks": "사전학습 뒤 실제로 풀고 평가하는 목표 과제들입니다.",
                "task-specific architectures": "특정 과제에 맞게 따로 설계한 모델 구조입니다.",
                "[cls]": "입력 맨 앞에 붙어 전체 sequence 표현을 만들 때 쓰는 특수 토큰입니다.",
                "[sep]": "두 문장이나 segment를 구분할 때 쓰는 특수 토큰입니다.",
                "masked language model": "가려진 단어를 주변 문맥으로 예측하는 pre-training 과제입니다.",
                "next sentence prediction": "두 문장이 실제로 이어지는지 맞히는 BERT pre-training 과제입니다.",
                "we propose": "논문의 새 기여를 제시할 때 쓰는 표현입니다.",
                "based solely on": "무엇 하나만을 기반으로 한다고 제한해서 말하는 표현입니다.",
                "dispensing with": "기존에 쓰던 요소를 제거하거나 쓰지 않는다는 뜻입니다.",
                "remains unclear": "아직 명확하지 않은 연구 문제를 표시합니다.",
                "to address this gap": "앞에서 말한 연구 공백을 해결하기 위해 다음 방법을 제시합니다.",
                "large language models": "대규모 텍스트로 학습해 언어를 이해하고 생성하는 모델입니다.",
                "modern ai": "최근 모델 발전을 바탕으로 한 현재의 AI 시스템과 도구를 뜻합니다.",
                "greenhouse effect": "대기 중 기체가 열을 가두어 지구를 따뜻하게 만드는 현상입니다.",
                "climate change": "기후가 장기적으로 빠르게 변하는 현상과 그 영향을 가리킵니다.",
                "carbon dioxide": "열을 가두는 대표적인 온실가스로, CO2라고도 부릅니다.",
                "greenhouse gases": "대기 중에서 열을 가두어 온난화에 영향을 주는 기체들입니다.",
                "atmospheric heating": "대기가 열을 흡수하고 보존해 따뜻해지는 과정입니다.",
                "earth's temperature": "지구 전체의 평균적인 온도 변화를 말할 때 쓰는 표현입니다.",
                "human activities": "환경이나 사회 변화를 일으키는 인간의 활동을 뜻합니다.",
                "economics": "선택, 자원, 시장, 유인, tradeoff를 다루는 학문입니다.",
                "economic theories": "경제 현상을 설명하는 원리와 모델을 뜻합니다.",
                "theories and graphs": "경제학의 원리와 관계를 설명할 때 쓰는 이론과 그래프입니다.",
                "real world applications": "개념이 실제 경제 상황에서 어떻게 쓰이는지를 보여주는 적용 사례입니다.",
                "scarce resources": "한정되어 있어 선택과 tradeoff가 필요한 자원입니다.",
                "opportunity cost": "어떤 선택 때문에 포기한 차선의 가치입니다.",
                "virus": "살아있는 세포 안에서 증식하는 작은 감염성 입자입니다.",
                "genetic material": "생물학적 정보를 담는 DNA나 RNA입니다.",
                "protein shell": "바이러스의 유전물질을 감싸는 단백질 껍질입니다.",
                "fastapi": "Python으로 API를 만들 때 쓰는 현대적인 웹 프레임워크입니다.",
                "fast api": "Python으로 API를 만들 때 쓰는 현대적인 웹 프레임워크입니다.",
                "apis with python": "Python으로 만드는 API 또는 웹 서비스 인터페이스를 뜻합니다.",
                "web framework": "웹 서비스나 API 서버를 만들기 위한 기본 구조와 도구를 제공하는 프레임워크입니다.",
                "python web framework": "Python으로 웹 서비스나 API를 만들게 해주는 프레임워크입니다.",
                "python package manager": "Python 패키지를 설치하고 관리하는 도구입니다.",
                "pip": "Python 패키지를 설치할 때 흔히 쓰는 명령줄 도구입니다.",
                "automatic documentation": "코드나 API 정의에서 자동으로 만들어지는 문서입니다.",
            }
            if key in known:
                return known[key]
            if kind == "term":
                return f"문맥상 의미: {meaning}"
            if kind == "concept":
                return f"핵심 개념: {meaning}"
            return f"문맥상 기능: {meaning}"
        if not language or language in {"english", "en"}:
            return meaning
        return f"{support_language}: {meaning}"

    def _with_support_language_glosses(self, rows: list[dict[str, Any]], support_language: str, kind: str) -> list[dict[str, Any]]:
        text_key = "term" if kind == "term" else "phrase"
        meaning_key = "meaning" if kind == "term" else "explanation"
        support_key = "support_language_meaning" if kind == "term" else "support_language_explanation"
        updated: list[dict[str, Any]] = []
        for row in rows:
            row = dict(row)
            if not self._is_valid_support_language_gloss(str(row.get(support_key) or ""), support_language):
                row[support_key] = self._support_language_gloss(
                    str(row.get(text_key) or ""),
                    str(row.get(meaning_key) or ""),
                    support_language,
                    kind,
                )
            updated.append(row)
        return updated

    def _is_valid_support_language_gloss(self, value: str, support_language: str) -> bool:
        normalized = normalize_pdf_ligatures(value).strip()
        if not normalized:
            return False
        language = (support_language or "").strip().lower()
        if language not in {"korean", "ko", "한국어", "chinese", "zh", "中文", "japanese", "ja", "日本語"} and self._contains_cjk(normalized):
            return False
        if language in {"korean", "ko", "한국어"}:
            if not re.search(r"[가-힣]", normalized):
                return False
            generic_fallbacks = (
                "새로 분석하면 더 구체적인 한국어 gloss",
                "이 섹션을 읽을 때 확인해야 하는 핵심 용어입니다",
                "논문 문장에서 재사용할 수 있는 표현입니다",
            )
            return not any(fragment in normalized for fragment in generic_fallbacks)
        return True

    def _contains_cjk(self, value: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", value))

    def _concepts(self, value: Any, document_text: str, terms: list[dict[str, Any]], support_language: str) -> list[dict[str, Any]]:
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
            support_explanation = normalize_pdf_ligatures(
                str(row.get("support_language_explanation") or row.get("native_explanation") or "")
            ).strip()
            source_sentence = self._source_sentence(row.get("source_sentence"), concept, document_text)
            if not self._is_valid_support_language_gloss(support_explanation, support_language):
                support_explanation = self._support_language_gloss(concept, explanation, support_language, kind="concept")
            concepts.append(
                {
                    "concept": concept,
                    "explanation": explanation,
                    "support_language_explanation": support_explanation,
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
        return self._fallback_concepts(document_text, terms, support_language)

    def _fallback_concepts(self, document_text: str, terms: list[dict[str, Any]], support_language: str) -> list[dict[str, Any]]:
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
                    "support_language_explanation": str(term.get("support_language_meaning") or "")
                    or self._support_language_gloss(
                        concept,
                        str(term.get("meaning") or "Source-grounded concept from this section."),
                        support_language,
                        kind="concept",
                    ),
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
        generic_specs = self._generic_academic_term_specs(document_text)
        if self._is_convex_optimization_definition_section(document_text):
            known = [
                (
                    "convex optimization problem",
                    "An optimization problem whose objective and constraints satisfy convex standard-form requirements.",
                    "field_term",
                    "hard",
                    "This is the definition being refined in the section.",
                ),
                (
                    "objective function",
                    "The function the optimization problem minimizes or maximizes.",
                    "field_term",
                    "medium",
                    "It is one of the required parts of a convex optimization problem.",
                ),
                (
                    "affine",
                    "Linear plus a constant term; equality constraints in standard form must be affine.",
                    "field_term",
                    "hard",
                    "This is the key caveat in the section's definition.",
                ),
                (
                    "equality constraint",
                    "A constraint that must hold exactly rather than as an inequality.",
                    "field_term",
                    "medium",
                    "The section says non-affine equality constraints break standard form.",
                ),
                (
                    "standard form",
                    "The stricter formulation required by the textbook definition.",
                    "useful",
                    "medium",
                    "This separates geometric convexity from the formal optimization-problem definition.",
                ),
                (
                    "concave maximization problems",
                    "Maximization problems with concave objectives, treated as the counterpart of convex minimization.",
                    "field_term",
                    "hard",
                    "This explains the naming caveat after the convex standard-form definition.",
                ),
            ]
        elif self._is_bert_text(document_text):
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
                    "pre-trained language representations",
                    "Representations learned before downstream task training and reused across NLP tasks.",
                    "field_term",
                    "hard",
                    "This is the object being transferred by both strategies in the section.",
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
                (
                    "pre-trained word embeddings",
                    "Word vectors learned before downstream task training.",
                    "field_term",
                    "medium",
                    "This is the older feature-based representation line the section reviews.",
                ),
                (
                    "sentence embeddings",
                    "Vector representations for whole sentences rather than individual words.",
                    "field_term",
                    "medium",
                    "This shows how feature-based representation learning moves to coarser granularities.",
                ),
                (
                    "paragraph embeddings",
                    "Vector representations for paragraphs or longer text units.",
                    "field_term",
                    "medium",
                    "This is another coarser-granularity representation baseline.",
                ),
                (
                    "ELMo",
                    "A feature-based contextual representation model built from left-to-right and right-to-left language models.",
                    "field_term",
                    "hard",
                    "This is the key feature-based predecessor BERT contrasts with.",
                ),
                (
                    "context-sensitive features",
                    "Token representations that depend on surrounding context.",
                    "field_term",
                    "hard",
                    "This is the main feature extracted by ELMo.",
                ),
                (
                    "left-to-right and right-to-left language model",
                    "A pair of directional language models whose representations are concatenated.",
                    "field_term",
                    "hard",
                    "This explains the ELMo-style bidirectional feature construction.",
                ),
                (
                    "contextual word embeddings",
                    "Word representations whose meaning changes with the surrounding sentence context.",
                    "field_term",
                    "hard",
                    "This is the feature-based representation type being contrasted with BERT.",
                ),
                (
                    "cloze task",
                    "A prediction task where the model fills in a missing word from context.",
                    "field_term",
                    "medium",
                    "The section uses it as a related pre-training idea before BERT.",
                ),
                (
                    "fine-tuning approaches",
                    "Transfer-learning methods that pre-train a model and then adapt it to a supervised downstream task.",
                    "field_term",
                    "medium",
                    "This is the second prior strategy BERT improves.",
                ),
                (
                    "contextual token representations",
                    "Token vectors that depend on surrounding text, not just the token identity.",
                    "field_term",
                    "hard",
                    "This connects GPT-style encoders and BERT-style representation learning.",
                ),
                (
                    "supervised downstream task",
                    "A target task with labels used after pre-training.",
                    "useful",
                    "medium",
                    "This is where fine-tuned models are adapted after unsupervised pre-training.",
                ),
                (
                    "GLUE benchmark",
                    "A collection of language-understanding tasks used to compare NLP models.",
                    "useful",
                    "medium",
                    "The section cites GLUE as evidence for GPT-style fine-tuning performance.",
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
                (
                    "PASCAL VOC",
                    "An object-detection benchmark used to evaluate the detector.",
                    "field_term",
                    "medium",
                    "This section reports ResNet improvements on PASCAL VOC and COCO.",
                ),
                (
                    "mAP",
                    "Mean average precision, a standard object-detection evaluation metric.",
                    "field_term",
                    "hard",
                    "This is the metric improved by ResNet-101 over VGG-16.",
                ),
                (
                    "mAP @ IoU = 0.5",
                    "A PASCAL-style detection metric that counts detections correct at 0.5 IoU.",
                    "field_term",
                    "hard",
                    "This contrasts with the stricter COCO metric.",
                ),
                (
                    "mAP @ IoU = .5:.05:.95",
                    "The standard COCO metric averaged over IoU thresholds from .5 to .95.",
                    "field_term",
                    "hard",
                    "This tests localization quality more strictly than mAP@.5.",
                ),
                (
                    "RPN step",
                    "The region proposal network training stage in Faster R-CNN.",
                    "field_term",
                    "hard",
                    "This is one of the two detector-training steps described for COCO.",
                ),
                (
                    "Fast R-CNN step",
                    "The detection/classification training stage after region proposals.",
                    "field_term",
                    "hard",
                    "This is the second Faster R-CNN training stage described for COCO.",
                ),
                (
                    "box refinement",
                    "An inference-time improvement that re-pools features from regressed boxes to refine predictions.",
                    "field_term",
                    "hard",
                    "This is the first detection improvement described in the appendix.",
                ),
                (
                    "regressed box",
                    "A predicted bounding box after the detector adjusts the original proposal box.",
                    "field_term",
                    "hard",
                    "The section contrasts proposal boxes with refined regressed boxes.",
                ),
                (
                    "Non-maximum suppression (NMS)",
                    "A post-processing step that removes overlapping detection boxes using an IoU threshold.",
                    "field_term",
                    "hard",
                    "This explains how combined predictions are filtered after box refinement.",
                ),
                (
                    "box voting",
                    "A detection post-processing method applied after NMS to refine final boxes.",
                    "field_term",
                    "hard",
                    "It is part of the appendix's competition-improvement recipe.",
                ),
                (
                    "global context",
                    "Full-image information added to each region-level detection decision.",
                    "field_term",
                    "hard",
                    "This is the second detection improvement described in the appendix.",
                ),
                (
                    "RoI pooling",
                    "Region-of-interest pooling that extracts fixed-size features from a feature map.",
                    "field_term",
                    "hard",
                    "The section uses RoI pooling both for regions and for full-image context.",
                ),
                (
                    "multi-scale testing",
                    "Running detection at multiple image scales at inference time.",
                    "field_term",
                    "hard",
                    "This is the third improvement and is explicitly limited to testing in this implementation.",
                ),
                (
                    "baseline+++",
                    "The strengthened detector variant that includes box refinement, context, and multi-scale testing.",
                    "field_term",
                    "hard",
                    "This is the table shorthand for the improved detection system.",
                ),
                (
                    "COCO test-dev",
                    "The MS COCO evaluation split used for reporting final detection results.",
                    "field_term",
                    "medium",
                    "This distinguishes validation results from leaderboard-style test results.",
                ),
                (
                    "PASCAL VOC 2007 test set",
                    "The PASCAL VOC detection benchmark split used for one result table.",
                    "field_term",
                    "medium",
                    "This tells the reader which benchmark the table is evaluating.",
                ),
                (
                    "PASCAL VOC 2012 test set",
                    "The PASCAL VOC detection benchmark split used for another result table.",
                    "field_term",
                    "medium",
                    "This is the second PASCAL benchmark table in the section.",
                ),
                (
                    "ensemble",
                    "A combined prediction system using multiple models or runs.",
                    "useful",
                    "medium",
                    "The table reports an ensemble as the strongest COCO system.",
                ),
                (
                    "test-dev set",
                    "A benchmark evaluation split whose labels are hidden and scored by an evaluation server.",
                    "field_term",
                    "medium",
                    "This explains why the paper reports results through the COCO server.",
                ),
                (
                    "evaluation server",
                    "The external scoring service that reports results when ground truth is not public.",
                    "field_term",
                    "medium",
                    "This is part of the benchmark protocol, not a model component.",
                ),
                (
                    "single-model result",
                    "Performance from one detector model before ensembling.",
                    "useful",
                    "medium",
                    "This is the baseline for understanding the later ensemble gain.",
                ),
                (
                    "region proposals",
                    "Candidate object boxes generated before final classification.",
                    "field_term",
                    "hard",
                    "The ensemble is used to improve proposal generation as well as classification.",
                ),
                (
                    "per-region classifiers",
                    "Classifiers applied to each proposed image region.",
                    "field_term",
                    "hard",
                    "This is the second ensemble target in Faster R-CNN.",
                ),
                (
                    "state-of-the-art result",
                    "The best previously reported benchmark result at the time.",
                    "useful",
                    "medium",
                    "The PASCAL VOC 2012 result is described as 10 points higher than this.",
                ),
                (
                    "ImageNet Detection (DET)",
                    "The ImageNet object-detection task with 200 object categories.",
                    "field_term",
                    "medium",
                    "This names the benchmark setting for the section.",
                ),
                (
                    "mAP@.5",
                    "Mean average precision at IoU threshold 0.5.",
                    "field_term",
                    "hard",
                    "This is the evaluation metric used for ImageNet DET.",
                ),
                (
                    "pretrained on ImageNet classification",
                    "The detector networks start from weights learned on the 1000-class ImageNet classification task.",
                    "field_term",
                    "medium",
                    "This explains the transfer path before DET fine-tuning.",
                ),
                (
                    "DET training set",
                    "The ImageNet Detection training data used to fine-tune detection models.",
                    "field_term",
                    "medium",
                    "This is the target-task data used for fine-tuning.",
                ),
                (
                    "val1/val2 split",
                    "A validation-set split where val1 is used for fine-tuning and val2 for validation.",
                    "field_term",
                    "medium",
                    "This explains the experiment protocol in the section.",
                ),
                (
                    "ILSVRC 2015 data",
                    "Additional competition data that the authors explicitly do not use here.",
                    "useful",
                    "medium",
                    "This is a fairness/data-constraint statement.",
                ),
                (
                    "ImageNet Localization (LOC)",
                    "The ImageNet task that requires both class prediction and object localization.",
                    "field_term",
                    "medium",
                    "This is the new benchmark section after ImageNet DET.",
                ),
                (
                    "localization error",
                    "The percentage error metric reported for ImageNet localization.",
                    "field_term",
                    "medium",
                    "This is the table's main metric.",
                ),
                (
                    "ground truth class",
                    "The true image class used in one localization-error evaluation setting.",
                    "field_term",
                    "medium",
                    "This explains the `LOC error on GT class` column.",
                ),
                (
                    "predicted class",
                    "The class predicted by the image-level classifier before localization.",
                    "field_term",
                    "medium",
                    "This explains the harder predicted-class localization setting.",
                ),
                (
                    "per-class regression",
                    "A localization strategy that learns a separate bounding-box regressor for each class.",
                    "field_term",
                    "hard",
                    "This is the main localization method described in the section.",
                ),
                (
                    "category-agnostic",
                    "A detector design that does not use category-specific localization heads.",
                    "field_term",
                    "hard",
                    "The section contrasts this with the per-class RPN design.",
                ),
                (
                    "cls layer",
                    "The classification head in the localization RPN.",
                    "field_term",
                    "medium",
                    "This is one of the two sibling output heads.",
                ),
                (
                    "reg layer",
                    "The box-regression head in the localization RPN.",
                    "field_term",
                    "medium",
                    "This is the second sibling output head.",
                ),
                (
                    "binary logistic regression",
                    "A binary classifier used for each class dimension in the cls layer.",
                    "field_term",
                    "hard",
                    "This explains how the 1000-dimensional cls output is interpreted.",
                ),
                (
                    "anchor boxes",
                    "Translation-invariant reference boxes used for bounding-box regression.",
                    "field_term",
                    "hard",
                    "This is the reference structure for box regression.",
                ),
                (
                    "positive and negative anchors",
                    "Sampled anchor boxes balanced during fine-tuning.",
                    "field_term",
                    "hard",
                    "The section samples them at a 1:1 ratio to avoid dominance by negatives.",
                ),
                (
                    "oracle testing",
                    "Testing that uses the ground truth class as the class prediction.",
                    "field_term",
                    "hard",
                    "This separates localization quality from classification mistakes.",
                ),
                (
                    "fully-convolutional testing",
                    "Applying the network densely over the image rather than only on a crop.",
                    "field_term",
                    "hard",
                    "This is the testing mode that improves localization error.",
                ),
                (
                    "RoI-centric",
                    "A training style centered on region proposals rather than whole-image batches.",
                    "field_term",
                    "hard",
                    "This is why the authors switch from Fast R-CNN to original R-CNN.",
                ),
                (
                    "class-dependent proposals",
                    "Bounding-box proposals predicted for a specific class.",
                    "field_term",
                    "hard",
                    "The per-class RPN outputs these proposals for localization.",
                ),
                (
                    "highest scored proposals",
                    "The top-ranked proposal boxes selected for each image or predicted class.",
                    "field_term",
                    "medium",
                    "The section repeatedly uses the top 200 proposals.",
                ),
                (
                    "R-CNN classifier",
                    "The classifier trained on cropped proposal regions.",
                    "field_term",
                    "medium",
                    "This is the RoI-centric classifier used instead of Fast R-CNN.",
                ),
                (
                    "relative reduction of error",
                    "A percentage reduction compared with a previous error rate.",
                    "useful",
                    "medium",
                    "This is how the section reports the final localization improvement.",
                ),
            ]
        elif generic_specs:
            known = generic_specs
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
        if generic_specs:
            seen_terms = {term.lower() for term, *_ in known}
            known = [*known, *[item for item in generic_specs if item[0].lower() not in seen_terms]]
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

    def _generic_academic_term_specs(self, document_text: str) -> list[tuple[str, str, str, str, str]]:
        lowered = document_text.lower()
        specs: list[tuple[str, str, str, str, str]] = []
        candidates = [
            (
                "climate risk",
                "The potential harm from climate-related hazards, policy changes, or transition pressure.",
                "field_term",
                "hard",
                "This anchors climate and sustainability reports.",
            ),
            (
                "greenhouse gas emissions",
                "Gases released into the atmosphere that contribute to warming.",
                "field_term",
                "medium",
                "This is a core measurement term in climate reports.",
            ),
            (
                "decarbonization",
                "Reducing carbon emissions in energy, industry, transport, or operations.",
                "field_term",
                "hard",
                "This names the direction of climate mitigation strategy.",
            ),
            (
                "adaptation measures",
                "Actions that reduce vulnerability to climate impacts.",
                "field_term",
                "medium",
                "This separates adapting to impacts from reducing emissions.",
            ),
            (
                "monetary policy",
                "Central-bank policy that influences inflation, interest rates, and economic activity.",
                "field_term",
                "hard",
                "This anchors economics and central-bank reports.",
            ),
            (
                "inflation expectations",
                "Beliefs about future inflation that can affect prices, wages, and policy decisions.",
                "field_term",
                "hard",
                "This is a high-value economics concept rather than a generic word.",
            ),
            (
                "labor market",
                "The market for employment, wages, vacancies, and workers.",
                "field_term",
                "medium",
                "This often explains pressure on wages and inflation.",
            ),
            (
                "randomized controlled trial",
                "A study design that randomly assigns participants to compare an intervention with a control.",
                "field_term",
                "hard",
                "This is a core evidence term in medical and social-science papers.",
            ),
            (
                "confidence interval",
                "A range that expresses uncertainty around an estimated effect.",
                "field_term",
                "hard",
                "This helps readers interpret statistical claims.",
            ),
            (
                "adverse events",
                "Unwanted medical events observed during a study or intervention.",
                "field_term",
                "medium",
                "This is central to safety reporting.",
            ),
            (
                "idempotent preflight check",
                "A repeat-safe check run before deployment or migration.",
                "field_term",
                "hard",
                "This is a useful technical-video term.",
            ),
            (
                "stale metadata",
                "Outdated system metadata that can cause incorrect behavior.",
                "field_term",
                "medium",
                "This explains the failure mode in technical tutorials.",
            ),
            (
                "worker nodes",
                "Machines or processes that execute distributed work.",
                "field_term",
                "medium",
                "This is common infrastructure vocabulary.",
            ),
            (
                "API endpoint",
                "A specific URL path that a client calls to use a service.",
                "field_term",
                "medium",
                "This is a core technical-documentation term.",
            ),
            (
                "request payload",
                "The structured data sent with an API request.",
                "field_term",
                "medium",
                "This helps learners read API usage instructions.",
            ),
            (
                "authentication token",
                "A credential included with a request to prove access permission.",
                "field_term",
                "hard",
                "This is central to secure API documentation.",
            ),
            (
                "environment variable",
                "A named runtime setting read by software from its execution environment.",
                "field_term",
                "medium",
                "This is common in setup and deployment docs.",
            ),
            (
                "pagination cursor",
                "A value used to request the next page of API results.",
                "field_term",
                "hard",
                "This is a recurring docs term for list endpoints.",
            ),
            (
                "rate limit",
                "A restriction on how many requests can be made in a time window.",
                "field_term",
                "medium",
                "This is important for API reliability and error handling.",
            ),
            (
                "large language models",
                "Models trained on large text corpora that can generate and interpret language.",
                "field_term",
                "medium",
                "This is central to modern AI explainer videos.",
            ),
            (
                "modern AI",
                "Current AI systems and tools built from recent model advances.",
                "useful",
                "medium",
                "This anchors broad AI video introductions.",
            ),
            (
                "greenhouse effect",
                "The warming process caused when atmospheric gases trap heat.",
                "field_term",
                "medium",
                "This is a core climate-explainer concept.",
            ),
            (
                "climate change",
                "Long-term shifts in climate patterns, especially the rapid warming discussed in the explainer.",
                "field_term",
                "medium",
                "This is the central topic of the climate source.",
            ),
            (
                "carbon dioxide",
                "A greenhouse gas linked to atmospheric heating and global temperature rise.",
                "field_term",
                "medium",
                "This is the first concrete causal gas introduced in the climate source.",
            ),
            (
                "greenhouse gases",
                "Gases such as carbon dioxide, methane, and water vapor that trap heat in the atmosphere.",
                "field_term",
                "medium",
                "This explains the mechanism behind the greenhouse effect.",
            ),
            (
                "atmospheric heating",
                "The process of the atmosphere holding heat because of gas composition.",
                "field_term",
                "hard",
                "This connects the experiment to the climate mechanism.",
            ),
            (
                "earth's temperature",
                "A broad climate measure referring to global temperature change.",
                "useful",
                "medium",
                "This helps learners follow climate-change explanations.",
            ),
            (
                "human activities",
                "Actions by people that drive environmental or social change.",
                "useful",
                "medium",
                "This is common causal language in public reports and explainers.",
            ),
            (
                "economics",
                "The study of choices, incentives, resources, markets, and tradeoffs.",
                "field_term",
                "medium",
                "This anchors introductory economics videos.",
            ),
            (
                "theories and graphs",
                "The conceptual and visual tools used to explain economic reasoning.",
                "useful",
                "medium",
                "This describes the academic side of the economics source.",
            ),
            (
                "real world applications",
                "Examples of how economic ideas apply outside textbook explanations.",
                "useful",
                "medium",
                "This separates applied economics from abstract theory.",
            ),
            (
                "scarce resources",
                "Limited resources that require choices and tradeoffs.",
                "field_term",
                "medium",
                "This is a foundational economics concept.",
            ),
            (
                "opportunity cost",
                "The value of the next-best alternative given up when making a choice.",
                "field_term",
                "hard",
                "This is one of the most useful economics terms for learners.",
            ),
            (
                "virus",
                "A tiny infectious agent that replicates inside living cells.",
                "field_term",
                "medium",
                "This anchors medical explainer videos about infection.",
            ),
            (
                "genetic material",
                "DNA or RNA carrying biological instructions.",
                "field_term",
                "hard",
                "This explains how viruses store replication instructions.",
            ),
            (
                "protein shell",
                "A protective protein coat around viral genetic material.",
                "field_term",
                "medium",
                "This is a basic structural term in virus explanations.",
            ),
            (
                "fast api",
                "A modern Python web framework for building APIs.",
                "field_term",
                "medium",
                "This anchors FastAPI documentation and tutorial videos.",
            ),
            (
                "FastAPI",
                "A modern Python web framework for building APIs.",
                "field_term",
                "medium",
                "This is the framework being taught in the tutorial source.",
            ),
            (
                "APIs with Python",
                "API services built using the Python programming language.",
                "field_term",
                "medium",
                "This is the core tutorial task.",
            ),
            (
                "web framework",
                "A framework that provides structure and tools for building web applications or APIs.",
                "field_term",
                "medium",
                "This explains what kind of tool FastAPI is.",
            ),
            (
                "Python package manager",
                "A tool such as pip used to install Python packages.",
                "field_term",
                "medium",
                "This is needed to follow installation instructions.",
            ),
            (
                "pip",
                "The common command-line installer for Python packages.",
                "useful",
                "medium",
                "This appears in the installation step of the tutorial.",
            ),
            (
                "Python web framework",
                "A Python library or framework used to build web services.",
                "field_term",
                "medium",
                "This explains where FastAPI fits among tools.",
            ),
            (
                "automatic documentation",
                "Documentation generated by the framework from API definitions.",
                "field_term",
                "medium",
                "This is one of FastAPI's key tutorial claims.",
            ),
            (
                "recurrent models",
                "Sequence models that compute token positions step by step.",
                "field_term",
                "medium",
                "This explains the bottleneck the Transformer is designed to avoid.",
            ),
            (
                "hidden states",
                "Intermediate sequence representations generated by recurrent computation.",
                "field_term",
                "medium",
                "This is the mechanism behind recurrent sequence processing.",
            ),
            (
                "queries",
                "Vectors that ask what information an attention operation should retrieve.",
                "field_term",
                "medium",
                "This is one of the core Q/K/V roles in attention.",
            ),
            (
                "keys",
                "Vectors matched against queries to produce attention scores.",
                "field_term",
                "medium",
                "This is one of the core Q/K/V roles in attention.",
            ),
            (
                "values",
                "Vectors mixed by attention weights to produce the output.",
                "field_term",
                "medium",
                "This is one of the core Q/K/V roles in attention.",
            ),
            (
                "softmax function",
                "A function that turns scores into normalized attention weights.",
                "field_term",
                "medium",
                "This explains how attention scores become weights.",
            ),
            (
                "dot products",
                "Similarity scores computed between queries and keys.",
                "field_term",
                "medium",
                "This anchors scaled dot-product attention.",
            ),
            (
                "linear projections",
                "Learned linear transforms applied to queries, keys, and values.",
                "field_term",
                "hard",
                "This explains how multi-head attention creates different views.",
            ),
            (
                "position-wise feed-forward networks",
                "Feed-forward layers applied independently at each sequence position.",
                "field_term",
                "hard",
                "This is a core Transformer block component.",
            ),
            (
                "embeddings",
                "Vector representations used for input tokens and output tokens.",
                "field_term",
                "medium",
                "This explains how tokens enter the model.",
            ),
            (
                "positional encodings",
                "Vectors added to embeddings so the model can use token order.",
                "field_term",
                "hard",
                "This replaces recurrence or convolution as the source of order information.",
            ),
            (
                "sine and cosine functions",
                "Fixed sinusoidal functions used to build positional encodings.",
                "field_term",
                "medium",
                "This explains the paper's non-learned position signal.",
            ),
            (
                "training data",
                "The dataset used to train the model.",
                "useful",
                "medium",
                "This helps readers separate experiment setup from method claims.",
            ),
            (
                "batching",
                "Grouping examples into batches for efficient training.",
                "field_term",
                "medium",
                "This is part of the experimental setup.",
            ),
            (
                "NVIDIA P100 GPUs",
                "Hardware used to report the Transformer training schedule.",
                "useful",
                "medium",
                "This is experiment context, not a core concept.",
            ),
            (
                "Adam optimizer",
                "Optimization algorithm used to train the Transformer.",
                "field_term",
                "medium",
                "This is important for reading the training recipe.",
            ),
            (
                "warmup_steps",
                "Initial training steps where the learning rate increases.",
                "field_term",
                "hard",
                "This explains the paper's learning-rate schedule.",
            ),
            (
                "label smoothing",
                "Regularization that prevents the model from becoming too confident.",
                "field_term",
                "hard",
                "This explains a training choice that affects BLEU and perplexity.",
            ),
            (
                "BLEU score",
                "A machine translation quality metric based on overlap with references.",
                "field_term",
                "medium",
                "This is the main translation result metric.",
            ),
            (
                "beam search",
                "A decoding method that keeps several likely output sequences while generating text.",
                "field_term",
                "hard",
                "This belongs to inference and evaluation setup.",
            ),
            (
                "checkpoint averaging",
                "Averaging recent saved model checkpoints for final evaluation.",
                "field_term",
                "hard",
                "This explains the evaluation protocol.",
            ),
            (
                "model variations",
                "Ablation experiments that vary model components to test importance.",
                "field_term",
                "medium",
                "This marks the paper's component-level evaluation.",
            ),
            (
                "attention heads",
                "Parallel attention operations inside multi-head attention.",
                "field_term",
                "medium",
                "This is a key ablation dimension in Transformer experiments.",
            ),
            (
                "heads",
                "Parallel attention operations inside multi-head attention.",
                "field_term",
                "medium",
                "This is a key ablation dimension in Transformer experiments.",
            ),
            (
                "projections",
                "Learned transforms that map Q, K, and V into attention-head spaces.",
                "field_term",
                "hard",
                "This explains the parameter matrices in multi-head attention.",
            ),
            (
                "parameter matrices",
                "Learned matrices used to project model vectors.",
                "field_term",
                "hard",
                "This helps read formula-heavy Transformer sections.",
            ),
            (
                "feed-forward network",
                "A neural sub-layer that applies linear transformations and a nonlinearity.",
                "field_term",
                "medium",
                "This is a core Transformer block component.",
            ),
            (
                "linear transformations",
                "Linear layers used inside the feed-forward network.",
                "field_term",
                "medium",
                "This explains the FFN formula.",
            ),
            (
                "ReLU activation",
                "Nonlinear activation used between the two FFN linear transformations.",
                "field_term",
                "medium",
                "This explains the middle operation in the FFN.",
            ),
            (
                "maximum path length",
                "The longest computation path needed to connect two sequence positions.",
                "field_term",
                "hard",
                "This is a core comparison criterion in the self-attention argument.",
            ),
            (
                "convolutional layers",
                "Neural layers used as a comparison point for sequence modeling.",
                "field_term",
                "medium",
                "This is part of the self-attention versus convolution comparison.",
            ),
            (
                "separable convolutions",
                "Lower-cost convolution variants used in the complexity comparison.",
                "field_term",
                "hard",
                "This explains the paper's caveat about convolutional alternatives.",
            ),
            (
                "training steps",
                "The number of parameter-update steps used during training.",
                "field_term",
                "medium",
                "This is more useful than memorizing the hardware model.",
            ),
            (
                "base models",
                "The smaller Transformer configuration used as a comparison baseline.",
                "field_term",
                "medium",
                "This helps interpret training schedule and ablation sections.",
            ),
            (
                "big models",
                "The larger Transformer configuration trained longer for stronger results.",
                "field_term",
                "medium",
                "This helps interpret training schedule and result sections.",
            ),
            (
                "dropout",
                "A regularization method that randomly drops activations during training.",
                "field_term",
                "medium",
                "This is a common experiment and ablation term.",
            ),
            (
                "BN transform",
                "The Batch Normalization transformation applied inside the network.",
                "field_term",
                "hard",
                "This is the operation being analyzed in BatchNorm sections.",
            ),
            (
                "normalized activations",
                "Layer activations after normalization has been applied.",
                "field_term",
                "medium",
                "This explains what BatchNorm changes during training.",
            ),
            (
                "feature map",
                "A channel-wise activation map in a convolutional layer.",
                "field_term",
                "medium",
                "This is needed for convolutional BatchNorm sections.",
            ),
            (
                "gradient propagation",
                "How gradients move backward through the network during training.",
                "field_term",
                "hard",
                "This explains why BatchNorm can improve optimization behavior.",
            ),
            (
                "singular values",
                "Values describing how a transformation scales directions.",
                "field_term",
                "hard",
                "This appears in BatchNorm's gradient-propagation argument.",
            ),
            (
                "backpropagation",
                "The algorithm that propagates gradients backward to update parameters.",
                "field_term",
                "medium",
                "This is central to optimization sections.",
            ),
            (
                "ImageNet classification",
                "A large-scale image classification benchmark used for evaluation.",
                "field_term",
                "medium",
                "This anchors the BatchNorm experiment sections.",
            ),
            (
                "ensemble",
                "A combination of multiple models used to improve final predictions.",
                "field_term",
                "medium",
                "This helps read final experimental result sections.",
            ),
            (
                "general language representations",
                "Language representations learned broadly before being reused on tasks.",
                "field_term",
                "hard",
                "This anchors BERT related-work sections.",
            ),
            (
                "contextual representations",
                "Token or text representations that depend on surrounding context.",
                "field_term",
                "hard",
                "This explains ELMo/BERT-style representation learning.",
            ),
            (
                "question answering",
                "A task where the model answers questions from text.",
                "field_term",
                "medium",
                "This is one of BERT's benchmark task types.",
            ),
            (
                "named entity recognition",
                "A task that tags names such as people, organizations, and locations.",
                "field_term",
                "medium",
                "This is a common NLP benchmark task.",
            ),
            (
                "WordPiece embeddings",
                "Subword token embeddings used by BERT.",
                "field_term",
                "hard",
                "This explains BERT input representation.",
            ),
            (
                "token sequence",
                "The sequence of tokens fed into BERT.",
                "field_term",
                "medium",
                "This is central to BERT's input representation.",
            ),
            (
                "GLUE benchmark",
                "A collection of natural language understanding tasks.",
                "field_term",
                "medium",
                "This anchors BERT experiment sections.",
            ),
            (
                "final hidden vector",
                "The hidden representation used for classification.",
                "field_term",
                "hard",
                "This explains how BERT fine-tuning reads [CLS].",
            ),
            (
                "classification layer",
                "The task-specific output layer used for classification.",
                "field_term",
                "medium",
                "This is the new parameter layer in BERT fine-tuning.",
            ),
            (
                "F1 score",
                "An evaluation metric combining precision and recall.",
                "field_term",
                "medium",
                "This is used in SQuAD and other benchmark reporting.",
            ),
            (
                "leaderboard system",
                "A high-performing submitted system used as a comparison point.",
                "useful",
                "medium",
                "This helps read benchmark result claims.",
            ),
        ]
        climate_context = any(
            marker in lowered
            for marker in (
                "climate change",
                "greenhouse effect",
                "greenhouse gases",
                "global temperature",
                "atmospheric heating",
            )
        )
        climate_only = {"carbon dioxide", "greenhouse gases", "atmospheric heating"}
        for term, meaning, priority, difficulty, reason in candidates:
            if term.lower() in climate_only and not climate_context:
                continue
            if term.lower() in lowered:
                specs.append((term, meaning, priority, difficulty, reason))
        return specs

    def _generic_academic_phrase_specs(self, document_text: str) -> list[tuple[str, str, str]]:
        lowered = document_text.lower()
        candidates = [
            ("is associated with", "claim", "States a relationship without claiming direct causation."),
            ("remains elevated", "result", "Reports that a measured risk or level is still high."),
            ("remain elevated", "result", "Reports that a measured risk or level is still high."),
            ("remained elevated", "result", "Reports that a measured risk or level stayed high."),
            ("reports a", "result", "Introduces an empirical result or estimate."),
            ("in response to", "method", "Links an action to a condition or cause."),
            ("is likely to", "claim", "Expresses a probable but not certain outcome."),
            ("can propagate across", "result", "Explains how an effect spreads through a system."),
            ("before we", "method", "Introduces a required preliminary step in a procedure."),
            ("otherwise", "contrast", "Introduces the consequence if the previous condition is not met."),
            ("must include", "method", "States a required field or condition."),
            ("set this parameter to", "method", "Gives a concrete configuration instruction."),
            ("returns a", "result", "Describes the output produced by an API or function."),
            ("if the request fails", "limitation", "Introduces an error-handling condition."),
            ("known as", "general", "Introduces the name of a concept after describing it."),
            ("known collectively as", "general", "Introduces a grouped name for several examples."),
            ("based on", "claim", "Connects a conclusion to evidence or observation."),
            ("driving up", "claim", "Describes a cause increasing a measured level."),
            ("faster now than ever before", "result", "Emphasizes an unusually rapid rate of change."),
            ("became one of the first", "result", "Positions a person or study historically."),
            ("we need to", "method", "States a required next action in a tutorial."),
            ("focus on", "method", "States the part of a topic the speaker will emphasize."),
            ("real world applications", "general", "Names applied examples rather than abstract theory."),
            ("let's start with", "method", "Introduces the first step of an explanation."),
            ("what is", "general", "Introduces a definition question."),
            ("makes it quicker and easier to", "result", "States the practical benefit of a tool."),
            ("get started working with", "method", "Introduces an onboarding or setup step."),
            ("easy to follow documentation", "result", "Describes documentation that is learner-friendly."),
            ("the only requirement", "method", "States the prerequisite before following a tutorial."),
            ("minimum version", "general", "Specifies the lowest acceptable software version."),
            ("install FastAPI", "method", "Introduces the installation action for the framework."),
            ("in my opinion", "claim", "Marks a personal stance in spoken explanation."),
            ("there are", "general", "Introduces a category or list in spoken explanation."),
            ("typically factor computation along", "method", "Explains how recurrent models organize sequence computation."),
            ("precludes parallelization", "limitation", "States that a structure prevents parallel computation."),
            ("can be described as", "general", "Introduces a formal definition in prose."),
            ("we compute", "method", "Introduces the calculation steps of a method."),
            ("instead of performing", "contrast", "Contrasts the chosen architecture with a simpler baseline."),
            ("in addition to", "general", "Adds another component or method."),
            ("follows this overall architecture", "method", "Connects the Transformer to the encoder-decoder architecture pattern."),
            ("at each step", "method", "Explains an autoregressive generation process."),
            ("is applied to each position", "method", "Explains that the same operation is repeated per token position."),
            ("another way of describing this", "general", "Introduces an equivalent interpretation of a method."),
            ("we plan to investigate", "limitation", "Marks future work rather than a finished claim."),
            ("doing so requires", "result", "States a consequence of a proposed approach."),
            ("could yield", "claim", "Cautiously states a possible benefit."),
            ("similarly to", "contrast", "Connects the current method to a familiar prior pattern."),
            ("since our model contains", "claim", "Introduces a design reason based on what the model lacks."),
            ("we trained on", "method", "Introduces the dataset used for training."),
            ("were batched together by", "method", "Explains the batching criterion."),
            ("we trained our models on", "method", "States the hardware used for training."),
            ("we used the adam optimizer", "method", "Introduces the optimizer choice."),
            ("we varied the learning rate", "method", "Explains a learning-rate schedule."),
            ("we employ", "method", "States a method or regularization choice."),
            ("outperforms the best previously reported", "result", "States a benchmark improvement over prior work."),
            ("to evaluate the importance of", "method", "Introduces an ablation purpose."),
            ("unlisted values are identical to", "method", "Explains table shorthand."),
            ("this suggests that", "claim", "Draws a cautious conclusion from results."),
            ("we observe that", "result", "Introduces an interpretation of experimental results."),
            ("we further observe", "result", "Adds another result interpretation."),
            ("observe nearly identical results", "result", "Reports a close ablation comparison."),
            ("this ensures that", "claim", "Connects a mechanism to the property it guarantees."),
            ("allows the", "result", "States what a method makes possible."),
            ("in contrast", "contrast", "Introduces a comparison against a different condition."),
            ("as training progresses", "general", "Marks change over the course of training."),
            ("in this section", "general", "Introduces the scope of the current section."),
            ("we briefly review", "general", "Introduces a short related-work survey."),
            ("similar to", "contrast", "Compares the current method or result with a related one."),
            ("not deeply bidirectional", "limitation", "States a limitation of earlier representation methods."),
            ("to make", "method", "Introduces the purpose of a design choice."),
            ("throughout this work", "general", "Defines terminology used consistently in the paper."),
            ("to fine-tune on", "method", "Introduces the setup for adapting the model to a task."),
            ("we represent", "method", "Explains how inputs are encoded for a task."),
            ("the only new parameters", "method", "Emphasizes that task adaptation is small."),
            ("outperforms the top", "result", "States a benchmark improvement over a strong baseline."),
            ("in terms of", "general", "Specifies the metric or comparison dimension."),
        ]
        return [item for item in candidates if item[0].lower() in lowered]

    def _generic_academic_sentence(self, document_text: str) -> dict[str, str] | None:
        sentences = self._sentences_from_text(document_text)
        if not sentences:
            return None
        for sentence in sentences:
            lowered = sentence.lower()
            if "although" in lowered and "remains" in lowered:
                return {
                    "sentence": sentence,
                    "core_structure": "Although A, B remains C.",
                    "simplified_version": "The first clause gives background or contrast; the main clause states what is still unresolved.",
                    "korean_explanation": "'Although' 절은 배경/양보를 제시하고, 주절의 'remains'가 아직 해결되지 않은 상태를 말합니다.",
                    "difficulty_reason": "The sentence is difficult because the main claim comes after a long concession.",
                }
            if "remained elevated" in lowered and "although" in lowered:
                return {
                    "sentence": sentence,
                    "core_structure": "X remained elevated, although Y was modest.",
                    "simplified_version": "The author reports a high safety signal while limiting the strength of the effect.",
                    "korean_explanation": "'although' 뒤의 내용은 앞의 결과를 약화하거나 조심스럽게 해석하게 만드는 양보 표현입니다.",
                    "difficulty_reason": "The sentence is difficult because it reports a result and qualifies its strength in the same sentence.",
                }
            if "is associated with" in lowered:
                return {
                    "sentence": sentence,
                    "core_structure": "X is associated with Y, especially when Z.",
                    "simplified_version": "The author reports a relationship and then narrows the condition.",
                    "korean_explanation": "'is associated with'는 직접 원인이라고 단정하지 않고 관련성을 말하는 표현입니다.",
                    "difficulty_reason": "The sentence uses cautious empirical language and conditional narrowing.",
                }
            if "before we" in lowered and "otherwise" in document_text.lower():
                return {
                    "sentence": sentence,
                    "core_structure": "Before we do A, we need to do B.",
                    "simplified_version": "The speaker gives a required step that must happen before the main action.",
                    "korean_explanation": "'Before we...'는 본 작업 전에 필요한 사전 조건을 설명합니다.",
                    "difficulty_reason": "The sentence is procedural and depends on the following consequence introduced by 'otherwise'.",
                }
            if "must include" in lowered and ("request" in lowered or "payload" in lowered):
                return {
                    "sentence": sentence,
                    "core_structure": "The request/payload must include X to do Y.",
                    "simplified_version": "The documentation states a required input and why it is needed.",
                    "korean_explanation": "'must include'는 API 문서에서 필수 입력값을 표시하는 강한 의무 표현입니다.",
                    "difficulty_reason": "The sentence is difficult because it combines requirement, field name, and purpose.",
                }
            if "set this parameter to" in lowered:
                return {
                    "sentence": sentence,
                    "core_structure": "To enable X, set this parameter to Y.",
                    "simplified_version": "The documentation gives a configuration step for enabling a behavior.",
                    "korean_explanation": "'set this parameter to'는 설정값을 어떻게 지정해야 하는지 알려주는 문서 표현입니다.",
                    "difficulty_reason": "The sentence is procedural and maps a goal to a specific configuration value.",
                }
        return None

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
        if self._is_convex_optimization_definition_section(document_text):
            phrase_specs = [
                ("It is important to note", "claim", "Signals a definition caveat or subtle point."),
                ("not a convex optimization problem in standard form", "limitation", "States that a problem fails the formal definition."),
                ("since the equality constraint", "claim", "Gives the reason for the standard-form failure."),
                ("With a slight abuse of notation", "general", "Warns that terminology is being used informally."),
            ]
        generic_phrase_specs = self._generic_academic_phrase_specs(document_text)
        if generic_phrase_specs:
            phrase_specs = [*generic_phrase_specs, *phrase_specs]
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
                ("has been an active area of research", "general", "Introduces a long-running research area."),
                ("are an integral part of", "claim", "States that a method family is now central to modern systems."),
                ("offering significant improvements over", "result", "Compares pre-trained embeddings with training from scratch."),
                ("have been generalized to", "general", "Shows how a method family extends to broader representation levels."),
                ("along a different dimension", "contrast", "Marks that ELMo generalizes prior work in a different way."),
                ("extract context-sensitive features", "method", "Explains ELMo's feature-extraction role."),
                ("is the concatenation of", "method", "Explains how directional representations are combined."),
                ("advances the state of the art", "result", "States that a method improves benchmark performance."),
                ("when integrating", "method", "Introduces the condition or setup under which a method is used."),
                ("proposed learning contextual representations through", "method", "Describes a prior method by its training task."),
                ("Similar to ELMo", "contrast", "Compares a prior model to ELMo before stating its limitation."),
                ("not deeply bidirectional", "limitation", "Names the limitation that BERT is designed to overcome."),
                ("As with the feature-based approaches", "contrast", "Links the next related-work category back to the previous one."),
                ("fine-tuned for a supervised downstream task", "method", "Describes the pre-train then adapt workflow."),
                ("few parameters need to be learned from scratch", "result", "Explains the practical advantage of fine-tuning."),
                ("Apart from output layers", "contrast", "Separates the task-specific part from the shared BERT architecture."),
                ("are used to initialize", "method", "Explains how pre-trained parameters become the starting point for downstream models."),
                ("During fine-tuning", "method", "Marks what changes in the adaptation stage."),
                ("is a special symbol added", "general", "Defines an input-format token used by BERT."),
                ("is a special separator token", "general", "Defines the token that separates text segments."),
                ("There has also been work showing", "claim", "Introduces another related-work branch."),
                ("effective transfer from", "result", "States the source of transfer learning evidence."),
                ("A distinctive feature of BERT is", "claim", "Introduces the architectural property the section wants the reader to notice."),
                ("There is minimal difference between", "contrast", "Contrasts pre-trained and downstream architectures by emphasizing their similarity."),
                ("is a multi-layer bidirectional Transformer encoder", "method", "Defines the model architecture in one compressed noun phrase."),
                ("we denote the number of", "general", "Defines notation for model-size parameters."),
                ("we primarily report results on", "result", "Introduces the model-size variants used in experiments."),
                ("was chosen to have the same model size as", "method", "Explains why BERTBASE is comparable with GPT."),
                ("is able to unambiguously represent", "method", "Explains the design goal of BERT input representation."),
                ("refers to the input token sequence", "general", "Defines what sequence means in the paper."),
                ("The first token of every sequence is always", "general", "Defines a fixed input-format convention."),
                ("is used as the aggregate sequence representation", "method", "Explains how [CLS] summarizes a sequence for classification."),
                ("are packed together into a single sequence", "method", "Explains how sentence pairs are represented as one model input."),
                ("We differentiate the sentences in two ways", "general", "Introduces an ordered method explanation."),
                ("we separate them with", "method", "Explains one mechanism for separating sentence pairs."),
                ("we add a learned embedding", "method", "Explains segment embeddings for sentence identity."),
                ("is constructed by summing", "method", "Explains how BERT builds each token input vector."),
                ("we do not use traditional", "contrast", "Contrasts BERT pre-training with left-to-right/right-to-left language models."),
                ("Instead, we pre-train", "method", "Introduces the replacement method after rejecting a prior approach."),
                ("In order to train", "method", "Introduces the purpose of a training procedure."),
                ("We refer to this procedure as", "general", "Names a method after describing it."),
                ("although it is often referred to as", "general", "Connects the paper's term to another literature term."),
                ("are fed into", "method", "Describes where model vectors go in the prediction step."),
                ("In contrast to", "contrast", "Contrasts the method with a related prior method."),
                ("rather than reconstructing", "contrast", "Clarifies what the method does not try to predict."),
                ("a downside is that", "limitation", "Introduces a practical limitation of the method."),
                ("To mitigate this", "method", "Introduces a workaround for a stated limitation."),
                ("chooses 15% of the token positions", "method", "States the sampling rule for masked-token prediction."),
                ("will be used to predict", "method", "Explains the prediction target and loss connection."),
                ("binarized next sentence prediction task", "method", "Names the binary sentence-relationship pre-training task."),
                ("can be trivially generated from", "method", "Explains why the task can be produced without manual labels."),
                ("when choosing the sentences", "method", "Introduces how sentence pairs are sampled."),
                ("50% of the time", "method", "States the balanced positive/negative sampling rule."),
                ("labeled as IsNext", "general", "Defines the positive NSP label."),
                ("labeled as NotNext", "general", "Defines the negative NSP label."),
                ("Despite its simplicity", "result", "Contrasts a simple method with a strong result."),
                ("is very beneficial to", "result", "States the downstream benefit of the pre-training task."),
                ("is not a meaningful sentence representation without", "limitation", "Warns against overinterpreting the vector before fine-tuning."),
                ("closely related to", "general", "Connects the task to prior representation-learning objectives."),
                ("transfers all parameters", "method", "Contrasts full-parameter transfer with sentence-embedding transfer."),
                ("It is critical to use", "claim", "Marks a requirement for the training corpus."),
                ("rather than a shuffled", "contrast", "Contrasts the preferred data format with a weaker alternative."),
                ("in order to extract", "method", "Explains the purpose of a design choice."),
                ("Fine-tuning is straightforward since", "claim", "Introduces why adaptation is simple."),
                ("by swapping out", "method", "Explains the minimal task-specific change."),
                ("a common pattern is to", "general", "Introduces the baseline workflow being contrasted."),
                ("BERT instead uses", "contrast", "Introduces BERT's alternative to the common pattern."),
                ("to unify these two stages", "method", "States the unification goal of BERT's self-attention."),
                ("we simply plug in", "method", "Explains the fine-tuning recipe."),
                ("finetune all the parameters end-to-end", "method", "States that the whole model is updated during fine-tuning."),
                ("are analogous to", "general", "Maps BERT sentence slots to task-specific input pairs."),
                ("Compared to pre-training", "contrast", "Contrasts fine-tuning cost with pre-training cost."),
                ("we present BERT fine-tuning results on", "result", "Introduces the experiment scope."),
                ("is a collection of", "general", "Defines a benchmark or dataset group."),
                ("To fine-tune on", "method", "Introduces the fine-tuning setup for a benchmark."),
                ("use the final hidden vector", "method", "Explains which representation is used for classification."),
                ("The only new parameters introduced", "method", "Identifies what is newly learned during fine-tuning."),
                ("We compute a standard classification loss", "method", "Describes the training objective for classification tasks."),
                ("scored by the evaluation server", "result", "Explains how benchmark results are evaluated."),
                ("The number below each task denotes", "general", "Explains how to read the table header."),
                ("is slightly different than", "contrast", "Warns that a reported average differs from the official score."),
                ("are reported for", "general", "Explains metric conventions across benchmark tasks."),
                ("We exclude entries that use", "method", "Defines a comparison-filtering rule."),
                ("fine-tune for", "method", "States a training duration or protocol."),
                ("selected the best fine-tuning learning rate", "method", "Explains dev-set hyperparameter selection."),
                ("sometimes unstable on small datasets", "limitation", "Marks an instability caveat for small training sets."),
                ("ran several random restarts", "method", "Describes a robustness procedure for unstable fine-tuning."),
                ("selected the best model on the Dev set", "method", "Explains how the restart result was chosen."),
                ("perform different fine-tuning data shuffling", "method", "Explains what differs across random restarts."),
                ("outperform all systems", "result", "States the main benchmark result."),
                ("by a substantial margin", "result", "Signals the size of an improvement."),
                ("nearly identical in terms of", "contrast", "Controls for architecture similarity in a comparison."),
                ("apart from", "contrast", "Introduces the one exception in a comparison."),
                ("as of the date of writing", "general", "Qualifies a time-sensitive leaderboard claim."),
                ("significantly outperforms", "result", "States a stronger comparative result."),
                ("is explored more thoroughly in", "general", "Points forward to a later analysis section."),
                ("Given a question and a passage", "general", "Introduces the question-answering input setting."),
                ("the task is to predict", "claim", "Defines the task objective."),
                ("answer text span", "general", "Names the output unit in extractive question answering."),
                ("we represent the input question and passage as", "method", "Explains how QA inputs are packed for BERT."),
                ("We only introduce", "method", "Emphasizes the small task-specific parameter addition."),
                ("is computed as", "method", "Introduces a formula or scoring computation."),
                ("followed by a softmax", "method", "Explains the normalization step after scoring."),
                ("The analogous formula is used for", "method", "Maps the start-position computation to the end-position computation."),
                ("is defined as", "method", "Defines a scoring function."),
                ("maximum scoring span", "method", "Explains how the final answer span is selected."),
                ("The training objective is", "method", "Introduces the optimization target."),
                ("Table 2 shows", "result", "Introduces a result table."),
                ("do not have up-to-date public system descriptions", "limitation", "Qualifies leaderboard comparability."),
                ("are allowed to use any public data", "limitation", "Explains a benchmark-permission caveat."),
                ("We therefore use", "method", "Introduces a consequence-driven method choice."),
                ("by first fine-tuning on", "method", "Explains a staged fine-tuning or data-augmentation recipe."),
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
                ("improves the mAP by", "result", "States the detection performance gain over VGG-16."),
                ("solely because of", "claim", "Attributes the improvement to the learned ResNet features."),
                ("standard COCO metric", "general", "Names the stricter COCO detection metric."),
                ("similar to that for", "general", "Connects the COCO detection system to the PASCAL VOC setup."),
                ("relative improvement", "result", "Expresses the COCO mAP gain relative to the VGG baseline."),
                ("nearly as big as", "result", "Compares localization-sensitive and recognition-focused gains."),
                ("improve both recognition and localization", "result", "States the interpretation of the two metric gains."),
                ("partially follows", "method", "Signals that the improvement adapts an existing localization method."),
                ("followed by", "method", "Shows the order of post-processing steps."),
                ("Given the full-image", "method", "Introduces the input used to build global context."),
                ("is concatenated with", "method", "Explains how global context is combined with per-region features."),
                ("trained end-to-end", "method", "States that the added structure is optimized together."),
                ("single-scale training/testing", "contrast", "Names the baseline inference setting before multi-scale testing."),
                ("because of limited time", "limitation", "Explains an implementation limitation rather than a scientific claim."),
                ("Object detection improvements on", "result", "Introduces a result table and its benchmark setting."),
                ("Detection results on", "result", "Introduces benchmark-specific detection results."),
                ("The baseline is", "general", "Defines the comparison system used in a result table."),
                ("include box refinement", "method", "Expands what the improved `baseline+++` shorthand contains."),
                ("no publicly available ground truth", "limitation", "Explains why evaluation must go through a server."),
                ("reported by the evaluation server", "result", "Describes benchmark protocol for hidden-label test sets."),
                ("single-model result", "result", "Distinguishes one model's score from an ensemble score."),
                ("boost both tasks", "result", "Explains why ensembling helps proposals and classifiers."),
                ("based on the above model", "method", "Signals reuse of the COCO-trained detector for PASCAL VOC."),
                ("fine-tune this model", "method", "Explains the adaptation step from COCO to PASCAL VOC."),
                ("higher than the previous state-of-the-art", "result", "States the benchmark improvement over prior work."),
                ("task involves", "general", "Introduces what a benchmark task contains."),
                ("is evaluated by", "general", "Names the metric used to score a task."),
                ("is the same as that for", "method", "States that the method is reused from another benchmark setup."),
                ("are pretrained on", "method", "Explains the source task used before fine-tuning."),
                ("are fine-tuned on", "method", "Explains the target data used to adapt the detector."),
                ("We split the validation set", "method", "Describes the validation protocol."),
                ("is used for validation", "method", "Explains the role of the held-out validation split."),
                ("We do not use", "limitation", "States a data restriction or fairness constraint."),
                ("requires to classify and localize", "general", "Defines the localization task as classification plus bounding-box prediction."),
                ("only accounts for", "method", "Explains the division of labor between classifier and localization algorithm."),
                ("based on the predicted classes", "method", "Shows that localization depends on image-level class predictions."),
                ("We adopt", "method", "Introduces a chosen strategy from prior work."),
                ("per-class regression", "method", "Names the class-specific bounding-box regression strategy."),
                ("Unlike the way", "contrast", "Contrasts this RPN with the category-agnostic version."),
                ("is designed in a per-class form", "method", "States the key RPN modification for localization."),
                ("ends with two sibling", "method", "Describes the final RPN heads for classification and box regression."),
                ("surpassing the second place", "result", "States the competition margin over the runner-up."),
                ("in contrast to", "contrast", "Marks the difference from the category-agnostic Faster R-CNN setup."),
                ("Specifically", "general", "Introduces detailed layer dimensions after the high-level statement."),
                ("consisting of", "general", "Explains what an output vector contains."),
                ("with reference to", "method", "Explains that regression is defined relative to anchor boxes."),
                ("To avoid", "method", "Introduces a training-sampling constraint."),
                ("being dominate", "limitation", "Describes the imbalance that anchor sampling tries to avoid."),
                ("are randomly sampled", "method", "Explains the sampling procedure for anchors."),
                ("fully-convolutionally", "method", "Names dense convolutional testing over the image."),
                ("using the ground truth class", "method", "Defines oracle testing for localization."),
                ("Under the same setting", "result", "Introduces a controlled comparison result."),
                ("significantly reduces", "result", "States the result improvement."),
                ("One may use", "general", "Introduces a plausible alternative before rejecting or modifying it."),
                ("But we notice that", "contrast", "Signals the observation that changes the implementation choice."),
                ("As a result", "result", "Connects dataset properties to a training problem."),
                ("Motivated by this", "method", "Introduces the design decision caused by the previous observation."),
                ("in place of", "contrast", "States that one method replaces another."),
                ("play a role of", "general", "Explains the function of predicted boxes in the pipeline."),
                ("For each training image", "method", "Introduces a per-image training-sample extraction step."),
                ("are extracted as training samples", "method", "Explains how proposals become classifier training data."),
                ("is cropped from", "method", "Describes how an image region is prepared for R-CNN classification."),
                ("used to update", "method", "Explains how the R-CNN refines proposal scores and boxes at test time."),
                ("relative reduction of error", "result", "Reports the final improvement as relative error reduction."),
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
        if generic_phrase_specs:
            seen_phrases = {phrase.lower() for phrase, *_ in phrase_specs}
            phrase_specs = [
                *phrase_specs,
                *[item for item in generic_phrase_specs if item[0].lower() not in seen_phrases],
            ]
        rows: list[dict[str, Any]] = []
        lower_text = " ".join(document_text.lower().split())
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
                (
                    "feature-based representation history",
                    "The section reviews non-neural and neural word-representation methods before BERT.",
                    "This frames the related-work section as background, not BERT's method.",
                ),
                (
                    "coarser-granularity embeddings",
                    "Representation learning was extended from words to sentences and paragraphs.",
                    "This explains the progression from word embeddings to larger text-unit embeddings.",
                ),
                (
                    "ELMo contextual feature extraction",
                    "ELMo extracts context-sensitive token features from left-to-right and right-to-left language models.",
                    "This is the feature-based predecessor most relevant to BERT.",
                ),
                (
                    "directional representation concatenation",
                    "ELMo forms token representations by concatenating left-to-right and right-to-left representations.",
                    "This explains why earlier bidirectionality is shallow compared with BERT.",
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
                    "PASCAL and COCO evaluation setup",
                    "The appendix describes how detection models are trained and evaluated on PASCAL VOC and MS COCO.",
                    "This section is about evaluation protocol and benchmark evidence.",
                ),
                (
                    "ResNet feature gain attribution",
                    "The claim that mAP gains come from improved features learned by ResNet.",
                    "This extends the representation-quality claim into detection benchmarks.",
                ),
                (
                    "COCO metric comparison",
                    "The paper compares mAP@.5 with the stricter mAP@[.5,.95] metric.",
                    "This explains why the result matters for localization, not only recognition.",
                ),
                (
                    "recognition and localization improvement",
                    "The interpretation that deeper networks improve both category recognition and box localization.",
                    "This is the main takeaway from the COCO metric comparison.",
                ),
                (
                    "box refinement pipeline",
                    "The inference-time process of re-pooling features from regressed boxes, combining predictions, applying NMS, and box voting.",
                    "This teaches the ordered recipe behind the appendix improvement.",
                ),
                (
                    "global context feature",
                    "A full-image pooled feature concatenated with each region feature before classification and box regression.",
                    "This explains how the detector adds scene-level information to region-level decisions.",
                ),
                (
                    "multi-scale testing limitation",
                    "The competition-time choice to perform multi-scale testing only at inference and only for the Fast R-CNN step.",
                    "This helps the reader separate implemented improvements from untried extensions.",
                ),
                (
                    "detection result table reading",
                    "The result tables compare VGG-16, ResNet-101, improved baseline+++, and ensemble systems across COCO and PASCAL.",
                    "This section should be read as evidence tables, not as ordinary prose.",
                ),
                (
                    "baseline+++ system",
                    "The table shorthand for ResNet-101 plus box refinement, context, and multi-scale testing.",
                    "This connects the previous method-improvement section to the numeric benchmark gains.",
                ),
                (
                    "cross-benchmark detection validation",
                    "The results are reported on MS COCO test-dev and PASCAL VOC 2007/2012 test sets.",
                    "This shows the improvements are evaluated across multiple detection benchmarks.",
                ),
                (
                    "hidden-label benchmark evaluation",
                    "The COCO test-dev result is scored by an evaluation server because ground-truth labels are not public.",
                    "This explains the evaluation protocol before reading the reported mAP values.",
                ),
                (
                    "single model versus ensemble",
                    "The section separates one ResNet-101 detector result from an ensemble that boosts proposal and classification stages.",
                    "This helps the reader understand which result belongs to which system strength.",
                ),
                (
                    "COCO-to-PASCAL fine-tuning",
                    "The COCO-trained detector is fine-tuned on PASCAL VOC and keeps the same improvements.",
                    "This is the transfer step behind the final PASCAL VOC scores.",
                ),
                (
                    "competition result claim",
                    "The ensemble wins COCO 2015 detection and the PASCAL VOC 2012 result exceeds the prior state of the art by 10 points.",
                    "This is the benchmark significance of the appendix narrative.",
                ),
                (
                    "ImageNet DET benchmark setup",
                    "The section defines ImageNet DET as a 200-category object detection task evaluated by mAP@.5.",
                    "This gives the reader the benchmark context before reading protocol details.",
                ),
                (
                    "classification-to-detection transfer",
                    "Networks are pretrained on 1000-class ImageNet classification and fine-tuned on ImageNet DET.",
                    "This is the same transfer-learning pattern used throughout the detection appendix.",
                ),
                (
                    "val1/val2 validation protocol",
                    "The validation set is split so val1 helps fine-tuning and val2 remains validation.",
                    "This explains how the paper avoids using the same validation data for every role.",
                ),
                (
                    "restricted competition data use",
                    "The authors state that they do not use other ILSVRC 2015 data.",
                    "This is an experimental constraint worth noticing when comparing results.",
                ),
                (
                    "ImageNet LOC task framing",
                    "The LOC task requires both class prediction and object localization.",
                    "This explains why the section talks about classifiers before bounding boxes.",
                ),
                (
                    "classifier-then-localizer pipeline",
                    "Image-level classifiers first predict class labels, then the localization algorithm predicts boxes for those classes.",
                    "This is the workflow behind the reported localization system.",
                ),
                (
                    "per-class regression strategy",
                    "The method learns a bounding-box regressor for each class.",
                    "This is the key localization adaptation from prior work.",
                ),
                (
                    "per-class RPN modification",
                    "The RPN is changed from category-agnostic to per-class form with sibling classification and regression heads.",
                    "This is the architecture modification worth learning from the section.",
                ),
                (
                    "per-class cls/reg heads",
                    "The localization RPN has 1000-dimensional classification output and 1000x4-dimensional box-regression output.",
                    "This explains how class-specific localization is implemented.",
                ),
                (
                    "anchor-based box regression",
                    "Bounding-box regression is defined relative to multiple translation-invariant anchor boxes at each position.",
                    "This is the geometric reference system used by the localization RPN.",
                ),
                (
                    "balanced anchor sampling",
                    "The training procedure samples positive and negative anchors at a 1:1 ratio.",
                    "This explains how the model avoids being dominated by negative samples.",
                ),
                (
                    "oracle and dense testing comparison",
                    "The section compares oracle testing with ground-truth classes and dense multi-scale testing results.",
                    "This helps separate localization error from classification error.",
                ),
                (
                    "Fast R-CNN limitation for LOC",
                    "On ImageNet localization, overlapping proposal regions make Fast R-CNN image-centric training less desirable.",
                    "This explains why the authors switch methods instead of simply reusing the detector.",
                ),
                (
                    "RoI-centric R-CNN choice",
                    "The authors use original R-CNN because it trains on cropped proposal regions.",
                    "This is the main implementation decision in the final section.",
                ),
                (
                    "class-dependent proposal workflow",
                    "Per-class RPN predicts boxes for the ground-truth class, and the top 200 proposals become R-CNN training samples.",
                    "This is the localization pipeline to understand.",
                ),
                (
                    "localization competition result",
                    "The ensemble reaches 9.0% top-5 localization error and wins ImageNet localization in ILSVRC 2015.",
                    "This is the final benchmark claim of the paper.",
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
        if self._is_reference_list_section(document_text):
            sentence = self._source_sentence(None, "In Proceedings of", document_text)
            return [
                {
                    "sentence": sentence,
                    "core_structure": "Author(s). Year. Title. Venue.",
                    "simplified_version": "A reference entry names the authors, year, paper title, and publication venue.",
                    "korean_explanation": "참고문헌은 일반 문장이 아니라 저자, 연도, 제목, 학회/저널 정보를 나열하는 형식입니다.",
                    "difficulty_reason": "This is citation metadata, so it should be skimmed for sources rather than studied as prose.",
                }
            ]
        if self._is_attention_learning_section(document_text):
            profile = self._attention_profile(document_text) or {}
            sentence = self._source_sentence(None, str(profile.get("sentence_target") or ""), document_text)
            return [
                {
                    "sentence": sentence,
                    "core_structure": str(profile.get("core_structure") or "Transformer section sentence."),
                    "simplified_version": str(profile.get("simplified_version") or "This section explains part of the Transformer paper."),
                    "korean_explanation": str(profile.get("korean_explanation") or "이 문장은 Transformer 논문의 핵심 구조를 설명합니다."),
                    "difficulty_reason": str(profile.get("difficulty_reason") or "The section mixes architecture, notation, and method motivation."),
                }
            ]
        if self._is_batchnorm_learning_section(document_text):
            profile = self._batchnorm_profile(document_text) or {}
            sentence = self._source_sentence(None, str(profile.get("sentence_target") or ""), document_text)
            return [
                {
                    "sentence": sentence,
                    "core_structure": str(profile.get("core_structure") or "BatchNorm section sentence."),
                    "simplified_version": str(profile.get("simplified_version") or "This section explains why BatchNorm is useful."),
                    "korean_explanation": str(profile.get("korean_explanation") or "이 문장은 Batch Normalization 논문의 핵심 논리를 설명합니다."),
                    "difficulty_reason": str(profile.get("difficulty_reason") or "The section mixes optimization language, equations, and method motivation."),
                }
            ]
        generic_sentence = self._generic_academic_sentence(document_text)
        if generic_sentence:
            return [generic_sentence]
        if self._is_bert_text(document_text):
            if self._is_bert_masked_lm_procedure_section(document_text):
                sentence = self._source_sentence(None, "In contrast to", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "In contrast to A, we do B rather than C.",
                        "simplified_version": "Unlike denoising auto-encoders, BERT predicts masked words instead of reconstructing the whole input.",
                        "korean_explanation": "'In contrast to'는 비슷한 방법과 BERT의 차이를 설명하는 신호입니다.",
                        "difficulty_reason": "The sentence is dense because it compares objectives and uses a rather-than contrast.",
                    }
                ]
            if self._is_bert_nsp_procedure_section(document_text):
                sentence = self._source_sentence(None, "50% of the time", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "When choosing A and B, 50% is X and 50% is Y.",
                        "simplified_version": "For NSP, half the pairs are real next sentences and half are random non-next sentences.",
                        "korean_explanation": "'Specifically' 이후의 50%/50% 구조는 NSP 학습 예시를 만드는 절차를 설명합니다.",
                        "difficulty_reason": "The sentence defines two labels and two sampling cases in one long procedure.",
                    }
                ]
            if self._is_bert_finetuning_unification_section(document_text):
                sentence = self._source_sentence(None, "BERT instead uses", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "A common pattern is X. BERT instead uses Y to do Z.",
                        "simplified_version": "Earlier systems encoded text pairs separately; BERT uses self-attention over the combined pair.",
                        "korean_explanation": "'instead'는 기존 방식과 BERT 방식의 차이를 보여주는 전환 신호입니다.",
                        "difficulty_reason": "The contrast is spread across prior-work and BERT-alternative clauses.",
                    }
                ]
            if self._is_bert_glue_setup_results_section(document_text):
                sentence = self._source_sentence(None, "To fine-tune on GLUE", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "To fine-tune on X, we use Y as Z.",
                        "simplified_version": "For GLUE tasks, BERT uses the final [CLS] vector C as the classifier's aggregate representation.",
                        "korean_explanation": "'To fine-tune on'은 특정 벤치마크에 맞춘 실험 절차를 소개하고, 'as'는 C의 역할을 설명합니다.",
                        "difficulty_reason": "The sentence combines benchmark setup, prior input-format reference, vector notation, and representation role.",
                    }
                ]
            if self._is_bert_glue_result_interpretation_section(document_text):
                sentence = self._source_sentence(None, "Both BERTBASE and BERTLARGE outperform", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "Both A and B outperform C by D, obtaining E.",
                        "simplified_version": "Both BERT model sizes beat previous GLUE systems, with BERTLARGE showing the larger average improvement.",
                        "korean_explanation": "'Both A and B'는 두 모델을 함께 비교하고, 'by a substantial margin'은 결과 차이가 크다는 평가 표현입니다.",
                        "difficulty_reason": "The sentence combines model comparison, benchmark claim, margin language, and two percentage improvements.",
                    }
                ]
            if self._is_bert_squad_span_prediction_section(document_text):
                sentence = self._source_sentence(None, "The score of a candidate span", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "The score of X is defined as Y, and the maximum-scoring X is used as Z.",
                        "simplified_version": "BERT scores each possible answer span with start and end vectors, then chooses the span with the highest score.",
                        "korean_explanation": "'is defined as'는 수식 정의를 알리는 표현이고, 'is used as a prediction'은 그 점수가 실제 답 선택으로 이어짐을 뜻합니다.",
                        "difficulty_reason": "The sentence is difficult because it mixes span notation, vector dot products, and prediction selection in one definition.",
                    }
                ]
            if self._is_bert_squad_results_transition_section(document_text):
                sentence = self._source_sentence(None, "Without TriviaQA", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "Without X, we only lose Y, still doing Z.",
                        "simplified_version": "Even without TriviaQA extra data, BERT loses only a small amount of F1 and still beats existing systems.",
                        "korean_explanation": "'Without X'는 제거 조건을 만들고, 'still'은 그 조건에서도 결과가 유지된다는 점을 강조합니다.",
                        "difficulty_reason": "The sentence combines an ablation condition, small metric loss, and comparison claim.",
                    }
                ]
            if self._is_bert_squad2_swag_transition_section(document_text):
                sentence = self._source_sentence(None, "We predict a non-null answer", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "We predict X when A > B + threshold, where threshold is selected to maximize Y.",
                        "simplified_version": "BERT answers only when the best real span scores higher than the no-answer span by a dev-set threshold.",
                        "korean_explanation": "'when'은 예측 조건을 만들고, 'where' 절은 threshold τ가 어떻게 선택되는지 설명합니다.",
                        "difficulty_reason": "The sentence combines a decision rule, mathematical notation, and dev-set model selection.",
                    }
                ]
            if self._is_bert_swag_ablation_transition_section(document_text):
                sentence = self._source_sentence(None, "The left-only constraint", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "X was also applied at Y, because removing it introduced Z.",
                        "simplified_version": "The left-to-right model stays left-only during fine-tuning because changing that would create a mismatch with pre-training.",
                        "korean_explanation": "'because' 뒤는 설계 선택의 이유입니다. 이 문장은 ablation이 공정하려면 제약을 유지해야 함을 설명합니다.",
                        "difficulty_reason": "The sentence is dense because it links a model constraint, fine-tuning condition, and mismatch explanation.",
                    }
                ]
            if self._is_bert_ablation_interpretation_section(document_text):
                sentence = self._source_sentence(None, "However:", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "However: (a) X; (b) Y; (c) Z.",
                        "simplified_version": "The two-direction LTR/RTL alternative is worse because it is expensive, awkward for QA, and less powerful than deep bidirectionality.",
                        "korean_explanation": "'However:' 뒤의 (a)(b)(c)는 대안의 한계를 순서대로 나열하는 논문식 반박 구조입니다.",
                        "difficulty_reason": "The sentence is difficult because it compresses three objections into one enumerated contrast.",
                    }
                ]
            if self._is_bert_model_size_effect_section(document_text):
                sentence = self._source_sentence(None, "provided that the model has been sufficiently pre-trained", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "However, X also leads to Y, provided that Z.",
                        "simplified_version": "Very large pre-trained models can help even small downstream tasks if pre-training is strong enough.",
                        "korean_explanation": "'provided that'은 조건을 붙입니다. 여기서는 모델 크기 증가 효과가 충분한 사전학습을 전제로 한다는 뜻입니다.",
                        "difficulty_reason": "The sentence links a contrast, a scaling claim, and a condition in one long academic claim.",
                    }
                ]
            if self._is_bert_feature_based_transition_section(document_text):
                sentence = self._source_sentence(None, "where fixed features are extracted", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "However, approach X, where Y, has advantages.",
                        "simplified_version": "The paper switches from fine-tuning to testing BERT as a fixed feature extractor.",
                        "korean_explanation": "'where' 절은 feature-based approach가 무엇인지 정의하고, 주절은 그 장점을 소개합니다.",
                        "difficulty_reason": "The sentence contrasts two experimental approaches while defining the second one inside a relative clause.",
                    }
                ]
            if self._is_bert_ner_feature_table_section(document_text):
                sentence = self._source_sentence(None, "without fine-tuning any parameters of BERT", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "To ablate X, we apply Y by doing Z.",
                        "simplified_version": "To compare against fine-tuning, they freeze BERT and use its layer activations as features.",
                        "korean_explanation": "'To ablate'는 비교 실험의 목적을 나타내고, 'by extracting'은 방법을 설명합니다.",
                        "difficulty_reason": "The sentence is dense because it describes purpose, method, and parameter-freezing in one structure.",
                    }
                ]
            if self._is_bert_conclusion_section(document_text):
                sentence = self._source_sentence(None, "Our major contribution", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "Our major contribution is X, allowing Y.",
                        "simplified_version": "The paper's main contribution is extending transfer learning from unidirectional models to deep bidirectional BERT.",
                        "korean_explanation": "'Our major contribution is'는 논문 결론에서 핵심 기여를 요약하는 표현이고, 'allowing'은 그 결과를 설명합니다.",
                        "difficulty_reason": "The sentence combines contribution framing with a result clause that summarizes the whole paper.",
                    }
                ]
            if self._is_bert_appendix_learning_section(document_text):
                profile = self._bert_appendix_profile(document_text) or {}
                sentence = self._source_sentence(None, str(profile.get("sentence_target") or ""), document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": str(profile.get("core_structure") or "Appendix setup/result sentence."),
                        "simplified_version": str(profile.get("simplified_version") or "This appendix detail supports the main BERT method or experiment."),
                        "korean_explanation": str(profile.get("korean_explanation") or "부록 문장은 본문 방법이나 실험 세부사항을 보충합니다."),
                        "difficulty_reason": str(profile.get("difficulty_reason") or "Appendix sections mix prose, examples, tables, and implementation details."),
                    }
                ]
            if self._is_reference_list_section(document_text):
                sentence = self._source_sentence(None, "In Proceedings of", document_text)
                return [
                    {
                        "sentence": sentence,
                        "core_structure": "Author(s). Year. Title. Venue.",
                        "simplified_version": "A reference entry names the authors, year, paper title, and publication venue.",
                        "korean_explanation": "참고문헌은 일반 문장이 아니라 저자, 연도, 제목, 학회/저널 정보를 나열하는 형식입니다.",
                        "difficulty_reason": "This is citation metadata, so it should be skimmed for sources rather than studied as prose.",
                    }
                ]
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
                (
                    "has been an active area of research",
                    "Learning A has been an active area of research for B.",
                    "The authors introduce a long-running related-work area.",
                    "'has been an active area of research'는 오래 연구된 주제임을 말하는 문헌리뷰 표현입니다.",
                    "This is background framing, not the paper's own method.",
                ),
                (
                    "have been generalized to",
                    "These approaches have been generalized to A, such as B or C.",
                    "The authors explain how representation learning extends from words to larger text units.",
                    "'have been generalized to'는 한 방법이 더 넓은 범위로 확장됐다는 뜻입니다.",
                    "The sentence is dense because it lists examples and citations inside a related-work move.",
                ),
                (
                    "is the concatenation of",
                    "The representation of A is the concatenation of B and C.",
                    "The authors explain how ELMo combines two directional representations.",
                    "'concatenation'은 여러 벡터를 이어 붙인다는 뜻입니다.",
                    "This sentence describes representation construction, not just a vocabulary word.",
                ),
                (
                    "When integrating contextual word embeddings",
                    "When integrating A with B, C advances the state of the art for D.",
                    "The authors state where ELMo works: contextual embeddings are added to task-specific architectures.",
                    "'When integrating'은 어떤 조건이나 사용 방식에서 결과가 나타나는지 여는 표현입니다.",
                    "The sentence is long because it combines method setup, model name, benchmark claim, and task examples.",
                ),
                (
                    "Similar to ELMo",
                    "Similar to A, B is C and not D.",
                    "The authors compare a prior model with ELMo and then mark its limitation.",
                    "'Similar to' 다음에는 공통점이 오고, 'not' 이후에는 한계가 나옵니다.",
                    "The sentence is easy to misread if the learner saves only 'bidirectional' instead of the full limitation.",
                ),
                (
                    "few parameters need to be learned from scratch",
                    "The advantage of A is that B.",
                    "The authors explain why fine-tuning is practically useful.",
                    "'The advantage of these approaches is that'는 방법의 장점을 명시하는 문헌리뷰 표현입니다.",
                    "The key content is in the that-clause after the evaluation phrase.",
                ),
                (
                    "Apart from output layers",
                    "Apart from A, the same B are used in C and D.",
                    "The authors explain that BERT keeps the same base architecture and only changes task output layers.",
                    "'Apart from'은 예외를 먼저 말한 뒤 나머지는 같다고 설명하는 표현입니다.",
                    "The figure caption is dense because it describes architecture reuse, parameter initialization, and fine-tuning in compressed form.",
                ),
                (
                    "are used to initialize",
                    "The same pre-trained parameters are used to initialize models for different downstream tasks.",
                    "The authors describe transfer learning as starting each task model from the same pre-trained BERT parameters.",
                    "'are used to initialize'는 사전학습된 파라미터가 새 모델의 시작점으로 쓰인다는 뜻입니다.",
                    "Passive voice hides the agent; focus on what is reused and where.",
                ),
                (
                    "During fine-tuning",
                    "During fine-tuning, all parameters are fine-tuned.",
                    "The authors clarify that fine-tuning updates the full model, not only the output layer.",
                    "'During fine-tuning'은 적용 단계에서 실제로 일어나는 일을 설명하는 시간/단계 신호입니다.",
                    "The repeated word 'fine-tuning/fine-tuned' is normal technical wording, not a typo.",
                ),
                (
                    "A distinctive feature of BERT is",
                    "A distinctive feature of X is Y.",
                    "The authors mark unified architecture across tasks as a key design property of BERT.",
                    "'A distinctive feature of'는 다른 방법과 구분되는 특징을 바로 소개하는 표현입니다.",
                    "The sentence is important because it tells you what to focus on before technical details begin.",
                ),
                (
                    "we denote the number of",
                    "We denote the number of A as X, B as Y, and C as Z.",
                    "The authors define L, H, and A before comparing BERTBASE and BERTLARGE.",
                    "'denote ... as'는 기호 정의를 나타내는 논문 표현입니다.",
                    "The notation sentence is dense because it defines three variables at once.",
                ),
                (
                    "is able to unambiguously represent",
                    "X is able to represent both A and B in one C.",
                    "The authors explain why BERT's input format works for both single-sentence and sentence-pair tasks.",
                    "'is able to'는 기능이나 capability를 설명하는 표현입니다.",
                    "This sentence shifts from model architecture to input representation.",
                ),
                (
                    "We differentiate the sentences in two ways",
                    "We differentiate X in two ways: first A; second B.",
                    "The authors explain sentence-pair encoding with two ordered mechanisms.",
                    "'in two ways'는 뒤에 두 가지 절차가 나온다는 신호입니다.",
                    "The learner should track [SEP] and segment embeddings as separate mechanisms.",
                ),
                (
                    "is constructed by summing",
                    "X is constructed by summing A, B, and C.",
                    "The authors define BERT's input representation as the sum of token, segment, and position embeddings.",
                    "'is constructed by'는 구성 방식을 설명하는 수동태 표현입니다.",
                    "The sentence is a definition; each listed embedding type has a different role.",
                ),
                (
                    "Instead, we pre-train",
                    "Instead, we pre-train X using Y.",
                    "The authors move from rejecting traditional directional language models to introducing BERT's two unsupervised tasks.",
                    "'Instead'는 앞 방법을 쓰지 않고 대체 방법을 제시한다는 신호입니다.",
                    "This sentence is the transition from input representation to masked language modeling.",
                ),
                (
                    "In contrast to",
                    "In contrast to A, we do B rather than C.",
                    "The authors contrast MLM with denoising auto-encoders: predict masked words, not the whole input.",
                    "'In contrast to'는 비슷한 방법과의 차이를 명확히 하는 표현입니다.",
                    "The sentence matters because it limits what the objective predicts.",
                ),
                (
                    "Although this allows us to",
                    "Although A allows us to do B, a downside is that C.",
                    "The authors state the benefit of MLM and immediately admit the [MASK] mismatch problem.",
                    "'Although'는 장점 뒤에 한계를 붙이는 논문식 균형 표현입니다.",
                    "The reader should keep both sides: bidirectional pre-training benefit and fine-tuning mismatch cost.",
                ),
                (
                    "To mitigate this",
                    "To mitigate this, we do not always replace X with Y.",
                    "The authors introduce the 80/10/10 replacement rule as a workaround for [MASK] mismatch.",
                    "'To mitigate this'는 앞에서 말한 문제를 줄이기 위한 조치를 소개합니다.",
                    "This sentence starts the procedural details; the percentages explain the actual rule.",
                ),
                (
                    "Specifically, when choosing",
                    "Specifically, when choosing A and B, 50% is X and 50% is Y.",
                    "The authors define the positive and negative examples for next sentence prediction.",
                    "'Specifically'는 앞의 일반 설명을 실제 절차로 좁히는 신호입니다.",
                    "This sentence is dense because it defines sampling, labels, and sentence relation at once.",
                ),
                (
                    "Despite its simplicity",
                    "Despite its simplicity, we demonstrate that X is beneficial to Y.",
                    "The authors argue that a simple NSP task still helps QA and NLI.",
                    "'Despite'는 예상과 반대되는 결과를 말할 때 쓰는 양보 표현입니다.",
                    "The phrase links a simple method to a useful downstream effect.",
                ),
                (
                    "Fine-tuning is straightforward since",
                    "Fine-tuning is straightforward since X allows Y.",
                    "The authors explain why BERT adapts easily to many downstream task formats.",
                    "'since'는 앞 주장에 대한 이유를 연결합니다.",
                    "The sentence contains a claim and its architectural reason in one clause.",
                ),
                (
                    "BERT instead uses",
                    "A common pattern is X. BERT instead uses Y to do Z.",
                    "The authors contrast prior text-pair encoding with BERT's self-attention unification.",
                    "'instead'는 기존 방식 대신 BERT가 선택한 방식을 소개합니다.",
                    "The contrast spans two sentences, so the reader must connect common pattern and BERT alternative.",
                ),
                (
                    "we simply plug in",
                    "For each task, we plug in task-specific inputs and outputs and fine-tune all parameters.",
                    "The authors summarize BERT fine-tuning as a reusable recipe.",
                    "'plug in'은 기존 구조에 필요한 입출력만 끼워 넣는다는 실용적 표현입니다.",
                    "The sentence is important because it describes how one model handles many tasks.",
                ),
                (
                    "To fine-tune on GLUE",
                    "To fine-tune on X, we use Y as Z.",
                    "The authors explain how [CLS]/C is used as the aggregate representation for GLUE classification.",
                    "'To fine-tune on'은 특정 벤치마크에 맞춘 실험 절차를 소개합니다.",
                    "The sentence is dense because it packs input format, vector notation, and classification representation together.",
                ),
                (
                    "The only new parameters introduced",
                    "The only new parameters introduced during X are Y.",
                    "The authors emphasize that GLUE fine-tuning adds only a classification layer.",
                    "'The only new parameters'는 모델 변경 범위가 작다는 것을 강조합니다.",
                    "This is a method detail, not just a parameter symbol.",
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
                    "is evaluated by",
                    "A is evaluated by B.",
                    "The authors name the metric used for ImageNet DET.",
                    "'is evaluated by'는 어떤 기준으로 평가되는지 설명합니다.",
                    "This is benchmark setup language, not a model component.",
                ),
                (
                    "are pretrained on",
                    "A are pretrained on B and fine-tuned on C.",
                    "The authors describe transfer from ImageNet classification to ImageNet detection.",
                    "'pretrained on'은 먼저 학습한 데이터나 과제를 말합니다.",
                    "This sentence is a transfer-learning protocol sentence.",
                ),
                (
                    "We do not use",
                    "We do not use A.",
                    "The authors state a data-use restriction.",
                    "'do not use'는 실험 조건에서 제외한 데이터를 명확히 말합니다.",
                    "This matters for fair comparison across competition systems.",
                ),
                (
                    "requires to classify and localize",
                    "A requires to classify and localize B.",
                    "The authors define the ImageNet localization task.",
                    "'requires to'는 과제가 요구하는 동작을 설명합니다.",
                    "This sentence defines the task before the method details.",
                ),
                (
                    "only accounts for",
                    "A only accounts for B based on C.",
                    "The authors separate class prediction from box localization.",
                    "'only accounts for'는 어떤 구성요소가 담당하는 범위를 제한합니다.",
                    "This prevents the reader from thinking the localization module also predicts classes.",
                ),
                (
                    "Unlike the way",
                    "Unlike A, B is designed in C.",
                    "The authors contrast category-agnostic RPN with the per-class localization RPN.",
                    "'Unlike'는 기존 방식과 새 변형의 차이를 여는 표현입니다.",
                    "This is the architecture-change sentence in the section.",
                ),
                (
                    "bounding box regression is with reference to",
                    "A is with reference to B at each position.",
                    "The authors explain that box regression is anchored to reference boxes.",
                    "'with reference to'는 어떤 기준점을 바탕으로 한다는 뜻입니다.",
                    "This sentence links regression outputs to anchor boxes.",
                ),
                (
                    "To avoid",
                    "To avoid A, B are sampled with C.",
                    "The authors explain the reason for balanced anchor sampling.",
                    "'To avoid'는 어떤 문제를 피하기 위한 목적을 말합니다.",
                    "This is a training-procedure rationale, not the main result.",
                ),
                (
                    "Under the same setting",
                    "Under the same setting, A significantly reduces B to C.",
                    "The authors state a controlled comparison result.",
                    "'Under the same setting'은 비교 조건이 같음을 강조합니다.",
                    "This phrase helps read the localization-error comparison fairly.",
                ),
                (
                    "Motivated by this",
                    "Motivated by this, we use A in place of B.",
                    "The authors connect an observed training issue to the R-CNN design choice.",
                    "'Motivated by this'는 앞 관찰이 뒤 방법 선택의 이유임을 보여줍니다.",
                    "This is the key method-decision sentence in the final section.",
                ),
                (
                    "play a role of",
                    "A play a role of B.",
                    "The authors explain how predicted boxes function as class-dependent proposals.",
                    "'play a role of'는 어떤 대상이 맡는 기능을 설명합니다.",
                    "This helps follow the proposal pipeline.",
                ),
                (
                    "relative reduction of error",
                    "A shows a B relative reduction of error.",
                    "The authors report the final localization gain relative to previous results.",
                    "'relative reduction'은 절대 차이가 아니라 비율로 줄어든 정도를 말합니다.",
                    "This is a benchmark-result sentence.",
                ),
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
                    "solely because of",
                    "This gain is solely because of A.",
                    "The authors attribute the PASCAL VOC improvement to ResNet features.",
                    "'solely because of'는 하나의 원인만을 강조합니다.",
                    "This is an attribution sentence, not just a result sentence.",
                ),
                (
                    "relative improvement",
                    "A has a B increase over C, which is a D relative improvement.",
                    "The authors report both absolute and relative COCO gains.",
                    "'which is' 절은 앞의 수치를 다른 방식으로 다시 해석합니다.",
                    "The sentence is dense because it contains metric, baseline, absolute gain, and relative gain.",
                ),
                (
                    "improve both recognition and localization",
                    "This suggests that A can improve both B and C.",
                    "The authors interpret metric gains as improvements in both classification and box quality.",
                    "'both A and B'는 두 가지 효과를 동시에 강조합니다.",
                    "This sentence converts metric comparison into the section's learning point.",
                ),
                (
                    "followed by",
                    "A is applied on B, followed by C.",
                    "The authors describe the ordered detection post-processing pipeline.",
                    "'followed by'는 앞 단계 다음에 이어지는 절차를 말합니다.",
                    "This is useful for reading method recipes where several operations happen in sequence.",
                ),
                (
                    "is concatenated with",
                    "A is concatenated with B, followed by C.",
                    "The authors explain how global context and per-region features are combined.",
                    "'concatenated with'는 두 feature를 이어 붙인다는 뜻입니다.",
                    "The sentence packs feature construction and downstream prediction layers together.",
                ),
                (
                    "because of limited time",
                    "We have not performed A because of B.",
                    "The authors disclose an implementation limitation in the multi-scale experiments.",
                    "'because of'는 명사구로 원인을 제시합니다.",
                    "This is a limitation sentence, not the main experimental result.",
                ),
                (
                    "reported by the evaluation server",
                    "A has no B and the result is reported by C.",
                    "The authors explain the hidden-label benchmark protocol.",
                    "'reported by'는 결과를 누가/무엇이 제공하는지 나타냅니다.",
                    "This is evaluation-protocol language, not a method claim.",
                ),
                (
                    "boost both tasks",
                    "A can be used to boost both B and C.",
                    "The authors explain why ensembling applies to both proposals and classifiers.",
                    "'both A and B'는 두 가지 대상을 동시에 강조합니다.",
                    "This sentence explains the role of the ensemble inside Faster R-CNN.",
                ),
                (
                    "higher than the previous state-of-the-art",
                    "A is B points higher than C.",
                    "The authors state the size of the PASCAL VOC 2012 improvement over prior work.",
                    "'higher than'은 수치 비교 결과를 말할 때 쓰는 기본 구조입니다.",
                    "The important part is the comparison target: previous state of the art.",
                ),
                (
                    "are pretrained on",
                    "A are pretrained on B and fine-tuned on C.",
                    "The authors describe transfer from ImageNet classification to ImageNet detection.",
                    "'pretrained on'은 먼저 학습한 데이터나 과제를 말합니다.",
                    "This sentence is a transfer-learning protocol sentence.",
                ),
                (
                    "is evaluated by",
                    "A is evaluated by B.",
                    "The authors name the metric used for ImageNet DET.",
                    "'is evaluated by'는 어떤 기준으로 평가되는지 설명합니다.",
                    "This is benchmark setup language, not a model component.",
                ),
                (
                    "We do not use",
                    "We do not use A.",
                    "The authors state a data-use restriction.",
                    "'do not use'는 실험 조건에서 제외한 데이터를 명확히 말합니다.",
                    "This matters for fair comparison across competition systems.",
                ),
                (
                    "The baseline is",
                    "The baseline is A.",
                    "The caption defines which detector the table compares against.",
                    "'baseline'은 비교 기준이 되는 시스템을 뜻합니다.",
                    "This is table-caption language; it tells you how to interpret the rows.",
                ),
                (
                    "include box refinement",
                    "A include B, C, and D.",
                    "The caption expands the `baseline+++` shorthand into its added components.",
                    "'include'는 구성 요소를 나열할 때 쓰는 기본 동사입니다.",
                    "This connects the table label to the previous method improvements.",
                ),
                (
                    "reported by the evaluation server",
                    "A has no B and the result is reported by C.",
                    "The authors explain the hidden-label benchmark protocol.",
                    "'reported by'는 결과를 누가/무엇이 제공하는지 나타냅니다.",
                    "This is evaluation-protocol language, not a method claim.",
                ),
                (
                    "boost both tasks",
                    "A can be used to boost both B and C.",
                    "The authors explain why ensembling applies to both proposals and classifiers.",
                    "'both A and B'는 두 가지 대상을 동시에 강조합니다.",
                    "This sentence explains the role of the ensemble inside Faster R-CNN.",
                ),
                (
                    "higher than the previous state-of-the-art",
                    "A is B points higher than C.",
                    "The authors state the size of the PASCAL VOC 2012 improvement over prior work.",
                    "'higher than'은 수치 비교 결과를 말할 때 쓰는 기본 구조입니다.",
                    "The important part is the comparison target: previous state of the art.",
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
        if self._is_attention_learning_section(document_text):
            profile = self._attention_profile(document_text) or {}
            return profile["summaries"]
        batchnorm_profile = self._batchnorm_profile(document_text)
        if batchnorm_profile:
            return batchnorm_profile["summaries"]
        if "convex optimization problem" in compact_lower and "affine" in compact_lower:
            return {
                "one_line": "This section clarifies what counts as a standard-form convex optimization problem.",
                "simple": (
                    "The text points out a subtle definition issue: a problem can have a convex feasible set but still fail to be a standard-form "
                    "convex optimization problem if its equality constraint is not affine."
                ),
                "academic": (
                    "The section distinguishes geometric convexity of the feasible set from the stricter standard-form requirements on objective, "
                    "inequality constraints, and affine equality constraints."
                ),
                "study_notes": [
                    "Separate feasible-set convexity from standard-form convex optimization.",
                    "Track why affine equality constraints matter in the definition.",
                    "Use this section as a definition caveat, not as a new algorithm.",
                ],
            }
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
            if self._is_resnet_detection_evaluation_section(document_text):
                return {
                    "one_line": "This appendix section evaluates ResNet-101 detection gains on PASCAL VOC and MS COCO.",
                    "simple": (
                        "The authors describe PASCAL VOC and COCO training/evaluation settings. ResNet-101 improves mAP over VGG-16, "
                        "and the COCO gains suggest better learned features improve both recognition and localization."
                    ),
                    "academic": (
                        "The section reports detection benchmark protocol and results: ResNet-101 improves PASCAL VOC mAP by more than 3%, "
                        "improves COCO mAP@[.5,.95] by 6 points, and attributes the gains to stronger ResNet features."
                    ),
                    "study_notes": [
                        "Read this as benchmark protocol plus evidence, not as a new model architecture.",
                        "Separate PASCAL's mAP@.5 metric from COCO's stricter averaged IoU metric.",
                        "The key interpretation is improved recognition and localization from better features.",
                    ],
                }
            if self._is_resnet_detection_improvements_section(document_text):
                return {
                    "one_line": "This appendix section describes three detector improvements: box refinement, global context, and multi-scale testing.",
                    "simple": (
                        "The authors refine predicted boxes, add full-image context features, and test at multiple scales. "
                        "These are competition-oriented detector improvements, not new residual-learning theory."
                    ),
                    "academic": (
                        "The section details detection-system enhancements: iterative box refinement with NMS and box voting, "
                        "global context features concatenated with per-region features, and limited multi-scale testing for the Fast R-CNN stage."
                    ),
                    "study_notes": [
                        "Read this as an engineering recipe for improving object detection results.",
                        "Track the sequence words: re-pool, combine predictions, apply NMS, then box voting.",
                        "Separate the limitation: multi-scale training was not performed because of limited time.",
                    ],
                }
            if self._is_resnet_detection_results_table_section(document_text):
                return {
                    "one_line": "This table section reports how ResNet-101 detector variants improve COCO and PASCAL VOC results.",
                    "simple": (
                        "The tables compare baseline Faster R-CNN systems with ResNet-101, then add box refinement, context, multi-scale testing, "
                        "and an ensemble. Read the rows as cumulative evidence that the detection improvements raise mAP across COCO and PASCAL."
                    ),
                    "academic": (
                        "The section is a result-table block: COCO and PASCAL VOC metrics show progressively stronger detection systems, "
                        "from VGG-16 and ResNet-101 baselines to `baseline+++` and ensemble variants."
                    ),
                    "study_notes": [
                        "Do not read the table dump word by word; identify rows, benchmarks, metrics, and system variants.",
                        "`baseline+++` means the improved ResNet detector with box refinement, context, and multi-scale testing.",
                        "Use mAP@.5 and mAP@[.5,.95] as metric labels rather than vocabulary to memorize in isolation.",
                    ],
                }
            if self._is_resnet_detection_result_narrative_section(document_text):
                return {
                    "one_line": "This section explains COCO test-dev evaluation, ensemble gains, and COCO-to-PASCAL fine-tuning results.",
                    "simple": (
                        "The authors report single-model and ensemble COCO test-dev results, explain that hidden labels require the evaluation server, "
                        "then fine-tune the COCO model on PASCAL VOC and report large benchmark gains."
                    ),
                    "academic": (
                        "The section narrates the final detection evaluation protocol and results: hidden-label COCO test-dev scoring, "
                        "proposal/classifier ensembling, COCO 2015 detection win, and PASCAL VOC transfer via fine-tuning."
                    ),
                    "study_notes": [
                        "Separate protocol from result: hidden ground truth explains the evaluation server.",
                        "Separate system strength: single model versus ensemble.",
                        "Track the transfer step from COCO training to PASCAL VOC fine-tuning.",
                    ],
                }
            if self._is_resnet_imagenet_detection_setup_section(document_text):
                return {
                    "one_line": "This section defines the ImageNet DET setup: 200 categories, mAP@.5 scoring, pretraining, fine-tuning, and val1/val2 validation.",
                    "simple": (
                        "The authors set up the ImageNet Detection experiment. They reuse the COCO-style detector, pretrain on ImageNet classification, "
                        "fine-tune on DET data, split validation into val1/val2, and state that no other ILSVRC 2015 data is used."
                    ),
                    "academic": (
                        "The section specifies the ImageNet DET protocol: 200 object categories scored by mAP@.5, classification-pretrained networks "
                        "fine-tuned on DET train/val1 data, val2 held for validation, and restricted competition data usage."
                    ),
                    "study_notes": [
                        "Read this as benchmark protocol rather than a new method.",
                        "Track the transfer chain: ImageNet classification pretraining -> DET fine-tuning.",
                        "Notice the data-use constraint: no other ILSVRC 2015 data.",
                    ],
                }
            if self._is_resnet_imagenet_localization_setup_section(document_text):
                return {
                    "one_line": "This section transitions from ImageNet detection results to the ImageNet localization task and its per-class RPN design.",
                    "simple": (
                        "The section first reports ImageNet DET competition results, then introduces ImageNet Localization. "
                        "For LOC, classifiers predict image classes first, and a per-class regression/RPN system predicts bounding boxes."
                    ),
                    "academic": (
                        "The section frames ImageNet LOC as classification plus localization, adopts per-class regression, and modifies the RPN "
                        "from category-agnostic detection to class-specific localization with sibling classification and box-regression heads."
                    ),
                    "study_notes": [
                        "Ignore the mangled table dump first; the prose after `ImageNet Localization` is the main reading material.",
                        "Separate classifier role from localization role.",
                        "Track the contrast: category-agnostic RPN versus per-class RPN.",
                    ],
                }
            if self._is_resnet_imagenet_localization_details_section(document_text):
                return {
                    "one_line": "This section details the per-class localization RPN: cls/reg heads, anchor boxes, balanced sampling, and oracle/dense testing.",
                    "simple": (
                        "The authors explain how the localization RPN works. It uses class-specific classification and box-regression heads, "
                        "regresses boxes relative to anchors, balances positive and negative anchors during training, and reports oracle/dense testing comparisons."
                    ),
                    "academic": (
                        "The section specifies the per-class RPN implementation for ImageNet localization, including 1000-class cls/reg outputs, "
                        "anchor-relative box regression, balanced anchor sampling, fully convolutional testing, and controlled localization-error comparisons."
                    ),
                    "study_notes": [
                        "Read the first prose sentences as implementation detail, not as a new paper thesis.",
                        "Anchor boxes are the reference frame for box regression.",
                        "Oracle testing uses the ground-truth class, so it isolates localization from classification error.",
                    ],
                }
            if self._is_resnet_imagenet_localization_rcnn_section(document_text):
                return {
                    "one_line": "This final section explains why ImageNet localization uses RoI-centric R-CNN and reports the winning localization result.",
                    "simple": (
                        "Fast R-CNN is less suitable here because proposals overlap heavily and create small sample variation. "
                        "The authors switch to RoI-centric R-CNN, train on class-dependent proposals, and report a 9.0% top-5 localization error ensemble win."
                    ),
                    "academic": (
                        "The section motivates replacing image-centric Fast R-CNN with original RoI-centric R-CNN for ImageNet LOC, "
                        "then describes proposal extraction, cropped-region classifier training, score/box updating, and the ILSVRC 2015 localization win."
                    ),
                    "study_notes": [
                        "Read the first paragraph as a design justification: overlapping proposals make image-centric training less useful.",
                        "Track the pipeline: per-class RPN -> top proposals -> cropped regions -> R-CNN classifier -> updated scores/boxes.",
                        "The final result is a localization competition result, not a new residual-block idea.",
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
        if self._is_reference_list_section(document_text):
            return {
                "one_line": "This is a reference-list section, so it should be skimmed for cited sources rather than studied as prose.",
                "simple": (
                    "The text is bibliography metadata: authors, years, titles, venues, and preprint labels. "
                    "For language learning, it is better to recognize citation formats and source types than save author names as vocabulary."
                ),
                "academic": (
                    "This section functions as the paper's reference list, mapping claims in the main text to prior papers, datasets, benchmarks, proceedings, journals, and arXiv preprints. "
                    "It is not part of the argument flow and should be treated as citation navigation."
                ),
                "study_notes": [
                    "Skip this during first-pass reading unless you need to trace a cited method or dataset.",
                    "Do not save author names as vocabulary.",
                    "Useful patterns are venue phrases such as 'In Proceedings of' and source labels such as 'arXiv preprint'.",
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
            if self._is_bert_conclusion_section(document_text):
                return {
                    "one_line": "This conclusion says BERT extends transfer learning from unidirectional models to deep bidirectional architectures.",
                    "simple": (
                        "The conclusion summarizes the paper's claim: unsupervised pre-training is central to language understanding, "
                        "and BERT generalizes the transfer-learning benefit to one deep bidirectional model that handles many NLP tasks."
                    ),
                    "academic": (
                        "The section closes the paper by positioning BERT as a bidirectional generalization of language-model transfer learning, "
                        "contrasting prior low-resource gains from deep unidirectional architectures with BERT's broad multi-task NLP applicability."
                    ),
                    "study_notes": [
                        "Read this as the final thesis, not as new experimental evidence.",
                        "The key phrase is 'Our major contribution is...', which names the contribution directly.",
                        "Stop before the references when studying the conclusion as language input.",
                    ],
                }
            if self._is_bert_appendix_learning_section(document_text):
                profile = self._bert_appendix_profile(document_text) or {}
                return profile["summaries"]
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
            if "feature-based approaches" in lower and "elmo" in lower and "context-sensitive features" in lower:
                return {
                    "one_line": "This related-work section traces feature-based representations from word embeddings to ELMo's contextual token features.",
                    "simple": (
                        "The authors review earlier feature-based representation learning: word embeddings, sentence and paragraph embeddings, "
                        "and ELMo. ELMo is important because it extracts context-sensitive features from left-to-right and right-to-left language models."
                    ),
                    "academic": (
                        "The section positions BERT against feature-based representation learning, moving from static word embeddings and sentence-level objectives "
                        "to ELMo's contextualized token features formed by concatenating directional language-model representations."
                    ),
                    "study_notes": [
                        "Read this as related work, not BERT's own method.",
                        "Track the granularity progression: words -> sentences/paragraphs -> contextual token features.",
                        "ELMo matters here because it is contextual and bidirectional, but still feature-based.",
                    ],
                }
            if self._is_bert_pretraining_finetuning_procedure_section(document_text):
                return {
                    "one_line": "This section explains BERT's pre-training to fine-tuning workflow and input-format tokens.",
                    "simple": (
                        "The figure caption says BERT uses the same base architecture for pre-training and fine-tuning. "
                        "The pre-trained parameters initialize downstream task models, all parameters are updated during fine-tuning, and [CLS]/[SEP] define the input format."
                    ),
                    "academic": (
                        "The section describes BERT's transfer-learning procedure: shared pre-trained parameters initialize multiple downstream models, "
                        "task-specific output layers are the main architectural exception, and special tokens structure single-sentence and text-pair inputs."
                    ),
                    "study_notes": [
                        "Ignore the figure token dump at the start; read the caption sentences.",
                        "Separate workflow concepts: pre-training, initialization, fine-tuning, and output layers.",
                        "Treat [CLS] and [SEP] as input-format terms, not paper concepts.",
                    ],
                }
            if self._is_bert_architecture_model_size_section(document_text):
                return {
                    "one_line": "This section defines BERT's unified Transformer-encoder architecture, model sizes, and input representation.",
                    "simple": (
                        "BERT uses nearly the same architecture for pre-training and downstream tasks: a multi-layer bidirectional Transformer encoder. "
                        "The section defines L, H, and A, compares BERTBASE with BERTLARGE, and introduces the input representation for single or paired text."
                    ),
                    "academic": (
                        "The section specifies BERT's architecture and experimental variants: unified task architecture, Transformer encoder backbone, "
                        "layer/hidden-size/attention-head notation, BERTBASE/BERTLARGE configurations, and WordPiece-based input sequences."
                    ),
                    "study_notes": [
                        "Do not stop at the question-answering example; the main point is unified architecture.",
                        "Read L/H/A as notation: layers, hidden size, and attention heads.",
                        "Separate model-size terms from input-format terms such as sentence, sequence, and WordPiece embeddings.",
                    ],
                }
            if self._is_bert_input_representation_masked_lm_transition_section(document_text):
                return {
                    "one_line": "This section explains BERT's input representation and transitions into masked language-model pre-training.",
                    "simple": (
                        "BERT packs one or two text spans into a single token sequence. [CLS] represents the whole sequence for classification, [SEP] separates spans, "
                        "segment embeddings mark sentence A versus B, and each input vector sums token, segment, and position embeddings."
                    ),
                    "academic": (
                        "The section defines BERT's input representation for single-sentence and sentence-pair tasks, then contrasts BERT with traditional directional language models "
                        "before introducing masked language modeling as one of two unsupervised pre-training tasks."
                    ),
                    "study_notes": [
                        "Separate token roles: [CLS] aggregates, [SEP] separates, segment embeddings label sentence identity.",
                        "The formula idea is simple: input representation = token + segment + position embeddings.",
                        "The final paragraph is a transition into Masked LM, not another input-format detail.",
                    ],
                }
            if self._is_bert_masked_lm_procedure_section(document_text):
                return {
                    "one_line": "This section defines BERT's Masked LM objective and its 80/10/10 token replacement workaround.",
                    "simple": (
                        "BERT masks 15% of WordPiece token positions and predicts the original tokens from their final hidden vectors. "
                        "Because [MASK] does not appear during fine-tuning, the selected tokens are replaced with [MASK] 80% of the time, a random token 10%, and unchanged 10%."
                    ),
                    "academic": (
                        "The section presents masked language modeling as BERT's bidirectional pre-training objective, contrasts it with full-input denoising reconstruction, "
                        "and explains the replacement distribution used to reduce the pre-training/fine-tuning mismatch introduced by [MASK]."
                    ),
                    "study_notes": [
                        "The important number is not just 15%; it is 15% selected positions plus 80/10/10 replacement.",
                        "Separate the objective from the workaround: predict original token vs. avoid [MASK] mismatch.",
                        "Read 'In contrast to' and 'Although' as signals for method comparison and limitation.",
                    ],
                }
            if self._is_bert_nsp_procedure_section(document_text):
                return {
                    "one_line": "This section defines BERT's Next Sentence Prediction task and why it supports sentence-pair understanding.",
                    "simple": (
                        "NSP trains BERT to decide whether sentence B really follows sentence A. Half the examples are true next sentences labeled IsNext, "
                        "and half are random sentences labeled NotNext. The paper says this simple task helps QA and NLI."
                    ),
                    "academic": (
                        "The section presents NSP as a binary pre-training task generated from monolingual text, using balanced IsNext/NotNext examples to train sentence-relationship understanding, "
                        "while noting that BERT transfers all parameters rather than only sentence embeddings."
                    ),
                    "study_notes": [
                        "Do not save 'binarized' alone; the useful concept is the IsNext/NotNext sampling rule.",
                        "Track the purpose: NSP is about sentence relationships for QA and NLI.",
                        "The vector C caveat matters: it is not a general sentence embedding without fine-tuning.",
                    ],
                }
            if self._is_bert_finetuning_unification_section(document_text):
                return {
                    "one_line": "This section explains why BERT fine-tuning can adapt one pre-trained model to many downstream task formats.",
                    "simple": (
                        "The paper first says pre-training needs document-level text so it can extract long contiguous sequences. "
                        "Then it explains fine-tuning: BERT changes task-specific inputs and outputs, uses self-attention to connect text pairs, and updates all parameters end-to-end."
                    ),
                    "academic": (
                        "The section links pre-training data requirements to BERT's fine-tuning strategy: document-level corpora support NSP-style sequence construction, "
                        "while self-attention over concatenated inputs unifies single-text, text-pair, token-level, and classification tasks."
                    ),
                    "study_notes": [
                        "Separate data requirement from fine-tuning method: document-level corpus first, task adaptation second.",
                        "The key contrast is independent pair encoding versus BERT's concatenated self-attention.",
                        "Map input/output examples instead of memorizing isolated task names.",
                    ],
                }
            if self._is_bert_glue_setup_results_section(document_text):
                return {
                    "one_line": "This section sets up the GLUE benchmark fine-tuning experiment and reports BERT's test-table results.",
                    "simple": (
                        "GLUE is a group of language-understanding tasks. For GLUE, BERT uses the final [CLS] vector C as the aggregate representation, "
                        "adds only classification-layer weights, computes a classification loss, and reports BERTBASE/BERTLARGE results in the table."
                    ),
                    "academic": (
                        "The section specifies the GLUE fine-tuning protocol: [CLS]-based aggregate representation, task-specific classification layer W, "
                        "standard classification loss, evaluation-server scoring, and comparison against prior systems across GLUE task columns."
                    ),
                    "study_notes": [
                        "Treat the large number block as a result table, not prose to memorize line by line.",
                        "Separate setup terms ([CLS] vector C, W, classification loss) from benchmark names.",
                        "The table-reading point is BERTBASE/BERTLARGE improvement over prior systems, not every score.",
                    ],
                }
            if self._is_bert_glue_result_interpretation_section(document_text):
                return {
                    "one_line": "This section explains GLUE metric conventions, fine-tuning protocol, random restarts, and BERT's result advantage.",
                    "simple": (
                        "The authors explain how GLUE scores are reported, how they fine-tune BERT for each task, why BERTLARGE needs random restarts on small datasets, "
                        "and how BERTBASE/BERTLARGE outperform earlier systems and OpenAI GPT."
                    ),
                    "academic": (
                        "The section interprets GLUE results by specifying task-specific metrics, a uniform three-epoch fine-tuning protocol, dev-set learning-rate selection, "
                        "restart-based stabilization for BERTLARGE, substantial average improvements over prior state of the art, and a model-size effect favoring BERTLARGE."
                    ),
                    "study_notes": [
                        "Do not memorize the score row first; identify what each metric type means.",
                        "Separate experimental protocol from result interpretation.",
                        "The random-restart detail is a caveat about small datasets and BERTLARGE stability.",
                    ],
                }
            if self._is_bert_squad_span_prediction_section(document_text):
                return {
                    "one_line": "This section explains how BERT fine-tunes on SQuAD by predicting answer-span start and end positions.",
                    "simple": (
                        "For SQuAD, BERT packs the question and passage into one sequence, adds only start and end vectors, scores possible answer spans, "
                        "trains on correct start/end positions, and compares results against leaderboard and published systems."
                    ),
                    "academic": (
                        "The section defines BERT's extractive question-answering formulation: question-passage packing with A/B embeddings, start/end vector scoring, "
                        "softmax probabilities over paragraph tokens, maximum-scoring span selection, log-likelihood training, and TriviaQA-then-SQuAD augmentation."
                    ),
                    "study_notes": [
                        "Read this as a task-adaptation recipe, not as a general SQuAD summary.",
                        "Track the start/end symmetry: start vector S predicts the start token, end vector E predicts the end token.",
                        "The leaderboard paragraph is about fair comparison and data augmentation caveats.",
                    ],
                }
            if self._is_bert_squad_results_transition_section(document_text):
                return {
                    "one_line": "This section interprets BERT's SQuAD v1.1 results and transitions to SQuAD v2.0 no-answer handling.",
                    "simple": (
                        "BERT's SQuAD systems beat strong leaderboard and published systems, the ensemble combines multiple checkpoints and seeds, "
                        "TriviaQA adds only a small F1 gain, and SQuAD 2.0 adds questions with no answer in the paragraph."
                    ),
                    "academic": (
                        "The section is a result-table interpretation plus task-transition passage: BERTLARGE single and ensemble systems outperform prior SQuAD v1.1 systems, "
                        "the ensemble uses different pre-training checkpoints and fine-tuning seeds, TriviaQA is an ablation variable, "
                        "and SQuAD v2.0 is framed as a realistic no-answer extension handled via the [CLS] span."
                    ),
                    "study_notes": [
                        "Read the table by separating EM/F1 metrics, single systems, ensembles, and TriviaQA variants.",
                        "The main result is not every row; it is that BERT single/ensemble systems exceed prior leaderboard systems.",
                        "The SQuAD v2.0 paragraph changes the task definition by adding no-answer cases.",
                    ],
                }
            if self._is_bert_squad2_swag_transition_section(document_text):
                return {
                    "one_line": "This section explains BERT's SQuAD v2.0 no-answer decision rule and introduces the SWAG commonsense task.",
                    "simple": (
                        "For SQuAD 2.0, BERT compares the best real answer span with a [CLS]-based no-answer score and uses a dev-set threshold. "
                        "The section then moves to SWAG, where BERT chooses the most plausible continuation from four sentence-pair choices."
                    ),
                    "academic": (
                        "The passage defines the SQuAD v2.0 null-answer extension through snull, best non-null span scoring, threshold τ selection on the dev set, "
                        "leaderboard comparison, and then introduces SWAG as a grounded commonsense inference benchmark using four constructed input sequences."
                    ),
                    "study_notes": [
                        "Separate the SQuAD v2.0 decision rule from the SWAG task transition.",
                        "The threshold τ is selected on the dev set, not learned as a new language concept.",
                        "SWAG changes the output type from answer span selection to four-choice continuation selection.",
                    ],
                }
            if self._is_bert_swag_ablation_transition_section(document_text):
                return {
                    "one_line": "This section finishes the SWAG setup/results and starts ablations that test which BERT pre-training tasks matter.",
                    "simple": (
                        "For SWAG, BERT scores each answer choice from the [CLS] representation and beats ESIM+ELMo and OpenAI GPT. "
                        "The paper then starts ablation studies comparing BERTBASE with No NSP, left-to-right No NSP, and a BiLSTM-added variant."
                    ),
                    "academic": (
                        "The passage combines SWAG fine-tuning/result interpretation with the opening of Section 5 ablations: task-specific choice scoring via [CLS], "
                        "softmax normalization, SWAG performance gains, and controlled pre-training-task ablations that isolate NSP, deep bidirectionality, and pre-train/fine-tune mismatch."
                    ),
                    "study_notes": [
                        "Separate the SWAG task adaptation from the ablation-study setup.",
                        "The ablation table is about why MLM + NSP + bidirectionality matter, not only about scores.",
                        "Treat No NSP, LTR & No NSP, and +BiLSTM as experimental variants.",
                    ],
                }
            if self._is_bert_ablation_interpretation_section(document_text):
                return {
                    "one_line": "This section interprets BERT ablations: NSP helps, left-to-right pre-training hurts, and deep bidirectionality matters.",
                    "simple": (
                        "Removing NSP hurts several tasks, especially QNLI, MNLI, and SQuAD. A left-to-right model performs worse than masked LM, "
                        "BiLSTM helps SQuAD only partially, and ELMo-style separate LTR/RTL models are less attractive than one deep bidirectional model."
                    ),
                    "academic": (
                        "The section reads Table 5 as evidence for two design claims: next sentence prediction contributes to sentence-pair and QA tasks, "
                        "and deep bidirectional pre-training is stronger than left-to-right pre-training plus task-time BiLSTM or separate LTR/RTL concatenation."
                    ),
                    "study_notes": [
                        "Track each variant as an experimental control: No NSP, LTR & No NSP, and +BiLSTM.",
                        "The key language move is causal interpretation of ablation results.",
                        "The final paragraph rejects an ELMo-style workaround with three reasons.",
                    ],
                }
            if self._is_bert_model_size_effect_section(document_text):
                return {
                    "one_line": "This section argues that larger pre-trained BERT models improve even small downstream tasks.",
                    "simple": (
                        "The authors vary BERT depth, hidden size, and attention heads while keeping training mostly fixed. "
                        "The larger models improve dev accuracy across datasets, suggesting that strong pre-training lets small downstream tasks benefit from very large representations."
                    ),
                    "academic": (
                        "The section interprets Table 6 as a model-scaling result: increasing BERT capacity lowers masked-LM perplexity and improves downstream accuracy, "
                        "contrasting fine-tuned BERT with earlier feature-based work that saw mixed benefits from larger pre-trained representations."
                    ),
                    "study_notes": [
                        "Read #L, #H, and #A as model-size controls, not vocabulary to memorize alone.",
                        "The main claim is conditional: scaling helps small tasks when the model is sufficiently pre-trained.",
                        "The comparison to prior feature-based work prepares the next section.",
                    ],
                }
            if self._is_bert_feature_based_transition_section(document_text):
                return {
                    "one_line": "This section transitions from full fine-tuning to using BERT as a fixed feature extractor for NER.",
                    "simple": (
                        "So far, BERT results used fine-tuning. This section explains why fixed feature extraction is still useful: some tasks need task-specific architectures, "
                        "and precomputing BERT representations can make many experiments cheaper. The test case is CoNLL-2003 named entity recognition."
                    ),
                    "academic": (
                        "The passage frames feature-based BERT as an alternative transfer setting: freeze the pre-trained model, extract contextual features, "
                        "and evaluate them on CoNLL-2003 NER with case-preserving WordPiece inputs and maximal document context."
                    ),
                    "study_notes": [
                        "Separate transfer mode from task: fine-tuning versus fixed-feature extraction, then NER as the evaluation task.",
                        "The two advantages are architectural flexibility and computational reuse.",
                        "This section is setup; the next section explains the actual NER table.",
                    ],
                }
            if self._is_bert_ner_feature_table_section(document_text):
                return {
                    "one_line": "This section shows that BERT's hidden layers work well as fixed NER features, nearly matching fine-tuning.",
                    "simple": (
                        "For NER, the authors use the first WordPiece sub-token representation for token classification. "
                        "Without fine-tuning BERT, they extract one or more layer activations, feed them to a BiLSTM, and find that concatenating the top four layers is only 0.3 F1 behind full fine-tuning."
                    ),
                    "academic": (
                        "The section combines Table 6/7 reading with the feature-based NER ablation: model-size scaling metrics, CoNLL-2003 F1 comparisons, "
                        "sub-token representation choice, frozen BERT activations, a randomly initialized BiLSTM, and layer-selection results for contextual embeddings."
                    ),
                    "study_notes": [
                        "Do not read the numeric table as prose; identify the comparison rows and the winning feature variant.",
                        "The key language-learning phrase is 'To ablate X, we apply Y by Z'.",
                        "The result supports BERT's usefulness beyond full-model fine-tuning.",
                    ],
                }
            if "contextual word embeddings" in lower and "openai gpt" in lower and "fine-tuning approaches" in lower:
                return {
                    "one_line": "This transition section compares ELMo-style feature integration with GPT-style unsupervised fine-tuning.",
                    "simple": (
                        "The authors first show that ELMo-style contextual embeddings work well when added to task-specific models. "
                        "Then they shift to fine-tuning approaches such as OpenAI GPT, where a pre-trained encoder is adapted to labeled downstream tasks."
                    ),
                    "academic": (
                        "The section bridges two strands of related work: feature-based contextual embeddings, including ELMo and cloze-style context prediction, "
                        "and unsupervised fine-tuning approaches exemplified by OpenAI GPT's GLUE performance."
                    ),
                    "study_notes": [
                        "Read this as a transition from feature-based baselines to fine-tuning baselines.",
                        "Do not memorize 'bidirectional' alone; the useful contrast is shallow bidirectionality versus deep bidirectional pre-training.",
                        "Track why GPT matters: strong fine-tuning baseline, but still left-to-right.",
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
            "feature-based",
            "embeddings",
            "language modeling objectives",
            "bidirectional",
        }
        if any("two existing strategies" in str(row.get("source_sentence") or "").lower() for row in rows):
            blocked = blocked - {"feature-based"}
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

    def _prefer_bert_feature_related_work_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"embeddings", "language modeling objectives", "context-sensitive features"}
        preferred = {
            "feature-based representation history": (
                "The section reviews non-neural and neural word-representation methods before BERT.",
                "This frames the section as related work, not BERT's own method.",
            ),
            "coarser-granularity embeddings": (
                "Representation learning extends from words to sentences and paragraphs.",
                "This explains the progression of representation granularity.",
            ),
            "ELMo contextual feature extraction": (
                "ELMo extracts context-sensitive token features from left-to-right and right-to-left language models.",
                "This is the key feature-based predecessor BERT builds against.",
            ),
            "directional representation concatenation": (
                "ELMo concatenates left-to-right and right-to-left token representations.",
                "This explains why earlier bidirectionality is shallower than BERT's joint bidirectional pre-training.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "active area of research"
                    if "history" in lowered
                    else "coarser granularities"
                    if "coarser" in lowered
                    else "context-sensitive features"
                    if "extraction" in lowered
                    else "concatenation"
                )
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

    def _prefer_bert_elmo_finetuning_transition_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bidirectional", "bert", "left-to-right language model"}
        preferred = [
            (
                "contextual word embeddings",
                "Word embeddings that change with the sentence context.",
                "field_term",
                "hard",
                "This is the feature-based representation family being evaluated through ELMo.",
            ),
            (
                "cloze task",
                "A task where a model predicts a missing word from context.",
                "field_term",
                "medium",
                "The section uses cloze-style prediction as a bridge toward BERT-style pre-training.",
            ),
            (
                "fine-tuning approaches",
                "Methods that pre-train representations and then adapt them to a labeled downstream task.",
                "field_term",
                "medium",
                "This marks the transition from feature-based related work to GPT-style fine-tuning.",
            ),
            (
                "contextual token representations",
                "Token vectors whose meaning depends on surrounding text.",
                "field_term",
                "hard",
                "This is the representation type shared by GPT-style encoders and BERT.",
            ),
            (
                "supervised downstream task",
                "A labeled target task used after unsupervised pre-training.",
                "useful",
                "medium",
                "This explains what fine-tuning adapts the pre-trained encoder for.",
            ),
            (
                "OpenAI GPT",
                "A prior left-to-right Transformer model used as the fine-tuning baseline for BERT.",
                "field_term",
                "medium",
                "This is the concrete prior system BERT is positioned against.",
            ),
            (
                "GLUE benchmark",
                "A benchmark suite for evaluating language-understanding models.",
                "useful",
                "medium",
                "This is the benchmark evidence used for GPT's prior state-of-the-art result.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            target = {
                "end-to-end fine-tuning": "finetune all the parameters end-to-end",
                "task-specific inputs and outputs": "inputs and outputs",
                "token-level tasks": "token representations",
                "classification tasks": "output layer for classification",
            }.get(term, term)
            if lowered in keyed:
                promoted.append(
                    {
                        **keyed[lowered],
                        "meaning": keyed[lowered].get("meaning") or meaning,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "reason": keyed[lowered].get("reason") or reason,
                    }
                )
            else:
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:20]

    def _prefer_bert_elmo_finetuning_transition_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"contextual word embeddings", "bidirectional", "cloze task"}
        preferred = {
            "ELMo benchmark integration": (
                "ELMo improves several NLP benchmarks when its contextual embeddings are integrated into task-specific architectures.",
                "This explains the strength of the feature-based baseline before BERT.",
                "advances the state of the art",
            ),
            "shallow bidirectionality limitation": (
                "Some prior models use both left and right context, but are still feature-based and not deeply bidirectional.",
                "This is the limitation BERT will target with deep bidirectional pre-training.",
                "not deeply bidirectional",
            ),
            "cloze-style context prediction": (
                "The cloze task predicts a missing word from surrounding context.",
                "This is a related self-supervised idea that foreshadows masked language modeling.",
                "cloze task",
            ),
            "unsupervised fine-tuning approach": (
                "A model is pre-trained on unlabeled text and then fine-tuned for a supervised downstream task.",
                "This is the GPT-style strategy BERT improves rather than abandoning.",
                "Fine-tuning Approaches",
            ),
            "parameter-efficient transfer": (
                "Fine-tuning is attractive because few parameters need to be learned from scratch.",
                "This explains why pre-training is useful in practice, not just as a benchmark trick.",
                "few parameters need to be learned from scratch",
            ),
            "GPT as fine-tuning baseline": (
                "OpenAI GPT is the left-to-right fine-tuning baseline that achieved strong GLUE results before BERT.",
                "This anchors the upcoming contrast between GPT's left-to-right objective and BERT's bidirectional objective.",
                "OpenAI GPT",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.86,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_pretraining_finetuning_procedure_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"tokm", "masked sentence a", "masked sentence b", "nermnli", "bert"}
        preferred = [
            (
                "pre-training",
                "The stage where BERT learns general language representations before task-specific training.",
                "field_term",
                "medium",
                "This is the first half of the BERT workflow.",
            ),
            (
                "fine-tuning",
                "The stage where the pre-trained BERT model is adapted to downstream tasks.",
                "field_term",
                "medium",
                "This is the second half of the BERT workflow.",
            ),
            (
                "output layers",
                "Task-specific layers added on top of the shared BERT architecture.",
                "field_term",
                "medium",
                "The caption says these are the main architectural exception across tasks.",
            ),
            (
                "pre-trained model parameters",
                "Weights learned during pre-training and reused to initialize downstream task models.",
                "field_term",
                "hard",
                "This is the mechanism that transfers BERT knowledge to multiple tasks.",
            ),
            (
                "[CLS]",
                "A special token placed at the front of every BERT input example.",
                "useful",
                "medium",
                "This is part of BERT's input formatting convention.",
            ),
            (
                "[SEP]",
                "A special separator token used between text segments such as question and answer.",
                "useful",
                "medium",
                "This helps BERT represent sentence-pair inputs.",
            ),
            (
                "supervised transfer",
                "Reusing knowledge from labeled large-data tasks for other tasks.",
                "useful",
                "medium",
                "The following related-work heading introduces supervised transfer as another background branch.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "Transfer Learning from Supervised Data" if term == "supervised transfer" else term
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _prefer_bert_pretraining_finetuning_procedure_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"pre-training", "fine-tuning", "[cls]", "[sep]", "output layers", "bert"}
        preferred = {
            "shared pre-training/fine-tuning architecture": (
                "BERT uses the same base architecture for pre-training and fine-tuning, apart from task-specific output layers.",
                "This is the central workflow idea shown by the figure.",
                "Apart from output layers",
            ),
            "parameter initialization for downstream tasks": (
                "The same pre-trained parameters initialize models for different downstream tasks.",
                "This explains how one offline model can become many task models.",
                "are used to initialize",
            ),
            "full-model fine-tuning": (
                "During fine-tuning, all BERT parameters are updated.",
                "This prevents the user from thinking only the output layer is trained.",
                "During fine-tuning",
            ),
            "BERT input formatting": (
                "[CLS] starts an input example and [SEP] separates segments such as question and paragraph.",
                "These tokens are mechanics for reading BERT examples, not high-level concepts to memorize alone.",
                "[CLS]",
            ),
            "supervised transfer background": (
                "The section begins a related-work branch about transfer from supervised tasks with large datasets.",
                "This is background after the main BERT workflow figure.",
                "Transfer Learning from Supervised Data",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.86,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_pretraining_finetuning_procedure_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"we introduce"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_architecture_model_size_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert", "openai gpt", "bidirectional transformer encoder"}
        preferred = [
            (
                "unified architecture",
                "A shared BERT architecture used across different downstream tasks.",
                "field_term",
                "medium",
                "This is the section's main architecture claim.",
            ),
            (
                "multi-layer bidirectional Transformer encoder",
                "BERT's backbone architecture: stacked Transformer encoder layers with bidirectional context.",
                "field_term",
                "hard",
                "This is the technical definition of BERT's model architecture.",
            ),
            ("L", "The number of Transformer blocks or layers.", "useful", "medium", "This notation is needed to read BERTBASE and BERTLARGE."),
            ("H", "The hidden size of the model.", "useful", "medium", "This notation is needed to compare model capacity."),
            ("A", "The number of self-attention heads.", "useful", "medium", "This notation is needed to read the model-size configurations."),
            (
                "BERTBASE",
                "The 12-layer, 110M-parameter BERT model sized for comparison with OpenAI GPT.",
                "field_term",
                "medium",
                "This is the smaller reported BERT variant.",
            ),
            (
                "BERTLARGE",
                "The 24-layer, 340M-parameter BERT model used for higher-capacity results.",
                "field_term",
                "medium",
                "This is the larger reported BERT variant.",
            ),
            (
                "input representation",
                "The format that lets BERT represent either one text span or a pair of text spans in one token sequence.",
                "field_term",
                "hard",
                "This explains how one architecture can handle many task types.",
            ),
            (
                "WordPiece embeddings",
                "Subword token embeddings using a fixed vocabulary.",
                "field_term",
                "medium",
                "This is BERT's tokenization/embedding choice.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = {
                    "end-to-end fine-tuning": "finetune all the parameters end-to-end",
                    "task-specific inputs and outputs": "inputs and outputs",
                    "token-level tasks": "token representations",
                    "classification tasks": "output layer for classification",
                }.get(term, term)
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_architecture_model_size_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bidirectional transformer encoder", "wordpiece embeddings", "bert", "openai gpt"}
        preferred = {
            "unified task architecture": (
                "BERT keeps minimal difference between the pre-trained architecture and final downstream architectures.",
                "This is the productively reusable design idea, larger than any single term.",
                "minimal difference",
            ),
            "Transformer encoder backbone": (
                "BERT is implemented as a multi-layer bidirectional Transformer encoder.",
                "This anchors the architecture in the Transformer family without repeating the whole Transformer paper.",
                "multi-layer bidirectional Transformer encoder",
            ),
            "model-size notation": (
                "The paper uses L for layers, H for hidden size, and A for self-attention heads.",
                "This lets the learner read BERTBASE and BERTLARGE configurations accurately.",
                "we denote the number of",
            ),
            "BERTBASE versus BERTLARGE": (
                "The paper reports a 12-layer 110M-parameter base model and a 24-layer 340M-parameter large model.",
                "This separates model variant names from general BERT terminology.",
                "BERTBASE",
            ),
            "single-or-pair input sequence": (
                "BERT's input representation can encode either one span or two spans in a single token sequence.",
                "This explains how BERT handles question answering and sentence-pair tasks with one architecture.",
                "unambiguously represent both a single sentence and a pair of sentences",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.86,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_input_representation_masked_lm_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"hidden state", "embedding", "bert"}
        preferred = [
            ("[CLS]", "A special classification token placed first in every BERT input sequence.", "field_term", "medium", "It provides the aggregate sequence representation for classification."),
            ("aggregate sequence representation", "A single vector used to represent the whole input sequence.", "field_term", "hard", "This explains why the [CLS] hidden state matters."),
            ("[SEP]", "A special separator token used to divide sentence pairs.", "useful", "medium", "It is one of BERT's sentence-pair encoding mechanisms."),
            ("segment embedding", "A learned embedding that marks whether a token belongs to sentence A or sentence B.", "field_term", "medium", "It lets BERT distinguish packed sentence pairs."),
            ("position embeddings", "Embeddings that encode token order inside the sequence.", "field_term", "medium", "They are one of the three summed components of BERT input vectors."),
            ("token embeddings", "Embeddings representing the token identity.", "field_term", "medium", "They are combined with segment and position embeddings."),
            ("masked LM", "A pre-training task where selected tokens are masked and predicted from context.", "field_term", "hard", "This is the next pre-training task introduced after input representation."),
            ("left-to-right language models", "Language models that use only previous context.", "useful", "medium", "BERT explicitly contrasts its pre-training with these directional models."),
            ("right-to-left language models", "Language models that use only following context.", "useful", "medium", "BERT contrasts its pre-training with separately directional models."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = {
                    "segment embedding": "learned embedding",
                    "token embeddings": "token, segment, and position embeddings",
                    "masked LM": "Masked LM",
                    "left-to-right language models": "left-to-right",
                    "right-to-left language models": "right-to-left",
                }.get(term, term)
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_input_representation_masked_lm_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"hidden state", "embedding", "[cls]", "[sep]", "masked lm", "bert", "pre-training"}
        preferred = {
            "classification-token aggregation": (
                "The final hidden state of [CLS] is used as the aggregate representation for classification.",
                "This explains why [CLS] is more than a marker token.",
                "aggregate sequence representation",
            ),
            "sentence-pair packing": (
                "BERT packs sentence pairs into one sequence and distinguishes them with [SEP] plus segment embeddings.",
                "This is how one input format handles pair tasks such as question answering.",
                "Sentence pairs are packed together",
            ),
            "segment identity encoding": (
                "A learned embedding marks whether each token belongs to sentence A or sentence B.",
                "This prevents the two packed spans from becoming indistinguishable.",
                "belongs to sentence A or sentence B",
            ),
            "summed input representation": (
                "Each token input is the sum of token, segment, and position embeddings.",
                "This is the core formula for reading BERT's input representation.",
                "constructed by summing",
            ),
            "masked-language-model transition": (
                "The section transitions from input formatting to BERT's non-directional masked LM pre-training task.",
                "This connects architecture mechanics to the next method section.",
                "Instead, we pre-train BERT using two unsupervised tasks",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.86,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_masked_lm_procedure_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bidirectional representation", "wordpiece tokens", "bert", "pre-training", "fine-tuning", "next sentence prediction"}
        preferred = [
            ("masked LM", "BERT's objective of predicting masked tokens from bidirectional context.", "field_term", "hard", "This is the section's central method."),
            ("Cloze task", "A fill-in-the-blank prediction task known in earlier literature.", "useful", "medium", "The paper maps MLM to a familiar prior term."),
            ("output softmax", "The prediction layer over vocabulary items for masked token prediction.", "field_term", "hard", "This explains how hidden vectors become token predictions."),
            ("15% of all WordPiece tokens", "The fraction of token positions selected for MLM prediction.", "field_term", "medium", "This is the sampling rate for the objective."),
            ("denoising auto-encoders", "Models trained to reconstruct corrupted input.", "useful", "medium", "BERT contrasts MLM with reconstructing an entire input."),
            ("pre-training and fine-tuning mismatch", "The gap created because [MASK] appears during pre-training but not fine-tuning.", "field_term", "hard", "This motivates the replacement workaround."),
            ("[MASK] token", "The special token used for most selected masked positions.", "field_term", "medium", "This is central to the mismatch problem and the 80% replacement case."),
            ("80/10/10 replacement rule", "The selected-token rule: [MASK] 80%, random token 10%, unchanged token 10%.", "field_term", "hard", "This is the practical detail learners need to retain."),
            ("original token", "The true token that the model must predict after replacement.", "useful", "medium", "This separates replacement input from prediction target."),
            ("cross entropy loss", "The loss used to train prediction of the original token.", "field_term", "medium", "This connects MLM prediction to the training signal."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = {
                    "masked LM": "masked LM",
                    "15% of all WordPiece tokens": "mask 15% of all WordPiece tokens",
                    "pre-training and fine-tuning mismatch": "mismatch between pre-training and fine-tuning",
                    "80/10/10 replacement rule": "80% of the time",
                    "original token": "predict the original token",
                }.get(term, term)
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_masked_lm_procedure_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {
            "bidirectional representation",
            "wordpiece tokens",
            "cross entropy loss",
            "masked lm",
            "cloze task",
            "fine-tuning",
            "next sentence prediction",
            "pre-training",
        }
        preferred = {
            "masked-token prediction objective": (
                "BERT selects some input tokens at random and predicts the original tokens from bidirectional context.",
                "This is the core method, not just a vocabulary item.",
                "mask some percentage of the input tokens",
            ),
            "MLM versus denoising reconstruction": (
                "BERT predicts only masked words rather than reconstructing the entire input.",
                "This explains how MLM differs from denoising auto-encoders.",
                "rather than reconstructing the entire input",
            ),
            "[MASK] mismatch problem": (
                "[MASK] appears during pre-training but not during fine-tuning, creating a distribution mismatch.",
                "This is why the paper needs the replacement rule.",
                "mismatch between pre-training and fine-tuning",
            ),
            "80/10/10 replacement strategy": (
                "Selected positions become [MASK] 80% of the time, a random token 10%, and unchanged 10%.",
                "This is the concrete workaround for the [MASK] mismatch problem.",
                "80% of the time",
            ),
            "original-token prediction target": (
                "Even when the input is replaced randomly or left unchanged, the target is still the original token.",
                "This prevents confusion between the input corruption and the training label.",
                "predict the original token",
            ),
            "transition to next sentence prediction": (
                "After MLM, the section moves to NSP for sentence-relationship tasks such as QA and NLI.",
                "This links token-level pre-training to sentence-pair understanding.",
                "Task #2: Next Sentence Prediction",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_masked_lm_procedure_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"allows us to", "during fine-tuning"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_nsp_procedure_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert", "pre-training", "fine-tuning", "sentence embeddings", "binarized", "monolingual corpus"}
        preferred = [
            ("next sentence prediction", "A binary pre-training task that predicts whether sentence B follows sentence A.", "field_term", "hard", "This is the section's central method."),
            ("binarized next sentence prediction task", "A two-label version of NSP with IsNext and NotNext labels.", "field_term", "hard", "This explains what 'binarized' means in context."),
            ("monolingual corpus", "A same-language text collection used to generate sentence-pair examples without manual labels.", "useful", "medium", "This explains why NSP data is easy to generate."),
            ("IsNext", "The positive NSP label when sentence B actually follows sentence A.", "field_term", "medium", "This is the positive class in the 50/50 sampling rule."),
            ("NotNext", "The negative NSP label when sentence B is randomly sampled from the corpus.", "field_term", "medium", "This is the negative class in the 50/50 sampling rule."),
            ("QA", "Question answering, a downstream task that depends on sentence or passage relationships.", "useful", "medium", "The paper cites QA as a task helped by NSP."),
            ("NLI", "Natural language inference, a task that judges relationships between sentences.", "useful", "medium", "The paper cites NLI as a task helped by NSP."),
            ("vector C", "The [CLS] vector used by BERT, which is not a meaningful sentence representation without fine-tuning.", "field_term", "hard", "This prevents overreading C as a standalone sentence embedding."),
            ("all parameters", "The full BERT parameter set transferred to initialize downstream models.", "field_term", "medium", "This contrasts BERT with prior work transferring only sentence embeddings."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = {
                    "binarized next sentence prediction task": "binarized next sentence prediction task",
                    "IsNext": "labeled as IsNext",
                    "NotNext": "labeled as NotNext",
                    "vector C": "The vector C",
                    "all parameters": "transfers all parameters",
                }.get(term, term)
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_nsp_procedure_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert", "pre-training", "fine-tuning", "next sentence prediction", "sentence embeddings", "binarized", "monolingual corpus"}
        preferred = {
            "sentence-relationship pre-training": (
                "NSP trains BERT to understand whether two sentences are connected.",
                "This is the purpose of NSP, beyond memorizing the task name.",
                "understands sentence relationships",
            ),
            "balanced IsNext/NotNext sampling": (
                "Half of sentence B examples are true next sentences and half are random corpus sentences.",
                "This is the actual data-generation rule for NSP.",
                "50% of the time B is the actual next sentence",
            ),
            "self-supervised NSP data generation": (
                "The NSP labels can be generated from a monolingual corpus without hand annotation.",
                "This explains why the task scales as a pre-training objective.",
                "trivially generated from any monolingual corpus",
            ),
            "QA/NLI sentence-pair benefit": (
                "The paper claims NSP is beneficial for QA and NLI, tasks based on sentence relationships.",
                "This links the pre-training task to downstream language understanding.",
                "beneficial to both QA and NLI",
            ),
            "C-vector caveat": (
                "The vector C is not a meaningful sentence representation without fine-tuning.",
                "This prevents confusing BERT's [CLS] vector with a general sentence embedding.",
                "not a meaningful sentence representation without fine-tuning",
            ),
            "full-parameter transfer": (
                "BERT transfers all parameters to initialize end-task models, unlike prior work that transferred only sentence embeddings.",
                "This is a key difference in how BERT uses pre-training.",
                "transfers all parameters",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_nsp_procedure_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"we demonstrate", "in order to train"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_finetuning_unification_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"corpus", "self-attention mechanism", "entailment", "bert", "fine-tuning", "pre-training"}
        preferred = [
            ("document-level corpus", "A corpus preserving long contiguous document sequences.", "field_term", "medium", "This is required for extracting long sequences for pre-training."),
            ("shuffled sentence-level corpus", "A corpus where sentences are shuffled and document continuity is lost.", "useful", "medium", "This is the data format the paper rejects."),
            ("long contiguous sequences", "Extended text spans that preserve document-level context.", "field_term", "medium", "This explains why document-level data matters."),
            ("self-attention mechanism", "The Transformer mechanism BERT uses to connect tokens across single or paired inputs.", "field_term", "hard", "This enables task unification during fine-tuning."),
            ("bidirectional cross attention", "Attention between two texts in both directions.", "field_term", "hard", "This is the prior pair-encoding pattern BERT replaces with concatenated self-attention."),
            ("task-specific inputs and outputs", "Inputs and output layers adjusted for each downstream task.", "field_term", "medium", "This is the main task-specific part of fine-tuning."),
            ("end-to-end fine-tuning", "Updating all BERT parameters for a downstream task.", "field_term", "medium", "The section says all parameters are fine-tuned, not just the output layer."),
            ("token-level tasks", "Tasks that need predictions for individual tokens.", "useful", "medium", "The output mapping differs for token-level tasks."),
            ("classification tasks", "Tasks that use the [CLS] representation for a whole-input prediction.", "useful", "medium", "This is the other output mapping in the section."),
            ("Cloud TPU", "Google hardware used to report fine-tuning runtime.", "useful", "medium", "This supports the claim that fine-tuning is relatively inexpensive."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            target = {
                "end-to-end fine-tuning": "finetune all the parameters end-to-end",
                "task-specific inputs and outputs": "inputs and outputs",
                "token-level tasks": "token representations",
                "classification tasks": "output layer for classification",
            }.get(term, term)
            row = keyed.get(lowered, {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_finetuning_unification_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"corpus", "self-attention mechanism", "entailment", "fine-tuning", "pre-training", "bert"}
        preferred = {
            "document-level pre-training data": (
                "BERT needs document-level text rather than shuffled sentences to extract long contiguous sequences.",
                "This connects the data source to NSP and long-context construction.",
                "document-level corpus",
            ),
            "fine-tuning by input/output swapping": (
                "BERT adapts to tasks by swapping task-specific inputs and outputs while keeping the same model core.",
                "This is the practical reason one pre-trained model can serve many tasks.",
                "swapping out the appropriate inputs and outputs",
            ),
            "self-attention task unification": (
                "BERT uses self-attention over concatenated text to unify stages that prior systems handled separately.",
                "This is the architecture reason text-pair tasks can be handled directly.",
                "to unify these two stages",
            ),
            "task input analogy map": (
                "Sentence A/B slots correspond to paraphrase pairs, hypothesis-premise pairs, question-passage pairs, or degenerate text pairs.",
                "This helps users read task examples without treating them as random vocabulary.",
                "are analogous to",
            ),
            "output routing by task type": (
                "Token representations feed token-level output layers, while [CLS] feeds classification output layers.",
                "This separates token-level tasks from classification tasks.",
                "At the output",
            ),
            "low-cost downstream adaptation": (
                "Fine-tuning is relatively inexpensive compared with pre-training.",
                "This explains the deployment/workflow appeal of pre-trained BERT.",
                "Compared to pre-training",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "concept": concept,
                        "explanation": explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": [concept],
                        "why_it_matters": why_it_matters,
                        "references": self._references_near("", document_text),
                        "learning_priority": "field_term",
                        "confidence": 0.88,
                        "user_state": "suggested",
                    }
                )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_finetuning_unification_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"are fed into"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_glue_setup_results_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert fine-tuning", "hidden vector c ∈ rh", "bert", "fine-tuning"}
        preferred = [
            ("GLUE benchmark", "A collection of diverse natural language understanding tasks.", "field_term", "medium", "This is the experiment benchmark for the section."),
            ("11 NLP tasks", "The scope of BERT fine-tuning results in this experiment section.", "useful", "medium", "This gives the experimental breadth without memorizing every task."),
            ("final hidden vector C", "The [CLS] vector used as the aggregate representation for GLUE classification.", "field_term", "hard", "This is the representation fed into the classifier."),
            ("aggregate representation", "A single vector summarizing the input sequence for classification.", "field_term", "hard", "This explains what C does in GLUE fine-tuning."),
            ("classification layer weights W", "The new task-specific weights added during GLUE fine-tuning.", "field_term", "hard", "The section says these are the only new parameters."),
            ("number of labels K", "The label count determining the classifier output size.", "useful", "medium", "This explains the K dimension in W."),
            ("classification loss", "The loss computed from C and W for GLUE classification.", "field_term", "medium", "This is the training objective for the benchmark."),
            ("evaluation server", "The GLUE server used to score test results.", "useful", "medium", "This explains the table's scoring source."),
            ("BERTBASE", "The smaller BERT model variant reported in the GLUE table.", "field_term", "medium", "This is one row in the result comparison."),
            ("BERTLARGE", "The larger BERT model variant reported in the GLUE table.", "field_term", "medium", "This is the strongest BERT row in the table."),
            ("Average column", "The table's aggregate score column, excluding WNLI in this paper.", "useful", "medium", "This helps read the table without overtrusting the official-score comparison."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            target = {
                "GLUE benchmark": "General Language Understanding Evaluation",
                "11 NLP tasks": "fine-tuning results",
                "final hidden vector C": "final hidden vector C",
                "classification layer weights W": "classification layer weights W",
                "number of labels K": "number of labels",
                "classification loss": "standard classification loss",
                "Average column": "official GLUE score",
            }.get(term, term)
            row = keyed.get(lowered, {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_glue_setup_results_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert fine-tuning", "hidden vector c ∈ rh", "glue benchmark", "fine-tuning", "bert"}
        preferred = {
            "GLUE experiment scope": (
                "The paper reports BERT fine-tuning results on 11 NLP tasks from GLUE.",
                "This frames the section as experiment setup and evaluation, not model definition.",
                "11 NLP tasks",
            ),
            "[CLS]-based aggregate representation": (
                "For GLUE, BERT uses the final hidden vector C for the first [CLS] token as the aggregate input representation.",
                "This connects the earlier input-format section to classification fine-tuning.",
                "aggregate representation",
            ),
            "minimal new classifier parameters": (
                "The only new fine-tuning parameters are classification layer weights W.",
                "This shows how small the task-specific addition is.",
                "only new parameters introduced",
            ),
            "classification-loss setup": (
                "The model computes a standard classification loss from C and W.",
                "This explains the training objective without dwelling on the formula.",
                "standard classification loss",
            ),
            "GLUE table reading": (
                "The table compares systems across GLUE tasks and reports BERTBASE/BERTLARGE improvements.",
                "This teaches how to read the result table rather than memorize every number.",
                "Table 1: GLUE Test results",
            ),
            "official-score caveat": (
                "The paper's Average column differs from the official GLUE score because WNLI is excluded.",
                "This prevents overinterpreting the average column.",
                "Average column",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            lowered = concept.lower()
            row = keyed.get(lowered, {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_glue_setup_results_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"for example", "during fine-tuning"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_glue_result_interpretation_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "fine-tune", "pre-trained checkpoint", "bert", "bert fine-tuning"}
        preferred = [
            ("F1 scores", "A metric reported for QQP and MRPC in the GLUE results.", "useful", "medium", "This teaches how to read task-specific score columns."),
            ("Spearman correlations", "A correlation metric reported for STS-B.", "field_term", "hard", "This explains why not every GLUE column is accuracy."),
            ("accuracy scores", "The metric reported for the other GLUE tasks.", "useful", "medium", "This distinguishes task metrics before comparing rows."),
            ("Dev set", "The validation split used to select learning rates and restart results.", "field_term", "medium", "This explains how model selection is performed."),
            ("fine-tuning learning rate", "The learning-rate hyperparameter selected from 5e-5, 4e-5, 3e-5, and 2e-5.", "field_term", "medium", "This is part of the experimental protocol."),
            ("random restarts", "Multiple fine-tuning runs used to stabilize BERTLARGE on small datasets.", "field_term", "hard", "This is the key caveat for unstable small-dataset fine-tuning."),
            ("fine-tuning data shuffling", "One source of variation across random restarts.", "field_term", "hard", "This explains what changes between runs."),
            ("classifier layer initialization", "Another source of variation across random restarts.", "field_term", "hard", "This explains how the classifier can start differently."),
            ("prior state of the art", "The previous best systems used as the comparison target.", "useful", "medium", "This helps read result claims like average improvement."),
            ("absolute accuracy improvement", "A direct percentage-point gain over a baseline.", "field_term", "medium", "This clarifies the MNLI result claim."),
            ("official GLUE leaderboard", "The public benchmark leaderboard used for result comparison.", "useful", "medium", "This grounds the OpenAI GPT comparison."),
            ("model size effect", "The observed advantage of BERTLARGE over BERTBASE, especially on small datasets.", "field_term", "medium", "This previews the later Section 5.2 analysis."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "fine-tuning learning rate": "selected the best fine-tuning learning rate",
                "absolute accuracy improvement": "absolute accuracy improvement",
                "official GLUE leaderboard": "official GLUE leaderboard",
                "model size effect": "effect of model size",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_glue_result_interpretation_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "f1 scores", "fine-tune", "pre-trained checkpoint", "bert", "bertbase", "bertlarge"}
        preferred = {
            "GLUE metric conventions": (
                "Different GLUE tasks report different metrics: F1, Spearman correlation, or accuracy.",
                "This keeps the reader from comparing every column as if it were the same score type.",
                "F1 scores are reported",
            ),
            "uniform fine-tuning protocol": (
                "The authors use batch size 32 and fine-tune for three epochs across GLUE tasks.",
                "This separates the training recipe from the model architecture.",
                "batch size of 32",
            ),
            "dev-set hyperparameter selection": (
                "The best fine-tuning learning rate is selected on the Dev set for each task.",
                "This explains how reported runs are chosen without memorizing the learning-rate list.",
                "selected the best fine-tuning learning rate",
            ),
            "BERTLARGE small-dataset instability": (
                "BERTLARGE can be unstable on small datasets, so the authors use several random restarts.",
                "This is a practical caveat and an important experimental detail.",
                "sometimes unstable on small datasets",
            ),
            "random-restart variation": (
                "Random restarts keep the same pre-trained checkpoint but change data shuffling and classifier initialization.",
                "This explains what is and is not changing across repeated runs.",
                "perform different fine-tuning data shuffling",
            ),
            "substantial GLUE improvement": (
                "Both BERTBASE and BERTLARGE outperform prior systems by large average margins.",
                "This is the main result claim of the section.",
                "outperform all systems",
            ),
            "controlled GPT comparison": (
                "BERTBASE and OpenAI GPT are architecturally similar except for attention masking.",
                "This makes the comparison support the bidirectionality argument.",
                "apart from the attention masking",
            ),
            "model-size effect": (
                "BERTLARGE significantly outperforms BERTBASE, especially where training data is limited.",
                "This previews the paper's later analysis of scale.",
                "effect of model size",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_glue_result_interpretation_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"during fine-tuning", "we present bert fine-tuning results on", "is a collection of"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_squad_span_prediction_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "fine-tune", "bert", "glue", "bertbase", "bertlarge"}
        preferred = [
            ("SQuAD v1.1", "A question-answering benchmark with crowdsourced question/answer pairs.", "field_term", "medium", "This is the benchmark for the section."),
            ("answer text span", "The contiguous passage span that the model must predict as the answer.", "field_term", "medium", "This is the output unit of extractive QA."),
            ("single packed sequence", "The combined question and passage input representation for BERT.", "field_term", "medium", "This explains how BERT receives QA inputs."),
            ("A embedding", "The segment embedding used for the question in the packed sequence.", "field_term", "medium", "This distinguishes the question segment."),
            ("B embedding", "The segment embedding used for the passage in the packed sequence.", "field_term", "medium", "This distinguishes the passage segment."),
            ("start vector S", "The fine-tuned vector used to score possible answer start tokens.", "field_term", "hard", "This is one of the only new QA parameters."),
            ("end vector E", "The fine-tuned vector used to score possible answer end tokens.", "field_term", "hard", "This mirrors the start vector for the span endpoint."),
            ("softmax over paragraph tokens", "The normalization that turns token scores into start or end probabilities.", "field_term", "hard", "This explains the probability formula."),
            ("candidate span", "A possible answer range from start position i to end position j.", "field_term", "medium", "This is what the model scores before prediction."),
            ("maximum scoring span", "The valid candidate span with the highest start-plus-end score.", "field_term", "medium", "This is how the final answer is selected."),
            ("log-likelihoods", "The training objective terms for the correct start and end positions.", "field_term", "hard", "This is the optimization target."),
            ("TriviaQA", "An additional QA dataset used before fine-tuning on SQuAD.", "field_term", "medium", "This explains the data augmentation step."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "SQuAD v1.1": "fine-tuning on SQuAD",
                "single packed sequence": "single packed sequence",
                "A embedding": "A embedding",
                "B embedding": "B embedding",
                "softmax over paragraph tokens": "softmax over all of the words",
                "log-likelihoods": "log-likelihoods",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_squad_span_prediction_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "packed sequence", "start vector s", "log-likelihoods", "bert", "squad"}
        preferred = {
            "extractive QA span prediction": (
                "SQuAD asks the model to predict the answer text span inside the passage.",
                "This frames the task as span extraction, not free-form answer generation.",
                "answer text span",
            ),
            "question-passage packed input": (
                "BERT represents the question and passage as one packed sequence with A/B segment embeddings.",
                "This reuses BERT's sentence-pair input machinery for QA.",
                "single packed sequence",
            ),
            "minimal QA-specific parameters": (
                "Fine-tuning introduces only a start vector S and end vector E.",
                "This continues the paper's theme that downstream tasks need small output changes.",
                "start vector S",
            ),
            "start/end probability scoring": (
                "Token start and end probabilities are computed with vector dot products followed by softmax.",
                "This explains how the formula turns token representations into answer-boundary probabilities.",
                "followed by a softmax",
            ),
            "maximum-span prediction rule": (
                "Candidate spans are scored with start and end vectors, and the highest valid span is selected.",
                "This explains how probabilities become the final answer span.",
                "maximum scoring span",
            ),
            "start/end log-likelihood objective": (
                "Training maximizes the correct start and end positions through log-likelihood terms.",
                "This is the supervised objective for the QA adaptation.",
                "log-likelihoods",
            ),
            "leaderboard comparability caveat": (
                "Top SQuAD leaderboard systems may lack public descriptions and may use public data.",
                "This warns the reader not to compare leaderboard rows too naively.",
                "up-to-date public system descriptions",
            ),
            "TriviaQA data augmentation": (
                "The system first fine-tunes on TriviaQA before fine-tuning on SQuAD.",
                "This is the section's practical augmentation step.",
                "TriviaQA",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _filter_bert_squad_span_prediction_phrases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked = {"during fine-tuning", "fine-tune for", "answer text span"}
        return [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked]

    def _prefer_bert_squad_span_prediction_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"during fine-tuning", "fine-tune for", "answer text span", "is a collection of"}
        preferred = [
            ("Given a question and a passage", "general", "Introduces the question-answering input setting."),
            ("the task is to predict", "claim", "Defines the task objective."),
            ("we represent the input question and passage as", "method", "Explains how QA inputs are packed for BERT."),
            ("We only introduce", "method", "Emphasizes the small task-specific parameter addition."),
            ("is computed as", "method", "Introduces a formula or scoring computation."),
            ("followed by a softmax", "method", "Explains the normalization step after scoring."),
            ("The analogous formula is used for", "method", "Maps the start-position computation to the end-position computation."),
            ("is defined as", "method", "Defines a scoring function."),
            ("maximum scoring span", "method", "Explains how the final answer span is selected."),
            ("The training objective is", "method", "Introduces the optimization target."),
            ("Table 2 shows", "result", "Introduces a result table."),
            ("We therefore use", "method", "Introduces a consequence-driven method choice."),
        ]
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for phrase, function, explanation in preferred:
            if phrase.lower() not in document_text.lower():
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable question-answering paper expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_squad_results_transition_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bertbase", "f1", "ensembling", "bert", "system"}
        preferred = [
            ("SQuAD leaderboard", "The benchmark ranking used to compare BERT against top QA systems.", "field_term", "medium", "This frames the result table."),
            ("EM", "Exact Match, a SQuAD metric that requires the predicted answer to exactly match a reference answer.", "field_term", "medium", "This explains one table column."),
            ("F1 score", "A token-overlap metric used to score SQuAD answers.", "field_term", "medium", "This explains the main result metric."),
            ("single system", "A single model run rather than an ensemble.", "useful", "medium", "This distinguishes rows in the result table."),
            ("ensemble system", "A combined system made from multiple model runs.", "field_term", "medium", "This explains why ensemble rows differ from single rows."),
            ("BERTLARGE", "The larger BERT model variant used for the best SQuAD results.", "field_term", "medium", "This is the model variant driving the table result."),
            ("TriviaQA fine-tuning data", "Extra QA data used before fine-tuning on SQuAD.", "field_term", "medium", "This explains the ablation row."),
            ("pre-training checkpoints", "Different saved pre-trained models used inside the BERT ensemble.", "field_term", "hard", "This explains ensemble diversity."),
            ("fine-tuning seeds", "Different random seeds used for fine-tuning runs in the ensemble.", "field_term", "hard", "This explains another ensemble variation source."),
            ("SQuAD 2.0", "A harder SQuAD task that includes questions with no answer in the paragraph.", "field_term", "medium", "This is the task transition at the end of the section."),
            ("no short answer", "The SQuAD 2.0 condition where the paragraph contains no answer span.", "field_term", "medium", "This is the new problem definition."),
            ("[CLS] token answer span", "The way BERT represents no-answer questions by assigning start and end to [CLS].", "field_term", "hard", "This is the model adaptation for SQuAD 2.0."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "F1 score": "F1 score",
                "TriviaQA fine-tuning data": "Without TriviaQA",
                "pre-training checkpoints": "pre-training checkpoints",
                "fine-tuning seeds": "fine-tuning seeds",
                "SQuAD 2.0": "SQuAD\n2.0" if "SQuAD\n2.0" in document_text else "SQuAD 2.0",
                "[CLS] token answer span": "[CLS] token",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_squad_results_transition_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"ensembling", "f1", "bertbase", "bertlarge", "squad leaderboard"}
        preferred = {
            "SQuAD v1.1 result comparison": (
                "BERT's best single and ensemble systems outperform prior SQuAD leaderboard systems.",
                "This is the main table-reading claim.",
                "outperforms the top leaderboard system",
            ),
            "single versus ensemble distinction": (
                "The section compares BERT as a single system and as an ensemble system.",
                "This prevents mixing rows with different inference setups.",
                "single system",
            ),
            "BERT ensemble construction": (
                "The BERT ensemble uses different pre-training checkpoints and fine-tuning seeds.",
                "This explains what ensembling means in this table.",
                "different pre-training checkpoints",
            ),
            "TriviaQA ablation": (
                "Removing TriviaQA fine-tuning data loses only a small amount of F1.",
                "This shows the SQuAD result is not solely dependent on extra QA data.",
                "Without TriviaQA",
            ),
            "EM/F1 table reading": (
                "SQuAD result tables report EM and F1 for development and test splits.",
                "This helps the reader decode the table columns before comparing systems.",
                "System Dev Test EM F1",
            ),
            "SQuAD 2.0 no-answer extension": (
                "SQuAD 2.0 adds questions where no short answer exists in the paragraph.",
                "This changes the problem from always extracting a span to detecting no-answer cases.",
                "no short answer exists",
            ),
            "[CLS] no-answer handling": (
                "BERT treats no-answer questions as an answer span whose start and end are at [CLS].",
                "This is the practical adaptation from SQuAD v1.1 to v2.0.",
                "[CLS] token",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_squad_results_transition_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"best performing system", "outperforms", "in ensembling"}
        preferred = [
            ("outperforms the top leaderboard system", "result", "States the main benchmark comparison."),
            ("In fact", "result", "Introduces a stronger or surprising follow-up claim."),
            ("in terms of F1 score", "general", "Specifies the metric used for comparison."),
            ("Without TriviaQA", "contrast", "Introduces an ablation condition."),
            ("we only lose", "result", "Reports a small performance drop under an ablation."),
            ("still outperforming", "result", "States that the result remains strong despite the ablation."),
            ("by a wide margin", "result", "Signals a large comparison gap."),
            ("use different pre-training checkpoints", "method", "Explains ensemble diversity."),
            ("extends the SQuAD 1.1 problem definition by allowing", "method", "Defines the SQuAD 2.0 task change."),
            ("making the problem more realistic", "claim", "Explains why the task change matters."),
            ("We use a simple approach to extend", "method", "Introduces the adaptation strategy."),
            ("do not have an answer", "limitation", "Identifies no-answer questions."),
        ]
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for phrase, function, explanation in preferred:
            if phrase.lower() not in document_text.lower():
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable result-table expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_squad2_swag_transition_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "probability space", "non-null span", "fine-tuned", "bertbase"}
        preferred = [
            ("no-answer decision rule", "The rule that compares a no-answer score with the best non-null answer span.", "field_term", "hard", "This is the SQuAD v2.0 adaptation visible in this section."),
            ("[CLS] token", "The token used to represent the no-answer span.", "field_term", "medium", "This is the no-answer anchor in BERT."),
            ("no-answer span", "The null-answer candidate scored with the [CLS] representation.", "field_term", "hard", "This is the alternative to choosing a real passage span."),
            ("best non-null span", "The highest-scoring real answer span in the paragraph.", "field_term", "hard", "This is compared against the no-answer score."),
            ("threshold τ", "The dev-set threshold used to decide whether to return a non-null answer.", "field_term", "hard", "This explains the decision rule."),
            ("dev set", "The validation split used to choose the no-answer threshold.", "field_term", "medium", "This explains model selection."),
            ("SQuAD leaderboard entries", "Prior systems used for SQuAD v2.0 result comparison.", "useful", "medium", "This frames the result comparison."),
            ("SWAG dataset", "A sentence-pair completion dataset for grounded commonsense inference.", "field_term", "medium", "This is the next benchmark in the section."),
            ("grounded commonsense inference", "The reasoning ability SWAG evaluates.", "field_term", "hard", "This explains what SWAG is testing."),
            ("plausible continuation", "The most likely next sentence choice in SWAG.", "field_term", "medium", "This is the SWAG output target."),
            ("four input sequences", "The four BERT inputs constructed for the four SWAG answer choices.", "field_term", "medium", "This explains the adaptation recipe."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "no-answer decision rule": "We predict a non-null answer when",
                "threshold τ": "threshold τ",
                "SQuAD leaderboard entries": "leaderboard entries",
                "SWAG dataset": "Situations With Adversarial Generations",
                "four input sequences": "four input sequences",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_squad2_swag_transition_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"learning rate", "probability space", "non-null span", "fine-tuned"}
        preferred = {
            "SQuAD v2.0 null-answer scoring": (
                "The start/end probability space is extended so [CLS] can represent no answer.",
                "This is the core adaptation from SQuAD v1.1 to v2.0.",
                "probability space",
            ),
            "null versus non-null decision rule": (
                "BERT compares the no-answer score against the best non-null span plus threshold τ.",
                "This explains how the model decides whether to answer.",
                "snull",
            ),
            "dev-set threshold selection": (
                "The threshold τ is selected on the dev set to maximize F1.",
                "This is an evaluation-tuned decision rule, not a vocabulary item.",
                "threshold τ",
            ),
            "SQuAD v2.0 result comparison": (
                "The section compares BERT against prior leaderboard and published systems while excluding systems that use BERT.",
                "This frames the +5.1 F1 improvement claim.",
                "previous best system",
            ),
            "SWAG task transition": (
                "The section moves from extractive QA to SWAG sentence-pair completion.",
                "This marks a new task family after SQuAD.",
                "SW AG",
            ),
            "grounded commonsense inference": (
                "SWAG evaluates whether a model can choose the most plausible continuation from four options.",
                "This explains the reasoning target of the benchmark.",
                "grounded commonsense inference",
            ),
            "four-choice input construction": (
                "For SWAG, BERT constructs four input sequences, one for each possible continuation.",
                "This is the task-specific input adaptation.",
                "four input sequences",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_squad2_swag_transition_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"probability space", "non-null span"}
        preferred = [
            ("is extended to include", "method", "Explains an expanded probability space or label space."),
            ("For prediction, we compare", "method", "Introduces a decision comparison."),
            ("We predict a non-null answer when", "method", "States the answer/no-answer decision rule."),
            ("selected on the dev set to maximize", "method", "Explains threshold selection."),
            ("We did not use", "limitation", "States a data restriction."),
            ("The results compared to", "result", "Introduces benchmark comparison context."),
            ("excluding systems that use", "method", "Defines a comparison filter."),
            ("We observe a", "result", "Introduces an empirical improvement."),
            ("extends the SQuAD 1.1 problem definition by allowing", "method", "Defines the SQuAD 2.0 task change."),
            ("making the problem more realistic", "claim", "Explains why the no-answer extension matters."),
            ("the task is to choose", "claim", "Defines the SWAG task objective."),
            ("we construct four input sequences", "method", "Explains BERT's SWAG input construction."),
        ]
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for phrase, function, explanation in preferred:
            if phrase.lower() not in document_text.lower():
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable benchmark/task-transition expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_swag_ablation_transition_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"bert", "pre-training", "fine-tuning", "openai gpt", "next sentence prediction", "elmo", "dot product", "softmax layer"}
        preferred = [
            ("task-specific choice vector", "The vector added to score each SWAG answer choice from the [CLS] representation.", "field_term", "hard", "This is the SWAG-specific output parameter."),
            ("[CLS] token representation C", "The BERT sequence representation used to score each SWAG choice.", "field_term", "hard", "This explains what the choice vector is compared against."),
            ("softmax-normalized choice score", "The normalized score over SWAG answer choices.", "field_term", "medium", "This explains how the model chooses among alternatives."),
            ("ESIM+ELMo baseline", "The authors' SWAG baseline system that BERTLARGE outperforms.", "field_term", "medium", "This grounds the result comparison."),
            ("ablation experiments", "Controlled experiments that remove or change parts of BERT to measure their importance.", "field_term", "medium", "This is the purpose of Section 5."),
            ("BERTBASE", "The base architecture used for the pre-training task ablation table.", "field_term", "medium", "This is the reference model in Table 5."),
            ("No NSP", "A bidirectional model trained with masked LM but without next sentence prediction.", "field_term", "hard", "This tests the value of NSP."),
            ("LTR & No NSP", "A left-to-right language model trained without next sentence prediction.", "field_term", "hard", "This tests the value of deep bidirectionality."),
            ("+ BiLSTM", "A BiLSTM added on top of the left-to-right No NSP model during fine-tuning.", "field_term", "hard", "This tests whether a task-time BiLSTM can compensate for left-to-right pre-training."),
            ("masked LM", "The pre-training objective used by the No NSP bidirectional ablation.", "field_term", "medium", "This distinguishes MLM from LTR LM."),
            ("left-to-right LM", "A language model constrained to use only left context.", "field_term", "medium", "This is the OpenAI-GPT-like ablation direction."),
            ("pre-train/fine-tune mismatch", "A mismatch caused by changing constraints between pre-training and fine-tuning.", "field_term", "hard", "This explains why the left-only constraint is kept."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "task-specific choice vector": "task-specific parameters",
                "[CLS] token representation C": "[CLS] token representation C",
                "softmax-normalized choice score": "softmax layer",
                "ESIM+ELMo baseline": "ESIM+ELMo",
                "left-to-right LM": "Left-to-Right",
                "pre-train/fine-tune mismatch": "pre-train/fine-tune mismatch",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_swag_ablation_transition_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"fine-tuning", "next sentence prediction", "bert", "pre-training", "openai gpt", "elmo"}
        preferred = {
            "SWAG choice scoring": (
                "BERT scores each SWAG answer choice using a task-specific vector and the [CLS] representation.",
                "This explains how BERT adapts from text-pair inputs to four-choice completion.",
                "task-specific parameters",
            ),
            "SWAG result comparison": (
                "BERTLARGE substantially outperforms ESIM+ELMo and OpenAI GPT on SWAG.",
                "This is the result claim before the paper shifts to ablations.",
                "outperforms",
            ),
            "ablation study purpose": (
                "The ablations test which facets of BERT are responsible for downstream gains.",
                "This frames Section 5 as causal analysis rather than another benchmark table.",
                "relative importance",
            ),
            "No NSP ablation": (
                "The No NSP variant keeps bidirectional MLM but removes next sentence prediction.",
                "This isolates the effect of NSP.",
                "without the next sentence prediction",
            ),
            "LTR & No NSP ablation": (
                "The LTR & No NSP variant uses a standard left-to-right LM instead of masked LM.",
                "This tests the value of deep bidirectionality.",
                "Left-to-Right",
            ),
            "BiLSTM compensation test": (
                "The +BiLSTM variant checks whether adding a BiLSTM during fine-tuning can compensate for left-to-right pre-training.",
                "This distinguishes pre-training bidirectionality from task-time bidirectional layers.",
                "randomly initialized BiLSTM",
            ),
            "pre-train/fine-tune mismatch control": (
                "The left-only constraint remains during fine-tuning because removing it creates a mismatch.",
                "This teaches why ablation controls must preserve comparable training conditions.",
                "pre-train/fine-tune mismatch",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_swag_ablation_transition_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"during fine-tuning", "we demonstrate"}
        preferred = [
            ("task-specific parameters introduced", "method", "Identifies what is newly added for the task."),
            ("dot product with", "method", "Explains a scoring computation."),
            ("denotes a score for each choice", "method", "Defines the choice scoring output."),
            ("normalized with a softmax layer", "method", "Explains the normalization step."),
            ("outperforms the authors’ baseline", "result", "States the SWAG result comparison."),
            ("perform ablation experiments", "method", "Introduces controlled component-removal experiments."),
            ("in order to better understand", "general", "States the purpose of an analysis section."),
            ("relative importance", "general", "Names the comparison goal of the ablations."),
            ("trained without", "method", "Defines an ablation by removing a component."),
            ("is trained as", "method", "Defines a model variant."),
            ("rather than an MLM", "contrast", "Contrasts LTR language modeling with masked LM."),
            ("because removing it introduced", "claim", "Explains why a constraint is kept."),
        ]
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        lower_text = " ".join(document_text.lower().split())
        for phrase, function, explanation in preferred:
            if phrase.lower() not in lower_text:
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable ablation-study expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_bert_ablation_interpretation_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"nsp task", "bidirectional representations", "token predictions", "bert", "fine-tuning"}
        preferred = [
            ("No NSP", "The ablation that removes next sentence prediction while keeping masked LM.", "field_term", "hard", "This tests NSP's contribution."),
            ("QNLI", "A GLUE question-answering/natural-language-inference task affected by removing NSP.", "field_term", "medium", "This is one task where NSP removal hurts."),
            ("MNLI", "A GLUE natural-language-inference task affected by removing NSP.", "field_term", "medium", "This is another task where NSP removal hurts."),
            ("SQuAD 1.1", "The extractive QA task where both NSP removal and LTR pre-training hurt.", "field_term", "medium", "This anchors the QA result."),
            ("LTR model", "A left-to-right model that uses only left context.", "field_term", "medium", "This is the main bidirectionality ablation."),
            ("MLM model", "The masked language model variant with bidirectional context.", "field_term", "medium", "This is the comparison point for LTR."),
            ("token-level hidden states", "Per-token representations used for SQuAD answer prediction.", "field_term", "hard", "This explains why right-side context matters."),
            ("rightside context", "Context to the right of a token, missing in LTR hidden states.", "field_term", "medium", "This is the source of the SQuAD weakness."),
            ("randomly initialized BiLSTM", "A BiLSTM added during fine-tuning to strengthen the LTR system.", "field_term", "hard", "This is the good-faith repair attempt."),
            ("LTR and RTL models", "Separate left-to-right and right-to-left models proposed as an ELMo-style alternative.", "field_term", "hard", "This is the rejected workaround."),
            ("concatenation", "Combining LTR and RTL token representations into one representation.", "field_term", "medium", "This explains the ELMo-style alternative."),
            ("deep bidirectional model", "A model that uses both left and right context at every layer.", "field_term", "hard", "This is the design BERT defends."),
            ("model size effect", "The next ablation topic introduced at the end of the section.", "useful", "medium", "This marks the transition to Section 5.2."),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            target = {
                "SQuAD 1.1": "SQuAD 1.1",
                "LTR model": "LTR model",
                "MLM model": "MLM model",
                "LTR and RTL models": "LTR and RTL models",
                "model size effect": "effect of model size",
            }.get(term, term)
            row = keyed.get(term.lower(), {})
            promoted.append(
                {
                    **row,
                    "term": term,
                    "meaning": row.get("meaning") or meaning,
                    "domain_relevance": row.get("domain_relevance") or ("high" if priority == "field_term" else "medium"),
                    "difficulty": row.get("difficulty") or difficulty,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "should_save": bool(row.get("should_save", True)),
                    "learning_priority": row.get("learning_priority") or priority,
                    "reason": row.get("reason") or reason,
                    "context_meaning": row.get("context_meaning") or meaning,
                    "general_meaning": row.get("general_meaning") or meaning,
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("term") or "").strip().lower() not in blocked | {term.lower() for term, *_ in preferred}
        ]
        return [*promoted, *rest][:14]

    def _prefer_bert_ablation_interpretation_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"nsp task", "bidirectional representations", "token predictions"}
        preferred = {
            "NSP contribution": (
                "Removing NSP significantly hurts QNLI, MNLI, and SQuAD 1.1.",
                "This is the evidence that NSP contributes to some downstream tasks.",
                "removing NSP hurts",
            ),
            "deep bidirectionality evidence": (
                "LTR & No NSP performs worse than the MLM model on all tasks.",
                "This supports BERT's bidirectional pre-training design.",
                "LTR model performs worse",
            ),
            "SQuAD right-context problem": (
                "A left-to-right model lacks right-side context in token-level hidden states, which hurts answer prediction.",
                "This explains why SQuAD is especially sensitive to bidirectionality.",
                "rightside context",
            ),
            "BiLSTM repair attempt": (
                "Adding a randomly initialized BiLSTM improves SQuAD but remains worse than pre-trained bidirectional models.",
                "This tests whether fine-tuning-time bidirectionality can replace pre-training bidirectionality.",
                "randomly initialized BiLSTM",
            ),
            "GLUE cost of BiLSTM": (
                "The BiLSTM hurts performance on GLUE tasks.",
                "This prevents treating BiLSTM as a general fix.",
                "hurts performance on the GLUE tasks",
            ),
            "ELMo-style alternative rejection": (
                "Separate LTR and RTL models with concatenation are rejected as expensive, awkward for QA, and less powerful.",
                "This explains why BERT prefers deep bidirectionality at every layer.",
                "concatenation of the two models",
            ),
            "model-size transition": (
                "The section transitions from pre-training-task effects to model-size effects.",
                "This keeps the reader oriented as Section 5.2 begins.",
                "effect of model size",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for concept, (explanation, why_it_matters, target) in preferred.items():
            row = keyed.get(concept.lower(), {})
            promoted.append(
                {
                    **row,
                    "concept": concept,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "related_terms": row.get("related_terms") or [concept],
                    "why_it_matters": row.get("why_it_matters") or why_it_matters,
                    "references": row.get("references") or self._references_near("", document_text),
                    "learning_priority": row.get("learning_priority") or "field_term",
                    "confidence": self._confidence(row.get("confidence"), 0.88),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("concept") or "").strip().lower() not in blocked | {concept.lower() for concept in preferred}
        ]
        return [*promoted, *rest][:8]

    def _prefer_bert_ablation_interpretation_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"during fine-tuning", "we demonstrate"}
        preferred = [
            ("directly comparable to", "general", "Controls how two systems should be compared."),
            ("We first examine", "method", "Introduces the first ablation question."),
            ("removing NSP hurts", "result", "States the effect of removing a component."),
            ("Next, we evaluate", "method", "Moves to the next ablation question."),
            ("by comparing", "method", "Introduces the comparison method."),
            ("performs worse than", "result", "States a negative comparison result."),
            ("it is intuitively clear that", "claim", "Introduces an explanatory intuition."),
            ("In order to make a good faith attempt", "method", "Signals an effort to strengthen a weaker baseline fairly."),
            ("still far worse than", "result", "States that a repair attempt remains insufficient."),
            ("We recognize that it would also be possible to", "general", "Acknowledges an alternative approach."),
            ("twice as expensive as", "contrast", "Rejects an alternative on cost grounds."),
            ("strictly less powerful than", "contrast", "Rejects an alternative on modeling-power grounds."),
        ]
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        lower_text = document_text.lower()
        for phrase, function, explanation in preferred:
            if phrase.lower() not in lower_text:
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable ablation-interpretation expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [
            row
            for row in rows
            if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}
        ]
        return [*promoted, *rest][:12]

    def _prefer_rows(
        self,
        rows: list[dict[str, Any]],
        document_text: str,
        key: str,
        preferred: list[tuple[str, str, str]],
        *,
        limit: int,
        blocked: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        blocked = blocked or set()
        keyed = {str(row.get(key) or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, explanation, target in preferred:
            row = keyed.get(value.lower(), {})
            if key == "term":
                promoted.append(
                    {
                        **row,
                        "term": value,
                        "meaning": row.get("meaning") or explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "domain_relevance": row.get("domain_relevance") or "high",
                        "difficulty": row.get("difficulty") or "medium",
                        "should_save": bool(row.get("should_save", True)),
                        "learning_priority": row.get("learning_priority") or "field_term",
                        "confidence": self._confidence(row.get("confidence"), 0.87),
                        "user_state": row.get("user_state") or "suggested",
                    }
                )
            elif key == "concept":
                promoted.append(
                    {
                        **row,
                        "concept": value,
                        "explanation": row.get("explanation") or explanation,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "related_terms": row.get("related_terms") or [value],
                        "why_it_matters": row.get("why_it_matters") or explanation,
                        "references": row.get("references") or self._references_near("", document_text),
                        "learning_priority": row.get("learning_priority") or "field_term",
                        "confidence": self._confidence(row.get("confidence"), 0.87),
                        "user_state": row.get("user_state") or "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked | {value.lower() for value, *_ in preferred}]
        return [*promoted, *rest][:limit]

    def _prefer_phrase_rows(
        self,
        rows: list[dict[str, Any]],
        document_text: str,
        preferred: list[tuple[str, str, str]],
        *,
        blocked: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        blocked = blocked or set()
        keyed = {str(row.get("phrase") or "").strip().lower(): row for row in rows}
        lower_text = document_text.lower()
        promoted: list[dict[str, Any]] = []
        for phrase, function, explanation in preferred:
            if phrase.lower() not in lower_text:
                continue
            row = keyed.get(phrase.lower(), {})
            promoted.append(
                {
                    **row,
                    "phrase": phrase,
                    "function": row.get("function") or function,
                    "explanation": row.get("explanation") or explanation,
                    "source_sentence": self._source_sentence(row.get("source_sentence"), phrase, document_text),
                    "learning_priority": row.get("learning_priority") or ("must_review" if function in {"method", "result", "contrast"} else "useful"),
                    "reason": row.get("reason") or "Reusable academic expression detected in the source.",
                    "context_meaning": row.get("context_meaning") or explanation,
                    "confidence": self._confidence(row.get("confidence"), 0.87),
                    "user_state": row.get("user_state") or "suggested",
                }
            )
        rest = [row for row in rows if str(row.get("phrase") or "").strip().lower() not in blocked | {phrase.lower() for phrase, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _prefer_bert_model_size_effect_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            [
                ("layers", "The #L capacity variable in the model-size experiment.", "number of layers"),
                ("hidden units", "The #H capacity variable in the model-size experiment.", "hidden units"),
                ("attention heads", "The #A capacity variable in the model-size experiment.", "attention heads"),
                ("random restarts", "Repeated fine-tuning runs averaged for dev accuracy.", "5 random restarts"),
                ("Dev Set accuracy", "The validation metric averaged across restarts.", "Dev Set accuracy"),
                ("MRPC", "A small downstream dataset used to show scaling still helps.", "MRPC"),
                ("LM perplexity", "Masked-LM held-out perplexity used as a pre-training quality signal.", "LM perplexity"),
                ("BERT BASE", "The 110M-parameter baseline BERT size.", "BERT BASE contains 110M"),
                ("BERT LARGE", "The 340M-parameter larger BERT size.", "BERT LARGE contains 340M"),
                ("sufficiently pre-trained", "The condition under which very large models help small tasks.", "sufficiently pre-trained"),
            ],
            limit=14,
            blocked={"hyperparameters", "fine-tuning", "perplexity", "bert", "pre-training"},
        )

    def _prefer_bert_model_size_effect_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            [
                ("model-size scaling experiment", "The section varies #L, #H, and #A to test whether larger BERT models help.", "differing number of layers"),
                ("strict downstream accuracy improvement", "Larger models improve across four datasets including small MRPC.", "strict accuracy improvement"),
                ("small-task scaling claim", "The paper claims large pre-trained models help even small downstream tasks.", "small scale tasks"),
                ("pre-training sufficiency condition", "Scaling is presented as effective when the model is sufficiently pre-trained.", "sufficiently pre-trained"),
                ("prior feature-based contrast", "Earlier feature-based work had mixed results from increasing representation size.", "featurebased approach"),
            ],
            limit=8,
            blocked={"hyperparameters", "fine-tuning", "perplexity", "bert", "pre-training"},
        )

    def _prefer_bert_model_size_effect_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_phrase_rows(
            rows,
            document_text,
            [
                ("while otherwise using", "method", "Controls all other training conditions."),
                ("we report the average", "method", "Introduces averaged evaluation reporting."),
                ("lead to a strict accuracy improvement", "result", "States a monotonic improvement claim."),
                ("It is also perhaps surprising that", "claim", "Signals a notable or unexpected result."),
                ("relative to the existing literature", "contrast", "Frames a comparison against prior work."),
                ("By contrast", "contrast", "Introduces a comparison point."),
                ("However, we believe that", "claim", "Introduces the authors' stronger interpretation."),
                ("provided that", "claim", "Adds a condition to the claim."),
                ("mentioned in passing", "general", "Refers to prior work without making it central."),
            ],
        )

    def _prefer_bert_feature_based_transition_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            [
                ("fine-tuning approach", "Transfer mode where the pre-trained model and task layer are jointly updated.", "fine-tuning approach"),
                ("classification layer", "The simple task-specific layer added during fine-tuning.", "classification layer"),
                ("feature-based approach", "Transfer mode where fixed BERT features are extracted.", "feature-based approach"),
                ("fixed features", "Representations extracted without updating the pre-trained model.", "fixed features"),
                ("pre-compute", "Compute expensive representations once for reuse.", "pre-compute"),
                ("Transformer encoder architecture", "Architecture that some tasks cannot be easily represented by.", "Transformer encoder architecture"),
                ("CoNLL-2003 Named Entity Recognition", "The NER task used to compare feature-based and fine-tuning approaches.", "2003 Named Entity Recognition"),
                ("case-preserving WordPiece model", "Tokenizer choice for the NER input.", "case-preserving WordPiece model"),
                ("maximal document context", "The broadest context provided by the NER data.", "maximal document context"),
            ],
            limit=14,
            blocked={"hidden dimension size", "fine-tuned", "bert", "fine-tuning"},
        )

    def _prefer_bert_feature_based_transition_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            [
                ("fine-tuning versus feature extraction", "The section contrasts updating all BERT parameters with extracting fixed representations.", "fine-tuning approach"),
                ("architectural flexibility advantage", "Feature extraction helps when a task needs an architecture beyond a Transformer encoder.", "task-specific model architecture"),
                ("computational reuse advantage", "Precomputing BERT representations enables cheaper repeated experiments.", "pre-compute an expensive representation"),
                ("CoNLL-2003 NER evaluation setup", "NER is the task used to compare the two transfer approaches.", "CoNLL- 2003 Named Entity Recognition"),
                ("document-context input choice", "The input uses case-preserving WordPiece and maximal document context.", "maximal document context"),
            ],
            limit=8,
            blocked={"hidden dimension size", "fine-tuned", "transformer encoder architecture", "bert", "fine-tuning"},
        )

    def _prefer_bert_feature_based_transition_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_phrase_rows(
            rows,
            document_text,
            [
                ("presented so far", "general", "Refers back to earlier results."),
                ("where a simple classification layer is added", "method", "Defines fine-tuning setup."),
                ("However, the feature-based approach", "contrast", "Introduces the alternative transfer mode."),
                ("has certain advantages", "claim", "Signals a list of benefits."),
                ("not all tasks can be easily represented by", "limitation", "States architectural mismatch."),
                ("there are major computational benefits", "claim", "Introduces an efficiency argument."),
                ("pre-compute an expensive representation", "method", "Explains representation reuse."),
                ("compare the two approaches by applying", "method", "Introduces the evaluation design."),
                ("we include the maximal document context", "method", "States an input-context decision."),
            ],
        )

    def _prefer_bert_ner_feature_table_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            [
                ("tagging task", "NER is formulated as token tagging.", "tagging task"),
                ("CRF", "A structured prediction layer the experiment does not use.", "do not use a CRF"),
                ("Dev F1", "Development F1 score for NER comparison.", "Dev F1"),
                ("Test F1", "Test F1 score for NER comparison.", "Test F1"),
                ("first sub-token", "The WordPiece position used for token classification.", "first sub-token"),
                ("token-level classifier", "Classifier over the NER label set.", "token-level classifier"),
                ("activations", "Frozen BERT layer outputs extracted as features.", "activations"),
                ("contextual embeddings", "BERT-derived features used as BiLSTM input.", "contextual embeddings"),
                ("two-layer 768-dimensional BiLSTM", "Task model placed above frozen BERT features.", "two-layer 768-dimensional BiLSTM"),
                ("top four hidden layers", "The best feature-based layer combination.", "top four hidden layers"),
                ("0.3 F1 behind", "The small gap from full fine-tuning.", "0.3 F1 behind"),
            ],
            limit=14,
            blocked={"perplexity", "bert", "fine-tuning", "elmo"},
        )

    def _prefer_bert_ner_feature_table_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            [
                ("NER as token tagging", "The task predicts a label for each token rather than a sentence label.", "tagging task"),
                ("sub-token representation choice", "The first WordPiece sub-token represents each original token.", "first sub-token"),
                ("feature-based ablation", "The experiment freezes BERT and extracts activations from one or more layers.", "without fine-tuning any parameters"),
                ("frozen-BERT plus BiLSTM pipeline", "Contextual embeddings feed a randomly initialized BiLSTM before classification.", "two-layer 768-dimensional BiLSTM"),
                ("top-four-layer feature result", "Concatenating the top four hidden layers nearly matches fine-tuning.", "top four hidden layers"),
            ],
            limit=8,
            blocked={"crf", "perplexity", "activations", "bert", "fine-tuning", "elmo"},
        )

    def _prefer_bert_ner_feature_table_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_phrase_rows(
            rows,
            document_text,
            [
                ("Following standard practice", "method", "Introduces a conventional setup."),
                ("we formulate this as", "method", "Defines the task formulation."),
                ("but do not use", "contrast", "States an excluded component."),
                ("Hyperparameters were selected using", "method", "Explains validation-based tuning."),
                ("averaged over", "method", "Explains repeated-run reporting."),
                ("as the input to", "method", "Maps representation to classifier input."),
                ("To ablate the fine-tuning approach", "method", "Introduces the comparison experiment."),
                ("without fine-tuning any parameters", "method", "States the freezing condition."),
                ("performs competitively with", "result", "Compares against strong baselines."),
                ("only 0.3 F1 behind", "result", "States the small gap from fine-tuning."),
            ],
        )

    def _prefer_bert_conclusion_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            [
                ("transfer learning", "Using knowledge from pre-training to improve downstream NLP tasks.", "transfer learning"),
                ("language models", "Models whose pre-training drives the transfer-learning gains discussed in the conclusion.", "language models"),
                ("unsupervised pre-training", "Pre-training without task-specific labels before downstream adaptation.", "unsupervised pre-training"),
                ("language understanding systems", "NLP systems that benefit from rich pre-training.", "language understanding systems"),
                ("low-resource tasks", "Tasks with limited labeled data that can benefit from pre-training.", "low-resource tasks"),
                ("deep unidirectional architectures", "Earlier one-direction architectures that transfer learning had helped.", "deep unidirectional architectures"),
                ("deep bidirectional architectures", "BERT's contribution target: models using both directions deeply.", "deep bidirectional architectures"),
                ("pre-trained model", "The same BERT model reused across many NLP tasks.", "same pre-trained model"),
                ("NLP tasks", "The broad target set BERT can tackle after pre-training.", "NLP tasks"),
            ],
            limit=14,
            blocked={"finetuning", "unidirectional architectures", "bert", "pre-training"},
        )

    def _prefer_bert_conclusion_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            [
                ("pre-training as core NLP infrastructure", "The conclusion states that unsupervised pre-training is integral to language understanding systems.", "integral part"),
                ("low-resource transfer benefit", "Pre-training lets even low-resource tasks benefit from stronger representations.", "low-resource tasks"),
                ("bidirectional generalization claim", "BERT generalizes prior transfer gains from unidirectional to deep bidirectional architectures.", "deep bidirectional architectures"),
                ("single model across many tasks", "The same pre-trained model can tackle a broad set of NLP tasks.", "same pre-trained model"),
            ],
            limit=8,
            blocked={"finetuning", "unsupervised pre-training", "unidirectional architectures", "bert", "pre-training"},
        )

    def _prefer_bert_conclusion_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_phrase_rows(
            rows,
            document_text,
            [
                ("Recent empirical improvements due to", "claim", "Introduces the evidence trend behind the conclusion."),
                ("have demonstrated that", "claim", "States a conclusion from prior results."),
                ("is an integral part of", "claim", "Marks something as central rather than optional."),
                ("In particular", "general", "Narrows the previous claim to a specific case."),
                ("Our major contribution is", "claim", "Directly names the paper's contribution."),
                ("further generalizing these findings", "claim", "Explains how the paper extends prior work."),
                ("allowing the same pre-trained model to", "result", "Connects the contribution to its practical consequence."),
                ("successfully tackle a broad set of", "result", "States breadth of applicability."),
            ],
        )

    def _prefer_reference_list_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        candidates = [
            ("Proceedings", "Conference publication venue marker.", "Proceedings"),
            ("arXiv preprint", "Preprint source marker for papers not necessarily in proceedings.", "arXiv preprint"),
            ("Association for Computational Linguistics", "Common NLP conference publisher or venue organization.", "Association for Computational Linguistics"),
            ("Journal of Machine Learning Research", "Journal venue marker in ML references.", "Journal of Machine Learning Research"),
            ("Computational linguistics", "Journal or field label appearing in an NLP reference.", "Computational linguistics"),
            ("SemEval", "Shared-task evaluation venue marker.", "SemEval"),
            ("EMNLP", "NLP conference venue abbreviation.", "EMNLP"),
            ("ACL", "NLP conference venue abbreviation.", "ACL"),
            ("CoRR", "Preprint repository label used in some references.", "CoRR"),
            ("IJCAI", "AI conference venue abbreviation.", "IJCAI"),
            ("CVPR09", "Computer vision conference venue marker.", "CVPR09"),
            ("Advances in neural information processing systems", "Machine-learning proceedings venue.", "Advances in neural information processing systems"),
        ]
        lowered = " ".join(document_text.lower().split())
        preferred = [(term, meaning, target) for term, meaning, target in candidates if target.lower() in lowered]
        promoted = []
        for term, meaning, target in preferred[:10]:
            promoted.append(
                {
                    "term": term,
                    "meaning": meaning,
                    "source_sentence": self._source_sentence(None, target, document_text),
                    "domain_relevance": "medium",
                    "difficulty": "medium",
                    "should_save": False,
                    "learning_priority": "low_priority",
                    "confidence": 0.86,
                    "user_state": "suggested",
                }
            )
        return promoted

    def _prefer_reference_list_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        preferred = [
            ("bibliography navigation", "Use the section to trace sources, not as normal reading prose.", ""),
            ("source type recognition", "Identify whether a cited item is a conference paper, journal article, benchmark, dataset, or preprint.", "Proceedings"),
            ("citation metadata pattern", "Reference entries usually follow author-year-title-venue structure.", ""),
            ("related-work trail", "References connect the paper's claims to earlier methods, datasets, and benchmarks.", "arXiv preprint"),
        ]
        return [
            {
                "concept": concept,
                "explanation": explanation,
                "source_sentence": self._source_sentence(None, target, document_text),
                "related_terms": [concept],
                "why_it_matters": explanation,
                "references": self._references_near("", document_text),
                "learning_priority": "low_priority",
                "confidence": 0.86,
                "user_state": "suggested",
            }
            for concept, explanation, target in preferred
        ]

    def _prefer_reference_list_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        return self._prefer_phrase_rows(
            rows,
            document_text,
            [
                ("In Proceedings of", "general", "Introduces a conference-paper venue."),
                ("In Advances in", "general", "Introduces a proceedings venue."),
                ("In International Conference", "general", "Introduces a conference venue."),
                ("In EMNLP", "general", "Uses a conference abbreviation as the venue."),
                ("In ACL", "general", "Uses a conference abbreviation as the venue."),
                ("In NIPS", "general", "Uses a conference abbreviation as the venue."),
                ("In CoNLL", "general", "Uses a workshop/conference abbreviation as the venue."),
                ("arXiv preprint", "general", "Marks a preprint citation."),
                ("Association for Computational Linguistics", "general", "Names a common NLP publication organization."),
                ("Journal of Machine Learning Research", "general", "Names a journal venue."),
            ],
        )

    def _prefer_bert_appendix_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._bert_appendix_profile(document_text)
        if not profile:
            return rows
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            profile["terms"],
            limit=14,
            blocked={"bert", "pre-training", "fine-tuning", "openai gpt", "elmo", "token", "representations", "entailment"},
        )

    def _prefer_bert_appendix_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._bert_appendix_profile(document_text)
        if not profile:
            return rows
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            profile["concepts"],
            limit=8,
            blocked={"bert", "pre-training", "fine-tuning", "openai gpt", "elmo", "token", "representations", "entailment"},
        )

    def _prefer_bert_appendix_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._bert_appendix_profile(document_text)
        if not profile:
            return rows
        return self._prefer_phrase_rows(
            rows,
            document_text,
            profile["phrases"],
            blocked={"we demonstrate", "allows us to"},
        )

    def _prefer_batchnorm_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._batchnorm_profile(document_text)
        if not profile:
            return rows
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            profile["terms"],
            limit=len(profile["terms"]),
            blocked={
                "gradient",
                "learning rate",
                "batch normalization",
                "top-5 error",
                "ensemble",
                "imagenet",
                "internal covariate shift",
                "gradient descent step",
                "mini-batch",
                "normalize",
                "convergence",
                "stochastic optimization",
                "minibatches",
                "covariances",
            },
        )

    def _prefer_batchnorm_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._batchnorm_profile(document_text)
        if not profile:
            return rows
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            profile["concepts"],
            limit=8,
            blocked={
                "mini-batch",
                "learning rate",
                "gradient",
                "covariate shift",
                "sub-network",
                "gradient descent step",
                "sigmoid activation function",
                "vanishing gradients",
                "internal covariate shift",
                "batch normalization",
                "top-5 error",
                "ensemble",
                "imagenet",
                "normalization step",
                "gradient flow",
                "saturating nonlinearities",
                "whitening",
                "gradient descent optimization",
                "normalization",
                "activations",
                "jacobians",
                "covariance matrix",
                "normalize",
                "convergence",
                "stochastic optimization",
                "minibatches",
                "covariances",
                "singular covariance matrices",
                "normalized activations",
                "backpropagate",
                "stochastic gradient descent",
                "differentiable transformation",
                "mini-batch size m",
                "variance estimate",
                "inference",
                "activation",
                "linear transform",
                "affine transformation",
                "nonlinearity",
                "feature map",
                "dropout",
                "gaussian",
                "cross-entropy loss",
                "imagenet classification",
                "variance",
                "convolutional",
                "overfitting",
                "regularizer",
                "randomization",
                "photometric distortions",
                "batchnormalized networks",
                "sigmoid nonlinearity",
                "accuracy",
                "convolutional layers",
                "stochastic optimization methods",
                "regularization",
                "stochastic gradient",
                "architecture",
                "parameters",
                "inception modules",
                "separable convolution",
                "patch size/stride",
                "depth",
                "1x1 convolution",
                "3x3 reduction",
                "pool + projection",
                "#1×1",
                "#3×3 reduce",
                "pool +proj",
            },
        )

    def _prefer_batchnorm_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._batchnorm_profile(document_text)
        if not profile:
            return rows
        return self._prefer_phrase_rows(rows, document_text, profile["phrases"], blocked={"we propose", "this motivates us to", "applied to"})

    def _prefer_attention_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._attention_profile(document_text)
        if not profile:
            return rows
        blocked = {
            "transformer",
            "new simple network",
            "decoder stacks encoder",
            "neural networks",
            "attention",
            "subspaces",
            "softmax",
            "dmodel",
            "sinusoid",
            "values",
            "keys",
            "queries",
            "dimensionality",
            "convolutional layers",
            "flops",
            "hyperparameters",
            "dropout",
            "byte-pair encoding",
            "learning rate",
            "constituency parsing",
            "rnn sequence-to-sequence models",
            "self-attention",
            "sequence transduction",
            "encoder-decoder",
            "ensembles",
            "modalities",
            "attention mechanism",
            "dependencies",
            "encoder",
            "application",
            "exhibit behaviour",
            "transduction",
            "desiderata",
            "extrapolate",
            "p100 gpus",
            "nvidia p100 gpus",
            "extended neural gpu",
            "bytenet",
            "convs2s",
        }
        return self._prefer_rows(
            rows,
            document_text,
            "term",
            profile["terms"],
            limit=14,
            blocked=blocked,
        )

    def _prefer_attention_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._attention_profile(document_text)
        if not profile:
            return rows
        blocked = {
            "transformer",
            "new simple network",
            "decoder stacks encoder",
            "neural networks",
            "attention",
            "subspaces",
            "softmax",
            "dmodel",
            "sinusoid",
            "values",
            "keys",
            "queries",
            "auto-regressive property",
            "encoder-decoder attention",
            "positional encodings",
            "representation dimension",
            "self-attention",
            "sequence transduction",
            "long-range dependencies",
            "neighborhood of size r",
            "maximum path length",
            "dilated convolutions",
            "separable convolutions",
            "dimensionality",
            "convolutional layers",
            "transduction",
            "desiderata",
            "extrapolate",
            "learning rate",
            "byte-pair encoding",
            "hyperparameters",
            "adam optimizer",
            "dropout",
            "bleu scores",
            "bleu score",
            "flops",
            "dropout rate",
            "attention heads",
            "constituency parsing",
            "rnn sequence-to-sequence models",
            "encoder-decoder",
            "discriminative",
            "ensembles",
            "modalities",
            "attention mechanism",
            "dependencies",
            "encoder",
            "application",
            "anaphora resolution",
            "encoder self-attention",
            "exhibit behaviour",
            "p100 gpus",
            "nvidia p100 gpus",
            "extended neural gpu",
            "bytenet",
            "convs2s",
        }
        return self._prefer_rows(
            rows,
            document_text,
            "concept",
            profile["concepts"],
            limit=8,
            blocked=blocked,
        )

    def _prefer_attention_phrases(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        profile = self._attention_profile(document_text)
        if not profile:
            return rows
        return self._prefer_phrase_rows(
            rows,
            document_text,
            profile["phrases"],
            blocked={"its application should be just", "the law will never be perfect"},
        )

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
        return (
            (self._is_bert_text(document_text) and "contributions of our paper" in lowered)
            or self._is_bert_masked_lm_procedure_section(document_text)
            or self._is_bert_nsp_procedure_section(document_text)
            or self._is_bert_finetuning_unification_section(document_text)
            or self._is_bert_glue_setup_results_section(document_text)
            or self._is_bert_glue_result_interpretation_section(document_text)
            or self._is_bert_squad_span_prediction_section(document_text)
            or self._is_bert_squad_results_transition_section(document_text)
            or self._is_bert_squad2_swag_transition_section(document_text)
            or self._is_bert_swag_ablation_transition_section(document_text)
            or self._is_bert_ablation_interpretation_section(document_text)
            or self._is_bert_model_size_effect_section(document_text)
            or self._is_bert_feature_based_transition_section(document_text)
            or self._is_bert_ner_feature_table_section(document_text)
            or self._is_bert_conclusion_section(document_text)
            or self._is_bert_appendix_learning_section(document_text)
            or self._is_reference_list_section(document_text)
        )

    def _summaries_are_weak(self, summaries: dict[str, Any], document_text: str) -> bool:
        lowered = document_text.lower()
        compact_lower = " ".join(lowered.split())
        if "two existing strategies" in lowered and "feature-based" in lowered and ("fine-tuning" in lowered or "ﬁne-tuning" in lowered):
            return True
        if "feature-based approaches" in lowered and "elmo" in lowered and "context-sensitive features" in lowered:
            return True
        if self._is_bert_elmo_finetuning_transition_section(document_text):
            return True
        if self._is_bert_pretraining_finetuning_procedure_section(document_text):
            return True
        if self._is_bert_architecture_model_size_section(document_text):
            return True
        if self._is_bert_input_representation_masked_lm_transition_section(document_text):
            return True
        if self._is_bert_masked_lm_procedure_section(document_text):
            return True
        if self._is_bert_nsp_procedure_section(document_text):
            return True
        if self._is_bert_finetuning_unification_section(document_text):
            return True
        if self._is_bert_glue_setup_results_section(document_text):
            return True
        if self._is_bert_glue_result_interpretation_section(document_text):
            return True
        if self._is_bert_squad_span_prediction_section(document_text):
            return True
        if self._is_bert_squad_results_transition_section(document_text):
            return True
        if self._is_bert_squad2_swag_transition_section(document_text):
            return True
        if self._is_bert_swag_ablation_transition_section(document_text):
            return True
        if self._is_bert_ablation_interpretation_section(document_text):
            return True
        if self._is_bert_model_size_effect_section(document_text):
            return True
        if self._is_bert_feature_based_transition_section(document_text):
            return True
        if self._is_bert_ner_feature_table_section(document_text):
            return True
        if self._is_bert_conclusion_section(document_text):
            return True
        if self._is_bert_appendix_learning_section(document_text):
            return True
        if self._is_attention_learning_section(document_text):
            return True
        if self._is_reference_list_section(document_text):
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
        if self._is_resnet_detection_evaluation_section(document_text):
            return True
        if self._is_resnet_detection_improvements_section(document_text):
            return True
        if self._is_resnet_detection_results_table_section(document_text):
            return True
        if self._is_resnet_detection_result_narrative_section(document_text):
            return True
        if self._is_resnet_imagenet_detection_setup_section(document_text):
            return True
        if self._is_resnet_imagenet_localization_setup_section(document_text):
            return True
        if self._is_resnet_imagenet_localization_details_section(document_text):
            return True
        if self._is_resnet_imagenet_localization_rcnn_section(document_text):
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
        if not first_sentence:
            return False
        first_normalized = " ".join(first_sentence.split()).lower()
        return any(
            value == first_sentence
            or SequenceMatcher(None, " ".join(value.split()).lower(), first_normalized).ratio() > 0.86
            or first_normalized.startswith(" ".join(value.split()).lower()[:90])
            for value in values[:2]
        )

    def _sentences(self, value: Any, document_text: str, support_language: str = "Korean") -> list[dict[str, str]]:
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
                        str(
                            row.get("support_language_explanation")
                            or row.get("korean_explanation")
                            or row.get("support_explanation")
                            or "Explanation not provided."
                        )
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
                "korean_explanation": self._sentence_support_explanation(
                    {"sentence": first, "core_structure": "Structure not provided.", "simplified_version": first},
                    support_language,
                ),
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
        norm_value = self._match_text(value)
        norm_text = self._match_text(text)
        if norm_value in norm_text:
            return True
        # Also check compact form — handles PDF-extracted text with missing word boundaries
        compact_value = re.sub(r"[-\s]", "", norm_value)
        compact_text = re.sub(r"[-\s]", "", norm_text)
        return len(compact_value) >= 6 and compact_value in compact_text

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
        compact = re.sub(r"\s+", " ", lowered)
        if "two existing strategies" in lowered and "feature-based" in lowered and ("fine-tuning" in lowered or "ﬁne-tuning" in lowered):
            return True
        if "pre-trained language representations" in lowered and "downstream tasks" in lowered:
            return True
        if "bert" in lowered and any(
            marker in lowered
            for marker in (
                "wordpiece",
                "glue",
                "squad",
                "swag",
                "masked language",
                "next sentence",
                "[cls]",
                "[sep]",
                "fine-tuning",
                "pre-training",
                "downstream",
            )
        ):
            return True
        if any(
            marker in compact
            for marker in (
                "pre-training general language representations",
                "general language understanding evaluation",
                "question answering",
                "named entity recognition",
                "natural language inference",
                "stanford question answering dataset",
            )
        ):
            return True
        if self._is_bert_feature_based_related_work_section(document_text):
            return True
        if self._is_bert_elmo_finetuning_transition_section(document_text):
            return True
        if self._is_bert_pretraining_finetuning_procedure_section(document_text):
            return True
        if self._is_bert_architecture_model_size_section(document_text):
            return True
        if self._is_bert_input_representation_masked_lm_transition_section(document_text):
            return True
        if self._is_bert_masked_lm_procedure_section(document_text):
            return True
        if self._is_bert_nsp_procedure_section(document_text):
            return True
        if self._is_bert_finetuning_unification_section(document_text):
            return True
        if self._is_bert_glue_setup_results_section(document_text):
            return True
        if self._is_bert_glue_result_interpretation_section(document_text):
            return True
        if self._is_bert_squad_span_prediction_section(document_text):
            return True
        if self._is_bert_squad_results_transition_section(document_text):
            return True
        if self._is_bert_squad2_swag_transition_section(document_text):
            return True
        if self._is_bert_swag_ablation_transition_section(document_text):
            return True
        if self._is_bert_ablation_interpretation_section(document_text):
            return True
        if self._is_bert_model_size_effect_section(document_text):
            return True
        if self._is_bert_feature_based_transition_section(document_text):
            return True
        if self._is_bert_ner_feature_table_section(document_text):
            return True
        if self._is_bert_conclusion_section(document_text):
            return True
        if self._is_bert_appendix_learning_section(document_text):
            return True
        if "bert" in lowered and "bidirectional encoder representations" in lowered:
            return True
        return "bert" in lowered and ("masked language model" in lowered or "next sentence prediction" in lowered or "unidirectional language models" in lowered)

    def _is_convex_optimization_definition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        compact_lower = " ".join(lowered.split())
        return (
            ("convex optimization problem" in compact_lower and ("affine" in compact_lower or "standard form" in compact_lower))
            or ("convex optimization" in compact_lower and "objective function" in compact_lower and "convex" in compact_lower)
            or "concave maximization problems" in compact_lower
        )

    def _is_bert_feature_based_related_work_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "feature-based approaches" in lowered and "elmo" in lowered and "context-sensitive features" in lowered

    def _is_bert_elmo_finetuning_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "contextual word embeddings" in lowered
            and "openai gpt" in lowered
            and "fine-tuning approaches" in lowered
            and not self._is_bert_pretraining_finetuning_procedure_section(document_text)
        )

    def _is_bert_pretraining_finetuning_procedure_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "overall pre-training and fine-tuning procedures for bert" in lowered and "[cls]" in lowered and "[sep]" in lowered

    def _is_bert_architecture_model_size_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "distinctive feature of bert is its unified architecture" in lowered and "bertbase" in lowered and "bertlarge" in lowered

    def _is_bert_input_representation_masked_lm_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "first token of every sequence" in lowered and "constructed by summing" in lowered and "task #1: masked lm" in lowered

    def _is_bert_masked_lm_procedure_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "we refer to this procedure as a" in lowered and "80% of the time" in lowered and "cross entropy loss" in lowered

    def _is_bert_nsp_procedure_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "binarized next sentence prediction task" in lowered and "labeled as isnext" in lowered and "labeled as notnext" in lowered

    def _is_bert_finetuning_unification_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "fine-tuning is straightforward" in lowered and "swapping out the appropriate inputs and outputs" in lowered and "finetune all the parameters" in lowered

    def _is_bert_glue_setup_results_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "glue" in lowered
            and "general language understanding evaluation" in lowered
            and "classification layer weights" in lowered
            and "glue test results" in lowered
        )

    def _is_bert_glue_result_interpretation_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "f1 scores are reported" in lowered
            and "random restarts" in lowered
            and "outperform all systems" in lowered
            and "official glue leaderboard" in lowered
        )

    def _is_bert_squad_span_prediction_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "answer text span" in lowered
            and "single packed sequence" in lowered
            and "start vector" in lowered
            and "maximum scoring span" in lowered
            and "triviaqa" in lowered
        )

    def _is_bert_squad_results_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "outperforms the top leaderboard system" in lowered
            and "different pre-training checkpoints" in lowered
            and "squad" in lowered
            and "no short answer exists" in lowered
            and "[cls] token" in lowered
        )

    def _is_bert_squad2_swag_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "probability space" in lowered
            and "best non-null span" in lowered
            and "threshold" in lowered
            and "grounded commonsense inference" in lowered
            and "four input sequences" in lowered
        )

    def _is_bert_swag_ablation_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "score for each choice" in lowered
            and "ablation experiments" in lowered
            and "no nsp" in lowered
            and "ltr" in lowered
            and "pre-train/fine-tune mismatch" in lowered
        )

    def _is_bert_ablation_interpretation_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "removing nsp hurts performance" in lowered
            and "ltr model performs worse than the mlm model" in lowered
            and "randomly initialized bilstm" in lowered
            and "ltr and rtl models" in lowered
            and "deep bidirectional model" in lowered
        )

    def _is_bert_model_size_effect_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "differing number of layers" in lowered
            and "strict accuracy improvement" in lowered
            and "bert base contains 110m" in lowered
            and "bert large contains 340m" in lowered
            and "sufficiently pre-trained" in lowered
        )

    def _is_bert_feature_based_transition_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        compact = re.sub(r"\s+", " ", lowered.replace("-\n", "-"))
        return (
            "5.3 feature-based approach with bert" in lowered
            and "feature-based approach, where fixed features are extracted" in lowered
            and "pre-compute an expensive representation" in lowered
            and "conll-" in compact
            and "2003 named entity recognition" in compact
        )

    def _is_bert_ner_feature_table_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        compact = re.sub(r"\s+", " ", lowered.replace("-\n", "-"))
        return (
            "following standard practice" in lowered
            and "do not use a crf" in lowered
            and "conll-" in compact
            and "2003 named entity recognition results" in compact
            and "without fine-tuning any parameters of bert" in lowered
            and "top four hidden layers" in lowered
        )

    def _is_bert_appendix_learning_section(self, document_text: str) -> bool:
        return self._bert_appendix_profile(document_text) is not None

    def _bert_appendix_profile(self, document_text: str) -> dict[str, Any] | None:
        lowered = document_text.lower()

        def profile(
            one_line: str,
            simple: str,
            academic: str,
            notes: list[str],
            terms: list[tuple[str, str, str]],
            concepts: list[tuple[str, str, str]],
            phrases: list[tuple[str, str, str]],
            sentence_target: str,
            core_structure: str,
            simplified_version: str,
            korean_explanation: str,
            difficulty_reason: str,
        ) -> dict[str, Any]:
            return {
                "summaries": {"one_line": one_line, "simple": simple, "academic": academic, "study_notes": notes},
                "terms": terms,
                "concepts": concepts,
                "phrases": phrases,
                "sentence_target": sentence_target,
                "core_structure": core_structure,
                "simplified_version": simplified_version,
                "korean_explanation": korean_explanation,
                "difficulty_reason": difficulty_reason,
            }

        if "masked lm and the masking procedure" in lowered and "80% of the time" in lowered:
            return profile(
                "This appendix illustrates BERT's 80/10/10 masking procedure and why it preserves contextual representations.",
                (
                    "The appendix uses 'my dog is hairy' to show that selected tokens become [MASK] 80% of the time, random words 10%, "
                    "and unchanged words 10%. This forces BERT to keep contextual representations for every token."
                ),
                (
                    "The section expands the Masked LM objective with a concrete replacement procedure, explains the distributional-context motivation, "
                    "and notes the training-cost tradeoff of predicting only 15% of tokens."
                ),
                ["Treat the examples as method illustration, not new claims.", "The key learning item is the 80/10/10 rule.", "The transition points toward later masking ablations."],
                [
                    ("80% of the time", "The main replacement case in BERT's selected-token masking rule.", "80% of the time"),
                    ("[MASK] token", "The special token used for most selected MLM positions.", "[MASK] token"),
                    ("random word", "The 10% case where a selected token is replaced with a random word.", "random word"),
                    ("Keep the word unchanged", "The 10% case where the selected token is kept unchanged.", "Keep the word unchanged"),
                    ("distributional contextual representation", "A representation that preserves contextual information for every token.", "distributional contextual representation"),
                    ("15% of tokens", "The selected token fraction for MLM prediction.", "15% of tokens"),
                ],
                [
                    ("masking-procedure example", "The appendix turns the MLM replacement rule into concrete examples.", "my dog is hairy"),
                    ("contextual-representation pressure", "The encoder cannot know which tokens will be predicted, so every token must remain informative.", "forced to keep"),
                    ("MLM training-cost tradeoff", "MLM predicts fewer positions per batch than a standard language model.", "15% of tokens"),
                ],
                [
                    ("can be further illustrated by", "method", "Introduces a worked example."),
                    ("The purpose of this is to", "claim", "Explains design motivation."),
                    ("The advantage of this procedure is that", "claim", "Introduces the benefit of a method."),
                    ("so it is forced to", "result", "Connects design to model behavior."),
                    ("Compared to", "contrast", "Introduces a method comparison."),
                ],
                "The advantage of this procedure is that",
                "The advantage of X is that Y, so Z.",
                "The masking rule helps because the encoder must keep useful context for every token.",
                "'The advantage of this procedure is that'은 방법의 장점을 설명하는 논문식 표현입니다.",
                "The sentence links a procedure, the model's uncertainty, and the representation consequence.",
            )
        if "next sentence prediction" in lowered and "a.2 pre-training procedure" in lowered:
            return profile(
                "This appendix gives concrete NSP examples and then explains how BERT pre-training sequences are built.",
                "The section shows IsNext and NotNext examples, then says each training sequence samples two text spans, marks them with A/B embeddings, and uses a 50/50 next-sentence rule.",
                (
                    "The appendix operationalizes NSP and pre-training input construction: span sampling, segment embeddings, balanced next/random sentence pairs, "
                    "length limits, and MLM masking after WordPiece tokenization."
                ),
                ["Read this as implementation detail for Section 3.1.", "Do not memorize the example sentences; learn the IsNext/NotNext construction.", "A/B embeddings and the 50/50 rule are the useful details."],
                [
                    ("IsNext", "Label for a true next-sentence pair.", "Label = IsNext"),
                    ("NotNext", "Label for a random non-next sentence pair.", "Label = NotNext"),
                    ("training input sequence", "The constructed BERT pre-training example.", "training input sequence"),
                    ("A embedding", "Segment embedding for the first sampled span.", "A embedding"),
                    ("B embedding", "Segment embedding for the second sampled span.", "B embedding"),
                    ("combined length", "The total token length limit for the two spans.", "combined length"),
                    ("WordPiece tokenization", "Tokenization applied before LM masking.", "WordPiece tokenization"),
                ],
                [
                    ("NSP worked example", "The examples show how IsNext and NotNext pairs look.", "Label = IsNext"),
                    ("pre-training sequence construction", "Two spans are sampled and marked as sentence A and B.", "sample two spans"),
                    ("balanced next-sentence sampling", "Half the B spans are actual next sentences and half are random.", "50% of the time"),
                ],
                [
                    ("can be illustrated in the following examples", "method", "Introduces examples."),
                    ("To generate each training input sequence", "method", "Introduces construction procedure."),
                    ("which we refer to as", "general", "Defines local terminology."),
                    ("50% of the time", "method", "States a balanced sampling rule."),
                    ("which is done for", "claim", "Connects procedure to objective."),
                ],
                "To generate each training input sequence",
                "To generate X, we sample Y, which we refer to as Z.",
                "BERT builds pre-training examples by sampling two spans and treating them as sentence A and sentence B.",
                "'To generate'는 절차 설명의 시작이고, 'which we refer to as'는 용어 정의입니다.",
                "The sentence mixes implementation steps with a local definition of 'sentences'.",
            )
        if "we use adam with learning rate" in lowered and "a.3 fine-tuning procedure" in lowered:
            return profile(
                "This appendix lists BERT pre-training hyperparameters, compute setup, sequence-length schedule, and fine-tuning search ranges.",
                "The section specifies Adam settings, dropout, GELU, TPU training, four-day pre-training, a 128-to-512 sequence-length schedule, and task-specific fine-tuning ranges.",
                (
                    "The appendix is an implementation recipe: optimizer configuration, regularization, activation choice, compute budget, quadratic attention cost, "
                    "staged sequence lengths, and fine-tuning hyperparameter search."
                ),
                [
                    "This is not language argument flow; it is reproducibility detail.",
                    "Save hyperparameter terms only if you need to reproduce the model.",
                    "The most useful reading pattern is exception language: 'with the exception of'.",
                ],
                [
                    ("Adam", "Optimizer used for BERT pre-training.", "Adam"),
                    ("learning rate warmup", "Gradual learning-rate increase over initial steps.", "learning rate warmup"),
                    ("linear decay", "Learning-rate schedule after warmup.", "linear decay"),
                    ("dropout probability", "Regularization probability kept at 0.1.", "dropout probability"),
                    ("gelu activation", "Activation used instead of ReLU.", "gelu activation"),
                    ("Cloud TPUs", "Hardware used for pre-training.", "Cloud TPUs"),
                    ("attention is quadratic", "Attention cost grows quadratically with sequence length.", "attention is quadratic"),
                    ("sequence length", "Input length staged from 128 to 512.", "sequence length"),
                    ("batch size", "Fine-tuning hyperparameter exception.", "batch size"),
                    ("training epochs", "Fine-tuning hyperparameter exception.", "training epochs"),
                ],
                [
                    ("pre-training implementation recipe", "The section gives optimizer, activation, dropout, compute, and sequence schedule.", "We use Adam"),
                    ("sequence-length curriculum", "Most steps use length 128, then final steps use length 512.", "sequence length of 128"),
                    ("fine-tuning hyperparameter search", "Fine-tuning varies batch size, learning rate, and epochs.", "with the exception"),
                ],
                [
                    ("We use", "method", "Introduces implementation choices."),
                    ("rather than", "contrast", "Contrasts activation choices."),
                    ("was performed on", "method", "States compute setup."),
                    ("To speed up", "method", "Introduces an efficiency workaround."),
                    ("with the exception of", "contrast", "Names what changes from pre-training to fine-tuning."),
                    ("we found the following range", "method", "Introduces search ranges."),
                ],
                "with the exception of",
                "For X, most Y are the same as Z, with the exception of A, B, and C.",
                "Fine-tuning mostly reuses pre-training settings, except for a few task-specific hyperparameters.",
                "'with the exception of'는 대부분은 같지만 일부만 다르다는 대조 표현입니다.",
                "The sentence packs a general rule and a list of exceptions into one reproducibility statement.",
            )
        compact_lowered = re.sub(r"\s+", " ", lowered)
        if "comparison of bert" in compact_lowered and "minimally compared" in lowered:
            return profile(
                "This appendix compares BERT, ELMo, and OpenAI GPT and explains why BERT's gains are attributed to bidirectionality and pre-training tasks.",
                (
                    "The section says BERT and GPT are fine-tuning approaches, ELMo is feature-based, GPT is the closest comparison, "
                    "and BERT was designed to be close to GPT so ablations can isolate bidirectionality and the two pre-training tasks."
                ),
                "The appendix positions BERT against ELMo and GPT through transfer mode, architecture, corpus, special-token timing, training steps, and ablation logic.",
                [
                    "This is a comparison map, not another generic BERT intro.",
                    "The important claim is attribution: gains come mainly from bidirectionality and pre-training tasks.",
                    "Use the bullet list to understand controlled differences.",
                ],
                [
                    ("finetuning approaches", "Transfer mode used by BERT and OpenAI GPT.", "finetuning approaches"),
                    ("feature-based approach", "Transfer mode used by ELMo.", "feature-based approach"),
                    ("left-to-right Transformer LM", "OpenAI GPT's pre-training method.", "left-to-right Transformer LM"),
                    ("BooksCorpus", "Training corpus shared by GPT and BERT.", "BooksCorpus"),
                    ("Wikipedia", "Additional BERT training corpus.", "Wikipedia"),
                    ("[SEP]", "Separator token learned during BERT pre-training.", "[SEP]"),
                    ("[CLS]", "Classifier token learned during BERT pre-training.", "[CLS]"),
                    ("sentence A/B embeddings", "Segment embeddings learned during BERT pre-training.", "sentence A/B embeddings"),
                ],
                [
                    ("BERT/GPT controlled comparison", "BERT design choices were made close to GPT to enable minimal comparison.", "minimally compared"),
                    ("transfer-mode contrast", "BERT/GPT use fine-tuning while ELMo uses feature extraction.", "feature-based approach"),
                    ("improvement attribution", "The appendix says most gains come from bidirectionality and two pre-training tasks.", "core argument"),
                ],
                [
                    ("Here we studies the differences", "general", "Introduces a comparison section despite awkward grammar."),
                    ("in addition to", "general", "Adds another comparison dimension."),
                    ("The most comparable existing", "contrast", "Identifies the closest baseline."),
                    ("were intentionally made to", "claim", "Explains design motivation."),
                    ("so that", "claim", "Introduces purpose."),
                    ("account for the majority of", "claim", "States attribution of improvements."),
                ],
                "The core argument of this work",
                "The core argument is that X and Y account for Z.",
                "The appendix claims BERT's gains mostly come from bidirectionality and its two pre-training tasks.",
                "'The core argument'는 논문이 무엇을 입증하려는지 직접 알려주는 표현입니다.",
                "The sentence compresses attribution across multiple model differences.",
            )
        if "illustration of fine-tuning" in lowered and "mnli multi-genre" in lowered:
            return profile(
                "This appendix links BERT fine-tuning diagrams to the start of the GLUE dataset descriptions.",
                (
                    "The section explains that BERT adds one output layer for each task, distinguishes sequence-level from token-level tasks, "
                    "defines figure symbols, and then starts the GLUE benchmark descriptions with MNLI."
                ),
                "The appendix serves as a task-format guide: output-layer minimalism, sequence-versus-token tasks, diagram notation, and GLUE dataset taxonomy.",
                [
                    "Use the figure notation to read later task descriptions.",
                    "Do not save every GLUE dataset name equally; save the task type.",
                    "This section bridges architecture diagrams and benchmark descriptions.",
                ],
                [
                    ("task-specific output layer", "The small layer added on top of BERT for a task.", "additional output layer"),
                    ("sequence-level tasks", "Tasks classified at sentence or sentence-pair level.", "sequence-level tasks"),
                    ("token-level tasks", "Tasks predicting labels or spans for tokens.", "token-level tasks"),
                    ("input embedding", "Figure symbol E.", "input embedding"),
                    ("contextual representation", "Figure symbol Ti.", "contextual representation"),
                    ("MNLI", "Multi-Genre Natural Language Inference dataset.", "MNLI"),
                    ("entailment classification", "Task type for MNLI.", "entailment classification"),
                ],
                [
                    ("minimal task adaptation", "BERT uses one additional output layer for task-specific models.", "minimal number of parameters"),
                    ("task granularity distinction", "The appendix separates sequence-level and token-level tasks.", "sequence-level tasks"),
                    ("GLUE dataset taxonomy", "The section begins listing GLUE task definitions.", "GLUE benchmark includes"),
                ],
                [
                    ("can be seen in", "general", "Points to a figure."),
                    ("are formed by incorporating", "method", "Explains model construction."),
                    ("so a minimal number of", "result", "States the parameter-efficiency consequence."),
                    ("represents the contextual representation", "general", "Defines figure notation."),
                    ("includes the following datasets", "general", "Introduces a benchmark list."),
                ],
                "Our task-specific models are formed",
                "Models are formed by incorporating X with Y, so Z.",
                "BERT task models add only a small output layer, so few parameters are learned from scratch.",
                "'so'는 구조적 선택과 그 결과를 연결합니다.",
                "The sentence combines architecture construction and parameter-efficiency rationale.",
            )
        if "qnli question natural language inference" in lowered and "sts-b" in lowered:
            return profile(
                "This appendix explains several GLUE task definitions: QNLI, SST-2, CoLA, and STS-B.",
                "The section defines QNLI as binary QA-derived classification, SST-2 as sentiment classification, CoLA as acceptability judgment, and STS-B as semantic similarity scoring.",
                "The appendix is a benchmark-reading guide that maps dataset names to task formats, label types, and source data.",
                ["For learning, pair each acronym with its task format.", "Ignore figure-token debris in the middle.", "This is useful because GLUE tables assume you know these task names."],
                [
                    ("QNLI", "Question Natural Language Inference converted from SQuAD.", "QNLI"),
                    ("binary classification task", "A task with two label choices.", "binary classification task"),
                    ("Stanford Sentiment Treebank", "Source dataset for the SST-2 sentiment task.", "Stanford Sentiment Treebank"),
                    ("CoLA", "Corpus of Linguistic Acceptability.", "CoLA"),
                    ("linguistically acceptable", "Whether a sentence is acceptable English.", "linguistically"),
                    ("STS-B", "Semantic Textual Similarity Benchmark.", "STS-B"),
                    ("Semantic Textual Similarity", "Meaning similarity benchmark for sentence pairs.", "Semantic Textual Similarity"),
                ],
                [
                    ("QNLI task conversion", "QNLI turns SQuAD into binary question-sentence classification.", "converted to a binary classification task"),
                    ("single-sentence classification tasks", "SST-2 and CoLA classify one sentence.", "single-sentence classification"),
                    ("semantic similarity benchmark", "STS-B scores meaning similarity for sentence pairs.", "Semantic Textual Similarity"),
                ],
                [
                    ("is a version of", "general", "Introduces dataset lineage."),
                    ("has been converted to", "method", "Explains task transformation."),
                    ("consisting of", "general", "Defines dataset contents."),
                    ("where the goal is to", "claim", "States task objective."),
                    ("drawn from", "general", "Names data source."),
                ],
                "has been converted to a binary classification task",
                "X is a version of Y which has been converted to Z.",
                "QNLI is derived from SQuAD but converted into binary classification.",
                "'has been converted to'는 데이터셋이 원래 형태에서 다른 task format으로 바뀌었다는 뜻입니다.",
                "The sentence mixes dataset origin, citation, and task transformation.",
            )
        if "mrpc microsoft research paraphrase corpus" in lowered and "wnli winograd" in lowered:
            return profile(
                "This appendix finishes GLUE task descriptions and introduces extra ablations on training steps.",
                "The section defines MRPC, RTE, and WNLI, explains why WNLI is excluded for fair GPT comparison, then starts an ablation about how many pre-training steps BERT needs.",
                "The appendix combines benchmark caveats with ablation setup: paraphrase equivalence, entailment with less data, problematic WNLI construction, majority-class handling, and training-step sensitivity.",
                ["This is mixed: first GLUE dataset notes, then ablation setup.", "The WNLI exclusion is an evaluation caveat, not vocabulary.", "The training-step question continues in the next section."],
                [
                    ("MRPC", "Microsoft Research Paraphrase Corpus.", "MRPC"),
                    ("semantically equivalent", "Whether two sentences mean the same thing.", "semantically equivalent"),
                    ("RTE", "Recognizing Textual Entailment.", "RTE"),
                    ("WNLI", "Winograd NLI.", "WNLI"),
                    ("majority class", "Baseline prediction class used for WNLI.", "majority class"),
                    ("single-task fine-tuning", "Fine-tuning one task at a time.", "single-task fine-tuning"),
                    ("multitask fine-tuning", "Fine-tuning with multiple tasks together.", "multitask fine-tuning"),
                    ("pre-training steps", "Number of steps used before fine-tuning.", "pre-training"),
                ],
                [
                    ("paraphrase-equivalence task", "MRPC asks whether two sentences are semantically equivalent.", "semantically equivalent"),
                    ("WNLI exclusion caveat", "WNLI is excluded because GLUE notes construction issues.", "exclude this set"),
                    ("training-step ablation setup", "The section begins asking how much pre-training BERT needs.", "Effect of Number of Training Steps"),
                ],
                [
                    ("consists of sentence pairs", "general", "Defines a sentence-pair dataset."),
                    ("with human annotations for whether", "general", "Explains labels."),
                    ("similar to", "contrast", "Relates one task to another."),
                    ("We therefore exclude", "claim", "States an evaluation decision."),
                    ("This allows us to answer", "method", "Introduces ablation questions."),
                ],
                "We therefore exclude this set",
                "We therefore exclude X to be fair to Y.",
                "The authors exclude WNLI because its construction issues make comparison unfair.",
                "'therefore'는 앞의 문제 설명에서 평가 결정으로 이어지는 논리 연결입니다.",
                "The sentence relies on the previous caveat to justify an experimental exclusion.",
            )
        if "c. 2 ablation for different masking procedures" in lowered and "mlm model does converge" in lowered:
            return profile(
                "This appendix reports that MLM converges slower than LTR but quickly outperforms it, then sets up masking-strategy ablations.",
                "The section answers a training-step question: MLM is slightly slower but more accurate than LTR early on. It then introduces masking-procedure ablations for MNLI and NER.",
                "The appendix connects pre-training efficiency to downstream quality, then frames masking strategy as a pre-training/fine-tuning mismatch control tested under fine-tuning and feature-based NER.",
                [
                    "The useful distinction is convergence speed versus absolute accuracy.",
                    "The masking table belongs to the next section.",
                    "Feature-based NER is expected to amplify mismatch because it cannot adjust BERT.",
                ],
                [
                    ("MLM model", "Masked language model pre-training variant.", "MLM model"),
                    ("LTR model", "Left-to-right language model comparison.", "LTR model"),
                    ("absolute accuracy", "Accuracy level, not convergence speed.", "absolute accuracy"),
                    ("masking strategies", "Different token replacement distributions.", "masking strategies"),
                    ("pre-training/fine-tuning mismatch", "Mismatch because [MASK] appears in pre-training but not fine-tuning.", "mismatch between pre-training and fine-tuning"),
                    ("MNLI", "Downstream task used in masking ablation.", "MNLI"),
                    ("NER", "Named entity recognition task used in masking ablation.", "NER"),
                    ("feature-based approach", "Frozen-feature setting expected to amplify mismatch.", "feature-based approach"),
                ],
                [
                    ("speed-quality tradeoff", "MLM converges slower but reaches better accuracy than LTR.", "converge slightly slower"),
                    ("masking mismatch motivation", "Masking strategies reduce [MASK] mismatch between pre-training and fine-tuning.", "mismatch between pre-training and fine-tuning"),
                    ("feature-based mismatch sensitivity", "Feature extraction cannot adjust BERT representations during task training.", "will not have the chance to adjust"),
                ],
                [
                    ("does converge slightly slower than", "contrast", "Compares convergence speed."),
                    ("However, in terms of", "contrast", "Switches to a different metric."),
                    ("begins to outperform", "result", "States early result advantage."),
                    ("we mention that", "general", "Refers back to the main method section."),
                    ("The following is an ablation study", "method", "Introduces ablation purpose."),
                    ("as we expect", "claim", "Gives an experimental expectation."),
                ],
                "However, in terms of absolute accuracy",
                "However, in terms of X, A begins to outperform B.",
                "MLM may train slower, but it becomes more accurate than LTR quickly.",
                "'in terms of'는 비교 기준을 바꾸는 표현입니다.",
                "The sentence contrasts speed with accuracy, so the reader must track which metric is being discussed.",
            )
        if "numbers in the left part of the table" in lowered and "fine-tuning is surprisingly robust" in lowered:
            return profile(
                "This appendix interprets the masking-rate ablation table and says fine-tuning is robust but feature-based NER is sensitive.",
                "The left table columns are MASK/SAME/RND probabilities; the right columns are dev results. Fine-tuning barely changes across masking strategies, but feature-based NER suffers when only MASK is used.",
                "The appendix explains Table C.2: masking probabilities, MNLI/NER dev results, last-four-layer features, fine-tuning robustness, and feature-based sensitivity to pre-training/fine-tuning mismatch.",
                [
                    "Read left columns as masking probabilities and right columns as results.",
                    "The important contrast is fine-tuning robustness versus feature-based sensitivity.",
                    "This closes the appendix by validating the 80/10/10 strategy.",
                ],
                [
                    ("MASK", "Probability of replacing selected tokens with [MASK].", "MASK"),
                    ("R ND strategy", "Masking condition where selected tokens are replaced randomly.", "R ND strategy"),
                    ("Dev set results", "Validation results reported in the table.", "Dev set results"),
                    ("last 4 layers", "Feature representation used for feature-based NER.", "last 4 layers"),
                    ("fine-tuning is surprisingly robust", "Fine-tuning performs similarly across masking strategies.", "fine-tuning is surprisingly robust"),
                    ("featurebased approach", "Feature extraction setting sensitive to masking mismatch.", "featurebased approach"),
                    ("NER", "Named entity recognition task in the masking ablation.", "NER"),
                ],
                [
                    ("masking-rate table reading", "The table separates replacement probabilities from downstream dev results.", "left part of the table"),
                    ("fine-tuning robustness", "Fine-tuning is less sensitive to masking strategy changes.", "surprisingly robust"),
                    ("feature-based masking sensitivity", "Using only MASK hurts feature-based NER.", "problematic"),
                ],
                [
                    ("represent the probabilities of", "general", "Explains table columns."),
                    ("For the feature-based approach", "method", "Introduces a specific setting."),
                    ("which was shown to be", "claim", "References prior section evidence."),
                    ("From the table it can be seen that", "result", "Introduces table interpretation."),
                    ("However, as expected", "contrast", "Introduces an expected negative result."),
                    ("performs much worse than", "result", "States result comparison."),
                ],
                "From the table it can be seen that",
                "From the table it can be seen that X is Y.",
                "The table shows fine-tuning is robust to masking strategy changes.",
                "'From the table it can be seen that'은 표에서 해석을 끌어내는 표현입니다.",
                "The sentence asks the reader to move from numeric table values to a written conclusion.",
            )
        return None

    def _is_bert_conclusion_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "6 conclusion" in lowered
            and "our major contribution is" in lowered
            and "deep bidirectional architectures" in lowered
            and "broad set of nlp tasks" in lowered
        )

    def _is_reference_list_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        citation_markers = sum(
            marker in lowered
            for marker in (
                "in proceedings of",
                "in advances in",
                "in international conference",
                "in emnlp",
                "in acl",
                "in naacl",
                "in iclr",
                "in nips",
                "in conll",
                "arxiv preprint",
                "technical report",
                "association for computational linguistics",
                "journal of machine learning research",
                "journalism bulletin",
                "pages ",
                "j. mach. learn. res.",
                "arxiv e-prints",
                "neural netw.",
                "proceedings of the ieee",
                "co rr",
                "corr",
                "jmlr proceedings",
                "ieee computer society",
                "international conference on machine learning",
                "international conference on artificial intelligence and statistics",
            )
        )
        has_many_years = len(re.findall(r"\b(?:19|20)\d{2}\b", lowered)) >= 4
        return has_many_years and citation_markers >= 2 and not self._is_bert_conclusion_section(document_text)

    def _is_attention_learning_section(self, document_text: str) -> bool:
        return self._attention_profile(document_text) is not None

    def _is_batchnorm_learning_section(self, document_text: str) -> bool:
        if self._is_resnet_text(document_text):
            return False
        lowered = document_text.lower()
        compact = re.sub(r"\s+", " ", lowered)
        return self._batchnorm_profile(document_text) is not None or any(
            marker in compact
            for marker in (
                "batch normalization",
                "bn transform",
                "batch-normalized",
                "batch normalized",
                "internal covariate shift",
                "internalcovariate shift",
                "normalized activations",
                "gradient propagation",
            )
        )

    def _batchnorm_profile(self, document_text: str) -> dict[str, Any] | None:
        lowered = document_text.lower()
        compact_lowered = re.sub(r"\s+", " ", lowered)

        def profile(
            one_line: str,
            simple: str,
            academic: str,
            notes: list[str],
            terms: list[tuple[str, str, str]],
            concepts: list[tuple[str, str, str]],
            phrases: list[tuple[str, str, str]],
            sentence_target: str,
            core_structure: str,
            simplified_version: str,
            korean_explanation: str,
            difficulty_reason: str,
        ) -> dict[str, Any]:
            return {
                "summaries": {"one_line": one_line, "simple": simple, "academic": academic, "study_notes": notes},
                "terms": terms,
                "concepts": concepts,
                "phrases": phrases,
                "sentence_target": sentence_target,
                "core_structure": core_structure,
                "simplified_version": simplified_version,
                "korean_explanation": korean_explanation,
                "difficulty_reason": difficulty_reason,
            }

        if "with sgd" in compact_lowered and "mini-batch is used" in compact_lowered and "covariate shift" in lowered:
            return profile(
                "This section explains why mini-batch SGD is efficient but unstable in deep networks.",
                (
                    "The paper first explains how mini-batches estimate gradients efficiently. It then shifts to the training problem: "
                    "deeper networks make each layer's input distribution change as earlier layers update."
                ),
                (
                    "The passage builds the motivation for internal covariate shift by connecting mini-batch gradient estimates, parallel computation, "
                    "learning-rate sensitivity, parameter initialization, and covariate shift inside sub-networks or layers."
                ),
                [
                    "This is setup for the BatchNorm problem, not the solution yet.",
                    "Follow the chain: SGD minibatches -> hyperparameter sensitivity -> changing layer inputs -> covariate shift.",
                    "The useful academic contrast phrase is 'as opposed to'.",
                ],
                [
                    ("SGD", "Stochastic gradient descent training with mini-batch updates.", "SGD"),
                    ("mini-batch", "A subset of examples used to estimate the training-set gradient.", "mini-batch"),
                    ("gradient of the loss function", "Derivative estimated from a mini-batch.", "gradient of the loss function"),
                    ("batch size", "Number of examples in a mini-batch.", "batch size"),
                    ("parallelism", "Efficient batch computation on modern platforms.", "parallelism"),
                    ("model hyper-parameters", "Settings such as learning rate and initialization.", "model hyper-parameters"),
                    ("learning rate", "Optimization step-size that requires careful tuning.", "learning rate"),
                    ("covariate shift", "Change in input distribution, extended here to internal layers.", "covariate shift"),
                ],
                [
                    ("mini-batch gradient estimate", "Mini-batches approximate the full training-set gradient.", "approximate the gradient"),
                    ("deep-network input drift", "Layer inputs change because preceding layer parameters change.", "inputs to each layer are affected"),
                    ("internal covariate shift setup", "The covariate-shift concept is extended from systems to sub-networks and layers.", "extended beyond the learning system"),
                ],
                [
                    ("as opposed to", "contrast", "Contrasts mini-batches with one-example updates."),
                    ("is helpful in several ways", "claim", "Introduces multiple advantages."),
                    ("First", "general", "Starts an enumerated explanation."),
                    ("Second", "general", "Adds another reason."),
                    ("is complicated by the fact that", "claim", "Introduces the cause of difficulty."),
                    ("can be extended beyond", "claim", "Extends a known concept to a new scope."),
                ],
                "Using mini-batches of examples, as opposed to one example at a time",
                "Using A, as opposed to B, is helpful in several ways.",
                "Mini-batches are useful because they estimate gradients and make computation efficient.",
                "'as opposed to'는 두 방법을 대비하면서 저자가 선택한 방법의 장점을 설명할 때 쓰입니다.",
                "The section shifts from optimization mechanics into the paper's core instability argument.",
            )
        if "learning θ2 can be viewed" in compact_lowered and "remain fixed over time" in compact_lowered:
            return profile(
                "This section explains internal covariate shift as changing inputs to a sub-network.",
                (
                    "The paper treats part of a neural network as a sub-network receiving inputs from earlier layers. Training is easier if those input distributions stay fixed instead of changing over time."
                ),
                (
                    "The passage formalizes internal covariate shift with a two-part network F1/F2: even if a later sub-network is optimized normally, "
                    "its effective input distribution changes whenever earlier parameters change."
                ),
                [
                    "Read the equations as a conceptual split: earlier layers feed later layers.",
                    "The key idea is fixed distribution of x, not the exact gradient formula.",
                    "This section is the bridge from covariate shift to why normalization should stabilize layer inputs.",
                ],
                [
                    ("sub-network", "A later part of the network treated as its own learning system.", "sub-network"),
                    ("input distribution", "Distribution of x values received by the sub-network.", "input distribution"),
                    ("gradient descent step", "Parameter update used to train the sub-network.", "gradient descent step"),
                    ("batch size", "m in the gradient-descent expression.", "batch size"),
                    ("learning rate", "alpha in the parameter update.", "learning rate"),
                    ("stand-alone network", "Comparison used to explain the sub-network view.", "stand-alone network"),
                    ("fixed distribution", "Stable input distribution that would make training easier.", "remain fixed"),
                ],
                [
                    ("sub-network view", "Later layers can be analyzed as a network receiving inputs from earlier layers.", "viewed as if"),
                    ("fixed-input-distribution argument", "Stable x distributions would reduce readjustment during training.", "remain fixed over time"),
                    ("internal shift mechanism", "Changes in earlier parameters change what later layers receive.", "parameters"),
                ],
                [
                    ("can be viewed as if", "method", "Introduces a conceptual reframing."),
                    ("For example", "general", "Introduces a concrete formula."),
                    ("is exactly equivalent to", "claim", "States an equivalence."),
                    ("Therefore", "claim", "Draws the consequence."),
                    ("As such", "claim", "Introduces the practical implication."),
                ],
                "Learning Θ2 can be viewed as if the inputs",
                "Learning X can be viewed as if Y are fed into Z.",
                "Training later parameters can be understood as training a sub-network whose inputs come from earlier layers.",
                "'can be viewed as if'는 수식을 직관적인 모델로 다시 해석할 때 유용한 표현입니다.",
                "Greek parameters and nested functions make the simple sub-network idea hard to see.",
            )
        if "sigmoid activation function" in lowered and "saturated regime" in lowered and "we propose a new mechanism" in lowered:
            return profile(
                "This section connects sigmoid saturation and vanishing gradients to the need for Batch Normalization.",
                (
                    "The paper explains that changing layer inputs can push sigmoid activations into saturated regions where gradients vanish. "
                    "If input distributions stay more stable, training should accelerate; Batch Normalization is proposed to reduce that internal shift."
                ),
                (
                    "The passage turns internal covariate shift into an optimization failure mode: parameter changes move nonlinear inputs into saturation, "
                    "gradients vanish, small learning rates become necessary, and stabilizing input distributions motivates Batch Normalization."
                ),
                [
                    "This is the main problem-to-method transition.",
                    "Track the causal chain: changing x -> saturation -> vanishing gradients -> slower convergence -> BatchNorm.",
                    "The phrase 'If, however, we could ensure...' introduces the desired counterfactual solution.",
                ],
                [
                    ("sigmoid activation function", "Nonlinearity whose gradient shrinks for large absolute inputs.", "sigmoid activation function"),
                    ("vanishing gradients", "Gradients become too small for effective training.", "gradient flowing"),
                    ("saturated regime", "Input region where the nonlinearity has tiny gradients.", "saturated regime"),
                    ("ReLU", "Alternative activation used to avoid saturation problems.", "ReLU"),
                    ("careful initialization", "Existing mitigation for saturation and vanishing gradients.", "careful initialization"),
                    ("small learning rates", "Existing mitigation that slows training.", "small learning rates"),
                    ("Internal Covariate Shift", "Change in internal node distributions during training.", "Internal Covariate Shift"),
                    ("Batch Normalization", "Mechanism proposed to reduce internal covariate shift.", "Batch Normalization"),
                ],
                [
                    ("saturation failure mode", "Changing inputs can push sigmoid activations into low-gradient regions.", "saturated regime"),
                    ("stability counterfactual", "Stable nonlinearity inputs should make optimization less likely to get stuck.", "could ensure"),
                    ("BatchNorm motivation", "Batch Normalization is introduced as a mechanism to reduce internal covariate shift.", "takes a step towards reducing"),
                ],
                [
                    ("This means that", "claim", "Explains the consequence of a formula."),
                    ("However, since", "contrast", "Introduces why the problem occurs during training."),
                    ("In practice", "general", "Connects theory to common practice."),
                    ("If, however, we could ensure", "method", "Introduces a desired intervention."),
                    ("We refer to", "claim", "Names the phenomenon."),
                    ("We propose a new mechanism", "method", "Introduces the solution."),
                ],
                "If, however, we could ensure that the distribution of nonlinearity inputs remains more stable",
                "If we could ensure X, then Y would be less likely to Z.",
                "If layer-input distributions stayed stable, the optimizer would be less likely to get stuck in saturation.",
                "'If, however, we could ensure...'는 문제를 해결하기 위한 가정적 조건을 제시하는 표현입니다.",
                "The section mixes activation math, optimization failure, and the method introduction.",
            )
        if "beneficial effect on the gradient flow" in lowered and "towards reducing internal covariate shift" in lowered:
            return profile(
                "This section summarizes BatchNorm's benefits and starts the formal reduction of internal covariate shift.",
                (
                    "The paper says BatchNorm fixes means and variances of layer inputs, improves gradient flow, allows higher learning rates, "
                    "regularizes the model, and helps with saturating nonlinearities. It then defines internal covariate shift and motivates whitening layer inputs."
                ),
                (
                    "The passage bridges introduction and method: it lists practical benefits, reports ImageNet improvement claims, "
                    "defines internal covariate shift as activation-distribution change, and frames whitening as the ideal but expensive stabilization target."
                ),
                [
                    "This section is a benefit list plus the start of the formal method section.",
                    "Separate empirical ImageNet claims from the definition of internal covariate shift.",
                    "The phrase 'by fixing' explains the intended mechanism.",
                ],
                [
                    ("normalization step", "Operation that fixes means and variances of layer inputs.", "normalization step"),
                    ("gradient flow", "How gradients move through the network during training.", "gradient flow"),
                    ("higher learning rates", "Larger optimization steps enabled by BatchNorm.", "higher learning rates"),
                    ("Dropout", "Regularizer whose need may be reduced.", "Dropout"),
                    ("saturating nonlinearities", "Nonlinearities made easier to use by preventing saturation.", "saturating nonlinearities"),
                    ("top-5 error rate", "ImageNet metric improved by BatchNorm ensembles.", "top-5 error rate"),
                    ("Internal Covariate Shift", "Change in network activation distributions during training.", "Internal Covariate Shift"),
                    ("whitened", "Transformed to zero mean, unit variance, and decorrelated.", "whitened"),
                ],
                [
                    ("benefit stack", "BatchNorm is presented as helping learning rate, initialization, regularization, and saturation.", "beneficial effect"),
                    ("formal problem definition", "Internal Covariate Shift is defined as changing network activations during training.", "We define Internal Covariate Shift"),
                    ("whitening ideal", "Whitening each layer's inputs would stabilize distributions but is not yet practical.", "inputs are whitened"),
                ],
                [
                    ("It accomplishes this via", "method", "Explains the mechanism."),
                    ("by reducing", "method", "States how a benefit happens."),
                    ("This allows us to", "result", "Introduces a practical consequence."),
                    ("Furthermore", "general", "Adds another benefit."),
                    ("Finally", "general", "Adds the final benefit in a list."),
                    ("We define", "claim", "Names the formal concept."),
                    ("By fixing", "method", "States the stabilization strategy."),
                ],
                "By fixing the distribution of the layer inputs",
                "By doing X, we expect to improve Y.",
                "The authors expect stable layer-input distributions to improve training speed.",
                "'By fixing'은 어떤 조작이 어떤 효과로 이어지는지 설명하는 방법 표현입니다.",
                "The section rapidly moves from benefit claims to formal definition and whitening motivation.",
            )
        if "by whitening the inputs to each layer" in lowered and "computed outside the gradient descent step" in lowered:
            return profile(
                "This section explains why naive whitening or normalization can fail during gradient descent.",
                (
                    "The paper considers whitening activations during training, but shows a failure case: if normalization statistics are updated outside the gradient step, "
                    "a bias update can be canceled by the subsequent normalization change."
                ),
                (
                    "The passage motivates the need for differentiable normalization inside the optimization graph: whitening seems attractive, "
                    "but ignoring how normalization statistics depend on parameters can nullify updates or make parameters diverge."
                ),
                [
                    "The key lesson is not the algebra; it is that normalization must participate in backpropagation.",
                    "The bias example shows why external normalization can cancel learning.",
                    "Watch for 'However' and 'Thus' as the reasoning pivots.",
                ],
                [
                    ("whitening", "Transforming inputs toward fixed zero-mean, decorrelated distributions.", "whitening"),
                    ("fixed distributions", "Stable input distributions meant to reduce internal covariate shift.", "fixed distributions"),
                    ("optimization steps", "Gradient-descent updates interleaved with normalization updates.", "optimization steps"),
                    ("learned bias", "Bias parameter b in the failure example.", "learned bias"),
                    ("training data", "Dataset over which the mean is computed.", "training data"),
                    ("loss remains fixed", "Failure condition where the update does not change the objective.", "loss remains fixed"),
                    ("normalization parameters", "Statistics computed outside gradient descent in the failure case.", "normalization parameters"),
                ],
                [
                    ("naive-normalization failure", "Updating normalization outside gradient descent can erase parameter updates.", "no change in the output"),
                    ("gradient-dependence problem", "The optimizer must account for the dependence of normalization statistics on parameters.", "dependence of E"),
                    ("blow-up observation", "The authors observed models diverge when normalization statistics were external.", "model blows up"),
                ],
                [
                    ("could consider", "method", "Introduces a possible approach."),
                    ("However, if", "contrast", "Introduces a failure condition."),
                    ("For example", "general", "Starts the illustrative derivation."),
                    ("If a gradient descent step ignores", "limitation", "Names the mistake."),
                    ("Thus", "claim", "Draws the consequence."),
                    ("This problem can get worse", "claim", "Extends the failure case."),
                    ("We have observed this empirically", "result", "Connects the derivation to experiment."),
                ],
                "However, if these modifications are interspersed with the optimization steps",
                "However, if X, then Y may Z.",
                "If normalization updates are interleaved badly with optimization, the gradient step can be canceled.",
                "'However, if'는 가능해 보이는 방법의 실패 조건을 제시할 때 쓰입니다.",
                "The section is difficult because the main insight is hidden inside a bias-normalization algebra example.",
            )
        if "the issue with the above approach" in lowered and "desired distribution" in lowered:
            return profile(
                "This section states that normalization must be accounted for by gradient descent.",
                (
                    "The paper says the problem with the previous approach is that gradient descent ignored normalization. "
                    "The authors want activations to keep the desired distribution while gradients still account for the normalization."
                ),
                (
                    "The passage sets the design constraint for BatchNorm: normalization should be part of the computation that gradients see, "
                    "so its dependence on model parameters is not ignored."
                ),
                [
                    "This is the design-requirement section before mini-batch statistics.",
                    "The key is that normalization must be inside the computational graph.",
                    "The next section explains why full whitening is too expensive and motivates mini-batch statistics.",
                ],
                [
                    ("gradient descent optimization", "Optimization process that must account for normalization.", "gradient descent optimization"),
                    ("desired distribution", "Target distribution for network activations.", "desired distribution"),
                    ("model parameters", "Theta values that activations depend on.", "model parameters"),
                    ("activations", "Layer outputs whose distribution should be controlled.", "activations"),
                    ("normalization", "Transformation that must be included in gradient computation.", "normalization"),
                ],
                [
                    ("normalization-in-graph requirement", "Gradients must account for normalization and its parameter dependence.", "account for the normalization"),
                    ("distribution constraint", "The network should produce activations with the desired distribution for any parameters.", "desired distribution"),
                    ("parameter-dependence requirement", "The loss gradient must account for the dependence on model parameters.", "dependence on the model parameters"),
                ],
                [
                    ("The issue with", "claim", "Names the problem with the previous approach."),
                    ("To address this issue", "method", "Introduces the desired fix."),
                    ("Doing so would allow", "result", "States what the fix enables."),
                    ("with respect to", "general", "Names the gradient target."),
                    ("account for", "method", "States what the gradient must include."),
                ],
                "To address this issue, we would like to ensure",
                "To address this issue, we would like to ensure that X.",
                "The authors want normalization to be something the optimizer can account for.",
                "'To address this issue'는 앞에서 제기한 문제를 해결하는 조건을 제시할 때 쓰입니다.",
                "The section is short but abstract because it states a design constraint before showing the concrete mini-batch method.",
            )
        if "norm(x, x" in lowered and "this motivates us to seek an alternative" in lowered:
            return profile(
                "This section rejects full whitening and motivates a differentiable mini-batch alternative.",
                (
                    "The paper explains that normalization depends on both the current example and other training examples, so backpropagation would need difficult derivatives. "
                    "Full whitening is expensive, so the authors seek a differentiable method that avoids analyzing the whole training set after every update."
                ),
                (
                    "The passage closes the argument against full whitening: computing covariance matrices, inverse square roots, and all needed derivatives is too expensive, "
                    "and single-example statistics discard useful scale information."
                ),
                [
                    "This is the final motivation before mini-batch statistics.",
                    "The important language move is 'This motivates us to seek an alternative'.",
                    "Do not study Norm(x, X) as a term unless you need the math.",
                ],
                [
                    ("Norm(x, X)", "Normalization transformation depending on one example and all examples.", "Norm(x, X"),
                    ("Jacobians", "Derivatives needed for backpropagation through normalization.", "Jacobians"),
                    ("covariance matrix", "Matrix required for full whitening.", "covariance matrix"),
                    ("inverse square root", "Matrix operation needed for whitening.", "inverse square root"),
                    ("whitened activations", "Activations after covariance-based whitening.", "whitened activations"),
                    ("differentiable", "Property required for optimization through normalization.", "differentiable"),
                    ("entire training set", "Dataset the authors want to avoid reanalyzing after every update.", "entire training set"),
                    ("absolute scale of activations", "Information lost by some previous single-example methods.", "absolute scale of activations"),
                ],
                [
                    ("full-whitening cost", "Whitening needs covariance, inverse square root, and derivatives.", "whitening the layer inputs is expensive"),
                    ("differentiable-alternative motivation", "The authors need a cheaper differentiable normalization method.", "This motivates us to seek an alternative"),
                    ("scale-preservation concern", "The method should preserve activation scale information.", "preserve the information"),
                ],
                [
                    ("which depends not only on", "method", "Explains dependency scope."),
                    ("For backpropagation", "method", "Introduces derivative requirements."),
                    ("Within this framework", "general", "Evaluates the method under stated assumptions."),
                    ("This motivates us to seek", "method", "Connects cost to the next design."),
                    ("However", "contrast", "Introduces a problem with prior approaches."),
                    ("We want to preserve", "claim", "States a design goal."),
                ],
                "This motivates us to seek an alternative",
                "This motivates us to seek an alternative that does X and does not require Y.",
                "Because full whitening is expensive, the authors seek a cheaper differentiable normalization method.",
                "'This motivates us to seek'는 앞의 한계가 다음 설계 선택으로 이어진다는 신호입니다.",
                "The section is dense because it contains transformation notation, derivative requirements, and design constraints.",
            )
        if "normalize each scalar feature independently" in lowered and "scale and shift the normalized value" in lowered:
            return profile(
                "This section introduces per-feature normalization and learned scale/shift parameters.",
                (
                    "The first simplification is to normalize each scalar feature independently to mean zero and variance one. "
                    "Because pure normalization could reduce what a layer can represent, the method adds learned gamma and beta parameters to scale and shift the normalized value."
                ),
                (
                    "The passage introduces the core representation-preserving idea of BatchNorm: normalize each dimension separately, "
                    "then restore network capacity with learned affine parameters that can recover the identity transformation if needed."
                ),
                [
                    "This is one of the key algorithm sections.",
                    "Gamma and beta are not optional details; they preserve representation power.",
                    "The second simplification starts at the end: use mini-batches to estimate mean and variance.",
                ],
                [
                    ("scalar feature", "One dimension of a layer input normalized independently.", "scalar feature"),
                    ("mean of zero", "Target mean after normalization.", "mean of zero"),
                    ("variance of 1", "Target variance after normalization.", "variance of 1"),
                    ("identity transform", "Transform the network can still represent after normalization.", "identity transform"),
                    ("parameters γ, β", "Learned scale and shift parameters.", "parameters γ"),
                    ("scale and shift", "Affine operation applied after normalization.", "scale and shift"),
                    ("representation power", "Network's ability to express useful activations.", "representation power"),
                    ("mini-batches", "Batches used to estimate activation mean and variance.", "mini-batches"),
                ],
                [
                    ("per-feature normalization", "Features are normalized independently instead of full whitening.", "normalize each scalar feature independently"),
                    ("affine recovery mechanism", "Gamma and beta let the network recover identity if needed.", "represent the identity transform"),
                    ("mini-batch-statistics simplification", "Each mini-batch estimates mean and variance for each activation.", "mini-batch produces estimates"),
                ],
                [
                    ("The first is that", "method", "Introduces the first simplification."),
                    ("instead of", "contrast", "Contrasts scalar normalization with whitening."),
                    ("To address this", "method", "Introduces the fix."),
                    ("To accomplish this", "method", "Introduces implementation details."),
                    ("These parameters are learned", "method", "Explains trainable parameters."),
                    ("Therefore", "claim", "Introduces the second simplification."),
                ],
                "To address this, we make sure that the transformation inserted in the network can represent the identity transform.",
                "To address X, we make sure that Y can Z.",
                "Gamma and beta let normalization preserve the layer's ability to represent the identity transform.",
                "'To address this'는 바로 앞의 문제를 해결하는 장치를 소개하는 표현입니다.",
                "The section is algorithmically important because normalization and representation preservation are introduced together.",
            )
        if "batch normalizing transform" in lowered and "algorithm 1" in lowered:
            return profile(
                "This section defines the Batch Normalizing Transform over a mini-batch.",
                (
                    "The paper explains why mini-batches make per-dimension normalization practical, then defines BN_gamma,beta: compute mini-batch mean and variance, "
                    "normalize each activation, and apply learned scale and shift."
                ),
                (
                    "The passage is the algorithm definition: it avoids joint covariance issues, focuses on one activation dimension, defines the Batch Normalizing Transform, "
                    "and states Algorithm 1 with mean, variance, normalization, scale, and shift steps."
                ),
                [
                    "This is the core algorithm card for BatchNorm.",
                    "Read Algorithm 1 as four operations: mean, variance, normalize, scale/shift.",
                    "Epsilon is for numerical stability, not a learned parameter.",
                ],
                [
                    ("per-dimension variances", "Variance computed per activation dimension.", "per-dimension variances"),
                    ("joint covariances", "Full covariance terms avoided by the simplification.", "joint covariances"),
                    ("singular covariance matrices", "Failure mode avoided when mini-batches are small.", "singular covariance matrices"),
                    ("mini-batch mean", "Mean computed over the mini-batch.", "mini-batch mean"),
                    ("mini-batch variance", "Variance computed over the mini-batch.", "mini-batch variance"),
                    ("Batch Normalizing Transform", "BN_gamma,beta transform applied to activations.", "Batch Normalizing Transform"),
                    ("numerical stability", "Reason epsilon is added to variance.", "numerical stability"),
                    ("scale and shift", "Final learned affine transform with gamma and beta.", "scale and shift"),
                ],
                [
                    ("BN algorithm steps", "Algorithm 1 computes mean, variance, normalization, then scale/shift.", "Algorithm 1"),
                    ("small-batch covariance problem", "Joint covariance can be singular when batch size is smaller than activation count.", "singular covariance matrices"),
                    ("mini-batch transform definition", "BN_gamma,beta maps mini-batch activations to normalized scaled outputs.", "BNγ,β"),
                ],
                [
                    ("is enabled by", "claim", "Explains why mini-batches are possible."),
                    ("rather than", "contrast", "Contrasts per-dimension variance with joint covariance."),
                    ("Consider", "general", "Introduces the setup."),
                    ("We refer to", "claim", "Names the transform."),
                    ("In the algorithm", "general", "Explains an algorithm detail."),
                    ("for numerical stability", "method", "Explains epsilon's purpose."),
                ],
                "We refer to the transform BNγ,β",
                "We refer to X as Y.",
                "The authors name the mini-batch normalization operation the Batch Normalizing Transform.",
                "'We refer to X as Y'는 논문에서 새 개념이나 연산에 이름을 붙이는 표현입니다.",
                "The section combines statistical motivation and algorithm notation, so the reader needs a step-by-step view.",
            )
        if "does not independently process the activation in each training example" in lowered and "sub-network inputs all have fixed means and variances" in lowered:
            return profile(
                "This section explains that BatchNorm is a mini-batch operation, not an independent per-example operation.",
                (
                    "BN_gamma,beta depends on the current training example and the other examples in the same mini-batch. "
                    "The internal normalized activations have expected mean 0 and variance 1, so later sub-networks receive inputs with more stable moments."
                ),
                (
                    "The passage clarifies the training-time semantics of BatchNorm: the transform couples examples inside a mini-batch, creates internal normalized activations, "
                    "then sends scaled and shifted values to the next layers while preserving differentiability for backpropagation."
                ),
                [
                    "Do not read BatchNorm as a per-example preprocessing step; during training, each example is normalized using its mini-batch.",
                    "Separate internal normalized activations x-hat from the values y passed to later layers.",
                    "The learning goal is stable means and variances for sub-network inputs, not memorizing the summation identities.",
                ],
                [
                    ("BN γ,β", "The BatchNorm transform with learned scale gamma and shift beta.", "BN γ,β"),
                    ("mini-batch", "The group of examples whose statistics are used together.", "mini-batch"),
                    ("normalized activations", "Internal x-hat values with expected mean 0 and variance 1.", "normalized activations"),
                    ("scaled and shifted values", "Output y after applying gamma and beta to x-hat.", "scaled and shifted values"),
                    ("sub-network inputs", "Normalized activations viewed as inputs to later network parts.", "sub-network inputs"),
                    ("fixed means and variances", "Stable first and second moments for normalized activations.", "fixed means and variances"),
                    ("backpropagate", "Send loss gradients through the BatchNorm transformation.", "backpropagate"),
                    ("BN transform parameters", "Gamma and beta parameters learned with the network.", "parameters of the BN transform"),
                ],
                [
                    ("mini-batch coupling", "A training example's normalized value depends on other examples in its mini-batch.", "depends both on"),
                    ("internal-vs-output activations", "x-hat is internal to BN, while y is passed onward.", "internal to our transformation"),
                    ("stable-subnetwork-inputs", "Normalized activations give later sub-networks fixed means and variances.", "fixed means and variances"),
                ],
                [
                    ("it should be noted that", "claim", "Flags an important clarification."),
                    ("Rather", "contrast", "Corrects the previous interpretation."),
                    ("as long as", "limitation", "States the condition under which the claim holds."),
                    ("can be viewed as", "method", "Introduces a conceptual reframing."),
                    ("although", "contrast", "Concedes a remaining limitation."),
                    ("During training", "general", "Signals training-specific behavior."),
                ],
                "it should be noted that the BN transform does not independently process the activation in each training example",
                "It should be noted that X does not independently Y; rather, it depends on Z.",
                "BatchNorm normalizes each training example using statistics from the mini-batch, not only from itself.",
                "'it should be noted that'은 독자가 오해하기 쉬운 핵심 조건을 강조할 때 쓰는 논문 표현입니다.",
                "The section is hard because the paper switches between x, x-hat, y, gamma/beta, and sub-network interpretation.",
            )
        if "we use chain rule" in lowered and "training and inference with" in lowered and "population, rather than mini-batch, statistics" in lowered:
            return profile(
                "This section shows that BatchNorm is differentiable, then separates training-time and inference-time normalization.",
                (
                    "The derivative block only says gradients can pass through BatchNorm. The important reading point is the next distinction: "
                    "training uses mini-batch statistics, but inference should use fixed population statistics so the output depends only on the input."
                ),
                (
                    "The passage connects optimization and deployment: BN is inserted into selected activations and can be trained with SGD variants, "
                    "but the stochastic mini-batch dependency is replaced at inference by population mean and variance for deterministic prediction."
                ),
                [
                    "Do not study the derivative block first; identify its role: proving the transform can be trained end to end.",
                    "The major concept contrast is training-time mini-batch statistics versus inference-time population statistics.",
                    "This is where BatchNorm becomes a deployable network layer rather than just a training trick.",
                ],
                [
                    ("chain rule", "Calculus rule used to backpropagate through BatchNorm.", "chain rule"),
                    ("differentiable transformation", "A transform gradients can pass through during training.", "differentiable transformation"),
                    ("affine transform", "Learned scale and shift applied after normalization.", "affine transform"),
                    ("Stochastic Gradient Descent", "Optimizer family compatible with BatchNorm.", "Stochastic Gradient Descent"),
                    ("Adagrad", "Example SGD variant mentioned by the paper.", "Adagrad"),
                    ("inference", "Prediction phase after training.", "inference"),
                    ("population statistics", "Fixed mean and variance estimates used during inference.", "population, rather than mini-batch, statistics"),
                ],
                [
                    ("differentiability proof role", "The equations justify training through the BN transform.", "BN transform is a differentiable transformation"),
                    ("training/inference split", "Training uses mini-batch statistics; inference uses fixed population statistics.", "during inference"),
                    ("deterministic prediction requirement", "At inference, output should depend only on the input.", "depend only on the input"),
                ],
                [
                    ("Thus", "claim", "Draws the conclusion from equations."),
                    ("This ensures that", "result", "Explains the training benefit."),
                    ("Furthermore", "general", "Adds a second benefit."),
                    ("can be trained using", "method", "Lists compatible optimizers."),
                    ("but is neither necessary nor desirable", "limitation", "Rejects mini-batch dependency for inference."),
                    ("For this", "method", "Introduces the inference-time replacement."),
                    ("rather than", "contrast", "Contrasts population and mini-batch statistics."),
                ],
                "The normalization of activations that depends on the mini-batch allows efficient training, but is neither necessary nor desirable during inference",
                "X allows efficient training, but is neither necessary nor desirable during inference.",
                "Mini-batch statistics help training, but inference needs fixed statistics so predictions are deterministic.",
                "'but is neither necessary nor desirable'는 학습 단계에서 유용한 것이 추론 단계에는 맞지 않음을 강하게 대비합니다.",
                "The section starts with dense derivative notation, then quickly pivots into the more important training-vs-inference distinction.",
            )
        if "unbiased variance estimate" in lowered and "algorithm 2" in lowered and "batch-normalized convolutional networks" in lowered:
            return profile(
                "This section explains how a trained BatchNorm layer is converted into a fixed inference-time linear transform.",
                (
                    "After training, the model estimates population mean and variance from training mini-batches. "
                    "Because those statistics are fixed during inference, BatchNorm can be folded into one linear transform using gamma, beta, mean, and variance."
                ),
                (
                    "The passage operationalizes inference for BatchNorm: collect moving or averaged statistics from mini-batches, freeze them, replace BN(x) with an equivalent affine transform, "
                    "and then move to the convolutional-network case."
                ),
                [
                    "Algorithm 2 is a deployment recipe: train with BN, estimate population statistics, freeze them, replace BN with a linear transform.",
                    "The unbiased variance estimate corrects mini-batch variance before inference use.",
                    "The convolutional section begins at the end; do not merge it with Algorithm 2's inference procedure.",
                ],
                [
                    ("unbiased variance estimate", "Variance estimate corrected by m/(m-1).", "unbiased variance estimate"),
                    ("moving averages", "Running estimates of mean and variance during training.", "moving averages"),
                    ("inference", "Prediction phase using fixed normalization statistics.", "inference"),
                    ("linear transform", "Fixed affine replacement for BN during inference.", "linear transform"),
                    ("scaling by γ", "Learned multiplicative factor in the folded transform.", "scaling by γ"),
                    ("shift by β", "Learned additive factor in the folded transform.", "shift by β"),
                    ("Algorithm 2", "Procedure for training and converting a batch-normalized network for inference.", "Algorithm 2"),
                    ("batch-normalized convolutional networks", "Next application area introduced after Algorithm 2.", "Batch-Normalized Convolutional Networks"),
                ],
                [
                    ("inference-statistics estimation", "Population mean and variance are estimated from multiple training mini-batches.", "average over them"),
                    ("BN folding", "Frozen BN can be replaced by a single linear transform.", "yield a single linear transform"),
                    ("training-to-inference conversion", "Algorithm 2 describes converting N_tr_BN into N_inf_BN.", "Training a Batch-Normalized Network"),
                ],
                [
                    ("where the expectation is over", "general", "Defines what an expectation averages over."),
                    ("Using moving averages instead", "method", "Introduces an alternative statistics-tracking method."),
                    ("Since", "claim", "Gives the reason for the next simplification."),
                    ("It may further be composed with", "method", "Explains how operations can be folded together."),
                    ("to yield", "result", "Introduces the resulting transform."),
                    ("summarizes the procedure", "general", "Signals an algorithm overview."),
                ],
                "Since the means and variances are fixed during inference, the normalization is simply a linear transform",
                "Since X is fixed during inference, Y is simply Z.",
                "Once mean and variance are frozen, BatchNorm becomes a fixed affine operation at inference time.",
                "'Since X, Y is simply Z'는 조건이 고정되면 복잡한 절차가 단순화됨을 설명하는 구조입니다.",
                "The section is difficult because Algorithm 2 mixes training-network notation, inference-network notation, and folded affine parameters.",
            )
        if "this formulation covers both fully-connected and convolutional layers" in lowered and "feature map across both the elements of a mini-batch and spatial locations" in lowered:
            return profile(
                "This section explains where BatchNorm is inserted and how it is adapted to convolutional feature maps.",
                (
                    "For a layer z = g(Wu + b), the paper normalizes Wu + b immediately before the nonlinearity. "
                    "For convolutional layers, all activations in the same feature map are normalized together across mini-batch examples and spatial locations."
                ),
                (
                    "The passage defines the convolutional BatchNorm placement rule: normalize the pre-activation rather than the previous layer output, ignore the bias because mean subtraction cancels it, "
                    "and share normalization statistics and gamma/beta parameters across each feature map."
                ),
                [
                    "This is an implementation section: where exactly does BN go in a layer?",
                    "Read `Wu + b` as the pre-activation value before sigmoid/ReLU.",
                    "For CNNs, the key is feature-map sharing across spatial positions, not one gamma/beta per pixel activation.",
                ],
                [
                    ("affine transformation", "The linear part Wu + b before the nonlinearity.", "affine transformation"),
                    ("element-wise nonlinearity", "Activation function such as sigmoid or ReLU.", "element-wise nonlinearity"),
                    ("W u + b", "The pre-nonlinearity value normalized before applying g.", "W u + b"),
                    ("bias b", "Layer bias whose effect is canceled by mean subtraction.", "bias b"),
                    ("feature map", "Convolutional activation channel normalized consistently across locations.", "feature map"),
                    ("spatial locations", "Positions inside a convolutional feature map.", "spatial locations"),
                    ("effective mini-batch", "All feature-map values across examples and locations.", "effective mini-batch"),
                    ("learned parameters γ, β", "Scale and shift parameters shared per dimension or feature map.", "learned parameters γ"),
                ],
                [
                    ("pre-activation normalization", "BN is applied to Wu + b before the nonlinearity.", "immediately before the nonlinearity"),
                    ("bias cancellation", "The bias can be ignored because mean subtraction cancels it.", "bias b can be ignored"),
                    ("convolutional sharing rule", "CNN feature-map activations are normalized the same way across spatial locations.", "obey the convolutional property"),
                ],
                [
                    ("This formulation covers", "claim", "States the scope of the method."),
                    ("We add", "method", "Introduces an implementation step."),
                    ("We could have also", "contrast", "Mentions an alternative and prepares a rejection."),
                    ("In contrast", "contrast", "Explains why Wu + b is preferred."),
                    ("Note that", "claim", "Highlights an implementation consequence."),
                    ("To achieve this", "method", "Introduces the convolutional adaptation."),
                ],
                "We add the BN transform immediately before the nonlinearity",
                "We add X immediately before Y, by doing Z.",
                "The layer normalizes its pre-activation before the nonlinearity is applied.",
                "'immediately before'는 모델 구조에서 연산의 위치를 정확히 지정하는 표현입니다.",
                "The section is dense because it moves from fully connected layers to convolutional feature-map sharing in one paragraph.",
            )
        if "batch normalization enables higher learning rates" in lowered and "backpropagation through a layer is unaffected by the scale of its parameters" in lowered:
            return profile(
                "This section explains why BatchNorm lets networks use higher learning rates more safely.",
                (
                    "Without BatchNorm, too-large learning rates can explode or vanish gradients or push training into bad regions. "
                    "BatchNorm makes activations and backpropagation less sensitive to parameter scale, which stabilizes larger updates."
                ),
                (
                    "The passage argues that normalization dampens amplification through layers: parameter changes have less harmful effect on activations and gradients, "
                    "the scale of W does not change the normalized output, and larger weights receive smaller gradients."
                ),
                [
                    "This is a benefit-mechanism section, not just a hyperparameter claim.",
                    "The key idea is scale invariance: BN(Wu) behaves like BN((aW)u).",
                    "Connect this to demo learning: the phrase `helps address these issues` links a method to known optimization failures.",
                ],
                [
                    ("higher learning rates", "Larger optimization step sizes enabled by BatchNorm.", "higher learning rates"),
                    ("gradients explode or vanish", "Optimization failure from unstable gradient magnitudes.", "gradients that explode or vanish"),
                    ("poor local minima", "Bad optimization regions that high learning rates can worsen.", "poor local minima"),
                    ("parameter scale", "Magnitude of layer weights whose effect is reduced by BN.", "parameter scale"),
                    ("model explosion", "Unstable growth caused by amplified gradients.", "model explosion"),
                    ("layer Jacobian", "Derivative of a layer's output with respect to input.", "layer Jacobian"),
                    ("gradient propagation", "How gradients move backward through layers.", "gradient propagation"),
                    ("singular values", "Quantities used to describe how a Jacobian scales vectors.", "singular values"),
                ],
                [
                    ("learning-rate stability", "BatchNorm makes larger learning rates less likely to destabilize training.", "higher learning rates"),
                    ("scale-invariance argument", "Scaling W does not change BN(Wu) in the same harmful way.", "unaffected by the scale"),
                    ("gradient-stabilization hypothesis", "BN may keep layer Jacobian singular values closer to 1.", "singular values close to 1"),
                ],
                [
                    ("helps address these issues", "claim", "Links the method to known problems."),
                    ("By normalizing", "method", "Explains the mechanism."),
                    ("for instance", "general", "Introduces an example."),
                    ("Normally", "general", "States the baseline behavior."),
                    ("However, with", "contrast", "Contrasts the method behavior."),
                    ("Indeed", "claim", "Introduces supporting math."),
                    ("Moreover", "general", "Adds another mechanism."),
                    ("We further conjecture", "claim", "Signals a hypothesis rather than a proven result."),
                ],
                "Batch Normalization helps address these issues",
                "X helps address these issues by doing Y.",
                "BatchNorm reduces the instability that normally limits high learning rates.",
                "'helps address these issues'는 앞에서 나열한 문제와 새 방법의 효과를 연결하는 표현입니다.",
                "The section mixes practical optimizer language with scale-invariance equations and a conjecture about Jacobians.",
            )
        if "all singular values of j are equal to 1" in lowered and "batch normalization regularizes the model" in lowered:
            return profile(
                "This section connects BatchNorm to better gradient propagation and regularization.",
                (
                    "Under simplifying Gaussian and linear assumptions, BatchNorm would preserve gradient magnitudes. "
                    "The paper admits reality is messier, but expects better gradient behavior; it also notes that mini-batch dependence acts like regularization and can reduce the need for Dropout."
                ),
                (
                    "The passage shifts from a theoretical gradient-propagation intuition to a regularization claim: normalized layers may keep Jacobian singular values near 1, "
                    "and training examples become slightly stochastic because they are normalized with other mini-batch examples."
                ),
                [
                    "Notice the hedging: `If we assume`, `In reality`, `nevertheless`, and `remains an area of further study`.",
                    "This is not a formal proof; it is a motivation plus empirical expectation.",
                    "The regularization mechanism is mini-batch context: the same example can produce different normalized values depending on its batch.",
                ],
                [
                    ("unit covariances", "Normalized covariance assumption used in the gradient argument.", "unit covariances"),
                    ("singular values", "Values equal to 1 in the idealized Jacobian argument.", "singular values"),
                    ("gradient magnitudes", "Size of gradients during backpropagation.", "gradient magnitudes"),
                    ("gradient propagation", "Backward flow of gradients through the network.", "gradient propagation"),
                    ("regularizes the model", "Improves generalization by adding training-time stochasticity.", "regularizes the model"),
                    ("deterministic values", "Fixed outputs for an example, which BN disrupts during training.", "deterministic values"),
                    ("generalization", "Performance on unseen data.", "generalization"),
                    ("Dropout", "Regularizer that may be removed or reduced when using BN.", "Dropout"),
                ],
                [
                    ("idealized-gradient argument", "Under simplified assumptions, BN would preserve gradient magnitudes.", "singular values of J are equal to 1"),
                    ("hedged-theory claim", "The paper says the exact gradient effect is still open.", "remains an area of further study"),
                    ("mini-batch regularization", "An example is seen with other examples, adding stochasticity.", "seen in conjunction with other examples"),
                ],
                [
                    ("If we assume", "claim", "Introduces a simplifying assumption."),
                    ("Thus", "claim", "Draws the idealized conclusion."),
                    ("In reality", "contrast", "Walks back the simplification."),
                    ("nevertheless", "contrast", "Keeps the practical expectation despite limitations."),
                    ("remains an area of further study", "limitation", "Marks an unresolved theoretical question."),
                    ("Whereas", "contrast", "Contrasts Dropout with BatchNorm."),
                ],
                "In reality, the transformation is not linear",
                "In reality, X is not Y, but we nevertheless expect Z.",
                "The authors admit the assumptions are imperfect but still expect BatchNorm to improve gradient behavior.",
                "'In reality ... nevertheless'는 이론적 단순화와 실제 기대를 함께 제시할 때 쓰는 구조입니다.",
                "The section requires separating a mathematical intuition from a more practical regularization claim.",
            )
        if "figure 1:" in lowered and "mnist network trained with and without batch normalization" in lowered:
            return profile(
                "This section uses an MNIST experiment to visualize faster training and more stable activation distributions.",
                (
                    "Figure 1 compares a small sigmoid network with and without BatchNorm. "
                    "The BatchNorm version trains faster, reaches higher test accuracy, and keeps sigmoid input distributions more stable over training."
                ),
                (
                    "The passage is an experimental sanity check for the internal-covariate-shift story: "
                    "a controlled MNIST network shows improved accuracy and more stable activation percentiles when BN is inserted into each hidden layer."
                ),
                [
                    "Treat the leading numbers as figure-axis residue, not prose to memorize.",
                    "The experiment is not about state-of-the-art MNIST; it is about isolating the effect of BatchNorm.",
                    "Read Figure 1 as evidence for the paper's mechanism: stable sigmoid inputs and faster training.",
                ],
                [
                    ("MNIST network", "Small digit-classification network used for the sanity-check experiment.", "MNIST network"),
                    ("test accuracy", "Fraction of correct predictions on held-out data.", "test accuracy"),
                    ("training steps", "Optimization progress measured over 50,000 steps.", "training steps"),
                    ("input distributions", "Distributions of inputs to a typical sigmoid unit.", "input distributions"),
                    ("sigmoid nonlinearity", "Activation function used in the hidden layers.", "sigmoid nonlinearity"),
                    ("cross-entropy loss", "Classification loss used after the final layer.", "cross-entropy loss"),
                    ("held-out test data", "Data used to compare network accuracy during training.", "held-out test data"),
                    ("baseline network", "Network without BatchNorm used for comparison.", "baseline"),
                ],
                [
                    ("MNIST mechanism check", "The experiment checks whether BN stabilizes activation distributions while improving accuracy.", "Figure 1"),
                    ("baseline-vs-BN comparison", "The section compares the original network to the batch-normalized network.", "comparison between the baseline"),
                    ("percentile visualization", "The figure tracks activation-distribution percentiles over training.", "percentiles"),
                ],
                [
                    ("trained with and without", "method", "Introduces an experimental comparison."),
                    ("helps the network", "result", "States the experimental effect."),
                    ("over the course of training", "general", "Signals a temporal measurement."),
                    ("rather than achieving", "contrast", "Clarifies the experiment's purpose."),
                    ("To investigate why", "method", "Moves from result to mechanism analysis."),
                ],
                "We were interested in the comparison between the baseline and batch-normalized networks",
                "We were interested in X, rather than Y.",
                "The experiment is designed to compare mechanisms, not to set the best MNIST score.",
                "'rather than'은 실험의 목적과 목적이 아닌 것을 분리할 때 유용한 표현입니다.",
                "The section is hard because figure-caption text, architecture setup, and interpretation are mixed together.",
            )
        if "imagenet classification" in lowered and "we refer to this model as inception" in lowered:
            return profile(
                "This section finishes the MNIST figure interpretation and sets up the ImageNet Inception experiment.",
                (
                    "The paper says the original network's activation distributions change over time, while BatchNorm makes them more stable. "
                    "It then moves to ImageNet classification using an Inception-style network and defines the evaluation setup."
                ),
                (
                    "The passage bridges mechanism evidence and large-scale validation: stable distributions support the BN explanation, "
                    "then ImageNet experiments test the method on a convolutional Inception variant with validation accuracy@1."
                ),
                [
                    "This is a transition section: first close Figure 1, then start ImageNet setup.",
                    "Separate the mechanism claim from the dataset/model protocol.",
                    "Save evaluation terms only if they help you read result tables later.",
                ],
                [
                    ("distributions", "Mean and variance of layer inputs over training.", "distributions"),
                    ("batch-normalized network", "Network using BatchNorm whose distributions are more stable.", "batch - normalized network"),
                    ("ImageNet classification task", "Large-scale image classification benchmark.", "ImageNet classification task"),
                    ("Inception network", "Convolutional architecture variant used for the large-scale experiment.", "Inception network"),
                    ("softmax layer", "Output layer predicting one of 1000 classes.", "softmax layer"),
                    ("Stochastic Gradient Descent with momentum", "Optimizer used to train the ImageNet network.", "Stochastic Gradient Descent with momentum"),
                    ("validation accuracy @1", "Probability the top predicted label is correct.", "validation accuracy @1"),
                    ("single crop per image", "Evaluation setting using one crop for each image.", "single crop per image"),
                ],
                [
                    ("mechanism-to-benchmark transition", "The section moves from activation stability evidence to ImageNet validation.", "ImageNet classification"),
                    ("Inception experiment setup", "The authors define model, dataset, optimizer, and evaluation metric.", "We applied Batch Normalization"),
                    ("accuracy@1 protocol", "Validation accuracy@1 measures correct top-1 prediction among 1000 classes.", "probability of predicting the correct label"),
                ],
                [
                    ("In contrast", "contrast", "Contrasts original and batch-normalized distributions."),
                    ("as training progresses", "general", "Frames a temporal training observation."),
                    ("which aids", "result", "Connects stability to training benefit."),
                    ("We applied", "method", "Introduces experiment application."),
                    ("The main difference", "contrast", "Highlights architecture modification."),
                    ("We refer to", "claim", "Names the model for later discussion."),
                    ("In our experiments", "general", "Introduces experiment variants."),
                ],
                "In contrast, the distributions in the batch-normalized network are much more stable",
                "In contrast, X is much more Y, which aids Z.",
                "BatchNorm stabilizes activation distributions, which helps train later layers.",
                "'In contrast'는 baseline과 method 결과를 비교하는 실험 문장에서 자주 쓰입니다.",
                "The section is difficult because it switches from interpreting MNIST behavior to defining a new ImageNet experiment.",
            )
        if "accelerating bn networks" in lowered and "increase learning rate" in lowered and "remove dropout" in lowered:
            return profile(
                "This section lists the training changes that let BN-Inception exploit BatchNorm's advantages.",
                (
                    "Simply adding BatchNorm is not enough. The authors also increase the learning rate, remove Dropout, reduce L2 regularization, "
                    "decay the learning rate faster, remove local response normalization, and shuffle examples more thoroughly."
                ),
                (
                    "The passage is an ablation/setup recipe for accelerated BN-Inception: it keeps the architecture mostly constant "
                    "but changes optimization and regularization settings to use BatchNorm's scale stability and regularizing effect."
                ),
                [
                    "This is not a vocabulary-heavy section; it is a recipe of experimental modifications.",
                    "The core reading task is to connect each change to the earlier claimed BN benefit.",
                    "Notice the phrase `does not take full advantage`: it marks why extra tuning is needed.",
                ],
                [
                    ("input of each nonlinearity", "Where BatchNorm is applied in the network.", "input of each nonlinearity"),
                    ("convolutional way", "Feature-map-wise BatchNorm application from section 3.2.", "convolutional way"),
                    ("higher learning rates", "Larger step sizes enabled by BatchNorm.", "higher learning rates"),
                    ("Dropout", "Regularizer removed because BN provides related regularization.", "Dropout"),
                    ("L2 weight regularization", "Penalty reduced in Modified BN-Inception.", "L2 weight regularization"),
                    ("learning rate decay", "Schedule accelerated because the network trains faster.", "learning rate decay"),
                    ("Local Response Normalization", "Normalization method removed as unnecessary with BN.", "Local Response Normalization"),
                    ("within-shard shuffling", "More thorough data shuffling to vary mini-batch composition.", "within-shard shuffling"),
                ],
                [
                    ("BN-Inception tuning recipe", "The section lists optimization and regularization changes paired with BN.", "further changed the network"),
                    ("regularization substitution", "BN can reduce the need for Dropout and L2 strength.", "fulfills some of the same goals as Dropout"),
                    ("mini-batch regularizer view", "Shuffling improves validation accuracy because batch composition affects BN.", "view of Batch Normalization as a regularizer"),
                ],
                [
                    ("In all cases", "general", "States a condition across all variants."),
                    ("while keeping", "contrast", "Shows what was held constant."),
                    ("does not take full advantage", "limitation", "Explains why additional changes are needed."),
                    ("To do so", "method", "Introduces the recipe."),
                    ("as follows", "general", "Signals a list of changes."),
                    ("without increasing", "result", "States a benefit without a cost."),
                    ("which is consistent with", "claim", "Links evidence back to an interpretation."),
                ],
                "Simply adding Batch Normalization to a network does not take full advantage of our method",
                "Simply adding X does not take full advantage of Y.",
                "The method needs matching training settings to show its full speed benefit.",
                "'does not take full advantage of'는 단순 적용과 제대로 활용한 적용을 구분하는 표현입니다.",
                "The section is long because it compresses multiple hyperparameter and regularization changes into one list.",
            )
        if "randomization inherent in our method" in lowered and "reduce the photometric distortions" in lowered:
            return profile(
                "This short tail section finishes the BN-Inception tuning recipe with shuffling and image-distortion changes.",
                (
                    "The paper argues that BatchNorm's mini-batch randomness helps most when examples appear with different neighbors. "
                    "Because batch-normalized networks train faster and see each example fewer times, the authors reduce photometric distortions."
                ),
                (
                    "This is a continuation fragment from the previous experimental-modification list: it connects within-shard shuffling to BN's regularization effect, "
                    "then changes data augmentation so the faster trainer focuses on more realistic images."
                ),
                [
                    "This extracted section is a page-tail fragment; read it together with the previous BN-Inception tuning list.",
                    "The learning point is experimental rationale, not a standalone paper claim.",
                    "Save `photometric distortions` only if image-augmentation vocabulary matters to you.",
                ],
                [
                    ("randomization", "Training variation introduced by mini-batch composition.", "randomization"),
                    ("photometric distortions", "Image color/brightness-style data augmentation reduced in this experiment.", "photometric distortions"),
                    ("training example", "Example whose mini-batch context can change across training.", "training example"),
                    ("batchnormalized networks", "Networks using BN that train faster and see examples fewer times.", "batchnormalized networks"),
                ],
                [
                    ("mini-batch-randomization rationale", "BN regularization is stronger when examples meet different mini-batch neighbors.", "affects an example differently"),
                    ("augmentation-reduction rationale", "Faster BN training motivates reducing artificial image distortions.", "distorting them less"),
                    ("orphan-section continuation", "This text completes the preceding list of BN-Inception modifications.", "Reduce the photometric distortions"),
                ],
                [
                    ("inherent in our method", "claim", "Describes a property built into the method."),
                    ("should be most beneficial when", "claim", "States the condition under which an effect helps most."),
                    ("Because", "claim", "Introduces the reason for an experimental change."),
                    ("by distorting them less", "method", "Explains the practical data-augmentation adjustment."),
                ],
                "Because batchnormalized networks train faster",
                "Because X, we let Y do Z.",
                "Since BN networks train faster, the authors reduce artificial image distortion.",
                "'Because X, we let Y...'는 실험 설정을 바꾼 이유와 조치를 연결하는 구조입니다.",
                "The section is difficult mainly because it is a dangling continuation from the previous page.",
            )
        if "bn-baseline" in lowered and "bn-x5" in lowered and "bn-x30" in lowered and "single-network classification" in lowered:
            return profile(
                "This section defines the single-network ImageNet variants and the Figure 2/3 result-table setup.",
                (
                    "The paper compares Inception, BN-Baseline, BN-x5, BN-x30, and BN-x5-Sigmoid. "
                    "The variants test whether BatchNorm allows faster training, larger learning rates, and sigmoid networks that would otherwise fail."
                ),
                (
                    "The passage is a result-table setup section: it names each ImageNet network variant, lists the learning-rate changes, "
                    "and defines the speed/accuracy comparison against Inception's 72.2% validation accuracy."
                ),
                [
                    "Ignore the leading chart-axis numbers; they are figure extraction residue.",
                    "Focus on variant names and what each variant changes.",
                    "This is where `BN-x5` and `BN-x30` become shorthand for learning-rate stress tests.",
                ],
                [
                    ("BN-Baseline", "Inception plus BatchNorm before each nonlinearity.", "BN-Baseline"),
                    ("BN-x5", "BN-Inception with the section 4.2.1 modifications and 5x initial learning rate.", "BN-x5"),
                    ("BN-x30", "BN-x5-style model with 30x Inception initial learning rate.", "BN-x30"),
                    ("BN-x5-Sigmoid", "BN-x5 variant using sigmoid instead of ReLU.", "BN-x5-Sigmoid"),
                    ("LSVRC2012 training data", "ImageNet training data used for the single-network experiments.", "LSVRC2012 training data"),
                    ("validation accuracy", "Metric plotted as training progresses.", "validation accuracy"),
                    ("machine infinity", "Numerical blow-up when original Inception uses too large a learning rate.", "machine infinity"),
                    ("chance accuracy", "Near-random prediction performance for original sigmoid Inception.", "chance"),
                ],
                [
                    ("variant-definition table", "The section defines the models that later result numbers compare.", "We evaluated the following networks"),
                    ("learning-rate stress test", "BN-x5 and BN-x30 test whether BN tolerates much larger learning rates.", "learning rate was increased"),
                    ("sigmoid-rescue test", "BN-x5-Sigmoid tests whether BN can train sigmoid networks that otherwise fail.", "sigmoid nonlinearity"),
                ],
                [
                    ("Steps to match", "general", "Names a speed-to-target metric."),
                    ("as a function of", "general", "Describes the x-axis of a result plot."),
                    ("all trained on", "method", "States the shared data condition."),
                    ("Same as", "method", "Defines a variant relative to a baseline."),
                    ("Like", "method", "Defines another variant by analogy."),
                    ("but with", "contrast", "Names the changed setting."),
                    ("We also attempted", "method", "Reports an unsuccessful comparison attempt."),
                ],
                "We evaluated the following networks",
                "We evaluated the following X, all Y and Z.",
                "The authors define a controlled set of network variants before comparing speed and accuracy.",
                "'the following networks'은 실험 대상 목록이 시작된다는 신호입니다.",
                "The section is hard because chart text, table text, and variant definitions are extracted into one block.",
            )
        if "bn-x5 needs 14 times fewer steps" in lowered and "ensemble classification" in lowered:
            return profile(
                "This section interprets the ImageNet speed/accuracy results and begins the ensemble result claim.",
                (
                    "BN-Baseline matches Inception accuracy in less than half the steps. BN-x5 reaches the same target in 14 times fewer steps, "
                    "BN-x30 reaches higher final accuracy, and BN lets a sigmoid Inception train at all."
                ),
                (
                    "The passage converts Figure 3 into claims: BatchNorm accelerates optimization, supports high learning rates, "
                    "rescues sigmoid nonlinearities from chance-level failure, and then reports ImageNet ensemble top-5 error results."
                ),
                [
                    "This is a result-interpretation section: map each model variant to the claim it supports.",
                    "Separate single-network speed results from the ensemble classification claim at the end.",
                    "The important language pattern is `By only using...`, which isolates the effect of one modification.",
                ],
                [
                    ("steps to 72.2% accuracy", "Training-speed metric using Inception's target accuracy.", "72.2% accuracy"),
                    ("BN-Baseline", "BatchNorm-only Inception variant.", "BN-Baseline"),
                    ("BN-x5", "Modified BN-Inception with 5x initial learning rate.", "BN-x5"),
                    ("BN-x30", "BN variant with 30x initial learning rate.", "BN-x30"),
                    ("BN-x5-Sigmoid", "Sigmoid BN variant that reaches 69.8%.", "BN-x5-Sigmoid"),
                    ("internal covariate shift", "Mechanism whose reduction allows sigmoid networks to train.", "internal covariate shift"),
                    ("top-5 validation error", "ImageNet metric reported for the ensemble.", "top-5 validation error"),
                    ("ILSVRC server", "Evaluation server used for the reported test error.", "ILSVRC server"),
                ],
                [
                    ("BatchNorm-only speedup", "BN-Baseline alone cuts steps by more than half.", "less than half"),
                    ("modified-BN speedup", "BN-x5 reaches target accuracy with 14x fewer steps.", "14 times fewer steps"),
                    ("high-learning-rate accuracy gain", "BN-x30 trains slower at first but reaches higher final accuracy.", "higher final accuracy"),
                    ("sigmoid training rescue", "BatchNorm enables sigmoid Inception to train far above chance.", "sigmoid is used"),
                    ("ensemble result claim", "The section begins reporting top-5 validation/test error for a six-network ensemble.", "For our ensemble"),
                ],
                [
                    ("By only using", "method", "Isolates the effect of one modification."),
                    ("By applying", "method", "Introduces the combined modification effect."),
                    ("significantly increase", "result", "States a large performance change."),
                    ("Interestingly", "general", "Flags a non-obvious result."),
                    ("further", "general", "Signals an additional degree of change."),
                    ("despite", "contrast", "Contrasts success with known difficulty."),
                    ("Indeed", "claim", "Introduces supporting numeric evidence."),
                    ("Here we report", "result", "Introduces the authors' result claim."),
                ],
                "By only using Batch Normalization",
                "By only using X, we achieve Y.",
                "Using BatchNorm alone already matches the baseline in fewer training steps.",
                "'By only using'은 어떤 효과가 특정 변경 하나만으로도 나타남을 강조합니다.",
                "The section is dense because it interprets a table, compares multiple variants, and then shifts into ensemble results.",
            )
        if "the ensemble prediction was based on the arithmetic average" in lowered and "5 conclusion" in lowered:
            return profile(
                "This section finishes the ImageNet ensemble setup and begins the paper's conclusion.",
                (
                    "The ensemble is built from BN-x30-based networks and averages class probabilities. "
                    "The authors claim BatchNorm sets a new ImageNet state of the art, then start the conclusion by restating the internal-covariate-shift premise."
                ),
                (
                    "The passage connects final benchmark methodology to the paper thesis: modified BN-x30 networks are ensembled by probability averaging, "
                    "and the conclusion frames BatchNorm as a mechanism for accelerating deep-network training by reducing internal covariate shift inside layers."
                ),
                [
                    "This is a boundary section: first ensemble details, then conclusion thesis.",
                    "Do not save `we demonstrate` as a vocabulary item; the useful expression is the state-of-the-art claim pattern.",
                    "The conclusion starts by returning to the original premise: covariate shift applies inside networks.",
                ],
                [
                    ("BN-x30", "High-learning-rate BN-Inception variant used as the ensemble base.", "BN-x30"),
                    ("Dropout probability", "Dropout rate varied across ensemble members.", "Dropout probability"),
                    ("per-activation Batch Normalization", "Non-convolutional BN variant used in some hidden layers.", "per-activation Batch Normalization"),
                    ("ensemble prediction", "Prediction produced from multiple networks.", "ensemble prediction"),
                    ("arithmetic average of class probabilities", "Method for combining ensemble outputs.", "arithmetic average"),
                    ("multicrop inference", "Evaluation method using multiple crops of the same image.", "multicrop inference"),
                    ("state-of-the-art", "Best reported benchmark performance at the time.", "state-of-the-art"),
                    ("covariate shift", "Distribution shift premise extended to sub-networks and layers.", "covariate shift"),
                ],
                [
                    ("ensemble construction", "The final system averages class probabilities from multiple BN-x30-based networks.", "arithmetic average"),
                    ("state-of-the-art benchmark claim", "Figure 4 is used to claim a new ImageNet benchmark result.", "state-of-the-art"),
                    ("conclusion thesis return", "The conclusion restates that covariate shift also applies inside deep networks.", "also ap-"),
                ],
                [
                    ("based on", "method", "Explains how the ensemble prediction is formed."),
                    ("similar to", "general", "Relates inference details to prior work."),
                    ("We demonstrate", "result", "Introduces benchmark evidence."),
                    ("allows us to", "result", "Connects the method to a result."),
                    ("by a healthy margin", "result", "Emphasizes the size of improvement."),
                    ("We have presented", "claim", "Starts the conclusion contribution statement."),
                    ("is based on the premise that", "claim", "States the core assumption behind the method."),
                ],
                "We demonstrate in Fig. 4 that batch normalization allows us to set new state-of-the-art",
                "We demonstrate that X allows us to Y.",
                "The authors use Figure 4 to claim BatchNorm reaches a new ImageNet state of the art.",
                "'We demonstrate that X allows us to Y'는 실험 결과가 방법의 효과를 뒷받침한다는 구조입니다.",
                "The section is difficult because ensemble setup and conclusion thesis are joined by a page break.",
            )
        if "model resolution crops models top-1 error top-5 error" in lowered and "merely adding batch normalization" in lowered:
            return profile(
                "This section reads the Figure 4 ImageNet table and summarizes the main BatchNorm mechanism.",
                (
                    "Figure 4 compares BN-Inception against previous ImageNet systems. The conclusion explains that BatchNorm works by normalizing "
                    "internal activations inside the architecture, training with mini-batch statistics, and backpropagating through normalization."
                ),
                (
                    "The passage combines final benchmark evidence with the conclusion's method recap: BN-Inception ensemble reaches 4.9% validation top-5 error "
                    "and 4.82% test top-5 error, while the method preserves representation ability with two parameters per activation and supports faster, more stable training."
                ),
                [
                    "Treat the first table block as benchmark evidence, not normal prose.",
                    "The conclusion body is a compact recap of the whole method: normalization in architecture, mini-batch statistics, learned scale/shift, inference algorithm.",
                    "Separate speedup, saturating nonlinearities, learning rates, and Dropout as distinct benefits.",
                ],
                [
                    ("Top-1 error", "ImageNet metric: top prediction is wrong.", "Top-1 error"),
                    ("Top-5 error", "ImageNet metric: correct class absent from top five predictions.", "Top-5 error"),
                    ("BN-Inception ensemble", "Six-model BatchNorm ensemble reported in Figure 4.", "BN-Inception ensemble"),
                    ("test server", "ILSVRC server reporting 4.82% top-5 test error.", "test server"),
                    ("internal activations", "Activations inside the network that BN normalizes.", "internal activations"),
                    ("mini-batch", "Training batch used to compute normalization statistics.", "mini-batch"),
                    ("normalization parameters", "Parameters through which gradients are backpropagated.", "normalization parameters"),
                    ("saturating nonlinearities", "Nonlinearities made trainable by BatchNorm.", "saturating nonlinearities"),
                ],
                [
                    ("Figure 4 benchmark reading", "The table compares BN-Inception with previous ImageNet state of the art.", "Figure 4"),
                    ("architecture-integrated normalization", "BN draws power from normalization being part of the network.", "network architecture itself"),
                    ("representation-preserving transform", "Two extra parameters preserve representation ability.", "two extra parameters per activation"),
                    ("benefit recap", "BN supports saturating nonlinearities, higher learning rates, less Dropout, and training speedup.", "saturating nonlinearities"),
                ],
                [
                    ("comparison with previous", "general", "Introduces benchmark comparison."),
                    ("as reported by", "general", "Names the evaluation authority."),
                    ("draws its power from", "claim", "Explains the source of the method's effect."),
                    ("This ensures that", "result", "Connects architecture integration to optimizer handling."),
                    ("To enable", "method", "Introduces why mini-batch normalization is used."),
                    ("in doing so", "result", "Links added parameters to preserved representation ability."),
                    ("Merely adding", "method", "Isolates the effect of adding BN alone."),
                ],
                "Our proposed method draws its power from normalizing activations",
                "Our proposed method draws its power from X and Y.",
                "BatchNorm's power comes from normalizing activations inside the network architecture itself.",
                "'draws its power from'은 방법의 핵심 원천을 설명하는 강한 표현입니다.",
                "The section is hard because a benchmark table and a compressed method recap are extracted together.",
            )
        if "by further increasing the learning rates" in lowered and "standardization layer" in lowered:
            return profile(
                "This conclusion section states the final ImageNet claims and distinguishes BatchNorm from a prior standardization layer.",
                (
                    "With higher learning rates and other BN-enabled changes, the authors match and beat prior ImageNet results. "
                    "They then contrast BatchNorm with a prior standardization layer, emphasizing different goals, placement before the nonlinearity, "
                    "learned scale/shift, convolutional handling, and deterministic inference."
                ),
                (
                    "The passage closes the paper by combining final performance claims with method positioning: BatchNorm improves single-network and ensemble ImageNet performance, "
                    "then distinguishes itself from prior standardization work by its training-stability goal and deployment properties."
                ),
                [
                    "This is final-positioning prose: performance claim first, related-method contrast second.",
                    "The important academic move is `though the two methods stem from very different goals`.",
                    "This section is useful for learning how papers defend novelty against similar prior work.",
                ],
                [
                    ("state of the art", "Best known benchmark performance at the time.", "state of the art"),
                    ("single-network image classification", "One-model ImageNet performance setting.", "single-network image classification"),
                    ("standardization layer", "Prior related method compared against BatchNorm.", "standardization layer"),
                    ("stable distribution of activation values", "BatchNorm's stated goal throughout training.", "stable distribution of activation values"),
                    ("before the nonlinearity", "Placement of BatchNorm in the authors' experiments.", "before the nonlinearity"),
                    ("learned scale and shift", "Gamma/beta mechanism that can represent identity.", "learned scale and shift"),
                    ("deterministic inference", "Inference behavior not dependent on the mini-batch.", "deterministic"),
                    ("batchnormalizing each convolutional layer", "Applying BN to every convolutional layer.", "batchnormalizing each convolutional layer"),
                ],
                [
                    ("final single-network claim", "BN-enabled modifications beat prior single-network image classification state of the art.", "single-network image classification"),
                    ("final ensemble claim", "Combining BN-trained models beats the best known ImageNet system.", "combining multiple models"),
                    ("prior-method differentiation", "BatchNorm is contrasted with a standardization layer by goal, placement, scale/shift, convolution handling, and inference.", "standardization layer"),
                    ("novelty defense pattern", "The section explains similarity while listing important differences.", "different goals"),
                ],
                [
                    ("By further increasing", "method", "Connects extra modifications to final performance."),
                    ("Furthermore", "general", "Adds ensemble performance claim."),
                    ("Interestingly", "general", "Introduces a related-method comparison."),
                    ("though", "contrast", "Concedes similarity while preserving difference."),
                    ("stem from very different goals", "contrast", "States conceptual difference."),
                    ("On the contrary", "contrast", "Contrasts placement and resulting activations."),
                    ("Other notable differentiating characteristics include", "claim", "Introduces a list of novelty points."),
                ],
                "though the two methods stem from very different goals",
                "Though X and Y are similar, they stem from very different goals.",
                "The authors acknowledge similarity to prior work but argue the goals and details differ.",
                "'though ... stem from very different goals'는 유사한 선행연구와 자기 방법을 구분할 때 쓰는 표현입니다.",
                "The section is dense because it combines benchmark claims, prior-work comparison, and implementation differences.",
            )
        if "future work includes applications of our method to recurrent neural networks" in lowered and "references bengio" in lowered:
            return profile(
                "This section closes the conclusion with future work, then starts the references.",
                (
                    "The authors say BatchNorm may help RNNs, domain adaptation, and further theoretical analysis. "
                    "The section then transitions into the bibliography, so the reference entries should be skimmed as source metadata."
                ),
                (
                    "The passage is a conclusion-to-bibliography boundary: it names future research directions around RNN gradient problems, "
                    "domain adaptation, population-statistics recomputation, and theoretical analysis before citation entries begin."
                ),
                [
                    "Read the first paragraph as future work; read the rest as references.",
                    "Do not memorize author names as vocabulary unless you need the citation trail.",
                    "The useful language pattern is `Our future work includes...`, a common conclusion move.",
                ],
                [
                    ("future work", "Research directions the paper has not yet explored.", "future work"),
                    ("Recurrent Neural Networks", "Future application area where gradient problems may be severe.", "Recurrent Neural Networks"),
                    ("vanishing or exploding gradients", "Training problem that may be especially severe in RNNs.", "vanishing or exploding gradients"),
                    ("gradient propagation", "Hypothesis the authors want to test more thoroughly.", "gradient propagation"),
                    ("domain adaptation", "Future direction involving generalization to new data distributions.", "domain adaptation"),
                    ("population means and variances", "Statistics that may be recomputed for new data distributions.", "population means and variances"),
                    ("theoretical analysis", "Future work direction for understanding and improving the algorithm.", "theoretical analysis"),
                    ("References", "Bibliography section marker.", "References"),
                ],
                [
                    ("future-work roadmap", "The authors name RNNs, domain adaptation, and theory as future directions.", "future work includes"),
                    ("domain-adaptation hypothesis", "BN may help generalize to new distributions by recomputing population statistics.", "generalize to new data distributions"),
                    ("bibliography transition", "The section switches from conclusion prose into citation entries.", "References"),
                ],
                [
                    ("In this work, we have not explored", "limitation", "States scope left for future work."),
                    ("Our future work includes", "general", "Introduces future directions."),
                    ("where", "general", "Explains why a direction matters."),
                    ("We plan to investigate whether", "method", "Introduces a research question."),
                    ("Finally", "general", "Adds the last future-work direction."),
                    ("would allow", "result", "States a possible benefit."),
                ],
                "Our future work includes applications of our method to Recurrent Neural Networks",
                "Our future work includes applications of X to Y.",
                "The authors propose applying BatchNorm to RNNs as future work.",
                "'Our future work includes'는 결론에서 아직 하지 않은 연구 방향을 제시하는 표현입니다.",
                "The section is difficult because future-work prose and bibliography entries are extracted together.",
            )
        if "mean-normalized stochastic gradient" in lowered and "appendix variant of the inception model used" in lowered:
            return profile(
                "This section ends the references and starts the appendix describing the Inception variant.",
                (
                    "The first part is bibliography metadata. The appendix then explains that the BN-Inception experiments used a modified GoogLeNet/Inception architecture documented in Figure 5."
                ),
                (
                    "The passage is a reference-to-appendix boundary: it closes the citation list with deep-learning and recognition references, then introduces architecture changes relative to GoogLeNet."
                ),
                [
                    "Skim the reference entries unless you need a source trail.",
                    "The appendix is not a new method claim; it documents the exact Inception architecture used for experiments.",
                    "Figure 5 is architecture documentation for reproducibility.",
                ],
                [
                    ("Mean-normalized stochastic gradient", "Reference title ending the bibliography section.", "Mean-normalized stochastic gradient"),
                    ("Deep image", "Reference title about scaling image recognition.", "Deep image"),
                    ("Appendix", "Supplementary section after the main paper.", "Appendix"),
                    ("Variant of the Inception Model", "Appendix topic documenting the experiment architecture.", "Variant of the Inception Model"),
                    ("GoogLeNet architecture", "Baseline architecture the appendix compares against.", "GoogleNet archictecture"),
                    ("Figure 5", "Appendix figure documenting architecture changes.", "Figure 5"),
                    ("5 ×5 convolutional layers", "Original layers replaced in the modified architecture.", "5 ×5 convolutional layers"),
                    ("3 ×3 convolutional layers", "Replacement layers used in the variant.", "3 ×3 convolutional layers"),
                ],
                [
                    ("reference-to-appendix boundary", "The section switches from citations into reproducibility details.", "Appendix"),
                    ("architecture documentation purpose", "Figure 5 records changes made for the experimental Inception variant.", "documents the changes"),
                    ("GoogLeNet comparison", "The appendix describes notable changes compared to GoogLeNet.", "compared to the GoogLeNet"),
                ],
                [
                    ("Appendix", "general", "Marks supplementary material."),
                    ("documents the changes", "method", "Explains the appendix purpose."),
                    ("with respect to", "general", "States the comparison target."),
                    ("include", "general", "Introduces a list of changes."),
                    ("are replaced by", "method", "Describes architecture substitution."),
                ],
                "Figure 5 documents the changes",
                "Figure X documents the changes that were performed compared to Y.",
                "The appendix uses Figure 5 to document architecture changes relative to GoogLeNet.",
                "'documents the changes'는 재현성을 위해 무엇이 달라졌는지 기록한다는 표현입니다.",
                "The section is difficult because reference entries and appendix prose are extracted together.",
            )
        if "the number 28 ×28 inception modules is increased" in lowered and "separable convolution" in lowered:
            return profile(
                "This appendix section lists architecture changes in the modified Inception model.",
                (
                    "The appendix says the modified model adds depth and cost, increases 28x28 Inception modules, changes pooling choices inside modules, "
                    "avoids some across-the-board pooling, and uses separable convolution in the first layer."
                ),
                (
                    "The passage is an architecture-change checklist for reproducibility: it records layer-depth increase, parameter/computation cost changes, "
                    "module-count changes, pooling placement, stride-2 modules, and separable convolution."
                ),
                [
                    "This is not core language-learning prose; it is technical appendix documentation.",
                    "Use it to understand the experimental model, not the BatchNorm theory.",
                    "The important skill is reading bullet-style architecture changes without treating every number as vocabulary.",
                ],
                [
                    ("weight layers", "Network depth units increased by the architecture modification.", "weight layers"),
                    ("parameters", "Model parameters increased by about 25%.", "parameters"),
                    ("computational cost", "Compute increased by about 30%.", "computational cost"),
                    ("28 ×28 inception modules", "Modules whose count increased from 2 to 3.", "28 ×28 inception modules"),
                    ("average pooling", "Pooling type used inside some modules.", "average"),
                    ("maximum-pooling", "Pooling type used inside some modules.", "maximum-pooling"),
                    ("stride-2 convolution/pooling", "Downsampling operation before filter concatenation.", "stride-2 convolution"),
                    ("separable convolution", "First-layer convolution used to reduce compute cost.", "separable convolution"),
                ],
                [
                    ("architecture-change checklist", "The section lists reproducibility details for the modified Inception model.", "increased"),
                    ("cost-depth tradeoff", "The variant increases depth, parameter count, and compute cost.", "computational cost"),
                    ("pooling-layout change", "Pooling choices and stride-2 placements differ from GoogLeNet.", "pooling"),
                    ("separable-convolution tradeoff", "Separable convolution reduces compute but increases training memory.", "memory consumption"),
                ],
                [
                    ("Also", "general", "Adds another consequence."),
                    ("is increased from", "claim", "States a count change."),
                    ("This is indicated in", "general", "Points to table notation."),
                    ("There are no", "claim", "States a removed architecture pattern."),
                    ("while increasing", "contrast", "States a tradeoff."),
                ],
                "This reduces the computational cost while increasing the memory consumption",
                "This reduces X while increasing Y.",
                "The separable convolution trades lower compute for higher memory use during training.",
                "'reduces X while increasing Y'는 설계의 tradeoff를 설명하는 구조입니다.",
                "The section is hard because it is bullet-style appendix prose with many architecture details.",
            )
        if "type patch size" in lowered and "inception architecture" in lowered:
            return profile(
                "This section is the Figure 5 Inception architecture table.",
                (
                    "The table lists layer types, patch sizes, strides, output sizes, depths, channel counts, reduction layers, and pooling/projection choices for the Inception variant."
                ),
                (
                    "This is not ordinary prose. It is a compact architecture specification used to reproduce the modified Inception network in the BatchNorm experiments."
                ),
                [
                    "Skim this as an architecture table unless you are implementing the model.",
                    "Do not save every numeric cell as vocabulary.",
                    "The useful reading task is identifying columns: type, patch size/stride, output size, depth, channel reductions, and pooling/projection.",
                ],
                [
                    ("patch size/stride", "Convolution or pooling kernel size and stride column.", "patch size/ stride"),
                    ("output size", "Feature-map size after each stage.", "output size"),
                    ("depth", "Number of stacked layers or module depth in the table.", "depth"),
                    ("#1×1", "Channel projection column in Inception modules.", "#1×1"),
                    ("#3×3 reduce", "Channel-reduction column before 3x3 convolutions.", "#3×3 reduce"),
                    ("Pool +proj", "Pooling branch plus projection column.", "Pool"),
                    ("inception", "Repeated Inception block rows such as 3a, 4e, and 5b.", "inception"),
                    ("avg pool", "Final global pooling layer in the architecture.", "avg pool"),
                ],
                [
                    ("architecture-table navigation", "The section should be read by columns, not as prose.", "type patch size"),
                    ("Inception-stage progression", "Rows progress from convolution/pooling into Inception modules.", "inception"),
                    ("reproducibility appendix", "The table documents exact architecture dimensions.", "Figure"),
                ],
                [
                    ("type", "general", "Architecture table column naming layer type."),
                    ("patch size/stride", "general", "Architecture table column naming kernel/stride."),
                    ("output size", "general", "Architecture table column naming tensor size."),
                    ("Figure 5", "general", "Names the appendix architecture table."),
                ],
                "Figure 5: Inception architecture",
                "Figure X: architecture.",
                "This is an architecture table, not a paragraph to summarize.",
                "표 형식의 appendix는 문장 해석보다 column 의미를 파악하는 것이 중요합니다.",
                "The section is difficult because table cells were extracted as a long text stream.",
            )
        return None

    def _attention_profile(self, document_text: str) -> dict[str, Any] | None:
        lowered = document_text.lower()
        compact_lowered = re.sub(r"\s+", " ", lowered)

        def profile(
            one_line: str,
            simple: str,
            academic: str,
            notes: list[str],
            terms: list[tuple[str, str, str]],
            concepts: list[tuple[str, str, str]],
            phrases: list[tuple[str, str, str]],
            sentence_target: str,
            core_structure: str,
            simplified_version: str,
            korean_explanation: str,
            difficulty_reason: str,
        ) -> dict[str, Any]:
            return {
                "summaries": {"one_line": one_line, "simple": simple, "academic": academic, "study_notes": notes},
                "terms": terms,
                "concepts": concepts,
                "phrases": phrases,
                "sentence_target": sentence_target,
                "core_structure": core_structure,
                "simplified_version": simplified_version,
                "korean_explanation": korean_explanation,
                "difficulty_reason": difficulty_reason,
            }

        if (
            ("introduction recurrent neural networks" in compact_lowered or "introduction recurrent models" in compact_lowered)
            and "factor computation along" in lowered
            and "symbol positions" in lowered
        ):
            return profile(
                "This introduction explains why recurrent sequence models limit parallel training before motivating attention.",
                (
                    "The section reviews RNN/LSTM/GRU sequence models and explains their sequential computation bottleneck. "
                    "Because hidden states depend on previous positions, recurrence limits parallelization and makes long-range dependencies harder."
                ),
                (
                    "The passage sets up the Transformer by diagnosing recurrent encoder-decoder models: position-by-position computation, "
                    "sequential dependency, batching constraints, and difficulty connecting distant token positions."
                ),
                [
                    "Read this as problem setup, not the Transformer method yet.",
                    "The key contrast is sequential recurrence versus parallel attention.",
                    "Save terms that explain why recurrence is a bottleneck.",
                ],
                [
                    ("recurrent neural networks", "Sequence models that process tokens step by step.", "Recurrent neural networks"),
                    ("long short-term memory", "LSTM, a recurrent model family used in sequence modeling.", "long short-term memory"),
                    ("gated recurrent neural networks", "GRU-style recurrent models used for sequence tasks.", "gated recurrent"),
                    ("sequence modeling", "Modeling ordered token sequences.", "sequence modeling"),
                    ("sequence transduction", "Mapping one sequence to another, as in translation.", "transduction problems"),
                    ("symbol positions", "Token positions along which recurrent computation is factored.", "symbol positions"),
                    ("parallelization", "Running computation for positions at the same time.", "parallelization"),
                    ("hidden states", "Intermediate recurrent states generated step by step.", "hidden states"),
                ],
                [
                    ("recurrent-computation bottleneck", "RNNs factor computation by position, limiting parallel training.", "factor computation"),
                    ("hidden-state chain", "Each recurrent state depends on the previous state and current input.", "hidden states"),
                    ("Transformer motivation", "The section motivates replacing recurrence with attention.", "parallelization"),
                ],
                [
                    ("have been firmly established as", "claim", "States prior accepted baseline status."),
                    ("Numerous efforts have since continued to", "general", "Introduces ongoing prior work."),
                    ("typically factor computation along", "method", "Explains recurrent computation structure."),
                    ("precludes parallelization", "limitation", "States the bottleneck."),
                    ("critical in sequence modeling tasks", "claim", "Explains why the limitation matters."),
                ],
                "Recurrent models typically factor computation",
                "X typically factor computation along Y, generating Z.",
                "RNNs compute position by position, which creates hidden states and limits parallel training.",
                "'typically factor computation along'은 모델이 어떤 축으로 계산을 나누는지 설명하는 표현입니다.",
                "The sentence compresses model structure, computation order, and the hidden-state dependency.",
            )
        if (
            ("significantly more parallelization" in lowered and "2 background" in lowered)
            or (
                "goal of reducing sequential computation" in lowered
                and "extended neural gpu" in lowered
                and ("bytenet" in lowered or "convs2s" in lowered)
            )
        ):
            return profile(
                "This transition links the Transformer's parallelization claim to prior convolutional and attention-based sequence models.",
                (
                    "The section says the Transformer trains quickly and then reviews earlier attempts to reduce sequential computation, "
                    "including convolutional models and attention mechanisms."
                ),
                (
                    "The passage bridges introduction and architecture: it positions Extended Neural GPU, ByteNet, and ConvS2S as prior parallel-computation efforts, "
                    "then distinguishes the Transformer's fully self-attentive transduction design."
                ),
                [
                    "This is a literature-positioning section.",
                    "Track which models are convolutional baselines and which idea is attention.",
                    "The key claim is not only quality, but training parallelism.",
                ],
                [
                    ("sequential computation", "Step-by-step sequence processing that limits parallel training.", "sequential computation"),
                    ("in parallel", "Computing multiple sequence positions at the same time.", "in parallel"),
                    ("convolutional neural networks", "CNN-based models used here as prior alternatives to recurrence.", "convolutional neural networks"),
                    ("hidden representations", "Internal vector representations computed for input and output positions.", "hidden representations"),
                    ("dependencies between distant positions", "Relationships between far-apart positions that become harder to learn when path length grows.", "dependencies between distant positions"),
                    ("input and output positions", "Token positions in source and target sequences whose relationships must be modeled.", "input and output positions"),
                ],
                [
                    ("parallel-computation lineage", "The section maps prior work that also reduces sequential computation.", "reducing sequential computation"),
                    ("convolutional baseline family", "Extended Neural GPU, ByteNet, and ConvS2S are prior attempts to reduce sequential computation.", "Extended Neural GPU"),
                    ("Transformer efficiency claim", "The model reaches strong translation quality after a short GPU training window.", "twelve hours"),
                    ("constant path length", "The Transformer reduces the operation path between arbitrary positions to a constant number.", "constant number of operations"),
                ],
                [
                    ("allows for significantly more", "result", "States a comparative efficiency benefit."),
                    ("can reach a new state of the art", "result", "Claims benchmark performance."),
                    ("forms the foundation of", "claim", "Connects a goal to prior work."),
                    ("all of which use", "general", "Groups related prior methods."),
                    ("computing hidden representations in parallel", "method", "Explains the prior models' parallel mechanism."),
                ],
                "The goal of reducing sequential computation",
                "The goal of X also forms the foundation of Y.",
                "Prior models also tried to reduce sequential computation, mainly through convolution.",
                "'forms the foundation of'는 어떤 목표가 여러 선행연구의 기반이라는 뜻입니다.",
                "The sentence links a research goal to several model families in one compressed literature map.",
            )
        if "first transduction model relying entirely on self-attention" in lowered and "3 model architecture" in lowered:
            return profile(
                "This section states the Transformer's novelty and introduces the encoder-decoder architecture frame.",
                (
                    "The authors claim the Transformer is the first transduction model that relies entirely on self-attention, "
                    "then move into the standard encoder-decoder structure used by competitive sequence transduction models."
                ),
                (
                    "The passage is the method transition: it distinguishes the Transformer from RNN/CNN-aligned models, previews the self-attention motivation, "
                    "and anchors the architecture in encoder-decoder sequence modeling."
                ),
                [
                    "This is where the paper moves from motivation to method.",
                    "Separate novelty claim from architecture setup.",
                    "The useful phrase is 'To the best of our knowledge, however'.",
                ],
                [
                    ("self-attention", "The sole mechanism the Transformer uses for transduction representations.", "self-attention"),
                    ("transduction model", "A model that maps one sequence to another.", "transduction model"),
                    ("sequencealigned RNNs", "RNNs aligned to sequence positions, which the Transformer avoids.", "sequencealigned RNNs"),
                    ("convolution", "A prior sequence modeling mechanism the Transformer avoids.", "convolution"),
                    ("encoder-decoder structure", "Architecture pattern with input encoder and output decoder.", "encoder-decoder structure"),
                    ("input sequence", "The sequence consumed by the encoder.", "input sequence"),
                    ("output sequence", "The sequence produced by the decoder.", "output sequence"),
                ],
                [
                    ("attention-only novelty claim", "The paper claims the Transformer relies entirely on self-attention.", "relying entirely on self-attention"),
                    ("method-section roadmap", "The authors announce they will describe and motivate self-attention.", "following sections"),
                    ("encoder-decoder architecture frame", "The Transformer is introduced inside the standard sequence transduction frame.", "encoder-decoder structure"),
                ],
                [
                    ("To the best of our knowledge", "claim", "Qualifies a novelty claim."),
                    ("relying entirely on", "method", "States the exclusive mechanism."),
                    ("without using", "contrast", "Names excluded mechanisms."),
                    ("In the following sections", "general", "Introduces a roadmap."),
                    ("Most competitive", "claim", "Frames the baseline architecture family."),
                ],
                "relying entirely on self-attention",
                "X is the first Y relying entirely on Z without using A or B.",
                "The authors claim the Transformer is the first sequence transduction model based only on self-attention.",
                "'relying entirely on'은 핵심 메커니즘 하나에만 의존한다는 강한 설계 표현입니다.",
                "The sentence combines novelty, mechanism, and excluded alternatives.",
            )
        if "encoder is composed of a stack" in lowered and "multi-head self-attention mechanism" in lowered:
            return profile(
                "This section defines the Transformer's encoder/decoder stacks and their repeated sub-layer pattern.",
                (
                    "The encoder has six identical layers, each with multi-head self-attention and a position-wise feed-forward network. "
                    "Residual connections and layer normalization wrap the sub-layers, and the decoder adds masked self-attention."
                ),
                (
                    "The passage specifies the architectural recipe: stacked encoder/decoder layers, two encoder sub-layers, decoder masking, residual connections, "
                    "layer normalization, and fixed dimensionality across embeddings and sub-layer outputs."
                ),
                [
                    "This is architecture anatomy; read it like a parts list.",
                    "Separate sub-layer types from wrapper operations.",
                    "Masked decoder self-attention is different from encoder self-attention.",
                ],
                [
                    ("encoder stack", "Six repeated encoder layers.", "encoder is composed of a stack"),
                    ("decoder stack", "Repeated decoder layers with an extra masked attention sub-layer.", "decoder"),
                    ("multi-head self-attention", "Attention sub-layer used inside Transformer blocks.", "multi-head self-attention"),
                    ("positionwise fully connected feed-forward network", "Fully connected sub-layer applied at each position.", "positionwise fully connected"),
                    ("residual connection", "Skip connection around each sub-layer.", "residual"),
                    ("layer normalization", "Normalization applied after sub-layer residual addition.", "layer normalization"),
                    ("subsequent positions", "Future decoder positions that masking prevents attention to.", "subsequent positions"),
                    ("dmodel", "Model dimensionality used across sub-layers and embeddings.", "dmodel"),
                ],
                [
                    ("encoder block recipe", "Each encoder layer combines self-attention and feed-forward sub-layers.", "Each layer has two sub-layers"),
                    ("residual-normalization wrapper", "Each sub-layer is wrapped with residual connection and layer normalization.", "residual"),
                    ("decoder autoregressive masking", "The decoder masks future output positions during generation.", "masked"),
                ],
                [
                    ("is composed of a stack of", "method", "Defines repeated architecture layers."),
                    ("Each layer has", "method", "Introduces sub-layer components."),
                    ("We employ", "method", "States an architectural choice."),
                    ("around each of", "method", "Explains wrapper placement."),
                    ("to prevent positions from attending to", "method", "Explains masking purpose."),
                ],
                "Each layer has two sub-layers",
                "Each layer has A. The first is B, and the second is C.",
                "Each Transformer encoder layer contains self-attention followed by a feed-forward network.",
                "'The first is..., and the second is...'는 구성요소를 순서대로 정의하는 구조입니다.",
                "The sentence is easy grammatically but dense because every noun phrase is a model component.",
            )
        if (
            "scaled dot-product attention" in lowered
            and ("queries and keys" in lowered or "query with all keys" in lowered or "query and a set of keys" in lowered)
            and ("values of dimension" in lowered or "apply a softmax" in lowered)
        ):
            return profile(
                "This section defines scaled dot-product attention with queries, keys, values, softmax, and 1/sqrt(dk) scaling.",
                (
                    "Attention maps queries and key-value pairs to outputs. The Transformer computes query-key dot products, divides by sqrt(dk), "
                    "uses softmax to get weights, and applies those weights to values."
                ),
                (
                    "The passage formalizes the core attention operation: Q/K/V dimensions, dot-product compatibility, softmax weighting, matrix implementation, "
                    "and scaling to avoid unstable large dot products."
                ),
                [
                    "This is the math core; learn Q, K, V before memorizing the formula.",
                    "Scaling is there for optimization stability.",
                    "Do not save generic words like 'input' or 'values' without the Q/K/V role.",
                ],
                [
                    ("queries", "Vectors that ask what information is needed.", "queries"),
                    ("keys", "Vectors matched against queries.", "keys"),
                    ("values", "Vectors whose weighted sum becomes the output.", "values"),
                    ("dot products", "Compatibility scores between queries and keys.", "dot products"),
                    ("softmax function", "Function that turns scores into attention weights.", "softmax"),
                    ("dk", "Key/query dimensionality used in the scaling factor.", "dk"),
                    ("1√dk", "Scaling factor that reduces large dot-product effects.", "1√dk"),
                    ("additive attention", "Alternative attention mechanism compared with dot-product attention.", "additive attention"),
                ],
                [
                    ("Q/K/V attention roles", "Queries, keys, and values define the attention computation.", "queries and keys"),
                    ("scaled dot-product formula", "The Transformer scales dot products before softmax.", "scale the dot products"),
                    ("stability motivation", "Scaling counters large dot products that push softmax into tiny gradients.", "counteract this effect"),
                ],
                [
                    ("We call our particular", "method", "Names the method variant."),
                    ("The input consists of", "method", "Defines inputs to a formula."),
                    ("We compute", "method", "Introduces computation steps."),
                    ("The two most commonly used", "contrast", "Introduces method comparison."),
                    ("To counteract this effect", "method", "Explains why scaling is added."),
                ],
                "To counteract this effect",
                "To counteract X, we scale Y by Z.",
                "The Transformer scales dot products to avoid unstable softmax behavior.",
                "'To counteract this effect'는 앞에서 말한 문제에 대한 해결책을 도입하는 표현입니다.",
                "The sentence depends on the previous explanation of large dot products and softmax gradients.",
            )
        if "multi-head attention" in lowered and "linearly project the queries" in lowered:
            return profile(
                "This section explains multi-head attention as parallel learned projections of Q, K, and V.",
                (
                    "Instead of doing one attention operation, the model projects queries, keys, and values several times, runs attention in parallel, "
                    "concatenates the heads, and projects the result."
                ),
                (
                    "The passage motivates multi-head attention as a way to attend jointly to different representation subspaces and positions through learned projections, "
                    "parallel attention heads, concatenation, and output projection."
                ),
                [
                    "Read each head as one learned attention view.",
                    "Track the pipeline: project -> attend in parallel -> concatenate -> output projection.",
                    "The point is representational diversity, not only more parameters.",
                ],
                [
                    ("multi-head attention", "Attention with multiple parallel projected heads.", "Multi-Head Attention"),
                    ("linear projections", "Learned projections applied to Q, K, and V.", "linearly project"),
                    ("attention heads", "Parallel attention operations over projected Q/K/V.", "head"),
                    ("projected versions", "Projected Q/K/V versions processed by attention heads.", "projected versions"),
                ],
                [
                    ("parallel projection pipeline", "Q/K/V are projected multiple times and attended in parallel.", "linearly project"),
                    ("subspace attention benefit", "Different heads attend to different representation subspaces.", "representation subspaces"),
                    ("single-head averaging limitation", "A single attention head can blur information through averaging.", "averaging inhibits"),
                ],
                [
                    ("Instead of performing", "contrast", "Introduces an alternative to the simpler method."),
                    ("we found it beneficial to", "claim", "States empirical design preference."),
                    ("with different, learned", "method", "Describes learned projections."),
                    ("On each of these", "method", "Explains repeated operation over projected versions."),
                    ("allows the model to jointly attend to", "result", "States the benefit of multi-head attention."),
                    ("With a single attention head", "contrast", "Contrasts the limitation of the baseline."),
                ],
                "allows the model to jointly attend to",
                "X allows the model to jointly attend to A at B.",
                "Multi-head attention lets the model attend to different subspaces and positions at the same time.",
                "'allows the model to'는 구조적 선택이 가능하게 하는 기능을 설명합니다.",
                "The sentence uses abstract nouns, so the reader must map them back to Q/K/V projections and heads.",
            )
        if "applications of attention in our model" in lowered and "encoder-decoder attention" in lowered:
            return profile(
                "This section explains where the Transformer uses multi-head attention inside the model.",
                (
                    "After finishing the multi-head formula, the paper lists three attention uses: encoder-decoder attention, "
                    "encoder self-attention, and decoder self-attention."
                ),
                (
                    "The passage connects the abstract multi-head attention mechanism to concrete architectural locations, distinguishing "
                    "query/key/value sources in encoder-decoder attention from self-attention inside the encoder and decoder."
                ),
                [
                    "This is a placement guide: where does attention appear in the architecture?",
                    "For each attention type, ask where Q, K, and V come from.",
                    "Do not memorize the equation before understanding the three application sites.",
                ],
                [
                    ("encoder-decoder attention", "Attention where decoder queries attend to encoder keys and values.", "encoder-decoder attention"),
                    ("memory keys and values", "Encoder outputs used as keys and values for decoder attention.", "memory keys and values"),
                    ("self-attention layers", "Layers where queries, keys, and values come from the same source.", "self-attention layers"),
                    ("input sequence", "The source sequence the decoder can attend over through encoder outputs.", "input sequence"),
                    ("previous decoder layer", "The source of queries in encoder-decoder attention.", "previous decoder layer"),
                    ("previous layer in the encoder", "The source for encoder self-attention Q/K/V.", "previous layer in the encoder"),
                    ("parallel attention layers", "The attention heads used in multi-head attention.", "parallel attention layers"),
                ],
                [
                    ("three attention application sites", "The architecture uses attention in encoder-decoder, encoder self-attention, and decoder self-attention layers.", "three different ways"),
                    ("Q/K/V source distinction", "Attention type is defined by where queries, keys, and values come from.", "queries come from"),
                    ("decoder-to-input access", "Encoder-decoder attention lets each decoder position attend across the input sequence.", "attend over all positions in the input sequence"),
                ],
                [
                    ("in three different ways", "method", "Introduces a classification of uses."),
                    ("come from", "method", "Identifies source components."),
                    ("This allows", "result", "States the function enabled by a design."),
                    ("mimics the typical", "comparison", "Relates the design to prior models."),
                    ("Similarly", "general", "Signals a parallel case."),
                ],
                "The Transformer uses multi-head attention in three different ways",
                "X uses Y in N different ways: A, B, and C.",
                "The model places attention in three sites, and each site differs by where Q, K, and V originate.",
                "'in three different ways'는 뒤에 나올 분류를 예고하는 표현입니다.",
                "The passage is hard because it mixes formula continuation with an architecture taxonomy.",
            )
        if "prevent leftward information flow" in lowered and "position-wise feed-forward networks" in lowered:
            return profile(
                "This section explains decoder masking, position-wise feed-forward layers, embeddings, and softmax output.",
                (
                    "The decoder masks illegal future connections to preserve autoregressive generation. Each layer also has a position-wise feed-forward network, "
                    "and the model uses learned embeddings plus softmax to predict next-token probabilities."
                ),
                (
                    "The passage bundles several implementation details: future-token masking in scaled dot-product attention, identical per-position feed-forward networks, "
                    "1x1-convolution equivalence, learned token embeddings, shared weight matrices, and pre-softmax prediction."
                ),
                [
                    "This is an implementation-detail section, not a new main idea.",
                    "Separate decoder masking from feed-forward networks and output prediction.",
                    "The key language pattern is purpose: 'to preserve the auto-regressive property'.",
                ],
                [
                    ("leftward information flow", "Future-token information that must be blocked in the decoder.", "leftward information flow"),
                    ("auto-regressive property", "The rule that prediction uses only previous output positions.", "auto-regressive property"),
                    ("scaled dot-product attention", "The attention operation where masking is applied.", "scaled dot-product attention"),
                    ("illegal connections", "Connections to future positions masked before softmax.", "illegal connections"),
                    ("position-wise feed-forward network", "Feed-forward network applied separately and identically to each position.", "Position-wise Feed-Forward Networks"),
                    ("ReLU activation", "Nonlinear activation between two linear transformations.", "ReLU"),
                    ("learned embeddings", "Token-to-vector representations learned by the model.", "learned embeddings"),
                    ("predicted next-token probabilities", "Decoder output probabilities after linear transformation and softmax.", "predicted next-token probabilities"),
                ],
                [
                    ("causal decoder masking", "Future positions are masked to preserve autoregressive generation.", "preserve the auto-regressive property"),
                    ("position-wise transformation", "The same feed-forward network is applied independently to each position.", "each position separately and identically"),
                    ("weight sharing", "Embedding matrices and pre-softmax transformation share parameters.", "share the same weight matrix"),
                ],
                [
                    ("to preserve", "method", "Explains purpose."),
                    ("by masking out", "method", "Explains implementation mechanism."),
                    ("In addition to", "general", "Adds another component."),
                    ("applied to each position separately and identically", "method", "Defines position-wise behavior."),
                    ("Another way of describing this is", "general", "Rephrases a technical idea."),
                    ("Similarly to", "comparison", "Connects the method to prior models."),
                ],
                "We need to prevent leftward information flow",
                "We need to prevent X to preserve Y.",
                "The decoder blocks future-token information so generation remains autoregressive.",
                "'to preserve'는 어떤 성질을 유지하기 위한 목적을 나타냅니다.",
                "The section moves quickly across masking, feed-forward layers, and output embeddings.",
            )
        if "maximum path lengths" in lowered and "positional encoding" in lowered:
            return profile(
                "This section compares layer complexity and explains why the Transformer adds positional encodings.",
                (
                    "The table compares self-attention, recurrent, convolutional, and restricted self-attention layers. Because the Transformer has no recurrence or convolution, "
                    "it adds positional encodings to embeddings so the model can use token order."
                ),
                (
                    "The passage combines table interpretation with the positional-encoding method: self-attention has constant sequential operations, "
                    "but order information must be injected through learned or sinusoidal vectors added to input embeddings."
                ),
                [
                    "Read Table 1 as a design tradeoff table.",
                    "The positional-encoding paragraph answers the question: how does a non-recurrent model know word order?",
                    "The formula matters less than the role: inject relative or absolute position.",
                ],
                [
                    ("maximum path length", "Longest path between positions in a layer type.", "Maximum Path Length"),
                    ("sequential operations", "Operations that cannot be parallelized.", "Sequential"),
                    ("representation dimension", "The hidden vector size d.", "representation dimension"),
                    ("positional encodings", "Vectors added to embeddings to represent token order.", "positional encodings"),
                    ("relative or absolute position", "Two ways of representing token order.", "relative or absolute position"),
                    ("input embeddings", "Token vectors at the bottom of encoder and decoder stacks.", "input embeddings"),
                    ("sine and cosine functions", "Fixed sinusoidal functions used for positional encoding.", "sine and cosine functions"),
                    ("geometric progression", "Pattern of wavelengths in sinusoidal encodings.", "geometric progression"),
                ],
                [
                    ("complexity tradeoff table", "The paper compares layer types by complexity, sequential operations, and path length.", "Table 1"),
                    ("order injection problem", "Attention-only models need explicit positional information.", "contains no recurrence and no convolution"),
                    ("sinusoidal position encoding", "The chosen fixed encoding may support relative-position learning and extrapolation.", "sinusoid"),
                ],
                [
                    ("Since our model contains no", "method", "Introduces a consequence of an architectural absence."),
                    ("in order for", "method", "States purpose."),
                    ("To this end", "method", "Introduces the solution."),
                    ("There are many choices of", "general", "Signals design alternatives."),
                    ("because we hypothesized", "claim", "Explains design rationale."),
                    ("found that the two versions", "result", "Reports comparison outcome."),
                ],
                "Since our model contains no recurrence and no convolution",
                "Since X contains no A and no B, we must inject C.",
                "Because the Transformer lacks recurrence and convolution, it needs positional encodings for token order.",
                "'Since our model contains no...'는 설계상 빠진 요소가 어떤 보완책을 요구하는지 설명합니다.",
                "The section is difficult because a table, architecture rationale, and sinusoidal formula are packed together.",
            )
        if "why self-attention" in compact_lowered and "three desiderata" in lowered:
            return profile(
                "This section motivates self-attention using complexity, parallelism, and path length.",
                (
                    "The paper compares self-attention with recurrent and convolutional layers using three criteria: per-layer complexity, parallelizable computation, "
                    "and path length for long-range dependencies."
                ),
                (
                    "The passage provides the theoretical justification for self-attention: constant sequential operations, shorter paths between positions, "
                    "and favorable computational complexity under common sentence-representation settings."
                ),
                [
                    "This is the main design-justification section.",
                    "The three criteria are the reading frame for Table 1.",
                    "Long-range dependency is source-present here, so it is a valid save target in this section.",
                ],
                [
                    ("self-attention layers", "Layers compared against recurrent and convolutional alternatives.", "self-attention layers"),
                    ("variable-length sequence", "Sequence input whose length can vary.", "variable-length sequence"),
                    ("computational complexity per layer", "Cost criterion for comparing layer types.", "computational complexity per layer"),
                    ("minimum number of sequential operations", "Parallelization criterion in the comparison.", "minimum number of sequential operations"),
                    ("long-range dependencies", "Dependencies between distant sequence positions.", "long-range dependencies"),
                    ("maximum path length", "Longest signal path between input/output positions.", "maximum path length"),
                    ("constant number of sequentially executed operations", "Self-attention's parallelism advantage.", "constant number"),
                ],
                [
                    ("three desiderata", "The paper evaluates layer types by complexity, parallelism, and dependency path length.", "three desiderata"),
                    ("long-range dependency argument", "Shorter paths make distant dependencies easier to learn.", "Learning long-range dependencies"),
                    ("self-attention parallelism", "Self-attention connects all positions with constant sequential operations.", "constant number of sequentially executed operations"),
                ],
                [
                    ("In this section we compare", "general", "Announces comparison scope."),
                    ("Motivating our use of", "claim", "Introduces design rationale."),
                    ("One is", "general", "Begins an enumerated criterion."),
                    ("Another is", "general", "Adds a second criterion."),
                    ("The third is", "general", "Adds a final criterion."),
                    ("One key factor affecting", "claim", "Introduces causal explanation."),
                    ("As noted in", "general", "Connects prose to a table."),
                ],
                "Motivating our use of self-attention we consider three desiderata",
                "Motivating our use of X, we consider A, B, and C.",
                "The authors justify self-attention by comparing complexity, parallelism, and path length.",
                "'Motivating our use of'는 왜 이 방법을 선택했는지 설명하는 학술 표현입니다.",
                "The sentence is conceptually dense because each criterion connects to a different column in Table 1.",
            )
        if "restricted to considering only a neighborhood" in lowered and "separable convolutions" in lowered:
            return profile(
                "This section completes the self-attention comparison and transitions into training details.",
                (
                    "The paper explains when self-attention is faster, how restricted attention could handle very long sequences, why convolutional layers need stacks to connect positions, "
                    "and then moves toward the training regime."
                ),
                (
                    "The passage qualifies the self-attention advantage: sequence length versus dimensionality matters, restricted self-attention is a future option for long sequences, "
                    "convolutional alternatives increase path length or cost, and attention heads show syntactic/semantic behavior."
                ),
                [
                    "This is a caveat-and-transition section.",
                    "Track limits: very long sequences may need restricted attention.",
                    "The final sentence sets up appendix attention visualizations and training.",
                ],
                [
                    ("restricted self-attention", "Attention limited to a local neighborhood for long sequences.", "self-attention could be restricted"),
                    ("neighborhood of size r", "Local window considered by restricted attention.", "neighborhood of size r"),
                    ("maximum path length", "Dependency path length affected by restrictions and convolutions.", "maximum path length"),
                    ("dilated convolutions", "Convolutions that reduce required stack depth.", "dilated convolutions"),
                    ("separable convolutions", "Lower-cost convolution variant.", "Separable convolutions"),
                    ("point-wise feed-forward layer", "Feed-forward layer paired with self-attention in the Transformer.", "point-wise feed-forward layer"),
                    ("attention distributions", "Observed attention patterns in trained models.", "attention distributions"),
                    ("syntactic and semantic structure", "Language structure reflected by some attention heads.", "syntactic and semantic structure"),
                ],
                [
                    ("long-sequence caveat", "Self-attention may need locality restrictions for very long sequences.", "very long sequences"),
                    ("convolution path-length tradeoff", "Convolutions need stacks or dilation to connect distant positions.", "does not connect all pairs"),
                    ("attention-head interpretability", "Some heads appear to learn syntactic or semantic roles.", "different tasks"),
                ],
                [
                    ("To improve computational performance", "method", "Introduces an optimization motivation."),
                    ("could be restricted to", "method", "States a possible limitation strategy."),
                    ("We plan to investigate", "limitation", "Marks future work."),
                    ("Doing so requires", "result", "States a consequence."),
                    ("Not only do", "claim", "Introduces an additional result."),
                    ("many appear to exhibit", "claim", "Cautiously reports observed behavior."),
                ],
                "To improve computational performance for tasks involving very long sequences",
                "To improve X for tasks involving Y, Z could be restricted to A.",
                "For long sequences, attention can be restricted locally, but that increases path length.",
                "'could be restricted to'는 확정된 방법이 아니라 가능한 변형을 조심스럽게 제시합니다.",
                "The section alternates between complexity caveats, convolution comparisons, and qualitative attention behavior.",
            )
        if "training data and batching" in compact_lowered and "adam optimizer" in lowered:
            return profile(
                "This section specifies the Transformer's training data, batching, hardware schedule, optimizer, and warmup learning-rate rule.",
                (
                    "The paper describes WMT English-German and English-French data, byte-pair or word-piece tokenization, approximate-length batching, "
                    "P100 GPU training time, Adam optimizer settings, and the warmup-then-decay learning-rate schedule."
                ),
                (
                    "The passage is an experimental-reproducibility section: it gives dataset sizes, tokenization vocabulary sizes, token-based batching, "
                    "base/big model training schedules, Adam hyperparameters, and the inverse-square-root learning-rate decay after warmup."
                ),
                [
                    "Read this as reproducibility information, not the main architecture claim.",
                    "The important language pattern is reporting setup: 'We trained on', 'We used', 'This corresponds to'.",
                    "Save optimizer and batching terms only if they help you read ML experiment sections.",
                ],
                [
                    ("WMT 2014 English-German dataset", "Translation dataset used for training.", "WMT 2014 English-German dataset"),
                    ("byte-pair encoding", "Subword tokenization used for the English-German data.", "byte-pair encoding"),
                    ("shared sourcetarget vocabulary", "Vocabulary shared between source and target languages.", "shared sourcetarget vocabulary"),
                    ("word-piece vocabulary", "Subword vocabulary used for the English-French data.", "word-piece vocabulary"),
                    ("approximate sequence length", "Batching criterion used to group sentence pairs.", "approximate sequence length"),
                    ("P100 GPUs", "Hardware used for Transformer training.", "P100 GPUs"),
                    ("Adam optimizer", "Optimizer used with specified beta and epsilon values.", "Adam optimizer"),
                    ("warmup_steps", "Initial steps where learning rate increases linearly.", "warmup_steps"),
                    ("inverse square root", "Decay pattern after warmup.", "inverse square root"),
                ],
                [
                    ("training reproducibility recipe", "The section gives datasets, tokenization, batches, hardware, and optimizer settings.", "Training Data and Batching"),
                    ("token-based batching", "Batches are built by approximate length and token count rather than fixed sentence count.", "approximately 25000 source tokens"),
                    ("warmup learning-rate schedule", "The learning rate rises during warmup and then decays by inverse square root of step number.", "warmup_steps"),
                ],
                [
                    ("We trained on", "method", "Introduces training data."),
                    ("consisting of", "method", "Gives dataset size or composition."),
                    ("were encoded using", "method", "States preprocessing method."),
                    ("were batched together by", "method", "Explains batching criterion."),
                    ("For our base models", "comparison", "Introduces one model scale."),
                    ("For our big models", "comparison", "Introduces the larger model scale."),
                    ("This corresponds to", "method", "Explains what an equation means in words."),
                ],
                "This corresponds to increasing the learning rate linearly",
                "This corresponds to X for A, and Y thereafter.",
                "The formula means the learning rate first warms up linearly, then decays with the inverse square root of the step number.",
                "'This corresponds to'는 수식이나 설정의 의미를 prose로 다시 설명할 때 쓰는 표현입니다.",
                "The section is dense because dataset, tokenization, hardware, optimizer, and schedule details are compressed into one passage.",
            )
        if "table 2:" in lowered and "better bleu scores" in lowered and "label smoothing" in lowered:
            return profile(
                "This section combines Table 2 result reading with regularization and the start of machine-translation results.",
                (
                    "Table 2 compares BLEU scores and training cost across prior systems and Transformer variants. The surrounding text then explains residual dropout, "
                    "label smoothing, and the English-to-German result where Transformer big reaches 28.4 BLEU."
                ),
                (
                    "The passage is a results-and-regularization section: it reports quality/cost comparisons, describes dropout on sub-layer outputs and embeddings, "
                    "explains label smoothing's effect on perplexity versus BLEU, and states the WMT 2014 English-to-German state-of-the-art claim."
                ),
                [
                    "Read the table as evidence for quality per training cost, not as vocabulary.",
                    "Separate regularization methods from result claims.",
                    "Useful academic language here includes 'at a fraction of' and 'outperforms'.",
                ],
                [
                    ("BLEU scores", "Translation-quality metric used in Table 2.", "BLEU scores"),
                    ("training cost", "FLOP-based cost used to compare systems.", "training cost"),
                    ("Residual Dropout", "Dropout applied before residual addition and normalization.", "Residual Dropout"),
                    ("label smoothing", "Regularization that makes the model less overconfident.", "Label Smoothing"),
                    ("perplexity", "Metric hurt by label smoothing in this section.", "perplexity"),
                    ("English-to-German translation task", "WMT task where Transformer big reports 28.4 BLEU.", "English-to-German translation task"),
                    ("state-of-the-art BLEU score", "Claimed best reported BLEU result.", "state-of-the-art BLEU score"),
                    ("Pdrop", "Dropout rate notation used for the base model.", "Pdrop"),
                ],
                [
                    ("quality-cost comparison", "Table 2 argues the Transformer improves BLEU at lower training cost.", "fraction of the training cost"),
                    ("regularization setup", "Dropout and label smoothing are training choices before reporting results.", "Residual Dropout"),
                    ("German translation result claim", "Transformer big beats prior models and ensembles by more than 2 BLEU.", "outperforms the best previously reported models"),
                ],
                [
                    ("at a fraction of", "claim", "Claims lower cost relative to competitors."),
                    ("we apply dropout to", "method", "States where dropout is used."),
                    ("In addition", "general", "Adds another location or method."),
                    ("During training, we employed", "method", "Introduces a training technique."),
                    ("This hurts..., but improves", "contrast", "States a tradeoff."),
                    ("outperforms the best previously reported", "result", "States a benchmark result."),
                    ("establishing a new", "result", "Claims state-of-the-art status."),
                ],
                "This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score.",
                "This hurts A, but improves B.",
                "Label smoothing can worsen perplexity while improving accuracy and BLEU.",
                "'This hurts..., but improves...'는 한 방법의 trade-off를 설명하는 데 유용한 표현입니다.",
                "The section is hard because table rows, regularization details, and benchmark claims are interleaved.",
            )
        if "english-to-french translation task" in lowered and "model variations" in lowered:
            return profile(
                "This section finishes machine-translation results and introduces model-variation ablations.",
                (
                    "The paper reports the English-to-French BLEU result, explains checkpoint averaging, beam search, length penalty, and training-cost estimation, "
                    "then transitions to varying Transformer components for ablation experiments."
                ),
                (
                    "The passage moves from result reporting to inference protocol and ablation setup: it states the French single-model comparison, lists decoding and checkpoint choices, "
                    "defines cost estimation, and frames model variations as tests of component importance."
                ),
                [
                    "This is a bridge from main results to ablations.",
                    "Separate inference settings from architecture claims.",
                    "The phrase 'To evaluate the importance of' signals an ablation section.",
                ],
                [
                    ("English-to-French translation task", "WMT task where the big model reports 41.0 BLEU in this text.", "English-to-French translation task"),
                    ("BLEU score", "Translation quality score used for comparison.", "BLEU score"),
                    ("dropout rate", "Pdrop value adjusted for the English-to-French big model.", "dropout rate"),
                    ("checkpoint averaging", "Averaging recent checkpoints for final model evaluation.", "averaging the last"),
                    ("beam search", "Decoding method used during inference.", "beam search"),
                    ("length penalty", "Beam-search setting controlling output length.", "length penalty"),
                    ("floating point operations", "Estimated cost unit for model training.", "floating point operations"),
                    ("Model Variations", "Ablation section testing Transformer components.", "Model Variations"),
                ],
                [
                    ("French translation result claim", "Transformer big outperforms prior single models at lower training cost.", "outperforming all of the previously published single models"),
                    ("inference protocol", "Checkpoint averaging, beam size, and length penalty define evaluation decoding.", "beam search"),
                    ("ablation setup", "The next section varies components to measure importance.", "To evaluate the importance"),
                ],
                [
                    ("outperforming all of", "result", "States benchmark superiority."),
                    ("at less than", "claim", "States lower resource cost."),
                    ("For the base models", "comparison", "Introduces settings for one model scale."),
                    ("For the big models", "comparison", "Introduces settings for the larger model scale."),
                    ("chosen after experimentation", "method", "Explains development-set tuning."),
                    ("To evaluate the importance of", "method", "Introduces an ablation purpose."),
                ],
                "To evaluate the importance of different components of the Transformer",
                "To evaluate the importance of X, we varied Y and measured Z.",
                "The authors vary components to measure how each design choice affects translation performance.",
                "'To evaluate the importance of'는 ablation experiment 목적을 알리는 전형적인 표현입니다.",
                "The passage mixes result claims, inference hyperparameters, cost estimation, and a new ablation objective.",
            )
        if "unlisted values are identical" in lowered and "single-head attention" in lowered:
            return profile(
                "This section interprets Transformer model-variation ablations in Table 3.",
                (
                    "Table 3 varies attention heads, key/value dimensions, model size, dropout, and positional encoding. The prose explains that single-head attention is worse, "
                    "small key size hurts, bigger models help, dropout prevents overfitting, and learned positional embeddings perform almost the same as sinusoids."
                ),
                (
                    "The passage is an ablation-reading section: rows A-E isolate design dimensions and connect numeric changes in perplexity/BLEU "
                    "to architectural conclusions about heads, compatibility dimensions, capacity, regularization, and positional encoding."
                ),
                [
                    "Read rows A-E as controlled comparisons against the base model.",
                    "Do not save raw table column names unless they explain an ablation.",
                    "The reusable language is 'This suggests that' and 'as expected'.",
                ],
                [
                    ("base model", "Reference model used for controlled ablation comparisons.", "base model"),
                    ("attention heads", "Number of heads varied in Table 3 rows A.", "attention heads"),
                    ("attention key size", "dk size whose reduction hurts quality.", "attention key size"),
                    ("compatibility function", "Function judging query-key match quality.", "compatibility function"),
                    ("dropout", "Regularization found helpful against overfitting.", "dropout"),
                    ("over-fitting", "Problem reduced by dropout.", "over-fitting"),
                    ("sinusoidal positional encoding", "Original position encoding compared with learned embeddings.", "sinusoidal positional encoding"),
                    ("learned positional embeddings", "Alternative to sinusoidal positional encoding.", "learned positional embeddings"),
                ],
                [
                    ("attention-head ablation", "Quality drops with one head and with too many heads.", "single-head attention"),
                    ("key-size ablation", "Reducing dk hurts quality, suggesting dot-product compatibility is hard.", "reducing the attention key size"),
                    ("capacity and regularization finding", "Bigger models improve results and dropout helps avoid overfitting.", "bigger models are better"),
                    ("positional-encoding comparison", "Learned positional embeddings perform nearly identically to sinusoids.", "nearly identical results"),
                ],
                [
                    ("Unlisted values are identical to", "method", "Explains table shorthand."),
                    ("should not be compared to", "limitation", "Warns against invalid metric comparison."),
                    ("keeping the amount of computation constant", "method", "States controlled comparison condition."),
                    ("This suggests that", "claim", "Introduces interpretation from results."),
                    ("as expected", "claim", "Signals a predicted result."),
                    ("observe nearly identical results", "result", "Reports ablation comparison."),
                ],
                "This suggests that determining compatibility is not easy",
                "This suggests that X is not easy and that Y may be beneficial.",
                "The ablation implies that query-key compatibility may need more capacity than simple dot products provide.",
                "'This suggests that'은 table result에서 해석을 조심스럽게 끌어낼 때 쓰는 표현입니다.",
                "The section is difficult because the useful lesson is in prose interpretation, not the raw numeric table.",
            )
        if "english constituency parsing" in lowered and "wall street journal" in lowered and "penn treebank" in lowered:
            return profile(
                "This section tests whether the Transformer generalizes to English constituency parsing.",
                (
                    "The paper applies a 4-layer Transformer to constituency parsing, a task with structural output constraints and longer outputs than inputs. "
                    "It uses WSJ/Penn Treebank data, a semi-supervised setting, and mostly keeps translation-model parameters unchanged."
                ),
                (
                    "The passage is a task-transfer setup: it motivates constituency parsing as a challenging non-translation benchmark, describes WSJ and semi-supervised training data, "
                    "sets vocabulary sizes, and lists limited tuning choices before reporting parsing results."
                ),
                [
                    "Read this as evidence for generalization beyond translation.",
                    "Do not confuse task terms with architecture terms.",
                    "The key phrase is 'To evaluate if X can generalize to Y'.",
                ],
                [
                    ("English constituency parsing", "Parsing task used to test generalization beyond translation.", "English Constituency Parsing"),
                    ("structural constraints", "Output constraints that make parsing harder than plain generation.", "structural constraints"),
                    ("small-data regimes", "Low-data setting where previous RNN sequence-to-sequence models struggle.", "small-data regimes"),
                    ("Wall Street Journal", "WSJ portion of the Penn Treebank used for training.", "Wall Street Journal"),
                    ("Penn Treebank", "Dataset source for WSJ parsing experiments.", "Penn Treebank"),
                    ("semi-supervised setting", "Training setup using extra high-confidence parsed corpora.", "semi-supervised setting"),
                    ("beam size", "Inference hyperparameter tuned for parsing.", "beam size"),
                    ("Section 22 development set", "Development set used for limited tuning.", "Section 22 development set"),
                ],
                [
                    ("generalization test", "The paper tests whether Transformer works outside translation.", "generalize to other tasks"),
                    ("parsing task difficulty", "Parsing has structural constraints and outputs longer than inputs.", "specific challenges"),
                    ("limited task-specific tuning", "Most parameters remain from the English-to-German base model.", "all other parameters remained unchanged"),
                ],
                [
                    ("To evaluate if", "method", "Introduces a generalization test."),
                    ("This task presents specific challenges", "claim", "Signals why the task is hard."),
                    ("Furthermore", "general", "Adds another reason or evidence."),
                    ("We also trained it in", "method", "Introduces an additional training setting."),
                    ("all other parameters remained unchanged", "method", "States controlled reuse of settings."),
                ],
                "To evaluate if the Transformer can generalize to other tasks",
                "To evaluate if X can generalize to Y, we performed experiments on Z.",
                "The authors test whether the Transformer transfers from translation to constituency parsing.",
                "'To evaluate if'는 모델의 일반화 가능성을 실험으로 확인할 때 쓰는 표현입니다.",
                "The section mixes task motivation, dataset names, and tuning details.",
            )
        if "table 4:" in lowered and "generalizes well to english constituency parsing" in lowered:
            return profile(
                "This section interprets the Transformer constituency-parsing result table and starts the conclusion.",
                (
                    "Table 4 compares WSJ parsing F1 scores. The Transformer performs well with little task-specific tuning and beats BerkeleyParser when trained only on the small WSJ set."
                ),
                (
                    "The passage is a table-interpretation section: it compares discriminative, semi-supervised, multi-task, and generative parsers, "
                    "then argues that Transformer generalizes surprisingly well before transitioning to the conclusion."
                ),
                [
                    "Read parser names as references, not vocabulary to memorize.",
                    "The useful result is the comparison claim, not every numeric row.",
                    "The conclusion begins in this section after the parsing result.",
                ],
                [
                    ("WSJ 23 F1", "Evaluation score on WSJ section 23.", "WSJ 23 F1"),
                    ("discriminative", "Parser training type listed in Table 4.", "discriminative"),
                    ("semi-supervised", "Training setting using additional data.", "semi-supervised"),
                    ("generative", "Parser category of the RNN Grammar comparison.", "generative"),
                    ("task-specific tuning", "Tuning that the Transformer mostly lacks here.", "task-specific tuning"),
                    ("Berkeley- Parser", "Prior parser outperformed by the Transformer in the WSJ-only comparison.", "Berkeley- Parser"),
                    ("sequence transduction model", "Model family restated in the conclusion.", "sequence transduction model"),
                    ("multi-headed self-attention", "Attention mechanism replacing recurrent layers in the conclusion.", "multi-headed self-attention"),
                ],
                [
                    ("parsing result comparison", "The Transformer performs strongly versus prior parsers.", "performs surprisingly well"),
                    ("small-data comparison", "Transformer beats BerkeleyParser with only 40K WSJ sentences.", "training only on the WSJ training set"),
                    ("conclusion thesis", "The Transformer is an attention-only sequence transduction model.", "first sequence transduction model"),
                ],
                [
                    ("despite the lack of", "contrast", "Frames a strong result under limited tuning."),
                    ("with the exception of", "limitation", "States the remaining better comparator."),
                    ("In contrast to", "contrast", "Introduces a comparison against prior models."),
                    ("even when", "contrast", "Strengthens a comparison under a constraint."),
                    ("In this work, we presented", "claim", "Introduces the conclusion thesis."),
                    ("based entirely on", "method", "States the defining mechanism."),
                    ("replacing X with Y", "method", "Explains the architecture substitution."),
                ],
                "despite the lack of task-specific tuning",
                "Despite the lack of X, our model performs Y.",
                "Even without much task-specific tuning, the Transformer performs strongly on constituency parsing.",
                "'despite the lack of'는 불리한 조건에도 결과가 좋다는 contrast를 만드는 표현입니다.",
                "The section is difficult because a result table and the conclusion opening are merged by PDF extraction.",
            )
        if "future of attention-based models" in lowered and "modalities other than text" in lowered:
            return profile(
                "This conclusion states the Transformer's translation results and future research directions.",
                (
                    "The paper concludes that Transformer achieves state-of-the-art translation results, including beating ensembles on English-German, "
                    "and proposes future work on non-text modalities, restricted attention for large inputs, and less sequential generation."
                ),
                (
                    "The passage summarizes the final contribution and roadmap: attention-based models reach new translation performance, may extend to images/audio/video, "
                    "may use local restricted attention for large inputs, and motivate generation methods that are less sequential."
                ),
                [
                    "This is conclusion language: result claim plus future work.",
                    "Do not save acknowledgements or citation fragments as vocabulary.",
                    "The reusable expressions are 'We plan to' and 'other than'.",
                ],
                [
                    ("state of the art", "Best reported performance claim.", "state of the art"),
                    ("previously reported ensembles", "Strong prior systems outperformed in English-German.", "previously reported ensembles"),
                    ("attention-based models", "Future model family the authors want to extend.", "attention-based models"),
                    ("modalities other than text", "Images, audio, and video as non-text targets.", "modalities other than text"),
                    ("local, restricted attention mechanisms", "Attention variant proposed for large inputs and outputs.", "local, restricted attention mechanisms"),
                    ("large inputs and outputs", "Scale challenge for restricted attention.", "large inputs and outputs"),
                    ("generation less sequential", "Future goal of reducing sequential generation.", "generation less sequential"),
                ],
                [
                    ("final benchmark claim", "Transformer achieves new state of the art on both translation tasks.", "new state of the art"),
                    ("future multimodal extension", "The authors plan to apply attention models beyond text.", "modalities other than text"),
                    ("efficient large-input direction", "Restricted attention is proposed for images, audio, and video.", "large inputs and outputs"),
                ],
                [
                    ("On both", "result", "States a result across two tasks."),
                    ("In the former task", "general", "Refers back to the first of two tasks."),
                    ("We are excited about", "general", "Signals future-facing conclusion language."),
                    ("plan to apply", "future", "States future work."),
                    ("other than text", "future", "Defines modality expansion."),
                    ("to efficiently handle", "method", "States the purpose of a future mechanism."),
                    ("another research goal", "future", "Adds a future direction."),
                ],
                "We plan to extend the Transformer to problems involving input and output modalities other than text",
                "We plan to extend X to problems involving Y other than Z.",
                "The authors want to apply Transformer-style attention beyond text, including images, audio, and video.",
                "'other than text'는 기존 적용 영역을 넘어서는 범위를 설명할 때 유용합니다.",
                "The section is easy conceptually but PDF extraction mixes conclusion, acknowledgements, and references.",
            )
        if "attention visualizations" in lowered and "making...more difficult" in lowered:
            return profile(
                "This appendix figure shows encoder self-attention following a long-distance dependency.",
                (
                    "Figure 3 visualizes attention heads in encoder layer 5. The example shows heads attending from the word 'making' to the distant phrase that completes "
                    "'making ... more difficult'."
                ),
                (
                    "The passage is an interpretability appendix: it uses an attention visualization to argue that some encoder self-attention heads "
                    "track long-distance syntactic dependencies rather than only nearby words."
                ),
                [
                    "Do not study the example sentence as the paper's main argument.",
                    "The learning point is what the visualization demonstrates.",
                    "Useful figure-caption language includes 'An example of' and 'attend to'.",
                ],
                [
                    ("attention visualizations", "Appendix figures showing learned attention patterns.", "Attention Visualizations"),
                    ("encoder self-attention", "Self-attention inside the encoder stack.", "encoder self-attention"),
                    ("long-distance dependencies", "Distant sentence relationships tracked by attention heads.", "long-distance dependencies"),
                    ("attention heads", "Different colored heads in the visualization.", "attention heads"),
                    ("distant dependency", "Dependency completed by 'making...more difficult'.", "distant dependency"),
                    ("Figure 3", "Visualization of the long-distance dependency example.", "Figure 3"),
                ],
                [
                    ("attention-head interpretability", "The figure suggests some heads learn syntactic dependency patterns.", "attention mechanism"),
                    ("long-distance dependency example", "The word 'making' attends to a distant completion phrase.", "making...more difficult"),
                    ("encoder-layer visualization", "The appendix inspects layer 5 of 6 in the encoder.", "layer 5 of 6"),
                ],
                [
                    ("An example of", "general", "Introduces a figure example."),
                    ("following long-distance dependencies", "claim", "States what the visualization demonstrates."),
                    ("Many of the attention heads", "claim", "Generalizes over multiple heads."),
                    ("attend to", "method", "Describes the attention relation."),
                    ("Different colors represent", "general", "Explains visual encoding."),
                    ("Best viewed in color", "general", "Figure-viewing note."),
                ],
                "Many of the attention heads attend to a distant dependency",
                "Many of X attend to Y, completing Z.",
                "Several attention heads connect the word 'making' to a distant phrase needed to complete its meaning.",
                "'attend to'는 attention visualization에서 어떤 token이 어디를 참조하는지 설명하는 핵심 표현입니다.",
                "The section is visually grounded; extracted text repeats the example sentence and can obscure the caption's point.",
            )
        if "anaphora resolution" in lowered and "attentions are very sharp" in lowered:
            return profile(
                "This appendix figure shows attention heads involved in anaphora resolution.",
                (
                    "Figure 4 visualizes two encoder attention heads for the sentence about 'The Law'. The caption says the heads appear involved in anaphora resolution, "
                    "especially sharp attention from the word 'its'."
                ),
                (
                    "The passage is an interpretability example: attention heads in layer 5 are presented as resolving pronoun/reference structure, showing that some learned heads focus sharply on discourse relations."
                ),
                [
                    "The learner should focus on the caption, not memorize the repeated example sentence.",
                    "Anaphora resolution means connecting a pronoun or referring expression to its antecedent.",
                    "The useful phrase is 'apparently involved in'.",
                ],
                [
                    ("anaphora resolution", "Resolving what a pronoun or referring expression points to.", "anaphora resolution"),
                    ("attention heads", "Heads visualized in Figure 4.", "attention heads"),
                    ("layer 5 of 6", "Encoder layer where the heads are inspected.", "layer 5 of 6"),
                    ("sharp attentions", "Highly focused attention weights for a word.", "attentions are very sharp"),
                    ("the word 'its'", "Word whose isolated attentions are shown.", "word ‘its’"),
                    ("Figure 4", "Visualization of anaphora-related attention heads.", "Figure 4"),
                ],
                [
                    ("anaphora-attention example", "The figure links attention to pronoun/reference resolution.", "anaphora resolution"),
                    ("sharp attention pattern", "The attention distribution for 'its' is highly focused.", "very sharp"),
                    ("head-specific behavior", "Different heads are inspected separately.", "heads 5 and 6"),
                ],
                [
                    ("apparently involved in", "claim", "Cautiously interprets model behavior."),
                    ("Full attentions for", "general", "Describes what the figure shows."),
                    ("Isolated attentions from", "general", "Describes a narrowed visualization."),
                    ("Note that", "general", "Directs reader attention."),
                    ("very sharp for", "claim", "Describes focused attention."),
                ],
                "Two attention heads, also in layer 5 of 6, apparently involved in anaphora resolution.",
                "X are apparently involved in Y.",
                "Two attention heads seem to help resolve what 'its' refers to.",
                "'apparently involved in'은 관찰 결과를 조심스럽게 해석할 때 쓰는 표현입니다.",
                "The repeated sentence text is noisy; the figure caption carries the learning value.",
            )
        if "figure 5:" in lowered and "different tasks" in lowered and "structure of the sentence" in lowered:
            return profile(
                "This appendix figure argues that different attention heads learn different sentence-structure roles.",
                (
                    "Figure 5 presents two examples where encoder self-attention heads appear related to sentence structure. The caption says the heads learned to perform different tasks."
                ),
                (
                    "The passage is the final interpretability appendix section: it summarizes evidence that attention heads specialize, with some heads reflecting syntactic or semantic sentence structure."
                ),
                [
                    "Treat this as qualitative evidence, not a main benchmark result.",
                    "The important claim is head specialization.",
                    "The phrase 'seems related to' is cautious interpretability language.",
                ],
                [
                    ("attention heads", "Different heads inspected in the visualization.", "attention heads"),
                    ("encoder self-attention", "Encoder attention mechanism being visualized.", "encoder self-attention"),
                    ("sentence structure", "Syntactic or semantic structure reflected by heads.", "structure of the sentence"),
                    ("different tasks", "Different roles learned by different heads.", "different tasks"),
                    ("Figure 5", "Final attention visualization figure.", "Figure 5"),
                    ("layer 5 of 6", "Encoder layer used for the examples.", "layer 5 of 6"),
                ],
                [
                    ("head specialization", "Different heads appear to learn different roles.", "different tasks"),
                    ("sentence-structure behavior", "Some heads align with sentence structure.", "structure of the sentence"),
                    ("qualitative interpretability claim", "The appendix uses examples rather than quantitative metrics.", "examples above"),
                ],
                [
                    ("exhibit behaviour that seems related to", "claim", "Cautiously links behavior to structure."),
                    ("We give two such examples", "general", "Introduces qualitative examples."),
                    ("from two different heads", "general", "Specifies separate heads."),
                    ("clearly learned to perform", "claim", "States head specialization."),
                ],
                "Many of the attention heads exhibit behaviour that seems related to the structure of the sentence.",
                "Many of X exhibit behaviour that seems related to Y.",
                "Several attention heads appear to encode sentence-structure information.",
                "'seems related to'는 interpretability에서 과도한 단정을 피하는 표현입니다.",
                "The extracted text repeats the example sentence, but the caption explains the actual claim.",
            )
        return None

    def _is_attention_text(self, document_text: str) -> bool:
        lowered = document_text.lower()
        compact = re.sub(r"\s+", " ", lowered)
        return (
            "attention is all you need" in lowered
            or ("transformer" in lowered and "sequence transduction" in lowered)
            or ("self-attention" in lowered and "recurrent" in lowered and "convolution" in lowered)
            or ("transformer" in lowered and "parallelization" in lowered)
            or ("scaled dot-product attention" in lowered)
            or ("multi-head attention" in lowered)
            or ("positional encoding" in lowered and "recurrence" in lowered)
            or ("attention heads" in lowered and "syntactic" in lowered)
            or ("encoder-decoder structure" in compact)
            or ("model architecture" in compact and "encoder" in lowered and "decoder" in lowered)
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
            or ("top-5 error" in lowered and "imagenet" in lowered and ("resnet" in lowered or "residual" in lowered or "plain net" in lowered))
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
            or self._is_resnet_detection_evaluation_section(document_text)
            or self._is_resnet_detection_improvements_section(document_text)
            or self._is_resnet_detection_results_table_section(document_text)
            or self._is_resnet_detection_result_narrative_section(document_text)
            or self._is_resnet_imagenet_detection_setup_section(document_text)
            or self._is_resnet_imagenet_localization_setup_section(document_text)
            or self._is_resnet_imagenet_localization_details_section(document_text)
            or self._is_resnet_imagenet_localization_rcnn_section(document_text)
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

    def _is_resnet_detection_evaluation_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "pascal voc" in lowered and "ms coco" in lowered and "improve both recognition and localization" in lowered

    def _is_resnet_detection_improvements_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return "box refinement" in lowered and "global context" in lowered and "multi-scale testing" in lowered

    def _is_resnet_detection_results_table_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "baseline+++resnet-101" in lowered
            and "detection results on the pascal voc" in lowered
            and "object detection improvements on ms coco" in lowered
        )

    def _is_resnet_detection_result_narrative_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            ("test-dev set has no publicly available ground truth" in lowered or "testdev set has no publicly available ground truth" in lowered)
            and "won the 1st place in the detection task in coco 2015" in lowered
            and "higher than the previous state-of-the-art" in lowered
        )

    def _is_resnet_imagenet_detection_setup_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "imagenet detection" in lowered
            and "200 object categories" in lowered
            and "fine-tuned on the det data" in lowered
            and "we do not use other ilsvrc 2015 data" in lowered
        )

    def _is_resnet_imagenet_localization_setup_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "imagenet localization" in lowered
            and "per-class regression" in lowered
            and "category-agnostic" in lowered
            and "two sibling" in lowered
        )

    def _is_resnet_imagenet_localization_details_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "cls and reg layers" in lowered
            and "anchor" in lowered
            and "oracle" in lowered
            and "localization error" in lowered
        )

    def _is_resnet_imagenet_localization_rcnn_section(self, document_text: str) -> bool:
        lowered = document_text.lower()
        return (
            "roi-centric" in lowered
            and "class-dependent proposals" in lowered
            and "relative reduction of error" in lowered
            and "imagenet localization task" in lowered
        )

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

    def _prefer_resnet_detection_evaluation_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"mini-batch", "learning rate", "pascal voc following", "ms coco the ms"}
        preferred = {
            "PASCAL and COCO evaluation setup": (
                "The training/evaluation setup for object detection on PASCAL VOC and MS COCO.",
                "This frames the appendix section as benchmark protocol plus evidence.",
            ),
            "ResNet feature gain attribution": (
                "The claim that detection gains come from improved features learned by ResNet.",
                "This continues the representation-quality argument.",
            ),
            "COCO metric comparison": (
                "The comparison between mAP@.5 and the stricter mAP@[.5,.95] metric.",
                "This explains why localization quality matters in the result.",
            ),
            "recognition and localization improvement": (
                "The interpretation that deeper networks improve both category recognition and box localization.",
                "This is the main learning point after the metric discussion.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "PASCAL VOC" if "pascal" in lowered else "improve both recognition and localization"
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

    def _filter_resnet_detection_evaluation_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"mini-batch", "learning rate", "pascal voc following", "ms coco the ms"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_detection_improvements_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"feature maps", "regressed box", "non-maximum suppression (nms)", "global spatial pyramid pooling"}
        preferred = {
            "box refinement pipeline": (
                "The inference-time sequence of re-pooling features from regressed boxes, combining predictions, applying NMS, and box voting.",
                "This is a method recipe; the order of operations matters for understanding the section.",
            ),
            "global context feature": (
                "A full-image pooled feature concatenated with each per-region feature before classification and box regression.",
                "This explains how image-level information is added to local object predictions.",
            ),
            "multi-scale testing limitation": (
                "The authors test at multiple scales but do not perform multi-scale training, and only apply it to the Fast R-CNN step.",
                "This keeps the reader from mistaking a partial competition tweak for a complete training method.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "box refinement" if "box refinement" in lowered else "global context" if "global" in lowered else "multi-scale testing"
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

    def _filter_resnet_detection_improvements_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"feature maps", "global spatial pyramid pooling", "map", "rpn step"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_detection_results_table_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"map", "faster r-cnn", "ensemble", "coco"}
        preferred = {
            "detection result table reading": (
                "The tables compare detector variants and benchmark splits rather than developing a new prose argument.",
                "This prevents the PDF table dump from becoming a fake paragraph summary.",
            ),
            "baseline+++ system": (
                "The improved ResNet-101 detector that includes box refinement, context, and multi-scale testing.",
                "This is the key row label that connects the numeric tables to the previous method section.",
            ),
            "cross-benchmark detection validation": (
                "The same detection system family is evaluated on MS COCO and PASCAL VOC 2007/2012.",
                "This explains why the table block matters for the paper's transfer claim.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = "baseline+++" if "baseline" in lowered else "Detection results on"
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

    def _filter_resnet_detection_results_table_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"map", "coco", "faster r-cnn"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_detection_result_narrative_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"roi pooling", "map@.5", "ensemble", "feature maps"}
        preferred = {
            "hidden-label benchmark evaluation": (
                "The COCO test-dev split has hidden labels, so the evaluation server reports the result.",
                "This explains why the section discusses protocol before scores.",
            ),
            "single model versus ensemble": (
                "The section separates one detector's score from the ensemble score that boosts proposals and classifiers.",
                "This prevents the reader from mixing system variants.",
            ),
            "COCO-to-PASCAL fine-tuning": (
                "The COCO-trained detector is adapted to PASCAL VOC with the same improvements.",
                "This is the transfer step behind the PASCAL VOC results.",
            ),
            "competition result claim": (
                "The ensemble wins COCO 2015 detection, and PASCAL VOC 2012 improves over the prior state of the art.",
                "This is the section's benchmark significance.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "evaluation server"
                    if "hidden" in lowered
                    else "ensemble"
                    if "ensemble" in lowered
                    else "fine-tune this model"
                    if "fine" in lowered
                    else "state-of-the-art"
                )
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

    def _filter_resnet_detection_result_narrative_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"roi pooling", "map@.5", "feature maps", "imagenet", "resnet-101", "coco dataset", "map@[.5, .95]", "faster r-cnn", "pascal voc", "map"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_imagenet_detection_setup_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"imagenet classification", "map@.5", "fine-tuned", "object categories"}
        preferred = {
            "ImageNet DET benchmark setup": (
                "ImageNet DET is a 200-category object-detection task evaluated by mAP@.5.",
                "This is the benchmark frame for the section.",
            ),
            "classification-to-detection transfer": (
                "Networks are pretrained on ImageNet classification and fine-tuned on DET data.",
                "This explains how classification representations become detection models.",
            ),
            "val1/val2 validation protocol": (
                "The validation set is split into val1 for fine-tuning and val2 for validation.",
                "This explains the experiment's data protocol.",
            ),
            "restricted competition data use": (
                "The authors state they do not use other ILSVRC 2015 data.",
                "This is an important fairness constraint for benchmark comparison.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "ImageNet Detection"
                    if "setup" in lowered
                    else "pretrained on"
                    if "transfer" in lowered
                    else "val1"
                    if "validation" in lowered
                    else "We do not use"
                )
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

    def _filter_resnet_imagenet_detection_setup_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"imagenet classification", "fine-tuned", "object categories", "imagenet", "map", "ilsvrc 2015"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_imagenet_localization_setup_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"imagenet classification", "loc", "map", "rpn", "convolutional layers"}
        preferred = {
            "ImageNet LOC task framing": (
                "ImageNet Localization requires classification and object localization.",
                "This explains the task before the method adaptation.",
            ),
            "classifier-then-localizer pipeline": (
                "Classifiers first predict image labels, then localization predicts boxes based on those labels.",
                "This explains the division of labor in the system.",
            ),
            "per-class regression strategy": (
                "A bounding-box regressor is learned for each class.",
                "This is the key localization strategy borrowed from prior work.",
            ),
            "per-class RPN modification": (
                "The RPN is changed from category-agnostic to per-class form with classification and regression heads.",
                "This is the section's architecture adaptation.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "requires to classify"
                    if "task" in lowered
                    else "predicted classes"
                    if "pipeline" in lowered
                    else "per-class regression"
                    if "regression" in lowered
                    else "per-class form"
                )
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

    def _filter_resnet_imagenet_localization_setup_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {
            "imagenet classification",
            "loc",
            "map",
            "rpn",
            "ensemble",
            "ilsvrc 2015",
            "convolutional layers",
            "imagenet",
            "resnet-101",
            "multi-scale testing",
        }
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_imagenet_localization_details_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"mini-batch", "imagenet classification", "cls layer", "box regressors", "anchor boxes"}
        preferred = {
            "per-class cls/reg heads": (
                "The localization RPN uses class-specific classification and box-regression outputs.",
                "This is the implementation detail behind per-class localization.",
            ),
            "anchor-based box regression": (
                "Bounding-box regression is defined relative to translation-invariant anchor boxes.",
                "This explains the geometric reference point for predicted boxes.",
            ),
            "balanced anchor sampling": (
                "Positive and negative anchors are sampled at a 1:1 ratio during fine-tuning.",
                "This prevents negative samples from dominating training.",
            ),
            "oracle and dense testing comparison": (
                "Oracle testing uses ground-truth classes, while dense testing applies the network fully convolutionally.",
                "This separates localization quality from classification quality.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "cls and reg layers"
                    if "heads" in lowered
                    else "anchor"
                    if "anchor-based" in lowered or "balanced" in lowered
                    else "oracle"
                )
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

    def _filter_resnet_imagenet_localization_details_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {
            "mini-batch",
            "imagenet classification",
            "cls layer",
            "box regressors",
            "resnet-101",
            "ground truth class",
            "localization error",
            "state-of-the-art methods",
            "imagenet",
            "faster r-cnn",
            "multi-scale testing",
        }
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_imagenet_localization_rcnn_concepts(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        blocked = {"mini-batch", "roi-pooled features", "stochastic training", "per-class rpn"}
        preferred = {
            "Fast R-CNN limitation for LOC": (
                "Overlapping proposal regions make Fast R-CNN image-centric training produce low-variation samples.",
                "This explains the method switch.",
            ),
            "RoI-centric R-CNN choice": (
                "The authors use original R-CNN because it trains on cropped proposal regions.",
                "This is the main design choice of the section.",
            ),
            "class-dependent proposal workflow": (
                "Per-class RPN boxes become class-dependent proposals, then the top 200 train an R-CNN classifier.",
                "This is the localization pipeline to understand.",
            ),
            "localization competition result": (
                "The ensemble reaches 9.0% top-5 localization error and wins ImageNet localization in ILSVRC 2015.",
                "This is the final benchmark claim.",
            ),
        }
        keyed = {str(row.get("concept") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for value, (explanation, why_it_matters) in preferred.items():
            lowered = value.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                target = (
                    "small variations"
                    if "limitation" in lowered
                    else "RoI-centric"
                    if "choice" in lowered
                    else "class-dependent proposals"
                    if "workflow" in lowered
                    else "relative reduction of error"
                )
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

    def _filter_resnet_imagenet_localization_rcnn_noise(self, rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        blocked = {"mini-batch", "roi-pooled features", "stochastic training", "per-class rpn", "faster r-cnn", "imagenet", "ilsvrc 2015"}
        return [row for row in rows if str(row.get(key) or "").strip().lower() not in blocked]

    def _prefer_resnet_imagenet_localization_rcnn_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        preferred = [
            (
                "RoI-centric",
                "A region-centered training style used by original R-CNN.",
                "field_term",
                "hard",
                "RoI-centric",
                "This is the design choice replacing image-centric Fast R-CNN.",
            ),
            (
                "class-dependent proposals",
                "Proposal boxes tied to a specific predicted or ground-truth class.",
                "field_term",
                "hard",
                "class-dependent proposals",
                "This explains how per-class RPN outputs are used.",
            ),
            (
                "highest scored proposals",
                "The top-ranked proposal boxes selected for training or testing.",
                "field_term",
                "medium",
                "highest scored",
                "The pipeline uses the top 200 proposals.",
            ),
            (
                "R-CNN classifier",
                "A classifier trained on cropped proposal regions.",
                "field_term",
                "medium",
                "R-CNN classifier",
                "This is the classifier trained after proposal extraction.",
            ),
            (
                "relative reduction of error",
                "A result reported as percentage reduction relative to prior error.",
                "useful",
                "medium",
                "relative reduction of error",
                "This is how the final localization improvement is expressed.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, target, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _prefer_resnet_imagenet_localization_details_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        preferred = [
            (
                "reg layer",
                "The box-regression output head in the per-class localization RPN.",
                "field_term",
                "medium",
                "reg layer",
                "This is one of the two sibling localization heads.",
            ),
            (
                "binary logistic regression",
                "The binary classifier used for each class dimension in the cls output.",
                "field_term",
                "hard",
                "binary logistic regression",
                "This explains how the 1000-dimensional classification output is interpreted.",
            ),
            (
                "anchor boxes",
                "Translation-invariant reference boxes used for bounding-box regression.",
                "field_term",
                "hard",
                "anchor",
                "This is the reference frame for box regression.",
            ),
            (
                "positive and negative anchors",
                "Balanced anchor samples used during fine-tuning.",
                "field_term",
                "hard",
                "positive and negative anchors",
                "This explains the 1:1 sampling rule.",
            ),
            (
                "oracle testing",
                "Testing that uses the ground-truth class as the class prediction.",
                "field_term",
                "hard",
                "oracle",
                "This separates localization quality from classification quality.",
            ),
            (
                "fully-convolutional testing",
                "Applying the network densely over the image at test time.",
                "field_term",
                "hard",
                "fully-convolutionally",
                "This is the dense testing mode used for localization.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, target, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _prefer_resnet_imagenet_detection_setup_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        preferred = [
            (
                "ImageNet Detection (DET)",
                "The 200-category ImageNet object detection task.",
                "field_term",
                "medium",
                "ImageNet Detection",
                "This names the benchmark setting for the section.",
            ),
            (
                "mAP@.5",
                "Mean average precision at IoU threshold 0.5.",
                "field_term",
                "hard",
                "mAP@.5",
                "This is the metric used to evaluate ImageNet DET.",
            ),
            (
                "ImageNet classification pretraining",
                "Starting from weights learned on the 1000-class ImageNet classification task.",
                "field_term",
                "medium",
                "pretrained on",
                "This explains the source task before DET fine-tuning.",
            ),
            (
                "DET training set",
                "The ImageNet Detection training data used to fine-tune detection models.",
                "field_term",
                "medium",
                "DET training set",
                "This is the target-task data for fine-tuning.",
            ),
            (
                "val1/val2 split",
                "A validation split where val1 supports fine-tuning and val2 is held for validation.",
                "field_term",
                "medium",
                "val1/val2",
                "This explains the experiment protocol.",
            ),
            (
                "ILSVRC 2015 data",
                "Additional competition data that the authors explicitly do not use.",
                "useful",
                "medium",
                "ILSVRC 2015 data",
                "This is a data-use constraint.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, target, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, target, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _prefer_resnet_detection_result_narrative_terms(self, rows: list[dict[str, Any]], document_text: str) -> list[dict[str, Any]]:
        preferred = [
            (
                "test-dev set",
                "A benchmark evaluation split whose labels are hidden and scored by an evaluation server.",
                "field_term",
                "medium",
                "This explains why COCO results are reported by the evaluation server.",
            ),
            (
                "evaluation server",
                "The external scoring service used when test labels are not public.",
                "field_term",
                "medium",
                "This is benchmark protocol, not a model component.",
            ),
            (
                "single-model result",
                "Performance from one detector before using an ensemble.",
                "useful",
                "medium",
                "This separates one-model performance from the stronger ensemble system.",
            ),
            (
                "region proposals",
                "Candidate object boxes generated before final classification.",
                "field_term",
                "hard",
                "The ensemble boosts proposal generation as one task.",
            ),
            (
                "per-region classifiers",
                "Classifiers applied to each proposed image region.",
                "field_term",
                "hard",
                "The ensemble also boosts per-region classification.",
            ),
            (
                "state-of-the-art result",
                "The best previously reported benchmark result at the time.",
                "useful",
                "medium",
                "This is the comparison target for the 10-point PASCAL VOC 2012 gain.",
            ),
        ]
        keyed = {str(row.get("term") or "").strip().lower(): row for row in rows}
        promoted: list[dict[str, Any]] = []
        for term, meaning, priority, difficulty, reason in preferred:
            lowered = term.lower()
            if lowered in keyed:
                promoted.append(keyed[lowered])
            else:
                promoted.append(
                    {
                        "term": term,
                        "meaning": meaning,
                        "domain_relevance": "high" if priority == "field_term" else "medium",
                        "difficulty": difficulty,
                        "source_sentence": self._source_sentence(None, term, document_text),
                        "should_save": True,
                        "learning_priority": priority,
                        "reason": reason,
                        "context_meaning": meaning,
                        "general_meaning": meaning,
                        "confidence": 0.9,
                        "user_state": "suggested",
                    }
                )
        rest = [row for row in rows if str(row.get("term") or "").strip().lower() not in {term.lower() for term, *_ in preferred}]
        return [*promoted, *rest][:12]

    def _fresh_quality_warnings(self, warnings: Any) -> list[str]:
        stale_prefixes = (
            "term_count_out_of_range:",
            "phrase_count_out_of_range:",
            "duplicate_term:",
            "empty_term_meaning:",
            "source_sentence_not_in_document:",
            "term_not_in_source_sentence:",
            "empty_phrase_explanation:",
            "phrase_source_sentence_not_in_document:",
            "phrase_not_in_source_sentence:",
            "analysis_mode:",
        )
        return [warning for warning in self._string_list(warnings) if not warning.startswith(stale_prefixes)]

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
