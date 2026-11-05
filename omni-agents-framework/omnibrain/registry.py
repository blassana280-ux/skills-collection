"""Registre des agents : découverte via matrix.toml + validation des fiches."""

from __future__ import annotations

from pathlib import Path

from .config import find_repo_root
from .frontmatter import parse_frontmatter, FrontmatterError
from .models import AgentDef, InterfaceContract

REQUIRED_FIELDS = ("id", "name", "description")


class Registry:
    def __init__(self, root: Path | None = None, matrix: dict | None = None):
        self.root = root or find_repo_root()
        self.matrix = matrix
        if self.matrix is None:
            from .config import load_matrix

            self.matrix = load_matrix(self.root)
        self._agents: list[AgentDef] | None = None

    # ------------------------------------------------------------- chargement

    def _load_agent(self, entry: dict) -> AgentDef:
        path = self.root / entry["file"]
        description = ""
        body = ""
        if path.is_file():
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            description = str(meta.get("description", ""))
        return AgentDef(
            id=entry["id"],
            name=entry.get("name", entry["id"]),
            file=entry["file"],
            domains=list(entry.get("domains", [])),
            keywords=list(entry.get("keywords", [])),
            artifacts=list(entry.get("artifacts", [])),
            emoji=entry.get("emoji", "🤖"),
            orchestrator=bool(entry.get("orchestrator", False)),
            risk=bool(entry.get("risk", False)),
            description=description,
            body=body,
            squad=entry.get("squad", "core"),
        )

    def agents(self) -> list[AgentDef]:
        if self._agents is None:
            self._agents = [self._load_agent(entry) for entry in self.matrix["agents"]]
        return list(self._agents)

    def by_id(self, agent_id: str) -> AgentDef:
        for agent in self.agents():
            if agent.id == agent_id:
                return agent
        raise KeyError(f"agent inconnu : {agent_id!r}")

    def contracts(self) -> list[InterfaceContract]:
        out: list[InterfaceContract] = []
        for entry in self.matrix.get("contracts", []):
            out.append(
                InterfaceContract(
                    artifact=entry["artifact"],
                    producers=list(entry["producers"]),
                    consumers=list(entry["consumers"]),
                    schema_ref=entry.get("schema", ""),
                )
            )
        return out

    # ------------------------------------------------------------- validation

    def validate(self) -> list[str]:
        """Retourne la liste des erreurs (liste vide = réseau valide)."""
        errors: list[str] = []
        ids: set[str] = set()
        for entry in self.matrix["agents"]:
            agent_id = entry.get("id", "<sans-id>")
            if agent_id in ids:
                errors.append(f"id dupliqué dans matrix.toml : {agent_id}")
            ids.add(agent_id)

            path = self.root / entry.get("file", "")
            if not path.is_file():
                errors.append(f"[{agent_id}] fichier introuvable : {entry.get('file')}")
                continue
            try:
                meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except FrontmatterError as exc:
                errors.append(f"[{agent_id}] frontmatter invalide : {exc}")
                continue
            for field_name in REQUIRED_FIELDS:
                if not meta.get(field_name):
                    errors.append(f"[{agent_id}] champ frontmatter manquant : {field_name}")
            if meta.get("id") and meta["id"] != agent_id:
                errors.append(
                    f"[{agent_id}] id de frontmatter ({meta['id']}) != id matrice ({agent_id})"
                )

        known = ids
        for contract in self.matrix.get("contracts", []):
            for role in ("producers", "consumers"):
                for agent_id in contract.get(role, []):
                    if agent_id not in known:
                        errors.append(
                            f"contrat {contract.get('artifact')!r}: agent {role} inconnu -> {agent_id}"
                        )
            schema_ref = contract.get("schema", "")
            if schema_ref and "#" in schema_ref:
                rel_path = schema_ref.split("#", 1)[0]
                if not (self.root / rel_path).is_file():
                    errors.append(f"contrat {contract.get('artifact')!r}: schéma introuvable -> {rel_path}")
        return errors
