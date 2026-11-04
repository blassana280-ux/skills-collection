"""Adaptateur OmniBrain v1 : contrat réel, sécurité, file JSONL, arbitrage."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.registry import OMNIBRAIN_DANGEROUS_ACTIONS


@pytest.mark.omnibrain
def test_bad_api_key_is_rejected(client):
    response = client.get("/api/omnibrain/v1/contract",
                          headers={"X-OmniBrain-Key": "wrong-key"})
    assert response.status_code == 401


@pytest.mark.omnibrain
def test_contract_matches_inspected_omnibrain_sources(client, omnibrain_auth):
    r = client.get("/api/omnibrain/v1/contract", headers=omnibrain_auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["contract_version"] == "1.0"
    assert data["agents_exported"] == 100
    assert any("OMNIBRAIN.md" in s for s in data["source_of_truth"])
    assert any("bridges/omnibrain.py" in s for s in data["source_of_truth"])
    assert any("omni_queue.py" in s for s in data["source_of_truth"])
    assert data["alignment"]["aligned"] is True
    assert set(OMNIBRAIN_DANGEROUS_ACTIONS) <= set(data["dangerous_actions_denied"])
    assert len(data["gates"]) == 6
    assert data["no_modification_of_omnibrain_repos"] is True
    assert set(data["registry_export"]["agents"][0]) == {
        "id", "title", "specialties", "skills", "provenance", "boundaries",
        "brief_template"}


@pytest.mark.omnibrain
def test_modes_and_version_guard(client, omnibrain_auth):
    modes = client.get("/api/omnibrain/v1/modes", headers=omnibrain_auth)
    assert modes.status_code == 200
    assert set(modes.json()["modes"]) == {"fast", "deep", "maximum"}
    bad = client.post("/api/omnibrain/v1/missions",
                      headers={**omnibrain_auth, "X-OmniBrain-Contract": "2.0"},
                      json={"request": "Version incompatible"})
    assert bad.status_code == 422


@pytest.mark.omnibrain
def test_submit_choose_mode_track_cancel_results_report_evidence(client,
                                                                 omnibrain_auth,
                                                                 runtime, settings):
    submitted = client.post("/api/omnibrain/v1/missions", headers=omnibrain_auth,
                            json={"contract_version": "1.0", "skill": "technology",
                                  "request": "Dernières versions de l'API et CVE ?",
                                  "task": {"mode": "fast"},
                                  "context": {"language": "fr"}})
    assert submitted.status_code == 202, submitted.text
    body = submitted.json()
    assert body["accepted"] is True and body["mode"] == "fast"
    mid = body["mission_id"]
    status = client.get(f"/api/omnibrain/v1/missions/{mid}",
                        headers=omnibrain_auth)
    assert status.status_code == 200
    assert {"agent", "ok", "result", "evidence_hash"} <= set(status.json())
    results = client.get(f"/api/omnibrain/v1/missions/{mid}/results",
                         headers=omnibrain_auth).json()
    assert results["agent"] == "omni-research-100"
    assert "result" in results
    report = client.get(f"/api/omnibrain/v1/missions/{mid}/report",
                        headers=omnibrain_auth).json()
    assert "citations" in report and "markdown" in report
    evidence = client.get(f"/api/omnibrain/v1/missions/{mid}/evidence",
                          headers=omnibrain_auth).json()
    assert evidence["evidence_hash"] and "sources" in evidence

    # Annulation sur une mission créée mais non lancée : déterministe.
    parked = runtime.commander.create("mission en attente", __import__(
        "app.core.schemas", fromlist=["Mode"]).Mode.DEEP, "omnibrain")
    cancelled = client.delete(f"/api/omnibrain/v1/missions/{parked}",
                              headers=omnibrain_auth)
    assert cancelled.json()["cancelled"] is True
    assert cancelled.json()["result"]["status"] == "cancelled"


@pytest.mark.omnibrain
def test_jsonl_queue_protocol_compatibility(client, omnibrain_auth, settings):
    directory = Path(settings.omnibrain_queue_dir)
    directory.mkdir(parents=True, exist_ok=True)
    inbox = directory / "omni-inbox.jsonl"
    inbox.write_text("\n".join([
        json.dumps({"id": "OMNI-1", "skill": "research",
                    "request": "Étude 2025 sur les API", "task": {"mode": "fast"}}),
        json.dumps({"id": "OMNI-2", "skill": "research",
                    "request": "x", "task": {}}),
    ]) + "\n", encoding="utf-8")
    before = client.get("/api/omnibrain/v1/queue/status",
                        headers=omnibrain_auth).json()
    assert before["pending"] == 2
    processed = client.post("/api/omnibrain/v1/queue/process?limit=2",
                            headers=omnibrain_auth)
    assert processed.status_code == 200
    assert processed.json()["processed"] == 2
    replies = [json.loads(line) for line in
               (directory / "cf100-outbox.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    assert len(replies) == 2
    assert {"in_response_to", "agent", "ok", "status", "result", "replied_at"} <= \
        set(replies[0])
    assert replies[0]["ok"] is True
    assert replies[1]["ok"] is False and replies[1]["status"] == "rejected"
    done = [json.loads(line) for line in
            (directory / "omni-done.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    assert {d["id"] for d in done} == {"OMNI-1", "OMNI-2"}
    after = client.get("/api/omnibrain/v1/queue/status",
                       headers=omnibrain_auth).json()
    assert after["pending"] == 0


@pytest.mark.omnibrain
def test_omnibrain_role_has_no_admin_permissions(client, omnibrain_auth):
    assert client.patch("/api/settings", headers=omnibrain_auth,
                        json={"max_parallel_agents": 2}).status_code == 403
    assert client.get("/api/audit", headers=omnibrain_auth).status_code == 403


@pytest.mark.omnibrain
def test_version_guard_applies_to_every_route(client, omnibrain_auth):
    for path in ("/contract", "/modes", "/queue/status"):
        bad = client.get("/api/omnibrain/v1" + path,
                         headers={**omnibrain_auth, "X-OmniBrain-Contract": "2.0"})
        assert bad.status_code == 422, (path, bad.text)
    good = client.get("/api/omnibrain/v1/contract",
                      headers={**omnibrain_auth, "X-OmniBrain-Contract": "1.0"})
    assert good.status_code == 200


@pytest.mark.omnibrain
def test_submit_accepts_root_level_mode(client, omnibrain_auth):
    response = client.post("/api/omnibrain/v1/missions", headers=omnibrain_auth,
                           json={"request": "Mode explicite au niveau racine",
                                 "skill": "technology", "mode": "fast"})
    assert response.status_code == 202, response.text
    assert response.json()["mode"] == "fast"
