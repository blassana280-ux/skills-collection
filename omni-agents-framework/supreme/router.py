"""Intelligent Model Router SUPREME — détection réelle des fournisseurs, routage
par capacité/coût/qualité/latence/confidentialité, fallback et budget.

Aucune connexion simulée : un fournisseur sans clé est `not_configured` ; un
fournisseur configuré mais injoignable est `unreachable`. Les adaptateurs HTTP
réels ne sont appelés que si une clé est présente. Les fixtures de test sont
injectées explicitement et marquées comme telles.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import env_present
from .db import log_event


@dataclass
class ModelSpec:
    provider: str
    model: str
    capabilities: tuple[str, ...]
    cost_per_1k_in: float
    cost_per_1k_out: float
    context: int
    tools: bool
    streaming: bool
    local: bool = False
    quality_prior: float = 0.5


@dataclass
class Provider:
    name: str
    env_var: str
    base_url: str
    models: list[ModelSpec] = field(default_factory=list)
    status: str = "not_configured"
    latency_ms: float | None = None
    error: str = ""

    @property
    def configured(self) -> bool:
        return env_present(self.env_var) or (self.name == "ollama" and env_present("OLLAMA_HOST"))


# Métadonnées déclarées (non vérifiées tant que le fournisseur n'est pas testé).
DEFAULT_PROVIDERS: list[Provider] = [
    Provider("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", [
        ModelSpec("openai", "gpt-4o-mini", ("general", "code", "tools", "reasoning"), 0.00015, 0.0006, 128000, True, True),
        ModelSpec("openai", "gpt-4o", ("general", "code", "tools", "reasoning", "long-context"), 0.0025, 0.01, 128000, True, True),
    ]),
    Provider("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1", [
        ModelSpec("mistral", "mistral-small-latest", ("general", "code", "tools"), 0.0002, 0.0006, 32000, True, True),
        ModelSpec("mistral", "mistral-large-latest", ("general", "reasoning", "long-context", "tools"), 0.002, 0.006, 128000, True, True),
    ]),
    Provider("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", [
        ModelSpec("deepseek", "deepseek-chat", ("general", "code", "reasoning"), 0.00014, 0.00028, 64000, True, True),
    ]),
    Provider("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta", [
        ModelSpec("gemini", "gemini-1.5-flash", ("general", "long-context", "tools"), 0.000075, 0.0003, 1000000, True, True),
    ]),
    Provider("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", [
        ModelSpec("openrouter", "openrouter/auto", ("general", "tools"), 0.0, 0.0, 128000, True, True),
    ]),
    Provider("ollama", "OLLAMA_HOST", "http://127.0.0.1:11434", [
        ModelSpec("ollama", "llama3.1", ("general", "local"), 0.0, 0.0, 128000, True, True, local=True),
    ]),
    Provider("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1", [
        ModelSpec("anthropic", "claude-3-5-haiku", ("general", "code", "long-context"), 0.0008, 0.004, 200000, True, True),
    ]),
]


class ModelRouter:
    def __init__(self, conn=None, providers: list[Provider] | None = None, budget=None,
                 http_timeout: float = 8.0, allow_network: bool = True):
        self.conn = conn
        self.providers = providers if providers is not None else [Provider(p.name, p.env_var, p.base_url, list(p.models), p.status) for p in DEFAULT_PROVIDERS]
        self.budget = budget
        self.http_timeout = http_timeout
        self.allow_network = allow_network
        self.quality_history: dict[str, list[float]] = {}

    def detect(self) -> list[dict]:
        out = []
        for p in self.providers:
            p.status = "configured" if p.configured else "not_configured"
            p.error = ""
            out.append({"provider": p.name, "configured": p.configured, "status": p.status,
                        "models_declared": [m.model for m in p.models]})
        return out

    def check_availability(self) -> list[dict]:
        """Vérification RÉELLE : appel HTTP seulement si configuré et réseau autorisé."""
        results = []
        for p in self.providers:
            if not p.configured:
                p.status = "not_configured"
                results.append({"provider": p.name, "status": p.status, "models": []})
                continue
            if not self.allow_network:
                p.status = "network_disabled"
                results.append({"provider": p.name, "status": p.status, "models": []})
                continue
            start = time.monotonic()
            try:
                req = urllib.request.Request(p.base_url.rstrip("/") + "/models", method="GET")
                key = __import__("os").environ.get(p.env_var, "")
                if p.name == "gemini":
                    req = urllib.request.Request(p.base_url.rstrip("/") + f"/models?key={key}")
                elif p.name == "ollama":
                    req = urllib.request.Request(p.base_url.rstrip("/") + "/api/tags")
                elif key:
                    req.add_header("Authorization", f"Bearer {key}")
                with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
                    status = resp.status
                p.latency_ms = (time.monotonic() - start) * 1000
                p.status = "available" if 200 <= status < 300 else "error"
                p.error = "" if p.status == "available" else f"HTTP {status}"
            except urllib.error.HTTPError as e:
                p.status = "auth_error" if e.code in (401, 403) else "error"
                p.error = f"HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                p.status = "unreachable"
                p.error = str(e)[:120]
            results.append({"provider": p.name, "status": p.status, "latency_ms": p.latency_ms,
                            "error": p.error, "models": [m.model for m in p.models] if p.status == "available" else []})
        if self.conn is not None:
            log_event(self.conn, "info", "router", "vérification disponibilité fournisseurs", data={"results": results})
        return results

    def available_models(self) -> list[ModelSpec]:
        return [m for p in self.providers if p.status == "available" for m in p.models]

    def _quality(self, m: ModelSpec) -> float:
        hist = self.quality_history.get(f"{m.provider}/{m.model}", [])
        return sum(hist) / len(hist) if hist else m.quality_prior

    def route(self, task: dict) -> dict:
        """Sélectionne un modèle. task: {capabilities[], max_cost_usd, privacy, tools_required}."""
        self.detect()
        candidates = self.available_models()
        if not candidates:
            return {"available": False, "reason": "aucun fournisseur IA configuré et disponible",
                    "fallback": "outil déterministe local si la tâche le permet", "model": None}
        caps = set(task.get("capabilities", ["general"]))
        max_cost = task.get("max_cost_usd", 0.05)
        privacy = task.get("privacy", "standard")
        scored = []
        for m in candidates:
            if privacy == "local-only" and not m.local:
                continue
            if task.get("tools_required") and not m.tools:
                continue
            cap_score = len(caps & set(m.capabilities)) / max(1, len(caps))
            est_cost = m.cost_per_1k_in * 2 + m.cost_per_1k_out * 1
            if est_cost > max_cost:
                continue
            p = next(x for x in self.providers if x.name == m.provider)
            latency_penalty = (p.latency_ms or 500) / 5000
            score = 0.5 * cap_score + 0.3 * self._quality(m) + 0.1 * (1 - min(1, est_cost / max(0.0001, max_cost))) - 0.1 * latency_penalty
            scored.append((score, m))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return {"available": False, "reason": "aucun modèle ne satisfait les contraintes", "model": None}
        best = scored[0][1]
        fallbacks = [f"{m.provider}/{m.model}" for _, m in scored[1:4]]
        return {"available": True, "model": f"{best.provider}/{best.model}", "spec": best,
                "fallbacks": fallbacks, "score": round(scored[0][0], 4)}

    def record_quality(self, model_key: str, score: float) -> None:
        self.quality_history.setdefault(model_key, []).append(max(0.0, min(1.0, score)))

    def status(self) -> dict:
        return {"providers": [{"name": p.name, "status": p.status, "configured": p.configured,
                               "latency_ms": p.latency_ms, "error": p.error,
                               "models": [m.model for m in p.models]} for p in self.providers],
                "available_count": len(self.available_models())}
