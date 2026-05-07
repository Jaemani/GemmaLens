import logging
from pathlib import Path
from typing import Any, ClassVar

from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.json_utils import extract_json_object
from app.llm.mock_adapter import MockModelAdapter
from app.schemas.analysis_schema import AnalysisResult

logger = logging.getLogger(__name__)


class MLXAdapter(ModelAdapter):
    _model: ClassVar[Any | None] = None
    _tokenizer: ClassVar[Any | None] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.fallback = MockModelAdapter()

    async def analyze_document(self, document_id: str, text: str, chunks: list[str]) -> AnalysisResult:
        try:
            model, tokenizer = self._load()
            prompt = self._build_prompt(document_id, text, chunks)
            messages = [
                {"role": "system", "content": "Return only valid JSON. Do not use markdown."},
                {"role": "user", "content": prompt},
            ]
            formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            from mlx_lm import generate

            output = generate(
                model,
                tokenizer,
                prompt=formatted_prompt,
                max_tokens=self.settings.mlx_max_tokens,
                verbose=False,
            )
            payload = extract_json_object(output)
            payload["document_id"] = document_id
            return AnalysisResult.model_validate(payload)
        except (ImportError, FileNotFoundError, ValidationError, Exception) as exc:
            logger.warning("MLX analysis failed, falling back to mock output: %s", exc)
            return await self.fallback.analyze_document(document_id, text, chunks)

    def _load(self):
        if self.__class__._model is not None and self.__class__._tokenizer is not None:
            return self.__class__._model, self.__class__._tokenizer

        model_path = Path(self.settings.mlx_model_path).expanduser()
        if not model_path.exists():
            raise FileNotFoundError(f"MLX model not found: {model_path}")

        from mlx_lm.utils import load_model, load_tokenizer

        self.__class__._model, _ = load_model(model_path, strict=False)
        self.__class__._tokenizer = load_tokenizer(model_path)
        return self.__class__._model, self.__class__._tokenizer

    def _build_prompt(self, document_id: str, text: str, chunks: list[str]) -> str:
        schema_hint = """
{
  "document_id": "string",
  "domain": {"primary_domain": "string", "secondary_domains": ["string"], "document_type": "paper|report|article|unknown", "confidence": 0.0},
  "difficulty": {"overall_level": "B1|B2|C1|C2|domain-heavy|unknown", "lexical_difficulty": 0, "syntax_difficulty": 0, "domain_difficulty": 0, "reason": "string"},
  "terms": [{"term": "string", "meaning": "string", "domain_relevance": "low|medium|high", "difficulty": "easy|medium|hard", "source_sentence": "string", "should_save": true}],
  "phrases": [{"phrase": "string", "function": "claim|contrast|limitation|method|result|general", "explanation": "string", "source_sentence": "string"}],
  "sentences": [{"sentence": "string", "core_structure": "string", "simplified_version": "string", "korean_explanation": "string", "difficulty_reason": "string"}],
  "summaries": {"one_line": "string", "simple": "string", "academic": "string", "study_notes": ["string"]}
}
"""
        chunk_note = f"Document chunks: {len(chunks)}"
        return (
            "Analyze this academic text for English learning. "
            "Extract reusable vocabulary, academic phrases, difficult sentence structures, and layered summaries. "
            f"Use this exact JSON shape:\n{schema_hint}\n"
            f"document_id: {document_id}\n{chunk_note}\n\nTEXT:\n{text[:12000]}"
        )
