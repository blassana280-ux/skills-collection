"""Fournisseurs IA réels SUPREME — client HTTP stdlib, multi-fournisseurs modulaire.

Aucune réponse simulée : `complete()` effectue un VRAI appel HTTP vers le fournisseur.
Sans clé -> non configuré. Sans réseau/clé invalide -> erreur honnête. Les clés ne
sont JAMAIS journalisées ni renvoyées ; elles sont lues depuis l'environnement ou un
fichier de secrets gitignoré (0600), et expurgées de toute erreur.

Familles d'API supportées :
  - openai      : OpenAI, Mistral (Vide), DeepSeek, Groq, OpenRouter, tout compatible
                  OpenAI (base_url + clé + modèle), Ollama en mode /v1.
  - anthropic   : Anthropic Messages API.
  - gemini      : Google Generative Language API.
  - ollama      : API native Ollama (local).

Priorité : Mistral/Vide en premier (priority=1), puis le reste. Le routeur reste
libre de choisir selon capacité/coût/qualité/latence/confidentialité.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import VAR_DIR, ensure_dirs

# ---------------------------------------------------------------------------
# Définitions des fournisseurs (métadonnées déclarées, non vérifiées tant qu'un
# appel réel n'a pas réussi). `priority` : plus petit = plus prioritaire.
# ---------------------------------------------------------------------------
PROVIDER_DEFS: list[dict] = [
    {"name": "mistral", "display_name": "Vide (Mistral AI)", "kind": "openai",
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
    """Expurge tout secret d'un texte (erreurs, journaux)."""
    out = str(text)
    for s in secrets:
        if s and len(s) >= 4:
            out = out.replace(s, "[REDACTED]")
    return out


def _secrets_file() -> dict:
    """Fichier de secrets optionnel, gitignoré, 0600. Ne jamais logger son contenu."""
    p = VAR_DIR / "providers.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items() if isinstance(v, str)}
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_key(env_var: str, provider_name: str = "") -> str:
    """Résout une clé : environnement d'abord, puis fichier de secrets gitignoré.

    La clé n'est jamais journalisée. Pour Ollama, 'env_var' est l'hôte (pas un secret).
    """
    val = os.environ.get(env_var, "")
    if val:
        return val
    sf = _secrets_file()
    return sf.get(provider_name, "") or sf.get(env_var, "")


def configured_providers() -> list[dict]:
    """Liste les fournisseurs configurés (clé présente) SANS exposer les clés."""
    out = []
    for d in PROVIDER_DEFS:
        if d["name"] == "openai_compat":
            base = os.environ.get("SUPREME_OPENAI_COMPAT_BASE_URL", "")
            if not base:
                continue
        key = resolve_key(d["env_var"], d["name"])
        present = bool(key) or (d["name"] == "ollama" and bool(os.environ.get("OLLAMA_HOST")))
        out.append({"name": d["name"], "display_name": d["display_name"], "kind": d["kind"],
                    "priority": d["priority"], "configured": present,
                    "env_var": d["env_var"]})
    return out


def write_secrets_template() -> str:
    """Crée un modèle de fichier de secrets (valeurs vides) en 0600, gitignoré.

    N'écrit AUCUNE clé réelle. L'utilisateur remplit le fichier hors dépôt.
    """
    ensure_dirs()
    p = VAR_DIR / "providers.json"
    if not p.is_file():
        template = {d["name"]: "" for d in PROVIDER_DEFS if d["name"] != "ollama"}
        p.write_text(json.dumps(template, indent=2), encoding="utf-8")
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    return str(p)


# ---------------------------------------------------------------------------
# Construction des requêtes / analyse des réponses par famille d'API.
# ---------------------------------------------------------------------------
def build_request(kind: str, base_url: str, model: str, messages: list[dict],
                  api_key: str, max_tokens: int, temperature: float) -> tuple[str, dict, dict]:
    base = base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if kind == "openai":
        url = base + "/chat/completions"
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature}
    elif kind == "anthropic":
        url = base + "/messages"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") != "system"]
        payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                   "messages": convo}
        if system:
            payload["system"] = system
    elif kind == "gemini":
        url = base + f"/models/{model}:generateContent"
        if api_key:
            headers["x-goog-api-key"] = api_key
        contents = []
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        for m in messages:
            if m.get("role") == "system":
                continue
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload = {"contents": contents,
                   "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
    elif kind == "ollama":
        url = base + "/api/chat"
        payload = {"model": model, "messages": messages, "stream": False,
                   "options": {"temperature": temperature, "num_predict": max_tokens}}
    else:
        raise ValueError(f"famille d'API inconnue : {kind}")
    return url, headers, payload


def parse_response(kind: str, data: dict) -> tuple[str, dict]:
    """Extrait le texte et l'usage (tokens) d'une réponse fournisseur réelle."""
    usage = {"input_tokens": 0, "output_tokens": 0}
    if kind == "openai":
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        u = data.get("usage", {}) or {}
        usage = {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0)}
    elif kind == "anthropic":
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        u = data.get("usage", {}) or {}
        usage = {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}
    elif kind == "gemini":
        cands = data.get("candidates", [{}])
        text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", [])) if cands else ""
        u = data.get("usageMetadata", {}) or {}
        usage = {"input_tokens": u.get("promptTokenCount", 0), "output_tokens": u.get("candidatesTokenCount", 0)}
    elif kind == "ollama":
        text = data.get("message", {}).get("content", "") or ""
        usage = {"input_tokens": data.get("prompt_eval_count", 0), "output_tokens": data.get("eval_count", 0)}
    else:
        text = ""
    return text, usage


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

    def to_dict(self) -> dict:
        return {"ok": self.ok, "text": self.text, "provider": self.provider, "model": self.model,
                "usage": self.usage or {"input_tokens": 0, "output_tokens": 0},
                "latency_ms": round(self.latency_ms, 2), "http_status": self.http_status,
                "error": self.error}


class ProviderClient:
    """Client HTTP réel. N'écrit jamais la clé dans les journaux/erreurs."""

    def __init__(self, timeout: float = 25.0, allow_network: bool = True):
        self.timeout = timeout
        self.allow_network = allow_network

    def complete(self, *, provider: str, model: str, messages: list[dict], base_url: str,
                 kind: str = "openai", api_key: str = "", max_tokens: int = 1024,
                 temperature: float = 0.2, extra_headers: dict | None = None) -> CompletionResult:
        if not self.allow_network:
            return CompletionResult(False, provider=provider, model=model,
                                    error="réseau désactivé (allow_network=False)")
        if not base_url:
            return CompletionResult(False, provider=provider, model=model,
                                    error="base_url non configurée pour ce fournisseur")
        try:
            url, headers, payload = build_request(kind, base_url, model, messages,
                                                  api_key, max_tokens, temperature)
        except ValueError as e:
            return CompletionResult(False, provider=provider, model=model, error=str(e))
        if extra_headers:
            headers.update(extra_headers)
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8", errors="replace")
            latency = (time.monotonic() - start) * 1000
            data = json.loads(raw)
            text, usage = parse_response(kind, data)
            return CompletionResult(True, text=text, provider=provider, model=model,
                                    usage=usage, latency_ms=latency, http_status=status)
        except urllib.error.HTTPError as e:
            latency = (time.monotonic() - start) * 1000
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            # Expurge la clé et tout en-tête d'auth du message d'erreur.
            msg = redact(f"HTTP {e.code}: {detail}", api_key)
            return CompletionResult(False, provider=provider, model=model,
                                    latency_ms=latency, http_status=e.code, error=msg)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            latency = (time.monotonic() - start) * 1000
            return CompletionResult(False, provider=provider, model=model, latency_ms=latency,
                                    error=redact(f"réseau injoignable : {e}", api_key)[:200])
        except json.JSONDecodeError:
            return CompletionResult(False, provider=provider, model=model,
                                    error="réponse fournisseur non JSON")
