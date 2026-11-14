"""Intelligent Model Router SUPREME — détection réelle des fournisseurs, routage
par capacité/coût/qualité/latence/confidentialité, fallback et budget.

Aucune connexion simulée : un fournisseur sans clé est `not_configured` ; un
fournisseur configuré mais injoignable est `unreachable`. Les adaptateurs HTTP
réels ne sont appelés que si une clé est présente. Les fixtures de test sont
injectées explicitement et marquées comme telles.
"""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

from .budget import BudgetController
from .config import env_present
from .db import epoch, log_event
from .provider_control import ProviderControl, is_external_endpoint
from .providers import ProviderClient, resolve_key


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
    pricing_verified: bool = False
    pricing_source: str = ""
    pricing_checked_at: str = ""


@dataclass
class Provider:
    name: str
    env_var: str
    base_url: str
    models: list[ModelSpec] = field(default_factory=list)
    status: str = "not_configured"
    latency_ms: float | None = None
    error: str = ""
    kind: str = "openai"
    priority: int = 50
    display_name: str = ""
    cooldown_until: float = 0.0

    @property
    def configured(self) -> bool:
        if self.name == "openai_compat":
            return bool(__import__("os").environ.get("SUPREME_OPENAI_COMPAT_BASE_URL")) and bool(resolve_key(self.env_var, self.name))
        if self.name == "ollama":
            return env_present("OLLAMA_HOST")
        return bool(resolve_key(self.env_var, self.name))


# Métadonnées déclarées (non vérifiées tant qu'un appel réel n'a pas réussi).
# priority : plus petit = plus prioritaire. Mistral/Vide est le fournisseur prioritaire.
DEFAULT_PROVIDERS: list[Provider] = [
    Provider("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1", [
        ModelSpec("mistral", "mistral-small-latest", ("general", "code", "tools"), 0.0002, 0.0006, 32000, True, True),
        ModelSpec("mistral", "mistral-large-latest", ("general", "reasoning", "long-context", "tools"), 0.002, 0.006, 128000, True, True),
    ], kind="mistral", priority=1, display_name="Vide (Mistral AI)"),
    Provider("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1", [
        ModelSpec("groq", "llama-3.1-8b-instant", ("general", "code", "tools"), 0.00005, 0.00008, 128000, True, True),
        ModelSpec("groq", "llama-3.3-70b-versatile", ("general", "reasoning", "code", "tools"), 0.00059, 0.00079, 128000, True, True),
    ], kind="openai", priority=2, display_name="Groq"),
    Provider("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", [
        ModelSpec("deepseek", "deepseek-chat", ("general", "code", "reasoning"), 0.00014, 0.00028, 64000, True, True),
    ], kind="openai", priority=3, display_name="DeepSeek"),
    Provider("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", [
        ModelSpec("openai", "gpt-4o-mini", ("general", "code", "tools", "reasoning"), 0.00015, 0.0006, 128000, True, True),
        ModelSpec("openai", "gpt-4o", ("general", "code", "tools", "reasoning", "long-context"), 0.0025, 0.01, 128000, True, True),
    ], kind="openai", priority=4, display_name="OpenAI"),
    Provider("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", [
        ModelSpec("openrouter", "openrouter/auto", ("general", "tools"), 0.0, 0.0, 128000, True, True),
    ], kind="openai", priority=5, display_name="OpenRouter"),
    Provider("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta", [
        ModelSpec("gemini", "gemini-1.5-flash", ("general", "long-context", "tools"), 0.000075, 0.0003, 1000000, True, True),
    ], kind="gemini", priority=6, display_name="Google Gemini"),
    Provider("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1", [
        ModelSpec("anthropic", "claude-3-5-haiku", ("general", "code", "long-context"), 0.0008, 0.004, 200000, True, True),
    ], kind="anthropic", priority=7, display_name="Anthropic"),
    Provider("ollama", "OLLAMA_HOST", "http://127.0.0.1:11434", [
        ModelSpec("ollama", "llama3.1", ("general", "local"), 0.0, 0.0, 128000, True, True, local=True),
    ], kind="ollama", priority=8, display_name="Ollama (local)"),
]


def _custom_compat_provider() -> Provider | None:
    """Fournisseur compatible OpenAI personnalisé via variables d'environnement."""
    import os
    base = os.environ.get("SUPREME_OPENAI_COMPAT_BASE_URL", "")
    if not base:
        return None
    model = os.environ.get("SUPREME_OPENAI_COMPAT_MODEL", "custom-model")
    return Provider("openai_compat", "SUPREME_OPENAI_COMPAT_API_KEY", base, [
        ModelSpec("openai_compat", model, ("general", "code", "tools"), 0.0, 0.0, 128000, True, True),
    ], kind="openai", priority=9, display_name="API compatible OpenAI (personnalisée)")


class ModelRouter:
    def __init__(self, conn=None, providers: list[Provider] | None = None, budget=None,
                 http_timeout: float = 8.0, allow_network: bool = True, client: ProviderClient | None = None,
                 control: ProviderControl | None = None):
        from dataclasses import replace
        self.conn = conn
        if providers is not None:
            self.providers = providers
        else:
            self.providers = [replace(p, models=list(p.models)) for p in DEFAULT_PROVIDERS]
            custom = _custom_compat_provider()
            if custom is not None:
                self.providers.append(custom)
        self.budget = budget if budget is not None else (BudgetController(conn) if conn is not None else None)
        self.http_timeout = http_timeout
        self.allow_network = allow_network
        self.client = client or ProviderClient(timeout=max(http_timeout, 25.0), allow_network=allow_network)
        self.control = control if control is not None else (ProviderControl(conn, self.budget) if conn is not None else None)
        self.quality_history: dict[str, list[float]] = {}

    def sync_provider_catalog(self) -> None:
        """Charge les modèles réellement découverts ; les prix restent une attestation humaine."""
        if self.control is None:
            return
        from dataclasses import replace
        for prov in self.providers:
            discovered = self.control.discovered_models(prov.name)
            if not discovered:
                continue
            specs = []
            for item in discovered:
                price = self.control.price(prov.name, item["id"])
                specs.append(ModelSpec(
                    prov.name, item["id"], tuple(item["capabilities"] or ["general"]),
                    float(price["input_usd_per_million"]) / 1000 if price else 0.0,
                    float(price["output_usd_per_million"]) / 1000 if price else 0.0,
                    int(item["context"] or 0), bool(item["tools"]), False, local=prov.name == "ollama",
                    pricing_verified=bool(price), pricing_source=price.get("source_url", "") if price else "",
                    pricing_checked_at=price.get("checked_at", "") if price else ""))
            prov.models = specs

    def detect(self) -> list[dict]:
        out = []
        for p in self.providers:
            p.status = "configured" if p.configured else "not_configured"
            p.error = ""
            out.append({"provider": p.name, "configured": p.configured, "status": p.status,
                        "models_declared": [m.model for m in p.models]})
        return out

    def discover_provider(self, name: str) -> dict:
        p = next((x for x in self.providers if x.name == name), None)
        if p is None:
            raise KeyError(f"fournisseur inconnu : {name}")
        if not p.configured:
            return {"provider": name, "ok": False, "status": "not_configured", "models": [], "category": None,
                    "error": "aucun identifiant configuré", "http_status": 0, "latency_ms": 0, "endpoint_host": ""}
        if not self.allow_network:
            return {"provider": name, "ok": False, "status": "network_disabled", "models": [], "category": None,
                    "error": "réseau désactivé", "http_status": 0, "latency_ms": 0, "endpoint_host": ""}
        import os
        key = resolve_key(p.env_var, p.name)
        base = os.environ.get("OLLAMA_HOST", p.base_url) if p.name == "ollama" else p.base_url
        res = self.client.discover_models(provider=p.name, base_url=base, kind=p.kind, api_key=key)
        p.latency_ms = res["latency_ms"]
        p.status = "available" if res["ok"] else ("auth_error" if res["http_status"] in (401, 403) else "unreachable" if res["http_status"] == 0 else "error")
        p.error = res["error"]
        if self.control is not None:
            res["verification_id"] = self.control.record_verification(p.name, res)
            self.sync_provider_catalog()
        return res | {"status": p.status}

    def check_availability(self) -> list[dict]:
        results = [self.discover_provider(p.name) for p in self.providers]
        if self.conn is not None:
            log_event(self.conn, "info", "router", "découverte de modèles effectuée",
                      data={"results": [{k: v for k, v in r.items() if k != "model_details"} for r in results]})
        return results

    def available_models(self) -> list[ModelSpec]:
        """Modèles des fournisseurs vérifiés disponibles (check_availability réussi)."""
        return [m for p in self.providers if p.status == "available" for m in p.models]

    def configured_models(self) -> list[ModelSpec]:
        """Modèles configurés/découverts ; configuré ne signifie pas autorisés ni vérifiés."""
        self.sync_provider_catalog()
        return [m for p in self.providers if p.configured for m in p.models]

    def routable_models(self) -> list[ModelSpec]:
        out = []
        for p in self.providers:
            if not p.configured or p.cooldown_until > epoch():
                continue
            external = is_external_endpoint(p.base_url)
            if external:
                if self.control is None or not self.control.preflight(p.name)["allowed"]:
                    continue
            for m in p.models:
                if external and (not m.pricing_verified or m.context <= 0):
                    continue
                out.append(m)
        return out

    def _quality(self, m: ModelSpec) -> float:
        hist = self.quality_history.get(f"{m.provider}/{m.model}", [])
        return sum(hist) / len(hist) if hist else m.quality_prior

    def route(self, task: dict) -> dict:
        """Sélectionne un modèle. task: {capabilities[], max_cost_usd, privacy, tools_required}."""
        self.detect()
        candidates = self.routable_models()
        if not candidates:
            return {"available": False, "reason": "aucun fournisseur IA configuré, autorisé et tarifé disponible",
                    "fallback": "outil déterministe local si la tâche le permet", "model": None}
        caps = set(task.get("capabilities", ["general"]))
        max_cost = task.get("max_cost_usd", 0.05)
        privacy = task.get("privacy", "standard")
        scored = []
        for m in candidates:
            if task.get("provider") and m.provider != task["provider"]:
                continue
            if task.get("model") and m.model != task["model"]:
                continue
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
            priority_bonus = 0.05 * (1 - min(p.priority, 50) / 50)  # Mistral/Vide prioritaire
            score = (0.5 * cap_score + 0.3 * self._quality(m)
                     + 0.1 * (1 - min(1, est_cost / max(0.0001, max_cost)))
                     - 0.1 * latency_penalty + priority_bonus)
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

    @staticmethod
    def _input_token_bound(messages: list[dict]) -> int:
        """Borne conservatrice sans tokenizer officiel : caractères + marge de overhead.

        Ce n'est pas une estimation marketing ; elle sert uniquement à réserver une
        limite haute avant l'appel. Le coût réel est soldé sur l'usage fournisseur.
        """
        chars = sum(len(str(m.get("content", ""))) for m in messages)
        return int(chars) + 1024

    @staticmethod
    def _cost(spec: ModelSpec, tokens_in: int, tokens_out: int) -> float:
        return (spec.cost_per_1k_in * int(tokens_in) + spec.cost_per_1k_out * int(tokens_out)) / 1000.0

    def complete(self, task: dict, messages: list[dict], max_tokens: int = 1024,
                 temperature: float = 0.2, mission_id: str | None = None,
                 agent_id: str | None = None, task_id: str | None = None,
                 call_key: str | None = None, extra_scopes: list | None = None) -> dict:
        """Routage + VRAI appel HTTP, réservation budgétaire avant chaque tentative.

        Renvoie {ok, text, provider, model, usage, cost_usd, latency_ms, error, attempts}.
        Chaque tentative est tracée (fournisseur/modèle/statut/coût/réservation). Les
        erreurs réseau sans statut HTTP conservent la réservation (`interrupted`) par
        prudence comptable ; aucun fallback ne contourne les quotas centraux.
        """
        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):
            return {"ok": False, "text": "", "error": "max_tokens invalide", "provider": None,
                    "model": None, "cost_usd": 0.0, "attempts": []}
        if max_tokens <= 0:
            return {"ok": False, "text": "", "error": "max_tokens doit être positif", "provider": None,
                    "model": None, "cost_usd": 0.0, "attempts": []}
        task_cap = task.get("max_cost_usd", 0.05)
        try:
            task_cap = float(task_cap)
        except (TypeError, ValueError):
            task_cap = 0.0
        if not math.isfinite(task_cap) or task_cap < 0:
            task_cap = 0.0
        route = self.route(task)
        if not route.get("available"):
            return {"ok": False, "text": "", "error": route.get("reason", "aucun modèle disponible"),
                    "provider": None, "model": None, "cost_usd": 0.0, "attempts": []}
        specs = {f"{m.provider}/{m.model}": m for m in self.configured_models()}
        order = [route["model"]]
        if not task.get("disable_fallback"):
            order += list(route.get("fallbacks", []))
        input_bound = self._input_token_bound(messages)
        attempts = []
        last_error = "aucune tentative"
        base_call_key = call_key or uuid.uuid4().hex
        for key in order:
            spec = specs.get(key)
            prov = next((x for x in self.providers if x.name == spec.provider), None) if spec else None
            if spec is None or prov is None:
                continue
            external = is_external_endpoint(prov.base_url)
            if prov.cooldown_until > epoch():
                attempts.append({"model": key, "ok": False, "skipped": True, "error": "cooldown fournisseur actif"})
                last_error = "cooldown fournisseur actif"
                continue
            if external:
                if self.control is None or self.budget is None:
                    attempts.append({"model": key, "ok": False, "skipped": True, "error": "inférence externe sans contrôle persistant refusée"})
                    last_error = "inférence externe sans contrôle persistant refusée"
                    continue
                gate = self.control.preflight(prov.name, self._cost(spec, input_bound, max_tokens))
                if not gate["allowed"]:
                    attempts.append({"model": key, "ok": False, "skipped": True, "error": gate["reason"]})
                    last_error = gate["reason"]
                    continue
                if not spec.pricing_verified or spec.context <= 0:
                    attempts.append({"model": key, "ok": False, "skipped": True, "error": "prix/contexte non attestés pour ce modèle"})
                    last_error = "prix/contexte non attestés pour ce modèle"
                    continue
            if max_tokens > spec.context or input_bound + max_tokens > spec.context:
                attempts.append({"model": key, "ok": False, "error": "limite de tokens/contexte dépassée",
                                 "skipped": True, "max_tokens": max_tokens, "context": spec.context})
                last_error = "limite de tokens/contexte dépassée"
                continue
            upper_cost = self._cost(spec, input_bound, max_tokens)
            if upper_cost > task_cap + 1e-12:
                attempts.append({"model": key, "ok": False, "error": "borne de coût supérieure au budget maximal",
                                 "skipped": True, "estimated_max_cost_usd": round(upper_cost, 9),
                                 "max_cost_usd": task_cap})
                last_error = "budget maximal insuffisant pour la borne de coût"
                continue
            entries = [("provider", prov.name), ("global", "default")]
            if mission_id:
                entries.append(("mission", mission_id))
            if agent_id:
                entries.append(("agent", agent_id))
            entries.extend(extra_scopes or [])
            reservation_id = None
            if self.budget is not None:
                reservation = self.budget.reserve(
                    entries, upper_cost, mission_id=mission_id, task_id=task_id,
                    provider=prov.name, model=spec.model, tokens_in_est=input_bound,
                    tokens_out_est=max_tokens, call_key=f"{base_call_key}:{key}:{uuid.uuid4().hex[:8]}",
                    guard=(lambda: self.control.preflight(prov.name, upper_cost)) if external else None)
                if not reservation.get("reserved"):
                    attempts.append({"model": key, "ok": False, "error": reservation.get("reason", "réservation refusée"),
                                     "skipped": True, "reservation": reservation})
                    last_error = reservation.get("reason", "réservation refusée")
                    continue
                reservation_id = reservation["reservation_id"]
            api_key = resolve_key(prov.env_var, prov.name)
            res = self.client.complete(provider=prov.name, model=spec.model, messages=messages,
                                       base_url=prov.base_url, kind=prov.kind, api_key=api_key,
                                       max_tokens=max_tokens, temperature=temperature)
            attempt = {"model": key, "provider": prov.name, "ok": res.ok, "http_status": res.http_status,
                       "error": res.error, "latency_ms": round(res.latency_ms, 2),
                       "reservation_id": reservation_id, "estimated_max_cost_usd": round(upper_cost, 9),
                       "category": res.category, "endpoint_host": res.endpoint_host, "request_id": res.request_id}
            if res.ok:
                usage = res.usage or {"input_tokens": 0, "output_tokens": 0}
                tokens_in = int(usage.get("input_tokens", 0) or 0)
                tokens_out = int(usage.get("output_tokens", 0) or 0)
                cost = self._cost(spec, tokens_in, tokens_out)
                attempt.update({"usage": usage, "cost_usd": round(cost, 9), "reservation_status": "settled" if reservation_id else "unmanaged_local",
                                "request_id": res.request_id, "response_id": res.response_id,
                                "endpoint_host": res.endpoint_host, "category": res.category,
                                "finish_reason": res.finish_reason})
                if self.budget is not None and reservation_id:
                    try:
                        settled = self.budget.settle(reservation_id, cost, tokens_in=tokens_in,
                                                     tokens_out=tokens_out, provider=prov.name, model=spec.model)
                        if not settled.get("recorded"):
                            raise ValueError(settled.get("reason", "solde budgétaire refusé"))
                    except Exception as e:
                        self.budget.release(reservation_id, reason=str(e), interrupted=True)
                        attempt.update({"ok": False, "error": f"comptabilisation refusée : {e}"})
                        attempts.append(attempt)
                        last_error = attempt["error"]
                        prov.status = "error"
                        continue
                attempts.append(attempt)
                if self.conn is not None:
                    log_event(self.conn, "info", "router", f"complétion réelle réussie : {key}",
                              mission_id, {"latency_ms": round(res.latency_ms, 2), "cost_usd": round(cost, 9),
                                           "reservation_id": reservation_id, "provider": prov.name, "model": spec.model})
                return {"ok": True, "text": res.text, "provider": prov.name, "model": spec.model,
                        "usage": usage, "cost_usd": round(cost, 9), "latency_ms": round(res.latency_ms, 2),
                        "error": "", "attempts": attempts, "reservation_id": reservation_id,
                        "proof": {"category": res.category, "http_status": res.http_status,
                                  "request_id": res.request_id, "response_id": res.response_id,
                                  "endpoint_host": res.endpoint_host, "reservation_id": reservation_id,
                                  "reservation_status": "settled" if reservation_id else "unmanaged_local",
                                  "usage": usage, "cost_usd": round(cost, 9), "finish_reason": res.finish_reason}}
            # Échec : libérer seulement si le fournisseur a explicitement rejeté avant traitement.
            if self.budget is not None and reservation_id:
                uncertain = res.uncertain or res.http_status == 0 or res.http_status >= 500
                self.budget.release(reservation_id, reason=res.error, interrupted=uncertain)
                attempt["reservation_status"] = "interrupted" if uncertain else "released"
            if res.retry_after_s is not None:
                prov.cooldown_until = epoch() + min(float(res.retry_after_s), 300)
                attempt["retry_after_s"] = res.retry_after_s
            attempts.append(attempt)
            last_error = res.error
            prov.status = "error" if res.http_status else "unreachable"
        if self.conn is not None:
            log_event(self.conn, "warning", "router", "complétion échouée sur tous les fournisseurs",
                      mission_id, {"attempts": attempts})
        return {"ok": False, "text": "", "error": last_error, "provider": None, "model": None,
                "cost_usd": 0.0, "attempts": attempts}

    def status(self) -> dict:
        self.sync_provider_catalog()
        verification = self.control.summary() if self.control else {"verified_count": 0, "connected_recently_count": 0}
        return {"providers": [{"name": p.name, "status": p.status, "configured": p.configured,
                               "latency_ms": p.latency_ms, "error": p.error,
                               "models": [m.model for m in p.models],
                               "priced_models": [m.model for m in p.models if m.pricing_verified],
                               "cooldown_until": p.cooldown_until,
                               "control": self.control.status(p.name) if self.control else None}
                              for p in self.providers],
                "available_count": len(self.available_models()),
                "routable_count": len(self.routable_models()),
                "verification": verification,
                "note": "available_count peut inclure un stub local ; seuls verified/external_api prouvent un fournisseur réel."}
