"""Abstraction des fournisseurs de modèles, interchangeables et optionnels.

Par défaut (`extractive`) aucune clé n'est requise : la synthèse est un calcul
déterministe sur les affirmations vérifiées. `used_llm=False` est alors explicite
dans le rapport — le système ne prétend jamais qu'un modèle a tourné.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..core.config import Settings
from ..core.errors import ProviderUnavailable
from ..core.logging_conf import log_event


@dataclass
class ModelReply:
    text: str
    provider: str = "extractive"
    model: str = "extractive-v1"
    used_llm: bool = False
    latency_ms: float = 0.0
    fallback_used: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text, "provider": self.provider, "model": self.model,
            "used_llm": self.used_llm, "latency_ms": round(self.latency_ms, 2),
            "fallback_used": self.fallback_used, "error": self.error,
        }


class ModelProvider:
    name = "base"
    requires_key = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return True

    async def complete(self, client: httpx.AsyncClient, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:  # pragma: no cover
        raise NotImplementedError


class ExtractiveModel(ModelProvider):
    """Synthèse extractive locale : sélectionne et ordonne les phrases utiles.

    C'est un calcul réel sur les données fournies, pas une réponse inventée et
    pas un résultat de recherche simulé.
    """
    name = "extractive"

    async def complete(self, client: httpx.AsyncClient, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:
        started = time.perf_counter()
        lines = [re.sub(r"\s+", " ", line).strip()
                 for line in prompt.splitlines() if line.strip()]
        useful = [line for line in lines
                  if not line.startswith("<<<") and not line.startswith("Le bloc suivant")
                  and len(line) > 25]
        # Déduplication et borne stricte sur le nombre de caractères.
        seen: set[str] = set()
        selected: list[str] = []
        for line in useful:
            key = line.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            selected.append(line)
            if sum(len(x) for x in selected) > max_tokens * 3:
                break
        text = "\n".join(f"- {line}" for line in selected[:24]) or \
            "Aucune affirmation exploitable n'a pu être extraite des preuves disponibles."
        return ModelReply(text=text, provider=self.name, model="extractive-v1",
                          used_llm=False,
                          latency_ms=(time.perf_counter() - started) * 1000)


class OpenAICompatibleModel(ModelProvider):
    name = "openai_compatible"
    requires_key = True

    def configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def complete(self, client: httpx.AsyncClient, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:
        if not self.configured():
            raise ProviderUnavailable("OMNI_OPENAI_API_KEY absente")
        started = time.perf_counter()
        r = await client.post(
            self.settings.openai_base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={"model": self.settings.openai_model, "max_tokens": max_tokens,
                  "temperature": 0.1,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        payload = r.json()
        text = payload["choices"][0]["message"]["content"]
        return ModelReply(text=text, provider=self.name, model=self.settings.openai_model,
                          used_llm=True, latency_ms=(time.perf_counter() - started) * 1000)


class AnthropicModel(ModelProvider):
    name = "anthropic"
    requires_key = True

    def configured(self) -> bool:
        return bool(self.settings.anthropic_api_key)

    async def complete(self, client: httpx.AsyncClient, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:
        if not self.configured():
            raise ProviderUnavailable("OMNI_ANTHROPIC_API_KEY absente")
        started = time.perf_counter()
        r = await client.post(
            self.settings.anthropic_base_url.rstrip("/") + "/v1/messages",
            headers={"x-api-key": self.settings.anthropic_api_key,
                     "anthropic-version": "2023-06-01"},
            json={"model": self.settings.anthropic_model, "max_tokens": max_tokens,
                  "system": system,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        payload = r.json()
        text = "".join(block.get("text", "") for block in payload.get("content", [])
                       if block.get("type") == "text")
        return ModelReply(text=text, provider=self.name, model=self.settings.anthropic_model,
                          used_llm=True, latency_ms=(time.perf_counter() - started) * 1000)


class OllamaModel(ModelProvider):
    name = "ollama"

    def configured(self) -> bool:
        return bool(self.settings.ollama_base_url)

    async def complete(self, client: httpx.AsyncClient, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:
        started = time.perf_counter()
        r = await client.post(
            self.settings.ollama_base_url.rstrip("/") + "/api/generate",
            json={"model": self.settings.ollama_model, "system": system,
                  "prompt": prompt, "stream": False,
                  "options": {"num_predict": max_tokens, "temperature": 0.1}},
        )
        r.raise_for_status()
        text = r.json().get("response", "")
        return ModelReply(text=text, provider=self.name, model=self.settings.ollama_model,
                          used_llm=True, latency_ms=(time.perf_counter() - started) * 1000)


BUILTIN_MODELS: tuple[type[ModelProvider], ...] = (
    OpenAICompatibleModel, AnthropicModel, OllamaModel, ExtractiveModel,
)


class ModelRouter:
    def __init__(self, settings: Settings,
                 client_factory: Any = None,
                 extra: list[ModelProvider] | None = None) -> None:
        self.settings = settings
        self.client_factory = client_factory
        self.providers: dict[str, ModelProvider] = {}
        for cls in BUILTIN_MODELS:
            instance = cls(settings)
            self.providers[instance.name] = instance
        for instance in extra or []:
            self.providers[instance.name] = instance
        self.active = settings.llm_provider if settings.llm_provider in self.providers \
            else "extractive"
        self.history: list[dict[str, Any]] = []

    def available(self) -> list[dict[str, Any]]:
        return [{"name": p.name, "configured": p.configured(),
                 "active": p.name == self.active, "requires_key": p.requires_key}
                for p in self.providers.values()]

    async def complete(self, system: str, prompt: str,
                       max_tokens: int = 1200) -> ModelReply:
        provider = self.providers[self.active]
        started_error = ""
        if provider.name != "extractive":
            client = (self.client_factory() if self.client_factory
                      else httpx.AsyncClient(timeout=self.settings.http_timeout_seconds))
            try:
                reply = await provider.complete(client, system, prompt, max_tokens)
                self.history.append(reply.to_dict())
                return reply
            except Exception as exc:
                started_error = f"{type(exc).__name__}: {exc}"[:300]
                log_event("models", "llm_fallback", level="WARNING",
                          provider=provider.name, error=started_error)
            finally:
                await client.aclose()
        async with httpx.AsyncClient() as local_client:
            reply = await self.providers["extractive"].complete(
                local_client, system, prompt, max_tokens
            )
        reply.fallback_used = bool(started_error)
        reply.error = started_error
        self.history.append(reply.to_dict())
        return reply

    def describe(self) -> dict[str, Any]:
        return {"active": self.active, "providers": self.available(),
                "last_calls": self.history[-5:]}
