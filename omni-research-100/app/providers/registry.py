"""Registre extensible des connecteurs.

Ajouter un fournisseur = implémenter BaseProvider et soit l'enregistrer via
`register()`, soit déclarer `OMNI_PROVIDER_PLUGINS=package.module:Classe`.
Aucune modification du routeur n'est nécessaire.
"""
from __future__ import annotations

import importlib
import os
from typing import Any, Iterable

from ..core.config import Settings
from ..core.logging_conf import log_event
from .base import BaseProvider, ProviderState
from .brave import BraveProvider
from .exa import ExaProvider
from .firecrawl import FirecrawlProvider
from .searxng import SearXNGProvider
from .tavily import TavilyProvider

BUILTIN: tuple[type[BaseProvider], ...] = (
    SearXNGProvider, TavilyProvider, BraveProvider, ExaProvider, FirecrawlProvider,
)


class ProviderRegistry:
    def __init__(self, settings: Settings, plugins: bool = True) -> None:
        self.settings = settings
        self._providers: dict[str, BaseProvider] = {}
        for cls in BUILTIN:
            self.register(cls(settings))
        if plugins:
            self.load_plugins()

    def register(self, provider: BaseProvider) -> None:
        if not isinstance(provider, BaseProvider):
            raise TypeError("Un connecteur doit hériter de BaseProvider")
        if not provider.name or provider.name in self._providers:
            raise ValueError(f"Nom de connecteur invalide ou déjà pris : {provider.name}")
        self._providers[provider.name] = provider

    def load_plugins(self) -> list[str]:
        spec = os.getenv("OMNI_PROVIDER_PLUGINS", "").strip()
        loaded: list[str] = []
        for entry in [x.strip() for x in spec.split(",") if x.strip()]:
            module_name, _, class_name = entry.partition(":")
            if not class_name:
                log_event("providers", "invalid_plugin_spec", level="WARNING", entry=entry)
                continue
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                self.register(cls(self.settings))
                loaded.append(entry)
            except Exception as exc:  # pragma: no cover - dépend des plugins
                log_event("providers", "plugin_load_failed", level="ERROR",
                          entry=entry, error=str(exc))
        return loaded

    def names(self) -> list[str]:
        return list(self._providers)

    def get(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def all(self) -> Iterable[BaseProvider]:
        return self._providers.values()

    def configured(self) -> list[str]:
        return [p.name for p in self._providers.values() if p.is_configured()]

    def set_enabled(self, name: str, enabled: bool) -> None:
        provider = self.get(name)
        if provider is None:
            raise KeyError(name)
        provider.state.enabled = enabled

    def describe(self, quota: Any | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for p in self._providers.values():
            state: ProviderState = p.state
            state.configured = p.is_configured()
            row = {
                "name": p.name, "label": p.label, "status": state.status(),
                "requires_key": p.requires_key, "supports_extract": p.supports_extract,
                "strengths": list(p.strengths), "consecutive_failures": state.consecutive_failures,
                "last_error": state.last_error, "last_latency_ms": state.last_latency_ms,
                "total_calls": state.total_calls, "total_results": state.total_results,
                "quota_limit": p.quota(),
                "verified_live": bool(getattr(state, "verified_live", False)),
            }
            if quota is not None:
                row["quota"] = quota.snapshot([p.name])[p.name]
            rows.append(row)
        return rows
