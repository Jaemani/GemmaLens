import asyncio
import logging
import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.json_utils import extract_json_object
from app.llm.mock_adapter import MockModelAdapter
from app.schemas.analysis_schema import AnalysisResult
from app.schemas.translation_schema import TranslationResponse
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.model_runtime_service import ModelRuntimeService

logger = logging.getLogger(__name__)


class MLXAdapter(ModelAdapter):
    _model: ClassVar[Any | None] = None
    _tokenizer: ClassVar[Any | None] = None
    _model_path: ClassVar[str | None] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.runtime_config = ModelRuntimeService().provider_config()
        self.fallback = MockModelAdapter()
        self.normalizer = AnalysisNormalizationService()

    def warmup(self) -> None:
        self._load()

    async def analyze_document(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str = "Korean",
        learning_language: str = "English",
        target_level: str | None = None,
        source_type: str | None = None,
    ) -> AnalysisResult:
        try:
            payload = await asyncio.to_thread(
                self._analyze_atomic,
                document_id,
                text,
                chunks,
                support_language,
                learning_language,
                target_level,
                source_type,
            )
            if self.settings.raw_model_output_path:
                raw_path = Path(self.settings.raw_model_output_path).expanduser()
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return self.normalizer.normalize_payload(
                payload,
                document_id,
                text,
                support_language=support_language,
                target_level=target_level,
                source_type=source_type,
            )
        except (ImportError, FileNotFoundError, ValidationError, Exception) as exc:
            logger.exception("MLX analysis failed")
            raise RuntimeError(f"MLX analysis failed: {exc}") from exc

    def _analyze_atomic(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str,
        learning_language: str,
        target_level: str | None,
        source_type: str | None,
    ) -> dict[str, Any]:
        task_text = text[: self.settings.analysis_model_input_chars]
        mode_note = self._mode_guidance(source_type)
        meta = self._json_task("meta", self._meta_prompt(task_text, mode_note), max_tokens=768, fallback=self._fast_meta(task_text))
        terms = self._json_task(
            "terms",
            self._terms_prompt(task_text, support_language, learning_language, target_level, mode_note),
            max_tokens=1024,
            fallback={"terms": []},
        )
        phrases = self._json_task(
            "phrases",
            self._phrases_prompt(task_text, support_language, learning_language, target_level, mode_note),
            max_tokens=768,
            fallback={"phrases": []},
        )
        concepts = self._json_task(
            "concepts",
            self._concepts_prompt(task_text, support_language, learning_language, target_level, mode_note),
            max_tokens=1536,
            fallback={"concepts": []},
        )
        sentences = self._json_task(
            "sentences",
            self._sentences_prompt(task_text, support_language, target_level, mode_note),
            max_tokens=768,
            fallback={"sentences": []},
        )
        return {
            "document_id": document_id,
            "domain": meta.get("domain", {}),
            "difficulty": meta.get("difficulty", {}),
            "summaries": meta.get("summaries", {}),
            "terms": terms.get("terms", []),
            "phrases": phrases.get("phrases", []),
            "concepts": concepts.get("concepts", []),
            "sentences": sentences.get("sentences", []),
            "quality_warnings": ["analysis_mode:atomic_mlx"],
        }

    def _json_task(self, task_name: str, prompt: str, max_tokens: int, fallback: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            try:
                output = self._generate_prompt_output(prompt, max_tokens=max_tokens)
                return extract_json_object(output)
            except Exception as exc:
                logger.warning("MLX atomic task failed: %s attempt=%s error=%s", task_name, attempt + 1, exc)
                prompt = (
                    "Your previous output was invalid or unusable. "
                    "Return exactly one valid JSON object. No markdown. No commentary. No placeholder strings.\n\n"
                    f"{prompt}"
                )
        return fallback

    async def translate_text(self, source_language: str, target_language: str, text: str) -> TranslationResponse:
        try:
            output = await asyncio.to_thread(self._generate_translation_output, source_language, target_language, text)
            payload = extract_json_object(output)
            translated_text = str(payload.get("translated_text", "")).strip()
            if not translated_text:
                raise ValueError("translated_text was empty")
            notes = payload.get("notes", [])
            if not isinstance(notes, list):
                notes = []
            notes = [str(note).strip() for note in notes if self._is_real_note(str(note))]
            return TranslationResponse(
                source_language=source_language,
                target_language=target_language,
                source_text=text,
                translated_text=translated_text,
                notes=notes[:3],
            )
        except (ImportError, FileNotFoundError, ValueError, Exception) as exc:
            logger.exception("MLX translation failed")
            raise RuntimeError(f"MLX translation failed: {exc}") from exc

    def _generate_prompt_output(self, prompt: str, max_tokens: int | None = None) -> str:
        model, tokenizer = self._load()
        messages = [
            {"role": "system", "content": "Return only valid JSON. Do not use markdown. Do not output thoughts, analysis, or commentary."},
            {"role": "user", "content": prompt},
        ]
        formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=False)
        from mlx_lm import generate

        return generate(
            model,
            tokenizer,
            prompt=formatted_prompt,
            max_tokens=max_tokens or self.settings.mlx_max_tokens,
            verbose=False,
        )

    def _generate_analysis_output(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str,
        learning_language: str,
        target_level: str | None,
        source_type: str | None,
    ) -> str:
        model, tokenizer = self._load()
        prompt = self._build_prompt(document_id, text, chunks, support_language, learning_language, target_level, source_type)
        messages = [
            {"role": "system", "content": "Return only valid JSON. Do not use markdown. Do not output thoughts, analysis, or commentary."},
            {"role": "user", "content": prompt},
        ]
        formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=False)
        from mlx_lm import generate

        return generate(
            model,
            tokenizer,
            prompt=formatted_prompt,
            max_tokens=self.settings.mlx_max_tokens,
            verbose=False,
        )

    def _generate_translation_output(self, source_language: str, target_language: str, text: str) -> str:
        prompt = self._build_translation_prompt(source_language, target_language, text)
        return self._generate_prompt_output(prompt, max_tokens=min(self.settings.mlx_max_tokens, 768))

    def _load(self):
        model_path = str(Path(self.runtime_config["mlx_model_path"]).expanduser())
        if (
            self.__class__._model is not None
            and self.__class__._tokenizer is not None
            and self.__class__._model_path == model_path
        ):
            return self.__class__._model, self.__class__._tokenizer

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"MLX model not found: {model_path}")

        from mlx_lm.utils import load_model, load_tokenizer

        self.__class__._model, _ = load_model(path, strict=False)
        self.__class__._tokenizer = load_tokenizer(path)
        self.__class__._model_path = model_path
        return self.__class__._model, self.__class__._tokenizer

    def _mode_guidance(self, source_type: str | None) -> str:
        if source_type in {"video_segment", "transcript"}:
            return (
                "This SOURCE is video subtitles, not a paper. Choose spoken expressions, scene concepts, and reusable listening patterns. "
                "Ignore subtitle boilerplate, credits, filenames, download-site text, and one-word filler."
            )
        return "This SOURCE is a document section. Keep the source primary and select learning objects from this section only."

    def _fast_meta(self, text: str) -> dict[str, Any]:
        first_sentence = self._first_sentence(text)
        return {
            "domain": {"primary_domain": "unknown", "secondary_domains": [], "document_type": "unknown", "confidence": 0.5},
            "difficulty": {
                "overall_level": "unknown",
                "lexical_difficulty": 5,
                "syntax_difficulty": 5,
                "domain_difficulty": 5,
                "reason": "Fallback metadata used after model output could not be parsed.",
            },
            "summaries": {"one_line": first_sentence, "simple": first_sentence, "academic": first_sentence, "study_notes": []},
        }

    def _first_sentence(self, text: str) -> str:
        compact = " ".join(text.split())
        if not compact:
            return "Summary not available."
        for marker in [". ", "? ", "! "]:
            index = compact.find(marker)
            if 40 <= index <= 420:
                return compact[: index + 1]
        return compact[:240]

    def _level_guidance(self, target_level: str | None) -> str:
        level = (target_level or "unknown").upper()
        if level == "B1":
            return (
                "Target learner level: B1. Select accessible but important academic vocabulary, core domain words, and reusable phrases. "
                "Explain meanings plainly. Skip expert-only nuance unless it is essential for the section."
            )
        if level == "B2":
            return (
                "Target learner level: B2. Select field-specific and higher academic vocabulary a strong intermediate learner is likely to need. "
                "Prefer methodology terms, statistical concepts, domain nouns, and academic collocations that carry the section's argument."
            )
        if level == "C1":
            return (
                "Target learner level: C1. Select sophisticated disciplinary collocations, compressed academic noun phrases, and rhetorical moves. "
                "Skip basic B2 vocabulary and generic connectors."
            )
        if level == "C2":
            return (
                "Target learner level: C2. Select only advanced domain-specific items, subtle argument structure, and expert-level collocations. "
                "Skip anything a strong academic reader would already know."
            )
        return "Target learner level: unknown. Prefer source-grounded items that help serious academic reading."

    def _terms_count(self, target_level: str | None) -> str:
        return {
            "B1": "roughly 8 to 12 if the section has enough real learning signal",
            "B2": "roughly 7 to 10 if the section has enough real learning signal",
            "C1": "roughly 5 to 7 if the section has enough real learning signal",
            "C2": "roughly 3 to 5 if the section has enough real learning signal",
        }.get((target_level or "").upper(), "roughly 6 to 8 if the section has enough real learning signal")

    def _phrases_count(self, target_level: str | None) -> str:
        return {
            "B1": "roughly 4 to 6 if available",
            "B2": "roughly 4 to 5 if available",
            "C1": "roughly 3 to 4 if available",
            "C2": "roughly 2 to 3 if available",
        }.get((target_level or "").upper(), "roughly 3 to 4 if available")

    def _meta_prompt(self, text: str, mode_note: str = "") -> str:
        return (
            "Atomic task: inspect SOURCE and return only JSON with keys domain, difficulty, summaries. "
            f"{mode_note} "
            "domain keys: primary_domain, secondary_domains, document_type, confidence. "
            "difficulty keys: overall_level, lexical_difficulty, syntax_difficulty, domain_difficulty, reason. "
            "summaries keys: one_line, simple, academic, study_notes. Use real source content.\n\n"
            f"SOURCE:\n{text}"
        )

    def _terms_prompt(
        self,
        text: str,
        support_language: str,
        learning_language: str,
        target_level: str | None,
        mode_note: str,
    ) -> str:
        return (
            f"Atomic task: extract {self._terms_count(target_level)} important learning terms from SOURCE. "
            f"{mode_note} {self._level_guidance(target_level)} "
            "Quality beats count. Return fewer terms when the page is sparse, boilerplate, a table of contents, a questionnaire, or mostly metadata. "
            "Never pad with random words. Terms must be high-value learning vocabulary from the current section: field terms, report methodology terms, statistical concepts, domain-specific nouns, or academic nouns that carry the argument. "
            "Reject generic words such as section, source, figure, table, page, note, report, study, participant, value, item, data, result, and generic organization names unless SOURCE teaches a technical meaning. "
            "Return only JSON: {\"terms\":[{\"term\":\"string\",\"meaning\":\"string\",\"support_language_meaning\":\"string\",\"domain_relevance\":\"low|medium|high\",\"difficulty\":\"easy|medium|hard\",\"source_sentence\":\"string\",\"should_save\":true,\"learning_priority\":\"must_review|useful|field_term|low_priority\",\"reason\":\"string\",\"confidence\":0.0}]}. "
            f"meaning must be concise {learning_language}. support_language_meaning must be concise {support_language}. term must appear in source_sentence copied from SOURCE.\n\n"
            f"SOURCE:\n{text}"
        )

    def _phrases_prompt(
        self,
        text: str,
        support_language: str,
        learning_language: str,
        target_level: str | None,
        mode_note: str,
    ) -> str:
        return (
            f"Atomic task: extract {self._phrases_count(target_level)} reusable academic or technical phrases from SOURCE. "
            f"{mode_note} {self._level_guidance(target_level)} "
            "Return fewer phrases when the section has fewer real reusable expressions. Never pad with generic fragments. "
            "A good phrase is a reusable academic expression, collocation, or rhetorical move from SOURCE. "
            "Reject weak phrases such as 'similarly to', 'based on', 'in addition to', 'as a result', and copied sentence fragments. "
            "Return only JSON: {\"phrases\":[{\"phrase\":\"string\",\"function\":\"claim|contrast|limitation|method|result|general\",\"explanation\":\"string\",\"support_language_explanation\":\"string\",\"source_sentence\":\"string\",\"learning_priority\":\"must_review|useful|field_term|low_priority\",\"reason\":\"string\",\"confidence\":0.0}]}. "
            f"explanation must be concise {learning_language}. support_language_explanation must be concise {support_language}. phrase must appear in source_sentence copied from SOURCE.\n\n"
            f"SOURCE:\n{text}"
        )

    def _concepts_prompt(
        self,
        text: str,
        support_language: str,
        learning_language: str,
        target_level: str | None,
        mode_note: str,
    ) -> str:
        return (
            "Atomic task: extract 2 to 4 source-grounded ideas/concepts from SOURCE, only when the section has real conceptual signal. "
            f"{mode_note} {self._level_guidance(target_level)} "
            "Concepts are ideas, methods, claims, mechanisms, or argument moves the reader must understand; they are not vocabulary duplicates. "
            "Good labels look like short ideas: 'diffusion-based coordinate refinement', 'burden-adjusted trial participation inequality', 'trade-policy uncertainty shock'. "
            "Bad labels are bare terms: 'diffusion module', 'weighted', 'GDP', 'Figure 1'. "
            "Keep each explanation and support_language_explanation to one concise sentence. "
            "Return only JSON: {\"concepts\":[{\"concept\":\"string\",\"explanation\":\"string\",\"support_language_explanation\":\"string\",\"source_sentence\":\"string\",\"related_terms\":[\"string\"],\"why_it_matters\":\"string\",\"references\":[\"string\"],\"learning_priority\":\"must_review|useful|field_term|low_priority\",\"confidence\":0.0}]}. "
            f"explanation must be concise {learning_language}. support_language_explanation must be concise {support_language}. source_sentence must be copied from SOURCE. Do not copy the terms list.\n\n"
            f"SOURCE:\n{text}"
        )

    def _sentences_prompt(
        self,
        text: str,
        support_language: str,
        target_level: str | None,
        mode_note: str,
    ) -> str:
        return (
            "Atomic task: choose 1 to 3 difficult source sentences and explain their reusable academic structure. "
            f"{mode_note} {self._level_guidance(target_level)} "
            "The core_structure must be a reusable pattern with placeholders and rhetorical function, not a generic label like 'main claim + detail'. "
            "Good examples: 'Although X, Y remains unclear'; 'X is attributed to Y, with Z as supporting evidence'; 'To address X, the authors use Y'. "
            "Return only JSON: {\"sentences\":[{\"sentence\":\"string\",\"core_structure\":\"string\",\"simplified_version\":\"string\",\"korean_explanation\":\"string\",\"difficulty_reason\":\"string\"}]}. "
            f"korean_explanation must be in {support_language}. sentence must be copied exactly from SOURCE.\n\n"
            f"SOURCE:\n{text}"
        )

    def _build_prompt(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str,
        learning_language: str,
        target_level: str | None = None,
        source_type: str | None = None,
    ) -> str:
        schema_hint = """
{
  "document_id": "string",
  "domain": {"primary_domain": "string", "secondary_domains": ["string"], "document_type": "paper|report|article|unknown", "confidence": 0.0},
  "difficulty": {"overall_level": "B1|B2|C1|C2|domain-heavy|unknown", "lexical_difficulty": 0, "syntax_difficulty": 0, "domain_difficulty": 0, "reason": "string"},
  "terms": [{
    "term": "string",
    "meaning": "string",
    "support_language_meaning": "string",
    "domain_relevance": "low|medium|high",
    "difficulty": "easy|medium|hard",
    "source_sentence": "string",
    "should_save": true,
    "learning_priority": "must_review|useful|field_term|low_priority",
    "reason": "string",
    "context_meaning": "string",
    "confidence": 0.0
  }],
  "phrases": [{
    "phrase": "string",
    "function": "claim|contrast|limitation|method|result|general",
    "explanation": "string",
    "support_language_explanation": "string",
    "source_sentence": "string",
    "learning_priority": "must_review|useful|field_term|low_priority",
    "reason": "string",
    "confidence": 0.0
  }],
  "concepts": [{
    "concept": "string",
    "explanation": "string",
    "support_language_explanation": "string",
    "source_sentence": "string",
    "related_terms": ["string"],
    "why_it_matters": "string",
    "references": ["string"],
    "learning_priority": "must_review|useful|field_term|low_priority",
    "confidence": 0.0
  }],
  "sentences": [{"sentence": "string", "core_structure": "string", "simplified_version": "string", "korean_explanation": "string", "difficulty_reason": "string"}],
  "summaries": {"one_line": "string", "simple": "string", "academic": "string", "study_notes": ["string"]},
  "quality_warnings": ["string"]
}
"""
        chunk_note = f"Document chunks: {len(chunks)}"
        video_guidance = ""
        if source_type in {"video_segment", "transcript"}:
            video_guidance = (
                "This SOURCE is video subtitles, not an academic paper. "
                "Teach listening and language from the current scene: choose spoken expressions, idioms, collocations, field terms, and reusable sentence patterns. "
                "Do not produce a generic whole-document summary. Ignore subtitle boilerplate, credits, filenames, download-site text, and one-word filler. "
                "Use the support language as quick meaning support, but keep the learning target in the source language. "
            )
        level_upper = (target_level or "").upper()
        count_guidance = {
            "B1": "Aim for 8-12 terms, 4-6 phrases, 3-5 concepts, and 2-3 sentence patterns when the section contains enough signal.",
            "B2": "Aim for 7-10 terms, 4-5 phrases, 3-5 concepts, and 2-3 sentence patterns when the section contains enough signal.",
            "C1": "Aim for 5-7 terms, 3-4 phrases, 3-4 concepts, and 2-3 sentence patterns when the section contains enough signal.",
            "C2": "Aim for 3-5 terms, 2-3 phrases, 2-3 concepts, and 1-2 sentence patterns when the section contains enough signal.",
        }.get(level_upper, "Aim for 6-8 terms, 3-4 phrases, 3-4 concepts, and 2 sentence patterns when the section contains enough signal.")
        quality_guidance = (
            "Quality beats count: if the section is a cover page, table of contents, bibliography, questionnaire topline, or mostly boilerplate, return fewer items and add a quality_warnings entry. "
            "Do not fill target ranges with random words. "
            "Terms must be high-value learning vocabulary from the current section: field terms, report methodology terms, statistical concepts, domain-specific nouns, or academic nouns that carry the argument. "
            "Reject generic words such as section, source, figure, table, page, note, report, study, participant, value, item, data, result, and generic organization names unless the current section teaches a technical meaning for them. "
            "Concepts are not vocabulary duplicates. A concept should explain an idea, method, claim, mechanism, or argument move in the section. "
            "Good concept labels look like short ideas: 'diffusion-based coordinate refinement', 'burden-adjusted trial participation inequality', 'trade-policy uncertainty shock', or 'human-caused warming attribution'. "
            "Bad concept labels are bare vocabulary duplicates: 'diffusion module', 'weighted', 'participants', 'GDP', or 'Figure 1'. "
            "Phrases must be reusable academic expressions or collocations, not arbitrary fragments. "
            "Reject weak phrases such as 'similarly to', 'based on', 'in addition to', 'as a result', 'this section', and copied sentence fragments. "
            "Sentence patterns must capture a real reusable structure from a difficult source sentence, not a generic label like 'main claim + detail'. "
            "Good sentence patterns use placeholders and rhetorical function, such as 'Although X, Y remains unclear' or 'X is attributed to Y, with Z as supporting evidence'. "
        )
        return (
            "Return JSON only. No reasoning. No markdown. "
            "Analyze this academic text for language learning. "
            f"{video_guidance}"
            f"Target learner level: {target_level or 'unknown'}. "
            "For B1-B2: select core domain terms and common academic collocations that carry content meaning. "
            "For C1-C2: select only field-specific terminology and sophisticated multi-word expressions; "
            "skip anything known at B2 or below, including: discourse connectors (based on, in addition to, as a result), "
            "simple reporting verbs (we propose, we show, we use, we compute, we employ, we find), "
            "generic transitions (similar to, such as, for example, in contrast), "
            "and single-clause subject+verb fragments. "
            "For phrases: write the BASE FORM of the expression, never copy a full clause or sentence from the text. "
            "Use infinitive or lemma form: 'rely entirely on' not 'The model relies entirely on'; "
            "'prevent X from attending to Y' not 'prevent positions from attending to subsequent positions'. "
            "Do not embed numbers, variable names, or bracketed citations in phrases. "
            "Prefer: complex nominalizations, disciplinary hedging patterns, collocational restrictions, "
            "argument-structure expressions (attribute X to Y, account for, give rise to), and rhetorical moves unique to the domain. "
            f"{count_guidance} "
            f"{quality_guidance} "
            "Every term and phrase must appear verbatim or in inflected form in its source_sentence. "
            "Use context-specific meanings, not generic dictionary definitions. "
            f"Add a short {support_language} learner gloss for every term, phrase, and concept. "
            f"The source language is {learning_language}; do not translate source_sentence. "
            "Return enough high-confidence learning objects for the learner level, but never invent low-value filler. "
            f"Use this exact JSON shape and key names:\n{schema_hint}\n"
            f"document_id: {document_id}\n{chunk_note}\n\nTEXT:\n{text[: self.settings.analysis_model_input_chars]}"
        )

    def _build_translation_prompt(self, source_language: str, target_language: str, text: str) -> str:
        return (
            "Return JSON only. No reasoning. No markdown. "
            "Translate the input faithfully for a language learner. "
            "Preserve technical terms when they are normally used in the target language, but translate surrounding explanation naturally. "
            "Do not add commentary inside translated_text. "
            "Use this exact JSON shape: {\"translated_text\":\"string\",\"notes\":[\"real note if useful\"]}\n"
            f"Source language: {source_language}\n"
            f"Target language: {target_language}\n\n"
            f"TEXT:\n{text[:1200]}"
        )

    def _is_real_note(self, value: str) -> bool:
        normalized = value.lower().strip()
        if not normalized:
            return False
        if normalized in {"string", "short learner note", "learner note", "note"}:
            return False
        return "actual translation" not in normalized
