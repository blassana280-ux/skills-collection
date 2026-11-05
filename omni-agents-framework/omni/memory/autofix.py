"""Auto-amélioration active (Phase 2.2).

Après ``threshold`` échecs d'un même profil, génère une **branche**
``omnibrain/fix-<agent>`` portant une fiche corrigée et ouvre une **PR**.
Aucune fusion, aucune écriture sur ``main``/``master`` : le backend n'expose
aucune méthode de merge et le garde-fou est testé.

Sécurité d'exécution : par défaut ``CommandBackend(dry_run=True)`` enregistre
les commandes sans les exécuter. La variable ``OMNIBRAIN_AUTOFIX_APPLY=1``
active l'exécution réelle (git + gh), toujours sur une branche dédiée.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .store import FRAMEWORK_ROOT, MemoryStore, _now


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "agent"


def build_corrected_fiche(agent_id: str, failures: list[dict[str, Any]], *, signature: str) -> str:
    """Fiche corrigée déterministe : une règle explicite par type d'échec observé."""
    types = sorted({str(f.get("error_type") or "unknown") for f in failures})
    rules = {
        "missing_keyword": "Ajouter des mots-clés explicites (expressions composées) et vérifier l'activation avec le test de fumée du catalogue.",
        "false_positive": "Remplacer tout mot-clé générique par une expression contextuelle ; exécuter le test de non-régression des faux positifs.",
        "timeout": "Découper la tâche en étapes bornées et tracer la durée mesurée de chaque étape avant nouvelle soumission.",
        "gate_blocked": "Joindre une preuve fraîche (sortie de commande ou ligne de fichier) pour chaque critère de gate.",
        "missing_evidence": "Ne jamais déclarer PASS sans artefact de preuve ; verdict par défaut NEEDS WORK.",
        "unknown": "Documenter la cause racine avant toute nouvelle tentative et conserver la trace de l'incident.",
    }
    lines = [
        "---",
        f"id: {agent_id}",
        f"name: {agent_id} (fiche corrigée OmniBrain v4)",
        f"description: \"Fiche auto-corrigée après {len(failures)} échecs du même profil.\"",
        f"signature: {signature}",
        "auto_generated: true",
        "human_merge_required: true",
        "---",
        "",
        f"# Fiche corrigée — `{agent_id}`",
        "",
        f"- **Déclencheur :** {len(failures)} échecs du profil, signature `{signature}`.",
        "- **Règle :** cette fiche arrive par branche + PR ; **Aucune fusion automatique**, décision réservée à Lassana.",
        "",
        "## Échecs observés",
        "",
    ]
    lines += [f"- `{f.get('error_type')}` (tentative {f.get('attempt')}) : {f.get('message')}" for f in failures]
    lines += ["", "## Règles correctives", ""]
    lines += [f"{i}. {rules.get(t, rules['unknown'])}" for i, t in enumerate(types, start=1)]
    lines += [
        "",
        "## Protocoles universels",
        "",
        "1. Raisonner par l'exécution : rien n'est affirmé sans sortie de commande.",
        "2. Preuve fraîche obligatoire, verdict par défaut NEEDS WORK.",
        "3. Revue adverse indépendante obligatoire avant toute promotion.",
        "4. Aucun secret dans le dépôt ; variables d'environnement uniquement.",
        "5. Aucune écriture directe sur la branche principale.",
        "",
    ]
    return "\n".join(lines)


class GitBackend(Protocol):
    """Contrat volontairement minimal : aucune opération de fusion."""

    def create_branch(self, branch: str) -> None: ...
    def write_fiche(self, relative_path: str, content: str) -> None: ...
    def commit(self, message: str) -> None: ...
    def push(self, branch: str) -> None: ...
    def open_pr(self, branch: str, title: str, body: str) -> str: ...


@dataclass
class RecordingBackend:
    """Backend de test / dry-run : trace les actions sans toucher au dépôt."""

    actions: list[tuple[str, str]] = field(default_factory=list)

    def create_branch(self, branch: str) -> None:
        self.actions.append(("create_branch", branch))

    def write_fiche(self, relative_path: str, content: str) -> None:
        self.actions.append(("write_fiche", relative_path))

    def commit(self, message: str) -> None:
        self.actions.append(("commit", message))

    def push(self, branch: str) -> None:
        self.actions.append(("push", branch))

    def open_pr(self, branch: str, title: str, body: str) -> str:
        self.actions.append(("open_pr", branch))
        return f"dry-run://pull/{branch}"


@dataclass
class CommandBackend:
    """Backend réel (git + gh), ``dry_run=True`` par défaut."""

    cwd: Path = FRAMEWORK_ROOT
    dry_run: bool = True
    base_branch: str = "main"
    actions: list[tuple[str, str]] = field(default_factory=list)

    def _run(self, *argv: str) -> str:
        cmd = " ".join(shlex.quote(a) for a in argv)
        self.actions.append(("command" if not self.dry_run else "dry-run", cmd))
        if self.dry_run:
            return ""
        proc = subprocess.run(argv, cwd=str(self.cwd), capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"commande échouée ({proc.returncode}) : {cmd}\n{proc.stderr.strip()}")
        return proc.stdout.strip()

    def create_branch(self, branch: str) -> None:
        if branch in {"main", "master", "HEAD"}:
            raise ValueError(f"branche interdite : {branch}")
        self._run("git", "checkout", "-B", branch, self.base_branch)

    def write_fiche(self, relative_path: str, content: str) -> None:
        self.actions.append(("write_fiche" if not self.dry_run else "dry-run-write", relative_path))
        if self.dry_run:
            return
        target = self.cwd / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._run("git", "add", relative_path)

    def commit(self, message: str) -> None:
        self._run("git", "commit", "-m", message)

    def push(self, branch: str) -> None:
        self._run("git", "push", "-u", "origin", branch)

    def open_pr(self, branch: str, title: str, body: str) -> str:
        return self._run("gh", "pr", "create", "--head", branch, "--base", self.base_branch, "--title", title, "--body", body)


@dataclass
class FixResult:
    triggered: bool
    reason: str
    profile: str = ""
    agent_id: str = ""
    signature: str = ""
    branch: str = ""
    fiche_path: str = ""
    pr_url: str = ""
    failures: int = 0
    actions: list[tuple[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "triggered": self.triggered, "reason": self.reason, "profile": self.profile,
            "agent_id": self.agent_id, "signature": self.signature, "branch": self.branch,
            "fiche_path": self.fiche_path, "pr_url": self.pr_url, "failures": self.failures,
            "actions": [list(a) for a in self.actions],
            "merge_forbidden": True,
        }


class AutoFix:
    """Déclenche la branche + PR correctrice après 2 échecs d'un même profil."""

    def __init__(
        self,
        store: MemoryStore,
        backend: GitBackend | None = None,
        *,
        threshold: int = 2,
        base_dir: Path | None = None,
    ):
        self.store = store
        self.backend = backend or CommandBackend(
            dry_run=os.environ.get("OMNIBRAIN_AUTOFIX_APPLY") != "1"
        )
        self.threshold = threshold
        self.base_dir = base_dir or (FRAMEWORK_ROOT / "var" / "autofix")

    def check(self, profile: str, agent_id: str | None = None) -> FixResult:
        agent = agent_id or profile
        failures = self.store.failures_for(profile, limit=20)
        if len(failures) < self.threshold:
            return FixResult(
                triggered=False,
                reason=f"{len(failures)} échec(s) < seuil {self.threshold}",
                profile=profile, agent_id=agent, failures=len(failures),
            )

        signature = hashlib.sha256(
            "|".join(sorted(f"{f['id']}:{f['error_type']}" for f in failures)).encode("utf-8")
        ).hexdigest()[:12]
        if self.store.autofix_exists(signature):
            return FixResult(
                triggered=False, reason="correctif déjà proposé pour cette signature",
                profile=profile, agent_id=agent, signature=signature,
                failures=len(failures),
            )

        branch = f"omnibrain/fix-{_slug(agent)}"
        relative = f"var/autofix/{_slug(agent)}-{signature}.md"
        content = build_corrected_fiche(agent, failures, signature=signature)
        target = self.base_dir / Path(relative).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        self.backend.create_branch(branch)
        self.backend.write_fiche(relative, content)
        self.backend.commit(f"fix(agents): fiche corrigée {agent} après {len(failures)} échecs")
        self.backend.push(branch)
        pr_url = self.backend.open_pr(
            branch,
            f"fix(agents): {agent} — fiche corrigée après {len(failures)} échecs",
            f"Auto-amélioration OmniBrain v4. {len(failures)} échecs du profil `{profile}` "
            f"(signature `{signature}`). Fiche corrigée : `{relative}`. "
            "**Aucune fusion automatique : décision réservée à Lassana.**",
        )
        self.store.mark_autofix(signature, profile, agent, branch, "pr_opened")
        self.store.log(
            "omnibrain", "orchestrator", "autofix_branch_pr",
            {"signature": signature, "branch": branch, "failures": len(failures)}, level="WARN",
        )
        return FixResult(
            triggered=True, reason="seuil atteint : branche + PR créées",
            profile=profile, agent_id=agent, signature=signature, branch=branch,
            fiche_path=str(target), pr_url=pr_url, failures=len(failures),
            actions=list(getattr(self.backend, "actions", [])),
        )
