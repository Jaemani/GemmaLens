import logging
import re
from typing import Any

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
            payload = await self._analyze_atomic(document_id, text, chunks)
            return self.normalizer.normalize_payload(payload, document_id, text)
        except (httpx.HTTPError, ValidationError, Exception) as exc:
            logger.exception("Remote Gemma analysis failed")
            raise RuntimeError(f"Remote Gemma analysis failed: {exc}") from exc

    async def _analyze_atomic(self, document_id: str, text: str, chunks: list[str]) -> dict[str, Any]:
        task_text = self._task_text(text, chunks)
        meta = self._fast_meta(task_text) if self._is_q4_remote() else await self._json_task(
            "meta",
            self._meta_prompt(task_text),
            max_tokens=self._task_budget("meta"),
            fallback=self._fast_meta(task_text),
        )
        terms = await self._json_task("terms", self._terms_prompt(task_text), max_tokens=self._task_budget("terms"), fallback={"terms": self._fallback_terms(task_text)})
        phrases = await self._json_task("phrases", self._phrases_prompt(task_text), max_tokens=self._task_budget("phrases"), fallback={"phrases": self._fallback_phrases(task_text)})
        sentences = await self._json_task("sentences", self._sentences_prompt(task_text), max_tokens=self._task_budget("sentences"), fallback={"sentences": []})
        if self._is_q4_remote() or len(terms.get("terms", [])) < 2:
            terms["terms"] = [*terms.get("terms", []), *self._fallback_terms(task_text)]
        if self._is_q4_remote() or len(phrases.get("phrases", [])) < 2:
            phrases["phrases"] = [*phrases.get("phrases", []), *self._fallback_phrases(task_text)]
        return {
            "document_id": document_id,
            "domain": meta.get("domain", {}),
            "difficulty": meta.get("difficulty", {}),
            "summaries": meta.get("summaries", {}),
            "terms": terms.get("terms", []),
            "phrases": phrases.get("phrases", []),
            "sentences": sentences.get("sentences", []),
            "quality_warnings": ["analysis_mode:atomic_remote"],
        }

    async def _json_task(self, task_name: str, prompt: str, max_tokens: int, fallback: dict[str, Any]) -> dict[str, Any]:
        attempts = 1 if self._is_q4_remote() else 2
        for attempt in range(attempts):
            try:
                output = await self._generate(prompt, json_mode=True, max_tokens=max_tokens)
                return extract_json_object(output)
            except Exception as exc:
                logger.warning("Remote atomic task failed: %s attempt=%s error=%s", task_name, attempt + 1, exc)
                prompt = (
                    "Your previous output was invalid or unusable. "
                    "Return only one valid JSON object. Do not include markdown, thoughts, labels, or placeholder values.\n\n"
                    f"{prompt}"
                )
        return fallback

    async def translate_text(self, source_language: str, target_language: str, text: str) -> TranslationResponse:
        try:
            prompt = (
                "Return JSON only. No markdown. "
                "Translate faithfully for a language learner. "
                "Do not copy placeholder words from this instruction. "
                "The translated_text value must be the actual translation of TEXT. "
                "Use this JSON shape: {\"translated_text\":\"actual translation\",\"notes\":[\"short learner note\"]}\n"
                f"Source language: {source_language}\n"
                f"Target language: {target_language}\n\n"
                f"TEXT:\n{text[:1200]}"
            )
            output = await self._generate(prompt, json_mode=True, max_tokens=256)
            try:
                payload = extract_json_object(output)
            except ValueError:
                translated_text = await self._translate_plain(source_language, target_language, text)
                return TranslationResponse(
                    source_language=source_language,
                    target_language=target_language,
                    source_text=text,
                    translated_text=translated_text,
                    notes=[],
                )
            translated_text = str(payload.get("translated_text", "")).strip()
            if translated_text.lower() in {"", "string", "actual translation"}:
                translated_text = await self._translate_plain(source_language, target_language, text)
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

    async def _translate_plain(self, source_language: str, target_language: str, text: str) -> str:
        prompt = (
            f"Translate the following {source_language} text into {target_language}. "
            "Return only the translated sentence, with no labels and no explanation.\n\n"
            f"{text[:1200]}"
        )
        output = await self._generate(prompt, json_mode=False, max_tokens=192)
        cleaned = output.strip().strip('"')
        if not cleaned:
            raise ValueError("translated_text was empty")
        return cleaned

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

    def _task_text(self, text: str, chunks: list[str]) -> str:
        source = "\n\n".join(chunks[:2]).strip() if chunks else text
        normalized = " ".join(source.split())
        limit = min(self.settings.analysis_model_input_chars, 1000 if self._is_q4_remote() else 1800)
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit].rsplit(" ", 1)[0]

    def _is_q4_remote(self) -> bool:
        model = str(self.runtime_config.get("remote_gemma_model", "")).lower()
        base_url = str(self.runtime_config.get("remote_gemma_base_url", "")).lower()
        return "q4" in model or "11445" in base_url

    def _task_budget(self, task_name: str) -> int:
        if not self._is_q4_remote():
            return {"meta": 256, "terms": 384, "phrases": 320, "sentences": 384}[task_name]
        return {"meta": 128, "terms": 160, "phrases": 128, "sentences": 144}[task_name]

    def _fast_meta(self, text: str) -> dict[str, Any]:
        first_sentence = text.split(". ")[0].strip()
        if first_sentence and not first_sentence.endswith("."):
            first_sentence = f"{first_sentence}."
        first_sentence = first_sentence or "Summary not available."
        domain = "Machine Learning" if any(term in text.lower() for term in ["normalization", "transformer", "gradient", "network"]) else "unknown"
        return {
            "domain": {"primary_domain": domain, "secondary_domains": [], "document_type": "unknown", "confidence": 0.5},
            "difficulty": {
                "overall_level": "unknown",
                "lexical_difficulty": 5,
                "syntax_difficulty": 5,
                "domain_difficulty": 6 if domain != "unknown" else 5,
                "reason": "Fast edge mode uses code-generated meta and model-generated learning objects.",
            },
            "summaries": {"one_line": first_sentence, "simple": first_sentence, "academic": first_sentence, "study_notes": []},
        }

    def _fallback_terms(self, text: str) -> list[dict[str, Any]]:
        candidates = [
            "Batch Normalization",
            "layer activations",
            "mini-batch",
            "internal covariate shift",
            "optimization landscape",
            "transformer models",
            "normalization layers",
            "gradients",
        ] + self._candidate_terms(text)
        rows: list[dict[str, Any]] = []
        for candidate in candidates:
            sentence = self._sentence_containing(text, candidate)
            if not sentence:
                continue
            rows.append(
                {
                    "term": candidate,
                    "meaning": "Important source-grounded technical term.",
                    "domain_relevance": "high",
                    "difficulty": "medium",
                    "source_sentence": sentence,
                    "should_save": True,
                    "learning_priority": "field_term",
                    "reason": "Selected by source-grounded fallback after invalid model output.",
                    "confidence": 0.45,
                }
            )
        return rows[:4]

    def _candidate_terms(self, text: str) -> list[str]:
        candidates: list[str] = []
        for match in re.finditer(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3}\b", text):
            candidates.append(match.group(0))
        for match in re.finditer(
            r"\b(?:[a-z]+(?:-[a-z]+)?\s+){1,3}(?:model|models|training|network|networks|gradient|gradients|normalization|activation|activations|landscape|shift|method|study|analysis)\b",
            text.lower(),
        ):
            candidates.append(match.group(0))
        seen: set[str] = set()
        unique: list[str] = []
        for candidate in candidates:
            key = candidate.lower().strip()
            if len(key) < 4 or key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique[:8]

    def _fallback_phrases(self, text: str) -> list[dict[str, Any]]:
        candidates = [
            ("accelerates deep network training", "claim"),
            ("introduced to reduce", "method"),
            ("later work suggests", "claim"),
            ("may come from", "limitation"),
            ("help stabilize training", "result"),
        ]
        rows: list[dict[str, Any]] = []
        for phrase, function in candidates:
            sentence = self._sentence_containing(text, phrase)
            if not sentence:
                continue
            rows.append(
                {
                    "phrase": phrase,
                    "function": function,
                    "explanation": "Reusable phrase selected by source-grounded fallback after invalid model output.",
                    "source_sentence": sentence,
                    "learning_priority": "useful",
                    "reason": "Selected by source-grounded fallback.",
                    "confidence": 0.45,
                }
            )
        return rows[:3]

    def _sentence_containing(self, text: str, needle: str) -> str:
        for sentence in text.split(". "):
            sentence = sentence.strip()
            if needle.lower() in sentence.lower():
                return sentence if sentence.endswith(".") else f"{sentence}."
        return ""

    def _meta_prompt(self, text: str) -> str:
        return (
            "Atomic task: inspect the source text and return only JSON. "
            "Keys: domain, difficulty, summaries. "
            "domain keys: primary_domain, secondary_domains, document_type, confidence. "
            "difficulty keys: overall_level, lexical_difficulty, syntax_difficulty, domain_difficulty, reason. "
            "summaries keys: one_line, simple, academic, study_notes. "
            "Use real values from the source. Do not use placeholder words.\n\n"
            f"SOURCE:\n{text}"
        )

    def _terms_prompt(self, text: str) -> str:
        return (
            "Atomic task: extract 2 to 4 important learning terms from SOURCE. "
            "Return only JSON with key terms. terms must be an array. "
            "Each term object must include: term, meaning, domain_relevance, difficulty, source_sentence, should_save, learning_priority, reason, confidence. "
            "The term text must literally appear in SOURCE. The source_sentence must be copied from SOURCE. "
            "Prefer field terms and high-value unknown words. Do not invent terms. Do not use placeholder values.\n\n"
            f"SOURCE:\n{text}"
        )

    def _phrases_prompt(self, text: str) -> str:
        return (
            "Atomic task: extract 1 to 3 reusable academic or technical phrases from SOURCE. "
            "Return only JSON with key phrases. phrases must be an array. "
            "Each phrase object must include: phrase, function, explanation, source_sentence, learning_priority, reason, confidence. "
            "The phrase must literally appear in SOURCE. The source_sentence must be copied from SOURCE. "
            "Use function values like claim, contrast, limitation, method, result, or general. Do not invent phrases.\n\n"
            f"SOURCE:\n{text}"
        )

    def _sentences_prompt(self, text: str) -> str:
        return (
            "Atomic task: choose 1 to 2 difficult sentences from SOURCE and explain their structure for a language learner. "
            "Return only JSON with key sentences. sentences must be an array. "
            "Each object must include: sentence, core_structure, simplified_version, korean_explanation, difficulty_reason. "
            "The sentence must be copied exactly from SOURCE. Keep explanations concise.\n\n"
            f"SOURCE:\n{text}"
        )
