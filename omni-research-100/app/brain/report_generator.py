"""Report Generator : rapport complet, citations vérifiables, six gates
OmniBrain et verdict honnête (READY exige un fournisseur réel).
"""
from __future__ import annotations

import time
from typing import Any

from ..agents.registry import OMNIBRAIN_GATES
from ..core.config import Settings
from ..core.db import ReportRow, Store, Task
from ..core.schemas import (MissionPlan, Mode, Report, Verdict)
from ..core.security import redact
from .consensus import ConsensusReport
from .conflict_resolver import ConflictReport
from .evidence_collector import EvidenceBundle
from .executor import ExecutionReport
from .claim_verifier import VerificationReport
from .synthesizer import SynthesisResult


class ReportGenerator:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def generate(self, *, mission_id: str, query: str, mode: Mode,
                 plan: MissionPlan, outcome: Any, bundle: EvidenceBundle,
                 execution: ExecutionReport, verification: VerificationReport,
                 consensus: ConsensusReport, conflicts: ConflictReport,
                 synthesis: SynthesisResult, provider_status: dict[str, Any],
                 data_origin: str, mode_summary: dict[str, Any]) -> Report:
        gates = self._gates(mission_id, plan, bundle, execution, conflicts, outcome,
                            data_origin)
        limitations = list(synthesis.limitations)
        if not bundle.docs:
            limitations.append("aucune source réelle obtenue : aucun fournisseur "
                               "configuré/joignable, ou quota épuisé")
        if not outcome.providers_real:
            limitations.append("preuves issues d'un fournisseur de test hors ligne : "
                               "verdict READY impossible")
        if bundle.stats.get("verified", 0) == 0:
            limitations.append("sources non vérifiées par requête HTTP")
        if conflicts.unresolved:
            limitations.append(f"{conflicts.unresolved} contradiction(s) non tranchée(s)")
        if execution.failed:
            limitations.append(f"{execution.failed} tâche(s) d'agent en échec")
        if execution.cancelled:
            limitations.append("mission annulée avant la fin des vagues")
        if data_origin != "live":
            limitations.append(f"origine des données : {data_origin}")

        markdown = self._markdown(
            mission_id=mission_id, query=query, mode=mode, plan=plan,
            outcome=outcome, bundle=bundle, execution=execution,
            verification=verification, consensus=consensus, conflicts=conflicts,
            synthesis=synthesis, gates=gates, limitations=limitations,
            provider_status=provider_status, data_origin=data_origin,
            mode_summary=mode_summary,
        )
        clean_markdown = redact(markdown)
        gates["secrets"] = gates["secrets"] and (clean_markdown == markdown)
        markdown = clean_markdown
        verdict = Verdict.READY if all(gates.values()) else Verdict.NEEDS_WORK

        coverage = {
            "agents_planned": len(plan.steps), "agents_executed": execution.executed,
            "agents_failed": execution.failed,
            "divisions": sorted({s.division for s in plan.steps}),
            "division_count": len({s.division for s in plan.steps}),
            "sources": len(bundle.docs),
            "domains": bundle.stats.get("domains", 0),
            "providers_used": outcome.providers_used,
            "providers_real": outcome.providers_real,
            "peak_concurrency_measured": execution.peak_concurrency,
            "queued_agents": execution.queued,
            "claims": len(verification.claims),
            "consensus_score": consensus.score,
            "data_origin": data_origin,
        }
        report = Report(
            mission_id=mission_id, markdown=markdown,
            claims=verification.claims, contradictions=conflicts.contradictions,
            sources=bundle.docs, verdict=verdict, gates=gates,
            coverage=coverage, limitations=limitations,
            citations=bundle.citations,
        )
        self.store.add(ReportRow(
            id=f"report-{mission_id}", mission_id=mission_id, markdown=markdown,
            payload=report.to_dict(), created_at=time.time(),
            citation_count=len(bundle.citations), verdict=verdict.value,
        ))
        return report

    # -- gates --------------------------------------------------------------
    def _gates(self, mission_id: str, plan: MissionPlan, bundle: EvidenceBundle,
               execution: ExecutionReport, conflicts: ConflictReport,
               outcome: Any, data_origin: str) -> dict[str, bool]:
        tasks = self.store.filter(Task, mission_id=mission_id)
        traced = self.store.events_after(mission_id, 0, limit=10000)
        dispatched = {e["payload"].get("agent") for e in traced
                      if e["kind"] == "agent_dispatched"}
        resulted = {e["payload"].get("agent") for e in traced
                    if e["kind"] == "agent_result"}
        evidence_ok = 0
        for task in tasks:
            findings = (task.output or {}).get("findings") or []
            if any(f.get("evidence_ids") for f in findings):
                evidence_ok += 1
        return {
            "completeness": (execution.executed == len(plan.steps)
                             and not execution.cancelled and len(tasks) == len(plan.steps)),
            "evidence": bool(bundle.docs) and evidence_ok >= max(1, int(len(tasks) * 0.7)),
            "execution": (execution.executed >= 1 and execution.failed == 0
                          and all((t.output or {}).get("agent_id") for t in tasks)),
            "arbitration": conflicts.unresolved == 0,
            "secrets": True,  # vérifié sur le markdown après génération
            "trace": ({s.agent_id for s in plan.steps} <= dispatched
                      and {s.agent_id for s in plan.steps} <= resulted
                      and len(traced) >= 2 * len(plan.steps)),
            "real_provider": bool(outcome.providers_real) and data_origin == "live"
                             and bool(bundle.docs),
        }

    # -- markdown -----------------------------------------------------------
    def _markdown(self, **k: Any) -> str:
        mission_id: str = k["mission_id"]
        query: str = k["query"]
        mode: Mode = k["mode"]
        plan: MissionPlan = k["plan"]
        outcome = k["outcome"]
        bundle: EvidenceBundle = k["bundle"]
        execution: ExecutionReport = k["execution"]
        verification: VerificationReport = k["verification"]
        consensus: ConsensusReport = k["consensus"]
        conflicts: ConflictReport = k["conflicts"]
        synthesis: SynthesisResult = k["synthesis"]
        gates: dict[str, bool] = k["gates"]
        limitations: list[str] = k["limitations"]
        provider_status: dict[str, Any] = k["provider_status"]
        data_origin: str = k["data_origin"]
        mode_summary: dict[str, Any] = k["mode_summary"]

        wave_text = ", ".join(
            "w{}={}/{}".format(w["wave"], w["ok"], w["tasks"])
            for w in execution.wave_timings
        ) or "aucune"
        out: list[str] = [
            f"# Rapport OMNI-RESEARCH 100 — mission `{mission_id}`",
            "",
            f"- **Question** : {query}",
            f"- **Mode** : {mode.value.upper()}",
            f"- **Généré le** : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"- **Origine des données** : {data_origin}",
            f"- **Verdict** : {'READY' if all(gates.values()) else 'NEEDS_WORK'}",
            "",
            synthesis.answer,
            "",
            "## Méthode",
            "",
            f"- Agents planifiés : **{len(plan.steps)}** / 100 profils disponibles.",
            f"- Agents réellement exécutés : **{execution.executed}**, "
            f"échecs : **{execution.failed}**, reprises : **{execution.retried}**.",
            f"- Pic de concurrence **mesuré** : **{execution.peak_concurrency}** "
            f"(limite configurée : {self.settings.max_parallel_agents}). "
            f"Agents mis en file : **{execution.queued}** — aucune simultanéité "
            "supérieure à la limite n'est revendiquée.",
            f"- Vagues : {wave_text}.",
            f"- Durée d'exécution des agents : **{execution.wall_s:.2f} s**.",
            f"- Fournisseurs utilisés : **{', '.join(outcome.providers_used) or 'aucun'}** "
            f"(réels : {', '.join(outcome.providers_real) or 'aucun'}).",
            f"- Déduplication : {outcome.dedup_removed} doublon(s) retiré(s).",
            f"- Extraction de pages : {outcome.extracted}.",
            f"- Recherche : {outcome.elapsed_ms:.0f} ms.",
            f"- Fournisseur de modèles : `{synthesis.model_provider}` "
            f"(LLM réel : {'oui' if synthesis.used_llm else 'non'}).",
            "",
            f"Raisonnement du plan : {plan.reasoning}",
            "",
            "## Affirmations et consensus",
            "",
            f"- Affirmations conservées : {len(verification.claims)} "
            f"(groupées depuis {verification.grouped} énoncés, "
            f"{verification.passes} passe(s) de vérification).",
            f"- Score de consensus : **{consensus.score}**.",
            f"- Indépendance : {consensus.independence}.",
            "",
            "| Affirmation | Statut | Confiance | Domaines | Preuves |",
            "|---|---|---|---|---|",
        ]
        for claim in verification.claims[:25]:
            safe = claim.text.replace("|", "\\|")[:170]
            out.append(f"| {safe} | {claim.status} | {claim.confidence} | "
                       f"{claim.independent_domains} | {', '.join(claim.support_ids[:3]) or '—'} |")
        out += ["", "## Contradictions", ""]
        if conflicts.contradictions:
            out.append(f"Règle d'arbitrage : `{conflicts.rule}`.")
            out.append("")
            for c in conflicts.contradictions[:12]:
                out.append(f"- **{c.resolution}** — A : {c.statement_a[:120]} | "
                           f"B : {c.statement_b[:120]} — {c.rationale}")
        else:
            out.append("Aucune contradiction inter-domaines détectée dans les preuves.")
        out += ["", "## Table des preuves", "",
                "| Réf. | Source | Domaine | Fournisseur | Vérifiée | Empreinte |",
                "|---|---|---|---|---|---|"]
        for c in bundle.citations[:60]:
            title = (c["title"] or c["url"]).replace("|", "\\|")[:90]
            out.append(f"| [{c['index']}] | [{title}]({c['url']}) | {c['domain']} | "
                       f"{c['provider']} | {c['verified']} | `{c['content_hash'][:12]}` |")
        if not bundle.citations:
            out.append("| — | Aucune source | — | — | — | — |")
        out += ["", "## État des fournisseurs", ""]
        for p in provider_status.get("providers", []):
            out.append(f"- **{p['label']}** : `{p['status']}`, "
                       f"appels={p['total_calls']}, résultats={p['total_results']}, "
                       f"erreurs consécutives={p['consecutive_failures']}")
        out += ["", "## Gates de validation (alignement OmniBrain)", "",
                "| Gate | Résultat |", "|---|---|"]
        for gate, passed in gates.items():
            out.append(f"| {gate} | {'PASS' if passed else 'FAIL'} |")
        out += ["", "## Limites et reproductibilité", ""]
        for limitation in limitations or ["Aucune limite identifiée."]:
            out.append(f"- {limitation}")
        out += [
            "",
            f"- Paramètres du mode : {mode_summary.get('description', '')}",
            f"- Sections prévues : {', '.join(mode_summary.get('report_sections', []))}",
            "- Les contenus web sont des données non fiables ; les instructions "
            "injectées sont neutralisées et aucun code issu d'une source n'est exécuté.",
            "- Ce rapport est rejouable : `GET /api/missions/{id}/report` et "
            "`GET /api/missions/{id}/events` restituent les preuves et la trace.",
            "",
        ]
        return "\n".join(out)
