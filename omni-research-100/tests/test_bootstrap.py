"""Garanties statiques du script de reprise vers le dépôt privé dédié.

Le dépôt cible n'existe pas encore : le comportement `--check` a donc été
exécuté manuellement (refus correct avec 404). Ces tests verrouillent les
garanties qui ne doivent jamais régresser, sans dépendre de l'état du remote.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap_remote.sh"


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_bootstrap_script_is_executable_and_never_force_pushes():
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)
    text = _text()
    assert "git push --force" not in text
    assert "git push -f " not in text
    assert "gh pr merge" not in text
    assert "rm -rf" not in text
    assert "git reset --hard" not in text


def test_bootstrap_never_puts_product_code_on_main():
    text = _text()
    assert text.count("git commit --allow-empty") == 1
    assert 'checkout -B main' in text
    # Les groupes de fichiers produit ne sont ajoutés QUE sur les branches feat.
    main_section = text.split("== 7. Copie", 1)[0]
    assert "git add app/" not in main_section
    assert "git add tests" not in main_section
    assert "PRs NON fusionnées" in text or "PR NON fusionnée" in text


def test_bootstrap_creates_stacked_feature_branches_and_checks_empty_repo():
    text = _text()
    assert "--check" in text
    assert "aucune écriture" in text
    assert "dépôt contient déjà des commits" in text  # refus d'écraser
    for branch in ("feat/01-core-memory", "feat/02-agents-providers-brain",
                   "feat/03-api-omnibrain-ui", "feat/04-tests-ci-docs"):
        assert branch in text
    assert text.count("gh pr create") == 1  # appelé une fois dans la boucle
    assert "for i in 0 1 2 3" in text
    assert "administration" in text  # protection signalée, jamais contournée
