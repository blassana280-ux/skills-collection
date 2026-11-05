"""Validation finale SUPREME 1.4.0 — protection continue, paliers, contexte attesté,
reprise d'activation, sauvegardes protégées, endpoints d'exploitation.

Tous les tests sont locaux et réels (SQLite, subprocess, HTTP loopback). Aucun
appel fournisseur externe. Un stub local ne prouve jamais une connexion réelle.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from supreme import activation as A
from supreme import provider_control as PC
from supreme.backup import BackupManager
from supreme.budget import BudgetController
from supreme.db import connect, epoch, init_db
from supreme.guardian import GuardianEngine, GuardianScheduler
from supreme.providers import ProviderClient
from supreme.registry import Registry
from supreme.router import ModelRouter, ModelSpec, Provider
from tests._supreme_util import SupremeTestCase


class TestGuardian(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.var_dir = Path(self._tmp.name) / "var"
        (self.var_dir / "secrets").mkdir(parents=True)
        self.engine = GuardianEngine(self.conn, registry=self.core.registry, budget=self.core.budget,
                                     var_dir=self.var_dir)

    def test_scan_persists_deduplicates_and_counts_occurrences(self):
        first = self.engine.scan()
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["errors"], {})
        self.assertTrue(all(v is not None for v in first["checks"].values()))
        before = {f["code"]: f for f in self.engine.findings()}
        second = self.engine.scan()
        after = {f["code"]: f for f in self.engine.findings()}
        self.assertEqual(set(before), set(after))
        for code in before:
            self.assertGreaterEqual(after[code]["occurrences"], before[code]["occurrences"])
        self.assertEqual(second["status"], "completed")

    def test_variable_names_are_not_reported_as_secrets(self):
        # MISTRAL_API_KEY est un nom de variable, pas une fuite : aucun faux positif.
        findings = self.engine.check_repo_secrets()
        self.assertFalse([f for f in findings if f["severity"] == "critical"], findings)

    def test_real_secret_value_in_tracked_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            payload = "API = 'sk-" + "a" * 40 + "'\n"
            (repo / "leak.py").write_text(payload)
            subprocess.run(["git", "add", "leak.py"], cwd=repo, check=True)
            engine = GuardianEngine(self.conn, repo_root=repo)
            findings = engine.check_repo_secrets()
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["code"], "secret_in_repo")
            self.assertEqual(findings[0]["severity"], "critical")
            # La valeur du secret n'est jamais recopiée dans le constat.
            self.assertNotIn("a" * 40, json.dumps(findings[0]))

    def test_world_readable_secret_file_is_flagged(self):
        secrets = self.var_dir / "secrets"
        secrets.mkdir(exist_ok=True)
        key = secrets / "mistral.key"
        key.write_text("placeholder")
        os.chmod(key, 0o644)
        codes = {f["code"] for f in self.engine.check_secret_permissions()}
        self.assertIn("secret_permissions", codes)
        os.chmod(key, 0o600)
        self.assertNotIn("secret_permissions", {f["code"] for f in self.engine.check_secret_permissions()})

    def test_core_integrity_detects_modification_without_rewriting_baseline(self):
        self.engine.check_core_integrity()  # baseline
        row = self.conn.execute("SELECT * FROM integrity_baseline LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.conn.execute("UPDATE integrity_baseline SET sha256=? WHERE path=?", ("0" * 64, row["path"]))
        self.conn.commit()
        findings = self.engine.check_core_integrity()
        self.assertIn("core_file_modified", {f["code"] for f in findings})
        untouched = self.conn.execute("SELECT sha256 FROM integrity_baseline WHERE path=?", (row["path"],)).fetchone()
        self.assertEqual(untouched["sha256"], "0" * 64)  # jamais réécrit silencieusement

    def test_double_execution_and_quota_breach_are_critical(self):
        self.core.budget.set_quota("global", "default", 0.0)
        self.conn.execute(
            "INSERT INTO budget_ledger(scope,scope_id,cost_usd,at) VALUES('global','default',5.0,'2026-11-05')")
        self.conn.commit()
        codes = {f["code"]: f["severity"] for f in self.engine.check_budget_anomalies()}
        self.assertEqual(codes.get("quota_exceeded"), "critical")

    def test_resolution_requires_documented_human_review(self):
        self.engine.scan()
        open_findings = self.engine.findings()
        if not open_findings:
            self.engine._persist([{"code": "test", "severity": "medium", "component": "test",
                                   "detail": "constat de test", "evidence": {}}])
            open_findings = self.engine.findings()
        fid = open_findings[0]["id"]
        with self.assertRaises(PermissionError):
            self.engine.resolve(fid, resolution="vu", acknowledged_by="human", confirm="non")
        with self.assertRaises(PermissionError):
            self.engine.resolve(fid, resolution="", acknowledged_by="human", confirm="REVUE HUMAINE EFFECTUEE")
        res = self.engine.resolve(fid, resolution="revue locale documentée", acknowledged_by="human-test",
                                  confirm="REVUE HUMAINE EFFECTUEE")
        self.assertEqual(res["status"], "resolved")

    def test_guardian_never_mutates_permissions_or_policies(self):
        secrets = self.var_dir / "secrets"
        secrets.mkdir(exist_ok=True)
        key = secrets / "mistral.key"
        key.write_text("placeholder")
        os.chmod(key, 0o644)
        self.engine.scan()
        self.assertEqual(key.stat().st_mode & 0o777, 0o644)  # détecté, pas corrigé silencieusement

    def test_github_check_is_opt_in_and_offline_by_default(self):
        findings = self.engine.check_github_permissions()
        self.assertEqual(findings[0]["code"], "github_check_skipped")

    def test_scheduler_runs_bounded_cycles_and_releases_lease(self):
        sched = GuardianScheduler(self.conn, self.engine, scheduler_id="t", interval_seconds=0.05,
                                  lease_seconds=5.0, heartbeat_interval=0.05)
        res = sched.run(max_cycles=2)
        self.assertEqual(res["status"], "stopped")
        self.assertEqual(res["cycles"], 2)
        row = self.conn.execute("SELECT state, owner_worker_id FROM guardian_schedulers WHERE id='t'").fetchone()
        self.assertEqual(row["state"], "stopped")
        self.assertIsNone(row["owner_worker_id"])

    def test_second_scheduler_is_refused_while_lease_is_alive(self):
        first = GuardianScheduler(self.conn, self.engine, scheduler_id="solo", interval_seconds=60,
                                  lease_seconds=60, worker_id="w1")
        self.assertIsNotNone(first._claim())
        second = GuardianScheduler(self.conn, self.engine, scheduler_id="solo", interval_seconds=60,
                                   lease_seconds=60, worker_id="w2")
        self.assertIsNone(second._claim())

    def test_only_one_scan_running_at_a_time(self):
        self.conn.execute(
            "INSERT INTO guardian_runs(id,trigger,status,started_at) VALUES('grd-x','cli','running','2026-11-05')")
        self.conn.commit()
        res = self.engine.scan()
        self.assertEqual(res["status"], "skipped")


class TestActivationMilestones(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.manager = A.ActivationManager(self.conn, self.core.registry, self.core.router)

    def test_milestones_match_requested_ladder(self):
        self.assertEqual(A.MILESTONES, [5, 20, 60, 100, 200, 400, 600, 800, 960])

    def test_jump_to_unlisted_or_later_tier_is_refused(self):
        for bad in (300, 500, 20, 960):
            with self.assertRaises(ValueError):
                self.manager.prepare(bad)

    def test_quarantine_release_invalidates_previous_proof(self):
        aid = self.manager.llm_agents()[0]["id"]
        # Fabriquer une preuve externe soldée antérieure, puis une quarantaine levée après.
        self.conn.execute(
            """INSERT INTO activation_campaigns(id,target_size,provider,status,budget_usd,per_agent_usd,created_at)
               VALUES('c1',5,'mistral','completed',0.05,0.01,'2026-11-05')""")
        self.conn.execute(
            """INSERT INTO budget_reservations(id,call_key,mission_id,status,amount_usd,actual_cost_usd,
                 created_at,updated_at) VALUES('r1','k1','c1','settled',0.01,0.001,'2026-11-05','2026-11-05')""")
        self.conn.execute(
            """INSERT INTO activation_proofs(id,campaign_id,agent_id,category,provider,model,http_status,
                 endpoint_host,reservation_id,output_sha256,usage_json,cost_usd,latency_ms,usable,
                 permissions_ok,budget_ok,checked_at)
               VALUES('p1','c1',?,'external_api','mistral','m',200,'api.mistral.ai','r1','x','{}',0.001,10,1,1,1,?)""",
            (aid, "2026-11-05T10:00:00+00:00"))
        self.conn.commit()
        self.assertIn(aid, self.manager.activated_ids())
        self.conn.execute(
            """INSERT INTO agent_quarantine(agent_id,reason,isolated_at,review_required,released_at)
               VALUES(?, 'test', '2026-11-05T11:00:00+00:00', 0, '2026-11-05T12:00:00+00:00')""", (aid,))
        self.conn.commit()
        self.assertNotIn(aid, self.manager.activated_ids(),
                         "une preuve antérieure à la quarantaine ne doit pas recompter après levée")

    def test_release_confirm_phrase_is_centralised(self):
        self.assertEqual(A.QUARANTINE_RELEASE_CONFIRM, "REVUE HUMAINE EFFECTUEE")
        with self.assertRaises(PermissionError):
            self.manager.release_quarantine("x", evidence="e", confirm="JE CONFIRME LA REVUE")

    def test_expired_lease_with_live_owner_is_not_recovered(self):
        st = self.manager.prepare(5)
        cid = st["campaign"]["id"]
        from supreme.leases import register_worker
        register_worker(self.conn, "live-owner")
        self.conn.execute(
            """UPDATE activation_campaigns SET status='running',owner_worker_id='live-owner',
                 lease_token='tok',lease_expires_at=?,heartbeat_at=? WHERE id=?""",
            (epoch() - 10, epoch(), cid))
        self.conn.execute("UPDATE workers SET last_heartbeat=?, state='alive' WHERE worker_id='live-owner'", (epoch(),))
        self.conn.commit()
        self.manager._recover_expired()
        row = self.conn.execute("SELECT status FROM activation_campaigns WHERE id=?", (cid,)).fetchone()
        self.assertEqual(row["status"], "running", "un propriétaire vivant ne doit pas être dépossédé")

    def test_expired_lease_with_stopped_owner_is_recovered(self):
        st = self.manager.prepare(5)
        cid = st["campaign"]["id"]
        from supreme.leases import register_worker, stop_worker
        register_worker(self.conn, "dead-owner")
        self.conn.execute(
            """UPDATE activation_campaigns SET status='running',owner_worker_id='dead-owner',
                 lease_token='tok',lease_expires_at=? WHERE id=?""", (epoch() - 10, cid))
        self.conn.commit()
        stop_worker(self.conn, "dead-owner")
        self.manager._recover_expired()
        row = self.conn.execute("SELECT status FROM activation_campaigns WHERE id=?", (cid,)).fetchone()
        self.assertEqual(row["status"], "interrupted")


class TestJsonModeContract(unittest.TestCase):
    """Le transport JSON natif est opt-in : la doc et le code doivent concorder."""

    def test_default_transport_sends_no_response_format(self):
        from supreme.providers import build_request
        msgs = [{"role": "user", "content": "x"}]
        for kind in ("openai", "mistral", "anthropic", "gemini", "ollama"):
            payload = build_request(kind, "https://api.example/v1", "m", msgs, "k", 64, 0.2)[2]
            self.assertNotIn("response_format", payload, kind)

    def test_opt_in_json_mode_only_where_documented(self):
        from supreme.providers import build_request
        msgs = [{"role": "user", "content": "x"}]
        for kind in ("openai", "mistral"):
            payload = build_request(kind, "https://api.example/v1", "m", msgs, "k", 64, 0.2, json_mode=True)[2]
            self.assertEqual(payload["response_format"], {"type": "json_object"})
        gemini = build_request("gemini", "https://api.example/v1", "m", msgs, "k", 64, 0.2, json_mode=True)[2]
        self.assertEqual(gemini["generationConfig"]["responseMimeType"], "application/json")
        for kind in ("anthropic", "ollama"):
            payload = build_request(kind, "https://api.example/v1", "m", msgs, "k", 64, 0.2, json_mode=True)[2]
            self.assertNotIn("response_format", payload, kind)

    def test_documented_contract_matches_implementation(self):
        root = Path(__file__).resolve().parent.parent
        text = (root / "docs/supreme/PROVIDERS.md").read_text(encoding="utf-8")
        self.assertIn("opt-in", text)
        self.assertIn("contrat de prompt", text)


class TestCampaignRecovery(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.manager = A.ActivationManager(self.conn, self.core.registry, self.core.router)
        self.cid = self.manager.prepare(5)["campaign"]["id"]

    def _fail_member(self):
        member = self.conn.execute(
            "SELECT agent_id FROM activation_members WHERE campaign_id=? ORDER BY position LIMIT 1",
            (self.cid,)).fetchone()["agent_id"]
        self.conn.execute("UPDATE activation_members SET status='failed' WHERE campaign_id=? AND agent_id=?",
                          (self.cid, member))
        self.conn.execute("UPDATE activation_campaigns SET status='blocked' WHERE id=?", (self.cid,))
        self.conn.commit()
        return member

    def test_respecify_requires_human_confirmation_and_author(self):
        for confirm, author in (("non", "h"), (A.RESPECIFY_CONFIRM, "")):
            with self.assertRaises(PermissionError):
                self.manager.respecify(self.cid, provider="openai", confirm=confirm, approved_by=author)

    def test_respecify_retargets_provider_model_and_budget(self):
        res = self.manager.respecify(self.cid, provider="openai", model="gpt-x", budget_usd=0.5,
                                     confirm=A.RESPECIFY_CONFIRM, approved_by="humain-test")
        camp = res["campaign"]
        self.assertEqual((camp["provider"], camp["model"], camp["budget_usd"]), ("openai", "gpt-x", 0.5))
        self.assertEqual(camp["status"], "prepared")
        self.assertEqual(res["previous"]["provider"], "mistral")
        quota = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope='mission' AND scope_id=?",
                                  (self.cid,)).fetchone()["limit_usd"]
        self.assertEqual(quota, 0.5)

    def test_respecify_refused_once_external_proof_exists(self):
        self.conn.execute(
            """INSERT INTO activation_proofs(id,campaign_id,agent_id,category,provider,model,http_status,
                 endpoint_host,output_sha256,usage_json,cost_usd,latency_ms,usable,permissions_ok,budget_ok,checked_at)
               VALUES('p9',?,'a9','external_api','mistral','m',200,'api.mistral.ai','x','{}',0.001,10,1,1,1,?)""",
            (self.cid, "2026-11-05T10:00:00+00:00"))
        self.conn.commit()
        with self.assertRaises(ValueError):
            self.manager.respecify(self.cid, provider="openai", confirm=A.RESPECIFY_CONFIRM, approved_by="h")

    def test_respecify_refused_while_members_are_running(self):
        self.conn.execute("UPDATE activation_members SET status='running' WHERE campaign_id=? AND position=1", (self.cid,))
        self.conn.commit()
        with self.assertRaises(ValueError):
            self.manager.respecify(self.cid, provider="openai", confirm=A.RESPECIFY_CONFIRM, approved_by="h")

    def test_reconcile_waives_member_and_keeps_tier_size_with_replacement(self):
        member = self._fail_member()
        res = self.manager.reconcile_member(self.cid, member, resolution="agent écarté",
                                            evidence="revue-2026-11-05", acknowledged_by="humain-test",
                                            confirm=A.QUARANTINE_RELEASE_CONFIRM)
        rec = res["reconciled"]
        self.assertEqual(rec["status"], "waived")
        self.assertTrue(rec["replacement_agent_id"])
        self.assertNotEqual(rec["replacement_agent_id"], member)
        self.assertEqual(rec["target_unchanged"], 5)
        self.assertEqual(res["member_counts"]["pending"], 5)
        self.assertEqual(res["campaign"]["status"], "prepared")
        self.assertEqual(res["campaign"]["target_size"], 5, "écarter un membre ne réduit pas le palier")

    def test_reconcile_retry_returns_member_to_pending(self):
        member = self._fail_member()
        res = self.manager.reconcile_member(self.cid, member, resolution="nouvelle tentative",
                                            evidence="revue-2", acknowledged_by="h",
                                            confirm=A.QUARANTINE_RELEASE_CONFIRM, retry=True)
        self.assertEqual(res["reconciled"]["status"], "pending")
        self.assertIsNone(res["reconciled"]["replacement_agent_id"])

    def test_reconcile_requires_documented_review(self):
        member = self._fail_member()
        for kwargs in ({"confirm": "non", "resolution": "r", "evidence": "e", "acknowledged_by": "h"},
                       {"confirm": A.QUARANTINE_RELEASE_CONFIRM, "resolution": "", "evidence": "e", "acknowledged_by": "h"},
                       {"confirm": A.QUARANTINE_RELEASE_CONFIRM, "resolution": "r", "evidence": "", "acknowledged_by": "h"}):
            with self.assertRaises(PermissionError):
                self.manager.reconcile_member(self.cid, member, **kwargs)

    def test_retry_refused_while_budget_reservation_is_uncertain(self):
        member = self._fail_member()
        self.conn.execute(
            """INSERT INTO budget_reservations(id,call_key,mission_id,status,amount_usd,created_at,updated_at)
               VALUES('ru','ku',?,'interrupted',0.01,'2026-11-05','2026-11-05')""", (self.cid,))
        self.conn.commit()
        with self.assertRaises(ValueError):
            self.manager.reconcile_member(self.cid, member, resolution="r", evidence="e", acknowledged_by="h",
                                          confirm=A.QUARANTINE_RELEASE_CONFIRM, retry=True)
        exposure = self.conn.execute("SELECT status FROM budget_reservations WHERE id='ru'").fetchone()["status"]
        self.assertEqual(exposure, "interrupted", "l'exposition incertaine ne doit pas être effacée")

    def test_reconcile_ignores_already_activated_member(self):
        self.conn.execute("UPDATE activation_members SET status='activated' WHERE campaign_id=? AND position=1", (self.cid,))
        self.conn.commit()
        member = self.conn.execute("SELECT agent_id FROM activation_members WHERE campaign_id=? AND position=1",
                                   (self.cid,)).fetchone()["agent_id"]
        with self.assertRaises(ValueError):
            self.manager.reconcile_member(self.cid, member, resolution="r", evidence="e", acknowledged_by="h",
                                          confirm=A.QUARANTINE_RELEASE_CONFIRM)


class TestAttestedContext(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.control = self.core.router.control

    def _discover(self, context=0):
        self.control.record_verification("openai", {
            "ok": True, "category": "external_api", "http_status": 200,
            "endpoint_host": "api.openai.com", "request_id": "req-1", "latency_ms": 12.0,
            "models": [{"id": "gpt-x", "capabilities": ["general"], "context": context, "tools": False}],
        })

    def test_context_attestation_requires_human_confirmation_and_https(self):
        self._discover(0)
        with self.assertRaises(PermissionError):
            self.control.attest_context("openai", "gpt-x", context_tokens=8000,
                                        source_url="https://official.example/pricing", confirm="non")
        with self.assertRaises(ValueError):
            self.control.attest_context("openai", "gpt-x", context_tokens=8000,
                                        source_url="http://insecure.example", confirm=PC.CONTEXT_CONFIRM)

    def test_undiscovered_model_cannot_be_attested(self):
        with self.assertRaises(KeyError):
            self.control.attest_context("openai", "invented-model", context_tokens=8000,
                                        source_url="https://official.example", confirm=PC.CONTEXT_CONFIRM)

    def test_attested_context_makes_model_routable_only_with_price(self):
        self._discover(0)
        self.assertEqual(self.control.discovered_models("openai")[0]["context"], 0)
        self.control.attest_context("openai", "gpt-x", context_tokens=128000,
                                    source_url="https://official.example/models", confirm=PC.CONTEXT_CONFIRM)
        models = self.control.discovered_models("openai")
        self.assertEqual(models[0]["context"], 128000)
        self.assertEqual(models[0]["context_discovered"], 0)
        self.assertEqual(models[0]["context_attested"], 128000)

    def test_discovered_context_wins_over_attestation(self):
        self._discover(64000)
        self.control.attest_context("openai", "gpt-x", context_tokens=8000,
                                    source_url="https://official.example", confirm=PC.CONTEXT_CONFIRM)
        self.assertEqual(self.control.discovered_models("openai")[0]["context"], 64000)

    def test_stale_attestation_expires(self):
        self._discover(0)
        self.control.attest_context("openai", "gpt-x", context_tokens=8000,
                                    source_url="https://official.example", confirm=PC.CONTEXT_CONFIRM)
        self.conn.execute("UPDATE provider_models SET context_attested_at='2020-01-01T00:00:00+00:00'")
        self.conn.commit()
        self.assertEqual(self.control.discovered_models("openai")[0]["context"], 0)

    def test_openrouter_context_length_is_parsed(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                body = json.dumps({"data": [{"id": "vendor/model", "context_length": 32768,
                                             "supported_parameters": ["tools", "temperature"]}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            client = ProviderClient(timeout=5, allow_network=True)
            res = client.discover_models(provider="openrouter",
                                         base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1",
                                         kind="openai", api_key="stub")
            self.assertTrue(res["ok"])
            self.assertEqual(res["models"][0]["context"], 32768)
            self.assertTrue(res["models"][0]["tools"])
            self.assertEqual(res["category"], "local_test")  # stub, jamais une preuve réelle
        finally:
            srv.shutdown(); srv.server_close()


class TestBackupProtection(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.backup_dir = Path(self._tmp.name) / "backups"
        self._patch = mock.patch("supreme.backup.BACKUP_DIR", self.backup_dir)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_new_backup_is_private_and_integrity_checked(self):
        meta = BackupManager(self.db_path).backup("test-final")
        db = Path(meta["db"])
        self.assertEqual(meta["integrity"], "ok")
        self.assertEqual(db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(db.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual((db.parent / "meta.json").stat().st_mode & 0o777, 0o600)

    def test_guardian_flags_world_readable_backup_then_clean_after_fix(self):
        meta = BackupManager(self.db_path).backup("perm-test")
        db = Path(meta["db"])
        engine = GuardianEngine(self.conn, var_dir=Path(self._tmp.name) / "var")
        os.chmod(db, 0o644)
        self.assertIn("backup_permissions", {f["code"] for f in engine.check_backups()})
        os.chmod(db, 0o600)
        self.assertNotIn("backup_permissions", {f["code"] for f in engine.check_backups()})


class TestBackupRetention(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.backup_dir = Path(self._tmp.name) / "backups"
        self._patch = mock.patch("supreme.backup.BACKUP_DIR", self.backup_dir)
        self._patch.start(); self.addCleanup(self._patch.stop)
        self.manager = BackupManager(self.db_path)

    def test_verify_all_reports_integrity_and_permissions(self):
        self.manager.backup("v1")
        res = self.manager.verify_all()
        self.assertEqual(res["count"], 1)
        self.assertTrue(res["all_integrity_ok"])
        self.assertTrue(res["all_private"])

    def test_prune_is_dry_run_by_default_and_deletes_nothing(self):
        for i in range(4):
            self.manager.backup(f"b{i}")
        res = self.manager.prune(keep=2, confirm="")
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["deleted"], [])
        self.assertEqual(len(res["would_delete"]), 2)
        self.assertEqual(len(self.manager.list_backups()), 4)

    def test_prune_requires_explicit_confirmation_to_apply(self):
        for i in range(3):
            self.manager.backup(f"b{i}")
        with self.assertRaises(PermissionError):
            self.manager.prune(keep=1, confirm="oui", dry_run=False)
        self.assertEqual(len(self.manager.list_backups()), 3)

    def test_prune_keeps_requested_window_and_never_zero(self):
        from supreme.backup import PRUNE_CONFIRM
        for i in range(4):
            self.manager.backup(f"b{i}")
        with self.assertRaises(ValueError):
            self.manager.prune(keep=0, confirm=PRUNE_CONFIRM, dry_run=False)
        res = self.manager.prune(keep=2, confirm=PRUNE_CONFIRM, dry_run=False)
        self.assertEqual(len(res["deleted"]), 2)
        self.assertEqual(len(self.manager.list_backups()), 2)
        self.assertGreater(res["bytes_reclaimed"], 0)

    def test_corrupt_backup_is_never_pruned(self):
        from supreme.backup import PRUNE_CONFIRM
        first = self.manager.backup("old")
        self.manager.backup("recent")
        Path(first["db"]).write_bytes(b"corrupted")
        res = self.manager.prune(keep=1, confirm=PRUNE_CONFIRM, dry_run=False)
        # L'invariant réel : une sauvegarde corrompue n'est JAMAIS supprimée,
        # quel que soit son rang dans la fenêtre de rétention.
        self.assertNotIn(first["id"], res["deleted"])
        self.assertTrue(Path(first["db"]).exists())
        self.assertTrue(any(p["id"] == first["id"] for p in res["protected"]))

    def test_retention_order_is_deterministic_within_same_second(self):
        from supreme.backup import PRUNE_CONFIRM
        first = self.manager.backup("a")
        second = self.manager.backup("b")
        self.assertEqual(first["created_at"], second["created_at"])
        self.assertGreater(second["created_epoch"], first["created_epoch"])
        res = self.manager.prune(keep=1, confirm=PRUNE_CONFIRM, dry_run=False)
        self.assertEqual(res["deleted"], [first["id"]], "la plus ancienne doit partir, pas la plus récente")
        self.assertTrue(Path(second["db"]).exists())


class TestOperationsEndpoints(SupremeTestCase):
    def setUp(self):
        super().setUp()
        import urllib.request
        import urllib.error
        from supreme.api import APIState, make_handler
        self.urllib_request = urllib.request
        self.urllib_error = urllib.error
        self._env = mock.patch.dict(os.environ, {"SUPREME_API_TOKEN": "test-token", "SUPREME_ALLOW_ANON_READ": "1"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.state = APIState(self.core)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close()
        super().tearDown()

    def _get(self, path):
        req = self.urllib_request.Request(f"http://127.0.0.1:{self.port}{path}")
        req.add_header("X-API-Token", "test-token")
        with self.urllib_request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())

    def _post(self, path, body, token=None):
        req = self.urllib_request.Request(f"http://127.0.0.1:{self.port}{path}",
                                          data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-API-Token", token)
        try:
            with self.urllib_request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except self.urllib_error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_divisions_detail_reports_real_40_960_60_split(self):
        code, data = self._get("/api/divisions/detail")
        self.assertEqual(code, 200)
        divisions = data["divisions"]
        self.assertEqual(len(divisions), 20)
        self.assertEqual(sum(d["total"] for d in divisions), 1000)
        self.assertEqual(sum(d["llm_agents"] for d in divisions), 960)
        self.assertEqual(sum(d["local_tool_agents"] for d in divisions), 40)
        self.assertEqual(sum(d["locally_proven_total"] for d in divisions), 60)
        self.assertTrue(all(d["manager"] for d in divisions))
        self.assertTrue(all(d["cross_division_links"] for d in divisions))

    def test_guardian_endpoint_exposes_real_findings_without_secrets(self):
        code, data = self._get("/api/guardian")
        self.assertEqual(code, 200)
        self.assertIn("blocking_findings", data)
        self.assertIn("checks", data)
        self.assertNotIn("api_key", json.dumps(data))

    def test_guardian_scan_requires_admin_and_explicit_confirm(self):
        self.assertEqual(self._post("/api/guardian/scan", {"confirm": "LANCER SCAN SECURITE"})[0], 401)
        self.assertEqual(self._post("/api/guardian/scan", {}, token="test-token")[0], 400)
        code, data = self._post("/api/guardian/scan", {"confirm": "LANCER SCAN SECURITE"}, token="test-token")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "completed")

    def test_activity_collaboration_and_quarantine_endpoints(self):
        self.core.submit({"objective": "vérifier la syntaxe Python puis valider un JSON"})
        for path in ("/api/activity", "/api/collaborations", "/api/quarantine"):
            code, data = self._get(path)
            self.assertEqual(code, 200, path)
            self.assertTrue(data)

    def test_dashboard_has_new_mobile_tabs(self):
        with self.urllib_request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=30) as r:
            html = r.read().decode()
        for marker in ('data-tab="guardian"', 'data-tab="collab"', 'data-tab="activity"',
                       'id="quarantineTable"', 'id="divTable"', 'viewport'):
            self.assertIn(marker, html)


class TestMemoryArbitration(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.memory = self.core.memory
        self.actor = "omnibrain-core"
        self.a = self.memory.add(self.actor, "central", "global", "semantic", "Priorité Mistral",
                                 source="audit", metadata={"subject_key": "provider",
                                                           "claim_key": "priority", "claim_value": "mistral"})
        self.b = self.memory.add(self.actor, "central", "global", "semantic", "Priorité OpenAI",
                                 source="note", metadata={"subject_key": "provider",
                                                          "claim_key": "priority", "claim_value": "openai"})

    def test_contradiction_is_detected_then_arbitrated_with_provenance(self):
        self.assertEqual(len(self.memory.contradictions(self.actor, "central", "global")), 1)
        res = self.memory.resolve_contradiction(self.actor, "central", "global", "provider", "priority",
                                               self.a, reason="priorité déclarée", evidence="directive-2026-11-05")
        self.assertTrue(res["resolved"])
        self.assertEqual(res["rows_physically_deleted"], 0)
        self.assertEqual(self.memory.open_contradictions(self.actor, "central", "global"), [])
        winner = self.memory.get(self.actor, res["winner_id"])
        self.assertEqual(winner["metadata"]["decided_by"], self.actor)
        self.assertEqual(winner["metadata"]["decision_evidence"], "directive-2026-11-05")

    def test_loser_stays_readable_and_linked(self):
        res = self.memory.resolve_contradiction(self.actor, "central", "global", "provider", "priority",
                                               self.a, reason="r", evidence="e")
        loser = self.memory.get(self.actor, self.b)
        self.assertEqual(loser["metadata"]["superseded_by"], res["winner_id"])
        rels = self.memory.neighbors(self.actor, res["winner_id"])
        self.assertIn("supersedes", [r["relation"] for r in rels])

    def test_no_row_is_physically_removed(self):
        before = self.conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]
        self.memory.resolve_contradiction(self.actor, "central", "global", "provider", "priority",
                                         self.a, reason="r", evidence="e")
        after = self.conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]
        self.assertEqual(after, before + 1)  # nouvelle version, aucune suppression
        self.assertIsNotNone(self.conn.execute("SELECT id FROM memory_items WHERE id=?", (self.a,)).fetchone())

    def test_arbitration_requires_reason_and_evidence(self):
        for reason, evidence in (("", "e"), ("r", ""), ("  ", "e")):
            with self.assertRaises(ValueError):
                self.memory.resolve_contradiction(self.actor, "central", "global", "provider", "priority",
                                                 self.a, reason=reason, evidence=evidence)

    def test_winner_must_belong_to_detected_contradiction(self):
        with self.assertRaises(ValueError):
            self.memory.resolve_contradiction(self.actor, "central", "global", "provider", "priority",
                                             "mem-inexistant", reason="r", evidence="e")

    def test_arbitration_respects_memory_acl(self):
        specialist = self.core.registry.list(division="D01", kind="specialist")[0]["id"]
        with self.assertRaises(PermissionError):
            self.memory.resolve_contradiction(specialist, "central", "global", "provider", "priority",
                                             self.a, reason="r", evidence="e")


class TestApiInputHardening(SupremeTestCase):
    def setUp(self):
        super().setUp()
        import urllib.error
        import urllib.request
        from supreme.api import APIState, make_handler
        self.urllib_request, self.urllib_error = urllib.request, urllib.error
        self._env = mock.patch.dict(os.environ, {"SUPREME_API_TOKEN": "t", "SUPREME_ALLOW_ANON_READ": "1"})
        self._env.start(); self.addCleanup(self._env.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(APIState(self.core)))
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def _post(self, path, body=None, raw=None):
        data = raw if raw is not None else json.dumps(body).encode()
        req = self.urllib_request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Token", "t")
        try:
            with self.urllib_request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except self.urllib_error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_oversized_body_is_rejected_with_413(self):
        code, data = self._post("/api/missions", raw=b'{"objective":"' + b"a" * 1_100_000 + b'"}')
        self.assertEqual(code, 413)
        self.assertIn("max_bytes", data)

    def test_invalid_json_is_400_not_silently_empty(self):
        self.assertEqual(self._post("/api/activation/prepare", raw=b"{oops")[0], 400)
        self.assertEqual(self._post("/api/activation/prepare", raw=b"[1,2]")[0], 400)

    def test_bad_numeric_fields_are_400_not_500(self):
        for body in ({"size": "abc"}, {"size": -1}, {"size": True}, {"per_agent_usd": "x"},
                     {"budget_usd": float("nan")}, {"budget_usd": float("inf")}, {"size": 1.5}):
            payload = {"confirm": "PREPARER CAMPAGNE", "size": 5} | body
            self.assertEqual(self._post("/api/activation/prepare", payload)[0], 400, body)

    def test_valid_campaign_still_accepted(self):
        code, _ = self._post("/api/activation/prepare", {"size": 5, "confirm": "PREPARER CAMPAGNE"})
        self.assertEqual(code, 201)


class TestGuardianRebaseline(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.engine = GuardianEngine(self.conn, registry=self.core.registry, budget=self.core.budget,
                                     var_dir=Path(self._tmp.name) / "var")

    def test_rebaseline_requires_confirmation_author_reason_and_evidence(self):
        self.engine.check_core_integrity()
        for kwargs in ({"confirm": "non", "approved_by": "h", "reason": "r", "evidence": "e"},
                       {"confirm": "REVUE HUMAINE EFFECTUEE", "approved_by": "", "reason": "r", "evidence": "e"},
                       {"confirm": "REVUE HUMAINE EFFECTUEE", "approved_by": "h", "reason": "r", "evidence": ""}):
            with self.assertRaises(PermissionError):
                self.engine.rebaseline_core(**kwargs)

    def test_rebaseline_records_previous_digests_in_events(self):
        self.engine.check_core_integrity()
        row = self.conn.execute("SELECT path FROM integrity_baseline LIMIT 1").fetchone()
        self.conn.execute("UPDATE integrity_baseline SET sha256=? WHERE path=?", ("0" * 64, row["path"]))
        self.conn.commit()
        self.assertTrue(self.engine.check_core_integrity())
        res = self.engine.rebaseline_core(confirm="REVUE HUMAINE EFFECTUEE", approved_by="human",
                                         reason="livraison 1.4.0", evidence="PR #5")
        self.assertEqual(len(res["changed"]), 1)
        self.assertEqual(res["changed"][0]["previous_sha256"], "0" * 64)
        self.assertEqual(self.engine.check_core_integrity(), [])
        event = self.conn.execute(
            "SELECT data_json FROM events WHERE component='guardian' ORDER BY id DESC LIMIT 1").fetchone()
        payload = json.loads(event["data_json"])
        self.assertEqual(payload["evidence"], "PR #5")
        self.assertEqual(payload["changed"][0]["previous_sha256"], "0" * 64)


class TestOperationsScripts(unittest.TestCase):
    def test_ctl_script_and_units_are_valid_and_local_by_default(self):
        root = Path(__file__).resolve().parent.parent
        script = root / "ops" / "supreme-ctl.sh"
        self.assertTrue(script.is_file())
        subprocess.run(["bash", "-n", str(script)], check=True)
        self.assertTrue(os.access(script, os.X_OK))
        text = script.read_text()
        self.assertIn('SUPREME_BIND:-127.0.0.1', text)
        self.assertIn('CONFIRMER RESTAURATION', text)
        units = list((root / "ops" / "systemd").glob("*.service"))
        self.assertGreaterEqual(len(units), 5)
        for unit in units:
            body = unit.read_text()
            self.assertIn("UMask=0077", body)
            self.assertIn("NoNewPrivileges=true", body)
        api_unit = (root / "ops" / "systemd" / "supreme-api.service").read_text()
        self.assertIn("--host 127.0.0.1", api_unit)
        self.assertIn("SUPREME_ALLOW_ANON_READ=0", api_unit)
        self.assertTrue((root / "ops" / "systemd" / "supreme-backup.timer").is_file())

    def test_env_example_contains_no_secret_value(self):
        root = Path(__file__).resolve().parent.parent
        text = (root / "ops" / "env.example").read_text()
        for line in text.splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if "KEY" in key or "TOKEN" in key:
                self.assertEqual(value.strip(), "", f"valeur secrète dans le modèle : {key}")


if __name__ == "__main__":
    unittest.main()
