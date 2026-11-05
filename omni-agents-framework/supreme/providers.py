"""Adaptateurs HTTP réels SUPREME — stdlib, sans secret dans les journaux.

Mistral utilise le contrat HTTP officiel /v1/models et /v1/chat/completions
(Bearer, messages, max_tokens, usage). Ce n'est pas une réimplémentation du SDK
et aucun fournisseur n'est déclaré connecté sans réponse externe réussie.
Les POST d'inférence ne sont jamais rejoués automatiquement : une réponse incertaine
peut avoir été facturée. Les GET de découverte ont seuls des retries bornés.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

from .config import VAR_DIR, ensure_dirs
from .credentials import resolve as resolve_credential, status as credential_status
from .security import redact as redact_patterns

PROVIDER_DEFS: list[dict] = [
    {"name": "mistral", "display_name": "Vide (Mistral AI)", "kind": "mistral",
     "env_var": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1", "priority": 1},
    {"name": "groq", "display_name": "Groq", "kind": "openai",
     "env_var": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1", "priority": 2},
    {"name": "deepseek", "display_name": "DeepSeek", "kind": "openai",
     "env_var": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "priority": 3},
    {"name": "openai", "display_name": "OpenAI", "kind": "openai",
     "env_var": "OPENAI_API_KEY", "base_url": "https://api.openai.com/v1", "priority": 4},
    {"name": "openrouter", "display_name": "OpenRouter", "kind": "openai",
     "env_var": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1", "priority": 5},
    {"name": "gemini", "display_name": "Google Gemini", "kind": "gemini",
     "env_var": "GEMINI_API_KEY", "base_url": "https://generativelanguage.googleapis.com/v1beta", "priority": 6},
    {"name": "anthropic", "display_name": "Anthropic", "kind": "anthropic",
     "env_var": "ANTHROPIC_API_KEY", "base_url": "https://api.anthropic.com/v1", "priority": 7},
    {"name": "ollama", "display_name": "Ollama (local)", "kind": "ollama",
     "env_var": "OLLAMA_HOST", "base_url": "http://127.0.0.1:11434", "priority": 8},
    {"name": "openai_compat", "display_name": "API compatible OpenAI (personnalisée)", "kind": "openai",
     "env_var": "SUPREME_OPENAI_COMPAT_API_KEY", "base_url": "", "priority": 9},
]


def redact(text: str, *secrets: str) -> str:
    out = str(text)
    for secret in secrets:
        if secret and len(secret) >= 4:
            out = out.replace(secret, "[REDACTED]")
    return redact_patterns(out)


def _secrets_file() -> dict:
    from .credentials import _legacy_file
    return _legacy_file()


def resolve_key(env_var: str, provider_name: str = "") -> str:
    if provider_name == "ollama":
        return os.environ.get(env_var, "")
    value, _ = resolve_credential(provider_name, env_var)
    return value


def configured_providers() -> list[dict]:
    out = []
    for d in PROVIDER_DEFS:
        if d["name"] == "openai_compat" and not os.environ.get("SUPREME_OPENAI_COMPAT_BASE_URL"):
            continue
        if d["name"] == "ollama":
            meta = {"configured": bool(os.environ.get("OLLAMA_HOST")), "source": "environment" if os.environ.get("OLLAMA_HOST") else None, "error": None}
        else:
            meta = credential_status(d["name"], d["env_var"])
        out.append({"name": d["name"], "display_name": d["display_name"], "kind": d["kind"],
                    "priority": d["priority"], "configured": meta["configured"],
                    "credential_source": meta["source"], "credential_error": meta["error"],
                    "env_var": d["env_var"]})
    return out


def write_secrets_template() -> str:
    """Compatibilité 1.2.1 : modèle vide 0600. La saisie interactive est préférée."""
    ensure_dirs()
    p = VAR_DIR / "providers.json"
    if not p.is_file():
        template = {d["name"]: "" for d in PROVIDER_DEFS if d["name"] != "ollama"}
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(template, handle, indent=2)
    else:
        st = p.lstat()
        if p.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise PermissionError("fichier de secrets hérité non sûr : régulier, propriétaire courant, chmod 600 requis")
        os.chmod(p, 0o600)
    return str(p)


def build_request(kind: str, base_url: str, model: str, messages: list[dict],
                  api_key: str, max_tokens: int, temperature: float) -> tuple[str, dict, dict]:
    base = base_url.rstrip("/")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if kind in ("openai", "mistral"):
        url = base + "/chat/completions"
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature, "stream": False}
    elif kind == "anthropic":
        url = base + "/messages"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") != "system"]
        payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": convo}
        if system:
            payload["system"] = system
    elif kind == "gemini":
        url = base + f"/models/{urllib.parse.quote(model, safe='')}:generateContent"
        if api_key:
            headers["x-goog-api-key"] = api_key
        contents, system = [], []
        for m in messages:
            if m.get("role") == "system":
                system.append(m["content"])
            else:
                contents.append({"role": "model" if m.get("role") == "assistant" else "user",
                                 "parts": [{"text": m["content"]}]})
        payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system)}]}
    elif kind == "ollama":
        url = base + "/api/chat"
        payload = {"model": model, "messages": messages, "stream": False,
                   "options": {"temperature": temperature, "num_predict": max_tokens}}
    else:
        raise ValueError(f"famille d'API inconnue : {kind}")
    return url, headers, payload


def parse_response(kind: str, data: dict) -> tuple[str, dict]:
    usage = {"input_tokens": 0, "output_tokens": 0}
    if kind in ("openai", "mistral"):
        choices = data.get("choices") or []
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        u = data.get("usage") or {}
        usage = {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0)}
    elif kind == "anthropic":
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        u = data.get("usage") or {}
        usage = {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}
    elif kind == "gemini":
        cands = data.get("candidates") or []
        text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", [])) if cands else ""
        u = data.get("usageMetadata") or {}
        usage = {"input_tokens": u.get("promptTokenCount", 0), "output_tokens": u.get("candidatesTokenCount", 0)}
    elif kind == "ollama":
        text = data.get("message", {}).get("content", "") or ""
        usage = {"input_tokens": data.get("prompt_eval_count", 0), "output_tokens": data.get("eval_count", 0)}
    else:
        text = ""
    return text or "", usage


def _safe_id(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", text) else None


def _category(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return "external_api" if p.scheme == "https" and p.hostname not in ("127.0.0.1", "::1", "localhost") else "local_test"


@dataclass
class CompletionResult:
    ok: bool
    text: str = ""
    provider: str = ""
    model: str = ""
    usage: dict = None
    latency_ms: float = 0.0
    http_status: int = 0
    error: str = ""
    request_id: str | None = None
    response_id: str | None = None
    endpoint_host: str = ""
    category: str = "local_test"
    finish_reason: str = ""
    retry_after_s: float | None = None
    uncertain: bool = False
    transport_attempts: int = 1

    def to_dict(self) -> dict:
        return {"ok": self.ok, "text": self.text, "provider": self.provider, "model": self.model,
                "usage": self.usage or {"input_tokens": 0, "output_tokens": 0},
                "latency_ms": round(self.latency_ms, 2), "http_status": self.http_status,
                "error": self.error, "request_id": self.request_id, "response_id": self.response_id,
                "endpoint_host": self.endpoint_host, "category": self.category,
                "finish_reason": self.finish_reason, "retry_after_s": self.retry_after_s,
                "uncertain": self.uncertain, "transport_attempts": self.transport_attempts}


@dataclass(frozen=True)
class RetryPolicy:
    max_get_retries: int = 2
    base_delay_s: float = 0.25
    max_delay_s: float = 5.0
    max_response_bytes: int = 2_000_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # ne jamais transmettre Authorization à une autre URL


class ProviderClient:
    """Transport réel partagé. Les fixtures sont des serveurs locaux, jamais des clés réelles."""

    def __init__(self, timeout: float = 25.0, allow_network: bool = True,
                 retry_policy: RetryPolicy | None = None, sleep=None):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout doit être fini et positif")
        self.timeout = timeout
        self.allow_network = allow_network
        self.retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep or time.sleep
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _request_json(self, url: str, *, method: str, headers: dict, payload: dict | None = None,
                      api_key: str = "", stop_event=None) -> dict:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        if not self.allow_network:
            return {"ok": False, "status": 0, "data": None, "error": "réseau désactivé (allow_network=False)", "latency_ms": 0, "attempts": 0}
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return {"ok": False, "status": 0, "data": None, "error": "URL invalide : identifiants/query interdits", "latency_ms": 0, "attempts": 0}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and host in ("127.0.0.1", "::1", "localhost")):
            return {"ok": False, "status": 0, "data": None, "error": "HTTPS requis hors boucle locale", "latency_ms": 0, "attempts": 0}
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        retries = self.retry_policy.max_get_retries if method == "GET" else 0
        start = time.monotonic()
        for attempt in range(retries + 1):
            if stop_event is not None and stop_event.is_set():
                return {"ok": False, "status": 0, "data": None, "error": "arrêt demandé", "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt}
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with self._opener.open(req, timeout=self.timeout) as resp:
                    raw = resp.read(self.retry_policy.max_response_bytes + 1)
                    status = resp.status
                    request_id = _safe_id(resp.headers.get("x-request-id") or resp.headers.get("x-kong-request-id"))
                if len(raw) > self.retry_policy.max_response_bytes:
                    return {"ok": False, "status": status, "data": None, "error": "réponse fournisseur trop volumineuse",
                            "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1, "uncertain": method == "POST", "request_id": request_id}
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("objet JSON attendu")
                if not 200 <= status < 300:
                    return {"ok": False, "status": status, "data": None, "error": f"HTTP {status}",
                            "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1, "request_id": request_id}
                return {"ok": True, "status": status, "data": data, "error": "",
                        "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1, "request_id": request_id}
            except urllib.error.HTTPError as exc:
                retry_after = self._retry_after(exc.headers.get("Retry-After") if exc.headers else None)
                try:
                    exc.read(4096)  # borner et fermer ; ne pas journaliser le corps fournisseur
                except Exception:
                    pass
                result = {"ok": False, "status": exc.code, "data": None,
                          "error": redact(f"HTTP {exc.code}", api_key), "retry_after_s": retry_after,
                          "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1,
                          "uncertain": method == "POST" and (exc.code >= 500 or exc.code == 408)}
                if method == "GET" and exc.code in (429, 502, 503, 504) and attempt < retries:
                    delay = min(retry_after if retry_after is not None else self.retry_policy.base_delay_s * (2 ** attempt), self.retry_policy.max_delay_s)
                    if stop_event is not None:
                        if stop_event.wait(delay):
                            result["error"] = "arrêt demandé pendant attente fournisseur"
                            return result
                    else:
                        self._sleep(delay)
                    continue
                return result
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                return {"ok": False, "status": 0, "data": None, "error": redact(f"réseau injoignable : {exc}", api_key)[:200],
                        "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1, "uncertain": method == "POST"}
            except (json.JSONDecodeError, UnicodeError, ValueError):
                return {"ok": False, "status": 200, "data": None, "error": "réponse fournisseur non JSON ou invalide",
                        "latency_ms": (time.monotonic()-start)*1000, "attempts": attempt+1, "uncertain": method == "POST"}
        return {"ok": False, "status": 0, "data": None, "error": "retries épuisés", "latency_ms": 0, "attempts": retries+1}

    @staticmethod
    def _retry_after(value):
        if not value:
            return None
        try:
            return max(0.0, min(3600.0, float(value)))
        except ValueError:
            try:
                dt = parsedate_to_datetime(value)
                return max(0.0, min(3600.0, dt.timestamp() - time.time()))
            except (TypeError, ValueError, OverflowError):
                return None

    def complete(self, *, provider: str, model: str, messages: list[dict], base_url: str,
                 kind: str = "openai", api_key: str = "", max_tokens: int = 1024,
                 temperature: float = 0.2, extra_headers: dict | None = None, stop_event=None) -> CompletionResult:
        try:
            max_tokens = int(max_tokens)
            temperature = float(temperature)
        except (TypeError, ValueError):
            return CompletionResult(False, provider=provider, model=model, error="paramètres de génération invalides")
        if max_tokens <= 0 or not math.isfinite(temperature) or not 0 <= temperature <= 2:
            return CompletionResult(False, provider=provider, model=model, error="max_tokens/temperature hors bornes")
        if not base_url:
            return CompletionResult(False, provider=provider, model=model, error="base_url non configurée pour ce fournisseur")
        try:
            url, headers, payload = build_request(kind, base_url, model, messages, api_key, max_tokens, temperature)
        except ValueError as exc:
            return CompletionResult(False, provider=provider, model=model, error=str(exc))
        if extra_headers:
            headers.update(extra_headers)
        host = urllib.parse.urlparse(url).hostname or ""
        category = _category(url)
        res = self._request_json(url, method="POST", headers=headers, payload=payload, api_key=api_key, stop_event=stop_event)
        common = dict(provider=provider, model=model, latency_ms=res["latency_ms"], http_status=res["status"],
                      request_id=res.get("request_id"), endpoint_host=host, category=category,
                      retry_after_s=res.get("retry_after_s"), uncertain=bool(res.get("uncertain")),
                      transport_attempts=res.get("attempts", 1))
        if not res["ok"]:
            return CompletionResult(False, error=redact(res["error"], api_key), **common)
        data = res["data"]
        text, usage = parse_response(kind, data)
        try:
            if kind in ("openai", "mistral", "anthropic") and not isinstance(data.get("usage"), dict):
                raise ValueError("usage absent")
            if kind == "gemini" and not isinstance(data.get("usageMetadata"), dict):
                raise ValueError("usage absent")
            tin, tout = int(usage["input_tokens"]), int(usage["output_tokens"])
            if tin < 0 or tout < 0 or not text.strip():
                raise ValueError
        except (TypeError, ValueError, KeyError):
            common["uncertain"] = True
            return CompletionResult(False, error="réponse exploitable/usage fournisseur absent ou invalide",
                                    response_id=_safe_id(data.get("id")), **common)
        choices = data.get("choices") or []
        finish = str(choices[0].get("finish_reason", "")) if kind in ("openai", "mistral") and choices else ""
        return CompletionResult(True, text=text, usage={"input_tokens": tin, "output_tokens": tout},
                                response_id=_safe_id(data.get("id")), finish_reason=finish, **common)

    def discover_models(self, *, provider: str, base_url: str, kind: str, api_key: str = "", stop_event=None) -> dict:
        base = base_url.rstrip("/")
        path = "/api/tags" if kind == "ollama" else "/models"
        url = base + path
        headers = {"Accept": "application/json"}
        if api_key:
            if kind == "gemini":
                headers["x-goog-api-key"] = api_key
            elif kind == "anthropic":
                headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
            elif kind != "ollama":
                headers["Authorization"] = f"Bearer {api_key}"
        res = self._request_json(url, method="GET", headers=headers, api_key=api_key, stop_event=stop_event)
        out = {"ok": res["ok"], "provider": provider, "http_status": res["status"],
               "latency_ms": round(res["latency_ms"], 2), "request_id": res.get("request_id"),
               "endpoint_host": urllib.parse.urlparse(url).hostname or "", "category": _category(url),
               "error": redact(res["error"], api_key), "models": [], "retry_after_s": res.get("retry_after_s"),
               "transport_attempts": res.get("attempts", 1), "endpoint": path}
        if not res["ok"]:
            return out
        data = res["data"]
        items = data.get("models", []) if kind == "ollama" else data.get("data", [])
        if not isinstance(items, list):
            out.update(ok=False, error="liste de modèles invalide")
            return out
        for item in items:
            if not isinstance(item, dict):
                continue
            mid = item.get("name") if kind == "ollama" else item.get("id") or item.get("name")
            if not isinstance(mid, str) or not mid:
                continue
            if kind == "gemini":
                mid = mid.removeprefix("models/")
                if "generateContent" not in item.get("supportedGenerationMethods", []):
                    continue
                caps, context, tools = ["general"], int(item.get("inputTokenLimit", 0) or 0), False
            elif kind == "ollama":
                caps, context, tools = ["general", "local"], 0, False
            elif kind == "mistral":
                c = item.get("capabilities") or {}
                if c.get("completion_chat") is False:
                    continue
                caps = ["general"]
                if c.get("function_calling"):
                    caps += ["tools"]
                if c.get("vision"):
                    caps += ["vision"]
                context, tools = int(item.get("max_context_length", 0) or 0), bool(c.get("function_calling"))
            else:
                caps, context, tools = ["general"], int(item.get("context_window", 0) or 0), False
            out["models"].append({"id": mid, "capabilities": caps, "context": context, "tools": tools})
        out["models"].sort(key=lambda m: m["id"])
        return out
