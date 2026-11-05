"""Parseur de frontmatter YAML minimal (sous-ensemble volontairement borné).

Les fichiers d'agents utilisent un YAML plat :
    clé: valeur
    clé: "valeur"
    clé: [a, b, c]
    clé:
      - item 1
      - item 2

Aucune dépendance externe : ce sous-ensemble est suffisant pour le réseau
OmniBrain et reste auditable en quelques dizaines de lignes.
"""

from __future__ import annotations


class FrontmatterError(ValueError):
    """Frontmatter mal formé."""


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _split_inline_list(raw: str) -> list[str]:
    inner = raw.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    return [_strip_quotes(part) for part in inner.split(",") if part.strip()]


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Retourne (métadonnées, corps Markdown).

    Si le document n'a pas de bloc ``--- ... ---`` en tête, retourne
    un dictionnaire vide et le texte intact.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise FrontmatterError("frontmatter non fermé : le délimiteur '---' de clôture est absent")

    meta: dict[str, object] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith(("  -", "\t-", "- ")) or line.strip().startswith("- "):
            if current_key is None:
                raise FrontmatterError(f"élément de liste sans clé parente : {line!r}")
            item = line.strip()[1:].strip()
            bucket = meta.setdefault(current_key, [])
            if not isinstance(bucket, list):
                raise FrontmatterError(f"la clé {current_key!r} mélange liste et valeur scalaire")
            bucket.append(_strip_quotes(item))
            continue
        if ":" not in line:
            raise FrontmatterError(f"ligne sans ':' dans le frontmatter : {line!r}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            meta[key] = []
            current_key = key
        elif value.startswith("["):
            meta[key] = _split_inline_list(value)
            current_key = None
        else:
            meta[key] = _strip_quotes(value)
            current_key = None

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body
