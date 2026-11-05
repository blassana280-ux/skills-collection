"""Shared/Individual Memory Engine SUPREME — 4 niveaux, 8 types, FTS5, graphe de
connaissances, provenance, confiance, versionnement, TTL, ACL, suppression contrôlée.

Niveaux : central, individual, division, collective.
Types : working, episodic, semantic, procedural, historical, decision, error, skill.
La recherche sémantique par embeddings est une interface ; sans fournisseur
d'embeddings configuré, seule la recherche plein texte (FTS5) et lexicale est
réellement disponible — signalé honnêtement.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from .db import log_event, now, transaction
from .security import redact, scan_injection, wrap_untrusted

LEVELS = ("central", "individual", "division", "collective")
KINDS = ("working", "episodic", "semantic", "procedural", "historical", "decision", "error", "skill")

_TOKEN_RE = re.compile(r"[a-z0-9àâäéèêëïîôöùûüç]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def tfidf_rank(query: str, documents: list[str]) -> list[float]:
    """Similarité cosinus TF-IDF locale (sans fournisseur). Vraie recherche contextuelle.

    Renvoie un score [0,1] par document. Fonctionne hors ligne ; ne remplace pas des
    embeddings neuronaux mais offre un rappel contextuel réel au-delà du simple LIKE.
    """
    q_tokens = _tokenize(query)
    if not q_tokens or not documents:
        return [0.0] * len(documents)
    doc_tokens = [_tokenize(d) for d in documents]
    n = len(documents)
    df = Counter()
    for toks in doc_tokens:
        for t in set(toks):
            df[t] += 1
    idf = {t: math.log((n + 1) / (df[t] + 1)) + 1 for t in df}
    q_tf = Counter(q_tokens)
    q_vec = {t: q_tf[t] * idf.get(t, 0.0) for t in q_tf}
    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
    scores = []
    for toks in doc_tokens:
        tf = Counter(toks)
        d_vec = {t: tf[t] * idf.get(t, 0.0) for t in tf}
        d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0
        dot = sum(q_vec.get(t, 0.0) * d_vec.get(t, 0.0) for t in q_vec)
        scores.append(max(0.0, min(1.0, dot / (q_norm * d_norm))))
    return scores


class MemoryEngine:
    def __init__(self, conn: sqlite3.Connection, registry):
        self.conn = conn
        self.registry = registry

    # ------------------------------------------------------------------ ACL
    def _can_write(self, actor: str, level: str, owner: str) -> bool:
        if actor == "omnibrain-core":
            return True
        prof = self.registry.profile(actor)
        if level not in prof["permissions"].get("memory_write", []):
            return False
        if level == "individual":
            return owner == actor
        if level == "division":
            return owner == prof["division"]
        if level in ("central", "collective"):
            return prof["kind"] == "manager"
        return False

    def _can_read(self, actor: str, level: str, owner: str) -> bool:
        if actor == "omnibrain-core":
            return True
        prof = self.registry.profile(actor)
        if level not in prof["permissions"].get("memory_read", []):
            return False
        if level == "individual":
            return owner == actor
        if level == "division":
            return owner == prof["division"]
        return True  # central/collective lisibles par tous les agents autorisés

    # ---------------------------------------------------------------- write
    def add(self, actor: str, level: str, owner: str, kind: str, content: str,
            source: str = "", confidence: float = 0.5, metadata: dict | None = None,
            ttl_days: int | None = None, untrusted: bool = False) -> str:
        if level not in LEVELS or kind not in KINDS:
            raise ValueError("niveau ou type de mémoire invalide")
        if not self._can_write(actor, level, owner):
            raise PermissionError(f"écriture mémoire refusée : {actor} -> {level}/{owner}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("contenu mémoire vide")
        meta = dict(metadata or {})
        if untrusted:
            flags = scan_injection(content)
            meta["untrusted"] = True
            meta["injection_flags"] = len(flags)
            content = wrap_untrusted(content)
        content = redact(content)
        mid = f"mem-{uuid.uuid4().hex[:12]}"
        expires = None
        if ttl_days:
            expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat(timespec="seconds")
        with transaction(self.conn):
            self.conn.execute(
                """INSERT INTO memory_items(id,level,owner,kind,content,metadata_json,confidence,source,
                   created_at,expires_at,version) VALUES(?,?,?,?,?,?,?,?,?,?,1)""",
                (mid, level, owner, kind, content, json.dumps(meta, ensure_ascii=False),
                 max(0.0, min(1.0, confidence)), redact(source), now(), expires))
        log_event(self.conn, "debug", "memory", f"ajout {level}/{owner}/{kind}", data={"id": mid})
        return mid

    def update(self, actor: str, item_id: str, content: str, confidence: float | None = None,
               metadata: dict | None = None) -> str:
        """Versionnement : crée une nouvelle version liée à la précédente."""
        old = self._get_raw(item_id)
        if not self._can_write(actor, old["level"], old["owner"]):
            raise PermissionError("mise à jour mémoire refusée")
        new_id = f"mem-{uuid.uuid4().hex[:12]}"
        meta = json.loads(old["metadata_json"])
        if metadata:
            meta.update(metadata)
        with transaction(self.conn):
            self.conn.execute(
                """INSERT INTO memory_items(id,level,owner,kind,content,metadata_json,confidence,source,
                   created_at,expires_at,version,parent_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_id, old["level"], old["owner"], old["kind"], redact(content),
                 json.dumps(meta, ensure_ascii=False), confidence if confidence is not None else old["confidence"],
                 old["source"], now(), old["expires_at"], old["version"] + 1, item_id))
            self.conn.execute("UPDATE memory_items SET deleted=1 WHERE id=?", (item_id,))
        return new_id

    def delete(self, actor: str, item_id: str, reason: str) -> None:
        item = self._get_raw(item_id)
        if not self._can_write(actor, item["level"], item["owner"]):
            raise PermissionError("suppression mémoire refusée")
        with transaction(self.conn):
            self.conn.execute("UPDATE memory_items SET deleted=1, metadata_json=? WHERE id=?",
                              (json.dumps({**json.loads(item["metadata_json"]), "deleted_reason": reason}), item_id))
        log_event(self.conn, "info", "memory", f"suppression contrôlée {item_id}: {reason}")

    def expire(self) -> int:
        with transaction(self.conn):
            cur = self.conn.execute("UPDATE memory_items SET deleted=1 WHERE expires_at IS NOT NULL AND expires_at < ? AND deleted=0", (now(),))
            return cur.rowcount

    # ----------------------------------------------------------------- read
    def _get_raw(self, item_id: str) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM memory_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(f"mémoire inconnue : {item_id}")
        return row

    def get(self, actor: str, item_id: str) -> dict:
        row = self._get_raw(item_id)
        if row["deleted"] or not self._can_read(actor, row["level"], row["owner"]):
            raise PermissionError("lecture mémoire refusée")
        d = dict(row)
        d["metadata"] = json.loads(d.pop("metadata_json"))
        return d

    def search(self, actor: str, query: str = "", level: str | None = None, owner: str | None = None,
               kind: str | None = None, limit: int = 20, mode: str = "auto") -> dict:
        fts_available = self.conn.execute("SELECT value FROM schema_meta WHERE key='fts5'").fetchone()["value"] == "1"
        results: list[dict] = []
        used = "metadata"
        if query and mode == "tfidf":
            # Recherche contextuelle locale réelle : rappel large par tokens + cosinus TF-IDF.
            tokens = _tokenize(query)
            seen, candidates = set(), []
            for tok in tokens or [query]:
                rows = self.conn.execute(
                    "SELECT * FROM memory_items WHERE deleted=0 AND content LIKE ? LIMIT ?",
                    (f"%{tok}%", limit * 6)).fetchall()
                for r in rows:
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        candidates.append(dict(r))
            if candidates:
                scores = tfidf_rank(query, [c["content"] for c in candidates])
                for c, s in zip(candidates, scores):
                    c["_tfidf"] = round(s, 4)
                candidates.sort(key=lambda c: c["_tfidf"], reverse=True)
                results = candidates
            used = "tfidf"
        elif query and fts_available and mode in ("auto", "fts"):
            try:
                rows = self.conn.execute(
                    """SELECT m.* FROM memory_fts f JOIN memory_items m ON m.rowid=f.rowid
                       WHERE memory_fts MATCH ? AND m.deleted=0 ORDER BY rank LIMIT ?""",
                    (query, limit * 4)).fetchall()
                results = [dict(r) for r in rows]
                used = "fts5"
            except sqlite3.OperationalError:
                results = []
                used = "like"
        if not results and query:
            like = f"%{query}%"
            rows = self.conn.execute(
                "SELECT * FROM memory_items WHERE deleted=0 AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (like, limit * 4)).fetchall()
            results = [dict(r) for r in rows]
            used = "like"
        if not query:
            rows = self.conn.execute("SELECT * FROM memory_items WHERE deleted=0 ORDER BY created_at DESC LIMIT ?",
                                     (limit * 4,)).fetchall()
            results = [dict(r) for r in rows]
            used = "metadata"
        # Filtres ACL + métadonnées
        filtered = []
        for r in results:
            if level and r["level"] != level:
                continue
            if owner and r["owner"] != owner:
                continue
            if kind and r["kind"] != kind:
                continue
            if not self._can_read(actor, r["level"], r["owner"]):
                continue
            r["metadata"] = json.loads(r.pop("metadata_json"))
            filtered.append(r)
            if len(filtered) >= limit:
                break
        return {"results": filtered, "mode": used, "semantic_available": False,
                "tfidf_available": True,
                "semantic_note": "recherche contextuelle TF-IDF locale disponible (mode='tfidf') ; "
                                 "embeddings neuronaux indisponibles sans fournisseur configuré"}

    # -------------------------------------------------------- knowledge graph
    def relate(self, actor: str, src: str, dst: str, relation: str) -> None:
        self.get(actor, src)
        self.get(actor, dst)
        with transaction(self.conn):
            self.conn.execute("INSERT OR IGNORE INTO memory_relations(src,dst,relation) VALUES(?,?,?)",
                              (src, dst, relation))

    def neighbors(self, actor: str, item_id: str) -> list[dict]:
        self.get(actor, item_id)
        rows = self.conn.execute("SELECT * FROM memory_relations WHERE src=? OR dst=?", (item_id, item_id)).fetchall()
        return [dict(r) for r in rows]

    def contradictions(self, actor: str, level: str, owner: str) -> list[dict]:
        """Détecte les connaissances contradictoires (même sujet/clé, valeurs différentes)."""
        items = self.search(actor, level=level, owner=owner, limit=1000)["results"]
        by_key: dict[tuple, list] = {}
        for it in items:
            meta = it["metadata"]
            key = meta.get("subject_key")
            if key:
                by_key.setdefault((key, meta.get("claim_key", "value")), []).append(it)
        out = []
        for (key, claim_key), group in by_key.items():
            values = {}
            for it in group:
                meta = it["metadata"]
                value = meta.get("claim_value", it["content"])
                canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                values.setdefault(canonical, []).append(it["id"])
            if len(values) > 1:
                out.append({"subject_key": key, "claim_key": claim_key,
                            "ids": [it["id"] for it in group], "distinct_values": len(values)})
        return out

    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) c FROM memory_items WHERE deleted=0").fetchone()["c"]
        by_level = {r["level"]: r["c"] for r in self.conn.execute(
            "SELECT level, COUNT(*) c FROM memory_items WHERE deleted=0 GROUP BY level")}
        relations = self.conn.execute("SELECT COUNT(*) c FROM memory_relations").fetchone()["c"]
        return {"total": total, "by_level": by_level, "relations": relations}
