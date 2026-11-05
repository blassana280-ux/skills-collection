#!/usr/bin/env python3
"""Exécute les actions restantes de la mission OmniBrain v4.

Conçu pour être lancé avec un jeton ayant les droits (PAT scope ``repo``), ou
depuis une session Arena dont l'installation GitHub App couvre les dépôts cibles.

    python3 scripts/finalize_actions.py                       # dry-run (défaut)
    python3 scripts/finalize_actions.py --apply --confirm-lassana

Chaque action est précédée d'une **sonde de permission** (payload invalide →
422 = droit présent, 403 = droit absent ; ``git push --dry-run`` pour l'écriture
git). Une action dont la sonde échoue est journalisée ``BLOQUÉ 403`` et
**jamais forcée**. Aucune fusion directe sur ``main``, aucune création de branche
dans le dépôt de session : les promotions passent par branche + PR.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

FRAMEWORK = Path(__file__).resolve().parents[1]
ACCOUNT = "blassana280-ux"
AGENTSKILLS = f"{ACCOUNT}/agentskills"
TARGET = f"{ACCOUNT}/omni-agents-framework"
SESSION_REPO = f"{ACCOUNT}/skills-collection"
SESSION_BRANCH = "arena/2644be5c-skills-collection"
MERGE_ORDER = [2, 4, 3]  # PR #2 fondation, #4 avec résolution AGENTS.md, #3 ensuite

PRESERVE_IN_TARGET = {
    "AGENTS.md",            # source de vérité du dépôt dédié
    "omni/__init__.py",     # orchestrateur v1 : fusionner, pas écraser
    "tests/__init__.py",    # suite 69 tests
    "tests/helpers.py",
    "OMNIBRAIN.md", "README.md", "LICENSE", "Makefile",
}


def run(cmd: list[str], *, cwd: Path | None = None, dry: bool = False, check: bool = True) -> dict[str, Any]:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(("[DRY] " if dry else "$ ") + printable, flush=True)
    if dry:
        return {"cmd": printable, "dry": True, "returncode": 0, "stdout": "", "stderr": ""}
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    result = {
        "cmd": printable, "dry": False, "returncode": proc.returncode,
        "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(),
    }
    if check and proc.returncode != 0:
        raise RuntimeError(f"échec ({proc.returncode}) : {printable}\n{proc.stderr.strip()}")
    return result


def gh_api(path: str, *, method: str = "GET", fields: list[str] | None = None, jq: str = ".") -> subprocess.CompletedProcess:
    cmd = ["gh", "api", "-X", method, path, "--jq", jq]
    for field in fields or []:
        cmd += ["-f", field]
    return subprocess.run(cmd, capture_output=True, text=True)


# ------------------------------------------------------------------ sondes
def probe_pulls(repo: str) -> tuple[bool, str]:
    """POST /pulls avec payload invalide : 422 = droit, 403 = absent."""
    p = gh_api(f"repos/{repo}/pulls", method="POST", fields=["title=", "head=", "base="], jq="{message,status}")
    body = (p.stdout + p.stderr).strip()
    ok = "403" not in body and '"status": 403' not in body
    return ok, body[:180]


def probe_repo_create() -> tuple[bool, str]:
    p = gh_api("user/repos", method="POST", fields=["name="], jq="{message,status}")
    body = (p.stdout + p.stderr).strip()
    ok = "403" not in body and '"status": 403' not in body
    return ok, body[:180]


def probe_push(repo: str) -> tuple[bool, str]:
    """push --dry-run vers une branche existante : aucune écriture."""
    url = f"https://github.com/{repo}.git"
    heads = subprocess.run(["git", "ls-remote", "--heads", url], capture_output=True, text=True)
    if heads.returncode != 0:
        return False, heads.stderr.strip()[:180]
    first = next((line.split("\t")[1] for line in heads.stdout.splitlines() if "\t" in line), None)
    if not first:
        return False, "aucune branche distante"
    p = subprocess.run(["git", "push", "--dry-run", url, f"HEAD:{first}"], capture_output=True, text=True)
    body = (p.stderr + p.stdout).strip()
    return p.returncode == 0, body[:180]


def probe_scopes() -> str:
    p = subprocess.run(["gh", "api", "-i", "user"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.lower().startswith("x-oauth-scopes:"):
            return line.split(":", 1)[1].strip()
    return ""


# ------------------------------------------------------------------ actions
def action_merge_agentskills(*, dry: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "merge_agentskills", "order": MERGE_ORDER, "merged": [], "errors": []}
    for number in MERGE_ORDER:
        state = gh_api(f"repos/{AGENTSKILLS}/pulls/{number}", jq="{state,mergeable,mergeStateStatus}")
        out.setdefault("states", {})[str(number)] = state.stdout.strip()
        if dry:
            run(["gh", "pr", "merge", str(number), "-R", AGENTSKILLS, "--merge"], dry=True)
            continue
        # #4 : conflit AGENTS.md avec #2 -> résolution manuelle avant fusion.
        if number == 4 and "CONFLICTING" in state.stdout.upper() or (number == 4 and "DIRTY" in state.stdout.upper()):
            out["errors"].append("PR #4 conflictante : résoudre AGENTS.md à la main avant fusion (jamais forcé)")
            continue
        try:
            run(["gh", "pr", "merge", str(number), "-R", AGENTSKILLS, "--merge"])
            out["merged"].append(number)
        except RuntimeError as exc:
            out["errors"].append(str(exc)[:200])
    return out


def action_profile_repo(*, dry: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "create_profile_repo", "repo": f"{ACCOUNT}/.github"}
    source = FRAMEWORK / "docs" / "PROFILE-REPO-AGENTS.md"
    cmds = [
        ["gh", "repo", "create", f"{ACCOUNT}/.github", "--public", "--description", "Profil OmniBrain", "--confirm"],
    ]
    for cmd in cmds:
        run(cmd, dry=dry)
    if dry:
        out["status"] = "dry-run"
        return out
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run(["git", "clone", f"https://github.com/{ACCOUNT}/.github.git", str(root / "profile")])
        repo = root / "profile"
        shutil.copyfile(source, repo / "AGENTS.md")
        (repo / "README.md").write_text("# blassana280-ux\n\nRéseau OmniBrain : voir AGENTS.md.\n", encoding="utf-8")
        run(["git", "switch", "-c", "omnibrain/profile-agents"], cwd=repo)
        run(["git", "add", "AGENTS.md", "README.md"], cwd=repo)
        run(["git", "commit", "-m", "docs(profile): routage OmniBrain au niveau du compte"], cwd=repo)
        run(["git", "push", "-u", "origin", "omnibrain/profile-agents"], cwd=repo)
        run(["gh", "pr", "create", "-R", f"{ACCOUNT}/.github", "--base", "main",
             "--head", "omnibrain/profile-agents", "--title", "Routage AGENTS.md au niveau du compte"], cwd=repo)
    out["status"] = "pr_opened"
    return out


def action_promote(*, dry: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "promote_v4", "target": TARGET, "branch": "omnibrain/promote-v4"}
    if dry:
        for cmd in [
            ["git", "clone", f"https://github.com/{TARGET}.git", "<TMP>"],
            ["git", "switch", "-c", "omnibrain/promote-v4"],
            ["cp", "-a", f"{FRAMEWORK}/{{omni,omnibrain,tools,tests,specialized,catalog,matrix.toml,docs}}", "."],
            ["gh", "pr", "create", "-R", TARGET, "--base", "main", "--head", "omnibrain/promote-v4"],
        ]:
            run(cmd, dry=True)
        out["status"] = "dry-run"
        out["preserved"] = sorted(PRESERVE_IN_TARGET)
        return out
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "target"
        run(["git", "clone", f"https://github.com/{TARGET}.git", str(repo)])
        run(["git", "switch", "-c", "omnibrain/promote-v4"], cwd=repo)
        for item in sorted(FRAMEWORK.iterdir()):
            if item.name in {".git", "__pycache__", "var", ".github"}:
                continue
            dest = repo / item.name
            if item.is_dir():
                for src in item.rglob("*"):
                    if not src.is_file() or "__pycache__" in src.parts:
                        continue
                    rel = src.relative_to(FRAMEWORK)
                    if str(rel) in PRESERVE_IN_TARGET:
                        continue  # ne jamais écraser la source de vérité du dépôt dédié
                    target = repo / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, target)
            elif item.is_file() and item.name not in PRESERVE_IN_TARGET:
                shutil.copyfile(item, dest)
        # Fusion additive des exports, sans écraser l'orchestrateur v1.
        init_v1 = repo / "omni" / "__init__.py"
        if init_v1.is_file():
            with init_v1.open("a", encoding="utf-8") as fh:
                fh.write("\n# OmniBrain v4\nfrom .memory import MemoryStore, record_mission, get_recettes\n"
                         "from .graph import StateGraph, build_pipeline, run_pipeline\n"
                         "from .sandbox import Sandbox, RBAC, Runtime\n"
                         "from .telemetry import WaveTelemetry\n")
        run(["git", "add", "-A"], cwd=repo)
        run(["git", "commit", "-m", "feat(omnibrain): promouvoir la couche v4"], cwd=repo)
        run(["git", "push", "-u", "origin", "omnibrain/promote-v4"], cwd=repo)
        run(["gh", "pr", "create", "-R", TARGET, "--base", "main", "--head", "omnibrain/promote-v4",
             "--title", "OmniBrain v4", "--body", "Décision de fusion : Lassana"], cwd=repo)
    out["status"] = "pr_opened"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Actions finales OmniBrain v4")
    parser.add_argument("--apply", action="store_true", help="exécute réellement (sinon dry-run)")
    parser.add_argument("--confirm-lassana", action="store_true", help="confirmation humaine explicite")
    args = parser.parse_args(argv)
    dry = not args.apply
    if args.apply and not args.confirm_lassana:
        print("REFUS : --apply exige --confirm-lassana (décision humaine explicite)", file=sys.stderr)
        return 2

    scopes = probe_scopes()
    probes = {
        "scopes": scopes or "(vide = jeton d'installation GitHub App)",
        "pulls_agentskills": probe_pulls(AGENTSKILLS),
        "pulls_target": probe_pulls(TARGET),
        "repo_create": probe_repo_create(),
        "push_agentskills": probe_push(AGENTSKILLS),
        "push_target": probe_push(TARGET),
        "push_session": probe_push(SESSION_REPO),
    }
    ok = {k: v[0] for k, v in probes.items() if isinstance(v, tuple)}
    print("\n=== Sondes de permission ===")
    for key, value in probes.items():
        print(f"{key}: {'OK' if isinstance(value, tuple) and value[0] else 'BLOQUÉ'} | {value if not isinstance(value, tuple) else value[1]}")

    results: list[dict[str, Any]] = []
    results.append(action_merge_agentskills(dry=dry or not ok["pulls_agentskills"]))
    results.append(action_profile_repo(dry=dry or not ok["repo_create"]))
    results.append(action_promote(dry=dry or not ok["push_target"]))

    summary = {
        "mode": "dry-run" if dry else "apply",
        "scopes": scopes,
        "probes_ok": ok,
        "actions": results,
        "executed": [r["action"] for r in results if r.get("status") not in {"dry-run", None} and not r.get("errors")],
        "blocked_403": [k for k, v in ok.items() if not v],
        "no_forced_merge": True,
    }
    print("\n=== Bilan JSON ===\n" + json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
