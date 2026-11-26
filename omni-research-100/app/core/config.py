"""Configuration centrale, entièrement pilotée par l'environnement.

Aucune valeur n'est inventée : une clé absente => fournisseur « non configuré ».
"""
from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    public_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"

    auth_secret: str = "dev-only-change-me-please-32-bytes-minimum"
    token_ttl_minutes: int = 720
    admin_password: str = "change-me-admin"
    user_password: str = "change-me-user"
    omnibrain_api_key: str = "change-me-omnibrain-key"
    omnibrain_queue_dir: str = "./data/omnibrain-queue"

    database_url: str = "sqlite:///./data/omni_research.db"
    redis_url: str = ""
    qdrant_url: str = ""
    qdrant_collection: str = "omni_research_evidence"
    retention_days: int = 90

    searxng_url: str = "http://searxng:8080"
    searxng_enabled: bool = True
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"
    brave_api_key: str = ""
    brave_base_url: str = "https://api.search.brave.com"
    exa_api_key: str = ""
    exa_base_url: str = "https://api.exa.ai"
    firecrawl_api_key: str = ""
    firecrawl_base_url: str = "https://api.firecrawl.dev/v1"

    quota_searxng: int = 0
    quota_tavily: int = 100
    quota_brave: int = 100
    quota_exa: int = 100
    quota_firecrawl: int = 100

    llm_provider: str = "extractive"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1"

    max_parallel_agents: int = 8
    max_concurrent_missions: int = 4
    max_agents_per_mission: int = 100
    max_sources_per_mission: int = 60
    max_extractions_per_mission: int = 12
    http_timeout_seconds: int = 12
    max_content_bytes: int = 262144
    max_query_length: int = 600
    rate_limit_per_minute: int = 60
    provider_failure_cooldown_seconds: int = 30
    # Désactivable uniquement pour les environnements hors ligne / tests :
    # le contrôle syntaxique SSRF reste toujours actif.
    dns_ssrf_check: bool = True

    # Réglages modifiables à chaud via /api/settings (persistés en base).
    mutable: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            env=os.getenv("OMNI_ENV", "development"),
            host=os.getenv("OMNI_HOST", "0.0.0.0"),
            port=_int("OMNI_PORT", 8000),
            public_base_url=os.getenv("OMNI_PUBLIC_BASE_URL", "http://localhost:8000"),
            log_level=os.getenv("OMNI_LOG_LEVEL", "INFO"),
            auth_secret=os.getenv("OMNI_AUTH_SECRET", cls.auth_secret),
            token_ttl_minutes=_int("OMNI_TOKEN_TTL_MINUTES", 720),
            admin_password=os.getenv("OMNI_ADMIN_PASSWORD", cls.admin_password),
            user_password=os.getenv("OMNI_USER_PASSWORD", cls.user_password),
            omnibrain_api_key=os.getenv("OMNI_OMNIBRAIN_API_KEY", cls.omnibrain_api_key),
            omnibrain_queue_dir=os.getenv("OMNI_OMNIBRAIN_QUEUE_DIR",
                                          cls.omnibrain_queue_dir),
            database_url=os.getenv("OMNI_DATABASE_URL", cls.database_url),
            redis_url=os.getenv("OMNI_REDIS_URL", ""),
            qdrant_url=os.getenv("OMNI_QDRANT_URL", ""),
            qdrant_collection=os.getenv("OMNI_QDRANT_COLLECTION", cls.qdrant_collection),
            retention_days=_int("OMNI_RETENTION_DAYS", 90),
            searxng_url=os.getenv("OMNI_SEARXNG_URL", cls.searxng_url),
            searxng_enabled=_bool("OMNI_SEARXNG_ENABLED", True),
            tavily_api_key=os.getenv("OMNI_TAVILY_API_KEY", ""),
            tavily_base_url=os.getenv("OMNI_TAVILY_BASE_URL", cls.tavily_base_url),
            brave_api_key=os.getenv("OMNI_BRAVE_API_KEY", ""),
            brave_base_url=os.getenv("OMNI_BRAVE_BASE_URL", cls.brave_base_url),
            exa_api_key=os.getenv("OMNI_EXA_API_KEY", ""),
            exa_base_url=os.getenv("OMNI_EXA_BASE_URL", cls.exa_base_url),
            firecrawl_api_key=os.getenv("OMNI_FIRECRAWL_API_KEY", ""),
            firecrawl_base_url=os.getenv("OMNI_FIRECRAWL_BASE_URL", cls.firecrawl_base_url),
            quota_searxng=_int("OMNI_QUOTA_SEARXNG", 0),
            quota_tavily=_int("OMNI_QUOTA_TAVILY", 100),
            quota_brave=_int("OMNI_QUOTA_BRAVE", 100),
            quota_exa=_int("OMNI_QUOTA_EXA", 100),
            quota_firecrawl=_int("OMNI_QUOTA_FIRECRAWL", 100),
            llm_provider=os.getenv("OMNI_LLM_PROVIDER", "extractive"),
            openai_base_url=os.getenv("OMNI_OPENAI_BASE_URL", cls.openai_base_url),
            openai_api_key=os.getenv("OMNI_OPENAI_API_KEY", ""),
            openai_model=os.getenv("OMNI_OPENAI_MODEL", cls.openai_model),
            anthropic_base_url=os.getenv("OMNI_ANTHROPIC_BASE_URL", cls.anthropic_base_url),
            anthropic_api_key=os.getenv("OMNI_ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("OMNI_ANTHROPIC_MODEL", cls.anthropic_model),
            ollama_base_url=os.getenv("OMNI_OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.getenv("OMNI_OLLAMA_MODEL", cls.ollama_model),
            max_parallel_agents=max(1, _int("OMNI_MAX_PARALLEL_AGENTS", 8)),
            max_concurrent_missions=max(1, _int("OMNI_MAX_CONCURRENT_MISSIONS", 4)),
            max_agents_per_mission=max(1, _int("OMNI_MAX_AGENTS_PER_MISSION", 100)),
            max_sources_per_mission=max(1, _int("OMNI_MAX_SOURCES_PER_MISSION", 60)),
            max_extractions_per_mission=max(0, _int("OMNI_MAX_EXTRACTIONS_PER_MISSION", 12)),
            http_timeout_seconds=max(1, _int("OMNI_HTTP_TIMEOUT_SECONDS", 12)),
            max_content_bytes=_int("OMNI_MAX_CONTENT_BYTES", 262144),
            max_query_length=_int("OMNI_MAX_QUERY_LENGTH", 600),
            rate_limit_per_minute=max(1, _int("OMNI_RATE_LIMIT_PER_MINUTE", 60)),
            provider_failure_cooldown_seconds=max(
                1, _int("OMNI_PROVIDER_FAILURE_COOLDOWN_SECONDS", 30)
            ),
            dns_ssrf_check=_bool("OMNI_DNS_SSRF_CHECK", True),
        )

    def provider_keys(self) -> dict[str, str]:
        return {
            "searxng": self.searxng_url if self.searxng_enabled else "",
            "tavily": self.tavily_api_key,
            "brave": self.brave_api_key,
            "exa": self.exa_api_key,
            "firecrawl": self.firecrawl_api_key,
        }

    def quota_for(self, provider: str) -> int:
        return int(
            getattr(self, f"quota_{provider}", 0)
        )

    def has_default_secret(self) -> bool:
        return "dev-only" in self.auth_secret

    def public_dict(self) -> dict[str, Any]:
        """État diffusable : jamais de secret, jamais de clé API."""
        d = asdict(self)
        for key in (
            "auth_secret", "admin_password", "user_password", "omnibrain_api_key",
            "tavily_api_key", "brave_api_key", "exa_api_key", "firecrawl_api_key",
            "openai_api_key", "anthropic_api_key",
        ):
            d.pop(key, None)
        d["configured_providers"] = [k for k, v in self.provider_keys().items() if v]
        d["default_secret_in_use"] = self.has_default_secret()
        return d


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reset_settings() -> None:
    get_settings.cache_clear()


def load_dotenv() -> None:
    """Charge .env sans dépendance obligatoire."""
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
