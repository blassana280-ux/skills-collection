"""Vérifications de déploiement et du garde SSRF DNS.

La résolution DNS réelle n'est pas joignable depuis ce sandbox : le résolveur
est donc contrôlé par monkeypatch, ce qui valide la LOGIQUE de la garde (IPv4
privée publique, échec DNS, mode hors ligne) sans prétendre à un test réseau
réel. Les manifests Docker et les scripts de sauvegarde sont validés par
exécution (`bash -n`) et analyse structurelle.
"""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import pytest
import yaml

from app.core.errors import UnsafeURL
from app.core.security import check_url_syntax, validate_public_url

ROOT = Path(__file__).resolve().parents[1]


def _fake_resolver(addresses):
    def resolve(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in addresses]
    return resolve


def test_dns_guard_blocks_private_addresses(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo",
                        _fake_resolver(["192.168.1.10", "10.0.0.4"]))
    with pytest.raises(UnsafeURL, match="non publique"):
        validate_public_url("https://research.example.org/page", require_dns=True)


def test_dns_guard_allows_public_addresses(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo",
                        _fake_resolver(["93.184.216.34", "8.8.8.8"]))
    url = "https://research.example.org/page"
    assert validate_public_url(url, require_dns=True) == url


def test_dns_guard_handles_resolution_failure(monkeypatch):
    def broken(host, port, *args, **kwargs):
        raise socket.gaierror("name or service not known")
    monkeypatch.setattr(socket, "getaddrinfo", broken)
    with pytest.raises(UnsafeURL, match="Résolution DNS impossible"):
        validate_public_url("https://inconnu.example.org", require_dns=True)
    # Mode hors ligne explicite : la syntaxe reste vérifiée, sans fetch DNS.
    assert validate_public_url("https://inconnu.example.org",
                               require_dns=False) == "https://inconnu.example.org"


def test_url_syntax_refuses_unsafe_schemes_and_hosts():
    for bad in ("file:///etc/passwd", "ftp://example.org", "http://127.0.0.1/a",
                "http://10.0.0.1/a", "http://user:pass@example.org/a",
                "http://localhost/a", "http://metadata.google.internal/a"):
        with pytest.raises(UnsafeURL):
            check_url_syntax(bad)
    assert check_url_syntax("https://example.org/a?q=1") == "https://example.org/a?q=1"


def test_docker_manifests_are_consistent_and_secret_free():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"app", "postgres", "redis", "qdrant", "searxng"} <= set(services)
    assert set(services["app"]["depends_on"]) == {"postgres", "redis", "qdrant", "searxng"}
    assert services["postgres"]["healthcheck"]["test"]
    assert not any(s.get("privileged") for s in services.values())
    for volume in compose["volumes"]:
        assert volume in ("pg-data", "redis-data", "qdrant-data", "app-data",
                          "searxng-data")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER omni" in dockerfile and "EXPOSE 8000" in dockerfile
    assert "--host" in dockerfile and "0.0.0.0" in dockerfile and "HEALTHCHECK" in dockerfile
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for name in ("OMNI_SEARXNG_SECRET", "OMNI_AUTH_SECRET", "OMNI_DATABASE_URL"):
        assert name in env_example
    # Aucune clé réelle ne doit se trouver dans les manifests.
    for path in (ROOT / "docker-compose.yml", ROOT / "Dockerfile"):
        text = path.read_text(encoding="utf-8")
        assert "tvly-" not in text and "sk-" not in text
    searx = yaml.safe_load((ROOT / "deploy/searxng-settings.yml").read_text(encoding="utf-8"))
    assert "json" in searx["search"]["formats"]


def test_backup_and_restore_scripts_are_valid_and_require_confirmation():
    backup = ROOT / "deploy/backup_postgres.sh"
    restore = ROOT / "deploy/restore_postgres.sh"
    for script in (backup, restore):
        assert script.is_file() and script.stat().st_mode & 0o111
        done = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
    text = restore.read_text(encoding="utf-8")
    assert "RESTAURER" in text and "read -r -p" in text
    assert "Restauration annulée" in text
    assert (ROOT / "scripts/bootstrap_remote.sh").is_file()
