import logging

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.json_utils import extract_json_object
from app.schemas.analysis_schema import AnalysisResult
from app.schemas.translation_schema import TranslationResponse
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.model_runtime_service import ModelRuntimeService

logger = logging.getLogger(__name__)


class RemoteGemmaAdapter(ModelAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.runtime_config = ModelRuntimeService().provider_config()
        self.normalizer = AnalysisNormalizationService()

    async def analyze_document(self, document_id: str, text: str, chunks: list[str]) -> AnalysisResult:
        try:
            prompt = self._build_analysis_prompt(document_id, text, chunks)
            output = await self._generate(prompt, json_mode=True, max_tokens=min(self.settings.mlx_max_tokens, 512))
            payload = extract_json_object(output)
            return self.normalizer.normalize_payload(payload, document_id, text)
        except (httpx.HTTPError, ValidationError, Exception) as exc:
            logger.exception("Remote Gemma analysis failed")
            raise RuntimeError(f"Remote Gemma analysis failed: {exc}") from exc

    async def translate_text(self, source_language: str, target_language: str, text: str) -> TranslationResponse:
        try:
            prompt = (
                "Return JSON only. No markdown. "
                "Translate faithfully for a language learner. "
                "Use this exact shape: {\"translated_text\":\"string\",\"notes\":[\"optional short learner note\"]}\n"
                f"Source language: {source_language}\n"
                f"Target language: {target_language}\n\n"
                f"TEXT:\n{text[:1200]}"
            )
            output = await self._generate(prompt, json_mode=True, max_tokens=256)
            payload = extract_json_object(output)
            translated_text = str(payload.get("translated_text", "")).strip()
            if not translated_text:
                raise ValueError("translated_text was empty")
            notes = payload.get("notes", [])
            if not isinstance(notes, list):
                notes = []
            return TranslationResponse(
                source_language=source_language,
                target_language=target_language,
                source_text=text,
                translated_text=translated_text,
                notes=[str(note) for note in notes[:3]],
            )
        except (httpx.HTTPError, ValueError, Exception) as exc:
            logger.exception("Remote Gemma translation failed")
            raise RuntimeError(f"Remote Gemma translation failed: {exc}") from exc

    async def warmup(self) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.runtime_config['remote_gemma_base_url']}/health")
            response.raise_for_status()
            return response.json()

    async def _generate(self, prompt: str, json_mode: bool, max_tokens: int) -> str:
        async with httpx.AsyncClient(timeout=360) as client:
            response = await client.post(
                f"{self.runtime_config['remote_gemma_base_url']}/generate",
                json={
                    "prompt": prompt,
                    "model": self.runtime_config["remote_gemma_model"],
                    "max_tokens": max_tokens,
                    "json_mode": json_mode,
                },
            )
            response.raise_for_status()
            body = response.json()
            return str(body.get("text", ""))

    def _build_analysis_prompt(self, document_id: str, text: str, chunks: list[str]) -> str:
        return (
            "Return JSON only. No reasoning. No markdown. "
            "Analyze this academic text for language learning. "
            "Select 3-5 terms, 2-3 academic phrases, 1-2 difficult sentence structures, and short summaries. "
            "Every term and phrase must appear in its source_sentence. "
            "Use this exact JSON shape: "
            "{\"document_id\":\"string\",\"domain\":{\"primary_domain\":\"string\",\"secondary_domains\":[\"string\"],"
            "\"document_type\":\"paper|report|article|unknown\",\"confidence\":0.0},"
            "\"difficulty\":{\"overall_level\":\"B1|B2|C1|C2|domain-heavy|unknown\",\"lexical_difficulty\":0,"
            "\"syntax_difficulty\":0,\"domain_difficulty\":0,\"reason\":\"string\"},"
            "\"terms\":[{\"term\":\"string\",\"meaning\":\"string\",\"domain_relevance\":\"low|medium|high\","
            "\"difficulty\":\"easy|medium|hard\",\"source_sentence\":\"string\",\"should_save\":true}],"
            "\"phrases\":[{\"phrase\":\"string\",\"function\":\"claim|contrast|limitation|method|result|general\","
            "\"explanation\":\"string\",\"source_sentence\":\"string\"}],"
            "\"sentences\":[{\"sentence\":\"string\",\"core_structure\":\"string\",\"simplified_version\":\"string\","
            "\"korean_explanation\":\"string\",\"difficulty_reason\":\"string\"}],"
            "\"summaries\":{\"one_line\":\"string\",\"simple\":\"string\",\"academic\":\"string\",\"study_notes\":[\"string\"]}}\n"
            f"document_id: {document_id}\nDocument chunks: {len(chunks)}\n\nTEXT:\n{text[: self.settings.analysis_model_input_chars]}"
        )
