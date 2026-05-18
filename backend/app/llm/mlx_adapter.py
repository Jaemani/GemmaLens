import logging
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
            output = self._generate_analysis_output(
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
                raw_path.write_text(output, encoding="utf-8")
            payload = extract_json_object(output)
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

    async def translate_text(self, source_language: str, target_language: str, text: str) -> TranslationResponse:
        try:
            output = self._generate_translation_output(source_language, target_language, text)
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
        model, tokenizer = self._load()
        prompt = self._build_translation_prompt(source_language, target_language, text)
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
            max_tokens=min(self.settings.mlx_max_tokens, 768),
            verbose=False,
        )

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
  "sentences": [{"sentence": "string", "core_structure": "string", "simplified_version": "string", "korean_explanation": "string", "difficulty_reason": "string"}],
  "summaries": {"one_line": "string", "simple": "string", "academic": "string", "study_notes": ["string"]}
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
            "B1": "Extract at least 12 terms and at least 6 phrases — at B1 most academic vocabulary is unfamiliar, so be comprehensive. Only skip truly basic everyday words.",
            "B2": "Extract at least 10 terms and at least 5 phrases — cover all field-specific and higher academic vocabulary a B2 learner would not know.",
            "C1": "Extract at least 6 terms and at least 4 phrases — focus on sophisticated multi-word expressions and disciplinary collocations above C1.",
            "C2": "Extract at least 4 terms and at least 3 phrases — only the most advanced domain-specific items; skip anything a strong academic reader would know.",
        }.get(level_upper, "Extract at least 8 terms and at least 4 phrases — cover all field-specific and academic vocabulary that would challenge the learner.")
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
            "Every term and phrase must appear verbatim or in inflected form in its source_sentence. "
            "Use context-specific meanings, not generic dictionary definitions. "
            f"Add a short {support_language} learner gloss for every term and phrase. "
            f"The source language is {learning_language}; do not translate source_sentence. "
            "Prefer 4-6 high-confidence items over an exhaustive list. "
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
