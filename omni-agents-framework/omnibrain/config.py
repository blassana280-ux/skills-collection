"""Chargement de la configuration et résolution des chemins du dépôt."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

MATRIX_NAME = "matrix.toml"


def find_repo_root(start: Path | None = None) -> Path:
    """Remonte l'arborescence jusqu'à trouver ``matrix.toml``.

    Permet au CLI de fonctionner depuis n'importe quel sous-dossier du dépôt.
    Variable d'évasion : ``OMNIBRAIN_HOME`` pointe directement vers la racine.
    """
    env_home = os.environ.get("OMNIBRAIN_HOME")
    if env_home:
        candidate = Path(env_home)
        if (candidate / MATRIX_NAME).is_file():
            return candidate
        raise FileNotFoundError(f"OMNIBRAIN_HOME={env_home} ne contient pas {MATRIX_NAME}")

    current = (start or Path.cwd()).resolve()
    for parent in (current, *current.parents):
        if (parent / MATRIX_NAME).is_file():
            return parent
    # Dernier recours : racine du paquet (cas d'un import depuis les tests).
    package_root = Path(__file__).resolve().parent.parent
    if (package_root / MATRIX_NAME).is_file():
        return package_root
    raise FileNotFoundError(
        f"{MATRIX_NAME} introuvable à partir de {current}. "
        "Positionnez-vous dans le dépôt omnibrain ou définissez OMNIBRAIN_HOME."
    )


def load_matrix(root: Path | None = None) -> dict[str, Any]:
    """Lit la matrice principale et fusionne les catalogues ``catalog/*.toml``.

    La matrice ``matrix.toml`` porte les 12 agents cœur, la classification et
    les contrats. Les catalogues générés (100 agents spécialisés) ajoutent
    leurs entrées ``[[agents]]`` sans écraser la configuration centrale.
    """
    root = root or find_repo_root()
    path = root / MATRIX_NAME
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if "agents" not in data or not isinstance(data["agents"], list):
        raise ValueError(f"{path}: la table [[agents]] est obligatoire et doit être une liste")
    if "classification" not in data:
        raise ValueError(f"{path}: la section [classification] est obligatoire")

    catalog_dir = root / "catalog"
    if catalog_dir.is_dir():
        for catalog_path in sorted(catalog_dir.glob("*.toml")):
            with catalog_path.open("rb") as fh:
                catalog = tomllib.load(fh)
            data["agents"].extend(catalog.get("agents", []))
    return data
