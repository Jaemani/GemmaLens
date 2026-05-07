import json
import logging

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.base import ModelAdapter
from app.llm.mock_adapter import MockModelAdapter
from app.schemas.analysis_schema import AnalysisResult

logger = logging.getLogger(__name__)


class OllamaAdapter(ModelAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fallback = MockModelAdapter()

    async def analyze_document(self, document_id: str, text: str, chunks: list[str]) -> AnalysisResult:
        prompt = self._build_prompt(document_id, text)
        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        f"{self.settings.ollama_base_url}/api/generate",
                        json={
                            "model": self.settings.ollama_model,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                        },
                    )
                    response.raise_for_status()
                    body = response.json()
                    payload = json.loads(body.get("response", "{}"))
                    payload["document_id"] = document_id
                    return AnalysisResult.model_validate(payload)
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as exc:
                logger.warning("Ollama analysis failed, retrying/falling back: %s", exc)
        return await self.fallback.analyze_document(document_id, text, chunks)

    def _build_prompt(self, document_id: str, text: str) -> str:
        return (
            "Analyze this academic text for language learning. Return only valid JSON "
            "matching fields: document_id, domain, difficulty, terms, phrases, sentences, summaries. "
            f"document_id={document_id}\n\n{text[:8000]}"
        )
