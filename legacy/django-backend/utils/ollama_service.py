"""
utils/ollama_service.py

Local LLM inference via Ollama (http://localhost:11434), used in place of a
cloud API for question generation. This is what makes the "no external API /
data never leaves government infrastructure" claim in the NEXUS SIH doc
actually true — the model, the prompt, and every generated token stay on the
machine running Ollama, whether that's a laptop for the demo or an on-prem
GPU box in a real MoSPI deployment.

Swap models by setting OLLAMA_MODEL (env) or passing model= explicitly.
Any model `ollama pull`-ed locally works — this service doesn't hardcode one.
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")


class OllamaUnavailableError(Exception):
    """Raised when the local Ollama daemon can't be reached or the model isn't pulled."""


class OllamaService:
    """Thin wrapper around Ollama's /api/generate, mirroring GeminiAPIService's
    call_api_with_fallback so callers don't care which engine is behind them."""

    def __init__(self, model: str = None):
        self.model = model or DEFAULT_MODEL

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            if not r.ok:
                return False
            names = [m.get("name", "") for m in r.json().get("models", [])]
            return any(self.model == n or self.model.split(":")[0] == n.split(":")[0] for n in names)
        except requests.RequestException:
            return False

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 240,
        use_cache: bool = True,
        cache_seconds: int = 86400,
    ) -> Dict[str, Any]:
        """
        Ask the local model for a single JSON object matching the prompt's
        described schema. Ollama's `format: "json"` constrains output to
        valid JSON syntax, but not to any particular shape — the schema has
        to be spelled out in the prompt itself.
        """
        cache_key = None
        if use_cache:
            import hashlib
            cache_key = "ollama_gen_" + hashlib.sha256((self.model + prompt).encode()).hexdigest()
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info("[Ollama] cache hit")
                return cached

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        try:
            start = time.time()
            resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=timeout)
        except requests.ConnectionError as e:
            raise OllamaUnavailableError(
                f"Could not reach Ollama at {OLLAMA_HOST}. Is `ollama serve` running? ({e})"
            )
        except requests.Timeout:
            raise OllamaUnavailableError(
                f"Ollama did not respond within {timeout}s for model '{self.model}'."
            )

        if not resp.ok:
            raise OllamaUnavailableError(f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        raw = body.get("response", "")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ollama did not return valid JSON: {e}. Raw: {raw[:300]}")

        elapsed = time.time() - start
        logger.info(f"[Ollama] {self.model} responded in {elapsed:.1f}s")

        if use_cache and cache_key:
            cache.set(cache_key, parsed, timeout=cache_seconds)

        return parsed


    def generate_flashcards(self, text_content: str, count: int = 10) -> list:
        """Same contract as GeminiAPIService.generate_flashcards: a list of
        {"front": ..., "back": ...} dicts, generated from uploaded content."""
        prompt = f"""You are an educational expert specialising in spaced-repetition study systems.
Generate exactly {count} flashcards from the text below.

Rules: one concept per card, front is a question or fill-in-the-blank prompt,
back is a concise answer (15-20 words max).

Text content:
{text_content[:3000]}

Output ONLY a JSON object of this exact shape, no markdown, no prose:
{{"flashcards": [{{"front": "string", "back": "string"}}]}}
The flashcards array must contain exactly {count} items."""
        try:
            data = self.generate_json(prompt, timeout=60 + count * 20, use_cache=True)
            cards = data.get("flashcards", [])
            return cards if isinstance(cards, list) else []
        except OllamaUnavailableError as e:
            logger.warning(f"[Ollama] flashcard generation unavailable: {e}")
            return []
        except ValueError as e:
            logger.error(f"[Ollama] flashcard generation parse error: {e}")
            return []

    def generate_questions_from_text(self, text_content: str, count: int = 5, question_type: str = "mcq") -> list:
        """Same contract as GeminiAPIService.generate_questions_from_text: a
        list of dicts with a nested {"A":.., "B":.., "C":.., "D":..} options
        map (note this differs from the flat option_a/b/c/d schema used by
        quiz.local_generator.LocalQuizGenerator — this one mirrors the
        learning-module pipeline it replaces)."""
        prompt = f"""You are an expert educator. Create exactly {count} multiple-choice questions based on the text below.

Difficulty 1-5 (1=basic, 5=advanced). Confidence 0.0-1.0 for your certainty in the answer's accuracy.

Text content:
{text_content[:3000]}

Output ONLY a JSON object of this exact shape, no markdown, no prose:
{{"questions": [{{"question_text": "string", "options": {{"A": "string", "B": "string", "C": "string", "D": "string"}}, "correct_answer": "A", "explanation": "string", "confidence_score": 0.9, "difficulty": 3}}]}}
The questions array must contain exactly {count} items."""
        try:
            data = self.generate_json(prompt, timeout=60 + count * 25, use_cache=False)
            questions = data.get("questions", [])
            return questions if isinstance(questions, list) else []
        except OllamaUnavailableError as e:
            logger.warning(f"[Ollama] question generation unavailable: {e}")
            return []
        except ValueError as e:
            logger.error(f"[Ollama] question generation parse error: {e}")
            return []


_default_service = None


def get_ollama_service(model: str = None) -> OllamaService:
    global _default_service
    if model:
        return OllamaService(model=model)
    if _default_service is None:
        _default_service = OllamaService()
    return _default_service
