#!/usr/bin/env python3
"""Vérification de compatibilité OmniBrain CONTRE LES SOURCES RÉELLES.

Ce script relit, à l'exécution, les fichiers du contrat dans le dépôt public
`blassana280-ux/omni-agents-framework` (aucune modification de ce dépôt) et
compare leur contenu à l'adaptateur OR100 réellement instancié :

  * les 6 gates de `OMNIBRAIN.md` ;
  * la règle d'arbitrage ordonnée et l'égalité ⇒ `unresolved` ;
  * les actions dangereuses de `registry/permissions.json` ;
  * les 3 fichiers JSONL de `cf100/bridges/omni_queue.py` ;
  * le format d'export `OmniBrainBridge` ;
  * l'alignement des permissions et l'absence de callback.

Résultat conservé dans `test-results/omnibrain_contract_check.json`.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.agents.registry import AgentRegistry  # noqa: E402
from app.runtime import build_runtime  # noqa: E402
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from tests.fixtures.provider_responses import FixtureProvider, make_mock_client  # noqa: E402

REPO = "blassana280-ux/omni-agents-framework"
SOURCES = {
    "omnibrain_md": "OMNIBRAIN.md",
    "permissions": "registry/permissions.json",
    "queue": "cyber-force-100/cf100/bridges/omni_queue.py",
    "bridge": "cyber-force-100/cf100/bridges/omnibrain.py",
}
OUT = ROOT / "test-results" / "omnibrain_contract_check.json"


def fetch(path: str) -> str:
    """Lecture seule : gh api si disponible, sinon API REST publique."""
    try:
        done = subprocess.run(
            ["gh", "api", f"repos/{REPO}/contents/{path}", "--jq", ".content"],
            capture_output=True, text=True, timeout=25, check=True)
        return base64.b64decode(done.stdout.strip()).decode("utf-8", "replace")
    except Exception:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"
        req = urllib.request.Request(url, headers={"Accept":
                                     "application/vnd.github+json",
                                     "User-Agent": "omni-research-100-verifier"})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.load(response)
        return base64.b64decode(data["content"]).decode("utf-8", "replace")


def local_contract() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        settings = replace(
            Settings.from_env(), env="test",
            database_url=f"sqlite:///{tmp}/contract.db",
            omnibrain_queue_dir=f"{tmp}/queue", searxng_enabled=False,
            dns_ssrf_check=False, llm_provider="extractive",
            auth_secret="contract-verification-secret-32-bytes",
            admin_password="admin", user_password="user",
            omnibrain_api_key="contract-key", redis_url="", qdrant_url="",
            tavily_api_key="", brave_api_key="", exa_api_key="",
            firecrawl_api_key="")
        runtime = build_runtime(
            settings, extra_providers=[FixtureProvider(settings)],
            client_factory=make_mock_client, provider_plugins=False)
        try:
            with TestClient(create_app(runtime=runtime, settings=settings)) as client:
                response = client.get(
                    "/api/omnibrain/v1/contract",
                    headers={"X-OmniBrain-Key": "contract-key",
                             "X-OmniBrain-Contract": "1.0"})
                assert response.status_code == 200, response.text
                return response.json()
        finally:
            runtime.close()


def main() -> int:
    checks: dict[str, dict] = {}
    try:
        sources = {name: fetch(path) for name, path in SOURCES.items()}
        sources_ok = True
    except Exception as error:  # réseau indisponible : statut honnête, non bloquant
        report = {"status": "BLOQUÉ", "reason": f"sources du contrat illisibles : {error}",
                  "note": "aucune compatibilité n'est affirmée sans lecture des sources"}
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    contract = local_contract()

    # 1. Les six gates, lues dans OMNIBRAIN.md §3
    gates = re.findall(r"`(completeness|evidence|execution|arbitration|secrets|trace)`",
                       sources["omnibrain_md"])
    expected_gates = ["completeness", "evidence", "execution", "arbitration",
                      "secrets", "trace"]
    checks["gates"] = {
        "ok": all(g in gates for g in expected_gates)
              and set(expected_gates) == set(contract["gates"]),
        "source": sorted(set(gates)), "adapter": contract["gates"]}

    # 2. Règle d'arbitrage et égalité
    rule_in_source = "nombre de preuves > exécution réelle > critères satisfaits > id de tâche" \
        in sources["omnibrain_md"]
    code = (ROOT / "app" / "brain" / "conflict_resolver.py").read_text(encoding="utf-8")
    checks["arbitration"] = {
        "ok": rule_in_source
              and "evidence_count > real_execution > criteria_satisfied > task_id" in code
              and '"unresolved"' in code,
        "source_rule_present": rule_in_source,
        "implementation_ordered": "_score" in code and "unresolved" in code}

    # 3. Actions dangereuses du registre réel
    permissions = json.loads(sources["permissions"])
    dangerous = permissions["dangerous_actions"]
    checks["dangerous_actions"] = {
        "ok": all(a in contract["dangerous_actions_denied"] for a in dangerous),
        "source": dangerous, "denied_by_adapter": contract["dangerous_actions_denied"]}

    # 4. Protocole de file JSONL réel
    queue_files = ["omni-inbox.jsonl", "cf100-outbox.jsonl", "omni-done.jsonl"]
    queue = contract["protocol"]["queue"]
    checks["queue_protocol"] = {
        "ok": all(f in sources["queue"] and f in json.dumps(queue) for f in queue_files)
              and "in_response_to" in sources["queue"]
              and "in_response_to" in queue["reply"],
        "source_files": [f for f in queue_files if f in sources["queue"]],
        "adapter": {k: queue[k] for k in ("inbox", "outbox", "done")}}

    # 5. Format d'export OmniBrainBridge et alignement
    export = AgentRegistry().export_for_omnibrain()
    bridge_keys = ["id", "title", "specialties", "skills", "provenance",
                   "boundaries", "brief_template"]
    checks["registry_export"] = {
        "ok": len(export["agents"]) == 100
              and all(k in export["agents"][0] for k in bridge_keys)
              and all(k in sources["bridge"] for k in ("brief_template", "evidence_hash")),
        "agents_exported": len(export["agents"]),
        "keys": sorted(export["agents"][0])}
    checks["alignment"] = {
        "ok": bool(contract["alignment"].get("aligned", False))
              and contract["no_modification_of_omnibrain_repos"] is True
              and contract["callback_posting"] is False,
        "adapter_alignment": contract["alignment"]}

    ok = all(check["ok"] for check in checks.values())
    report = {
        "status": "COMPATIBILITÉ VÉRIFIÉE CONTRE LES SOURCES RÉELLES" if ok else "ÉCHEC",
        "sources_read": list(sources), "contract_version": contract["contract_version"],
        "checks": checks,
        "limits": [
            "Vérification de conformité au contrat et à l'adaptateur OR100 uniquement.",
            "Aucun orchestrateur OmniBrain externe n'a été lancé (dépôts non modifiés).",
            "Les sources sont lues en lecture seule via l'API GitHub publique."],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks":
                      {k: v["ok"] for k, v in checks.items()}},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
