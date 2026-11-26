"""Mémoire persistante — SQLAlchemy (PostgreSQL en production, SQLite en dev/tests).

Source de vérité : toutes les entités de mission, preuves, rapports, historiques,
erreurs, performances et recherches réutilisables sont persistées ici.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import (
    Boolean, Column, Float, Integer, JSON, String, Text, create_engine, func
)
from sqlalchemy.orm import declarative_base, sessionmaker

from .security import hash_password, verify_password

Base = declarative_base()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


class Mission(Base):
    __tablename__ = "missions"
    id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    mode = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    verdict = Column(String, default="NEEDS_WORK")
    owner = Column(String, default="system")
    progress = Column(Float, default=0.0)
    stage = Column(String, default="queued")
    created_at = Column(Float, default=time.time, index=True)
    updated_at = Column(Float, default=time.time)
    finished_at = Column(Float, nullable=True)
    error = Column(Text, default="")
    plan = Column(JSON, default=dict)
    meta = Column(JSON, default=dict)
    data_origin = Column(String, default="live")  # live | offline-fixture | none


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    division = Column(String, default="")
    wave = Column(Integer, default=0)
    status = Column(String, default="queued")
    attempt = Column(Integer, default=0)
    started_at = Column(Float, nullable=True)
    finished_at = Column(Float, nullable=True)
    duration_ms = Column(Float, default=0.0)
    output = Column(JSON, default=dict)
    error = Column(Text, default="")


class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, default="")
    domain = Column(String, default="")
    title = Column(Text, default="")
    snippet = Column(Text, default="")
    provider = Column(String, default="")
    score = Column(Float, default=0.0)
    published_at = Column(String, nullable=True)
    content_hash = Column(String, default="", index=True)
    verified = Column(Boolean, default=False)
    http_status = Column(Integer, nullable=True)
    untrusted = Column(Boolean, default=True)
    injection_flags = Column(JSON, default=list)
    fetched_at = Column(Float, default=time.time)
    raw = Column(JSON, default=dict)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    quote = Column(Text, default="")
    content_hash = Column(String, default="")
    untrusted = Column(Boolean, default=True)
    injection_flags = Column(JSON, default=list)
    collected_at = Column(Float, default=time.time)
    meta = Column(JSON, default=dict)


class ClaimRow(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    text = Column(Text, default="")
    status = Column(String, default="uncertain")
    confidence = Column(Float, default=0.0)
    support_ids = Column(JSON, default=list)
    contradict_ids = Column(JSON, default=list)
    independent_domains = Column(Integer, default=0)
    rationale = Column(Text, default="")


class ContradictionRow(Base):
    __tablename__ = "contradictions"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    claim_id = Column(String, default="")
    statement_a = Column(Text, default="")
    statement_b = Column(Text, default="")
    resolution = Column(String, default="unresolved")
    winner = Column(String, default="")
    rationale = Column(Text, default="")
    evidence_ids = Column(JSON, default=list)


class ReportRow(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True)
    mission_id = Column(String, nullable=False, index=True)
    markdown = Column(Text, default="")
    payload = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time, index=True)
    citation_count = Column(Integer, default=0)
    verdict = Column(String, default="NEEDS_WORK")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    ts = Column(Float, default=time.time, index=True)
    actor = Column(String, default="")
    action = Column(String, default="")
    resource = Column(String, default="")
    detail = Column(JSON, default=dict)


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(String, primary_key=True)
    ts = Column(Float, default=time.time, index=True)
    mission_id = Column(String, default="", index=True)
    component = Column(String, default="")
    message = Column(Text, default="")
    severity = Column(String, default="error")


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(String, primary_key=True)
    ts = Column(Float, default=time.time, index=True)
    mission_id = Column(String, default="", index=True)
    name = Column(String, default="", index=True)
    value = Column(Float, default=0.0)
    detail = Column(JSON, default=dict)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    id = Column(String, primary_key=True)
    ts = Column(Float, default=time.time, index=True)
    provider = Column(String, default="", index=True)
    operation = Column(String, default="search")
    status = Column(String, default="ok")
    latency_ms = Column(Float, default=0.0)
    result_count = Column(Integer, default=0)
    mission_id = Column(String, default="")
    error = Column(Text, default="")


class ResearchCache(Base):
    __tablename__ = "research_cache"
    id = Column(String, primary_key=True)
    query_hash = Column(String, default="", index=True)
    query = Column(Text, default="")
    mission_id = Column(String, default="")
    created_at = Column(Float, default=time.time, index=True)
    hits = Column(Integer, default=0)
    payload = Column(JSON, default=dict)


class EventRow(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(String, nullable=False, index=True)
    ts = Column(Float, default=time.time)
    kind = Column(String, default="")
    stage = Column(String, default="")
    payload = Column(JSON, default=dict)


class SettingRow(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(JSON, default=dict)
    updated_at = Column(Float, default=time.time)


class UserRow(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(Float, default=time.time)


ALL_TABLES = (
    Mission, Task, Source, Evidence, ClaimRow, ContradictionRow, ReportRow,
    AuditLog, ErrorLog, Metric, ProviderUsage, ResearchCache, EventRow,
    SettingRow, UserRow,
)


class Store:
    """Accès synchrone thread-safe (SQLite / PostgreSQL), session courte par appel."""

    def __init__(self, database_url: str, *, admin_password: str = "change-me-admin",
                 user_password: str = "change-me-user") -> None:
        self.database_url = database_url
        kwargs: dict[str, Any] = {"future": True}
        if database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            path = database_url.split("///")[-1]
            if path and not path.startswith(":"):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(database_url, **kwargs)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._lock = threading.RLock()
        self._admin_password = admin_password
        self._user_password = user_password

    def init(self) -> None:
        with self._lock:
            Base.metadata.create_all(self.engine)
        with self.session() as s:
            for username, password, role in (
                ("admin", self._admin_password, "admin"),
                ("researcher", self._user_password, "researcher"),
            ):
                row = s.get(UserRow, username)
                if row is None:
                    s.add(UserRow(username=username,
                                  password_hash=hash_password(password), role=role))
                else:
                    # Une rotation de mot de passe dans l'environnement doit
                    # prendre effet au redémarrage, sans effacer les données
                    # ni réécrire inutilement un hash déjà conforme.
                    if not verify_password(password, row.password_hash):
                        row.password_hash = hash_password(password)
                    row.role = role
            s.commit()

    @contextmanager
    def session(self) -> Iterator[Any]:
        s = self.Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # -- CRUD générique -----------------------------------------------------
    def add(self, obj: Any) -> Any:
        with self._lock, self.session() as s:
            s.add(obj)
            s.flush()
        return obj

    def get(self, model: Any, key: Any) -> Any | None:
        with self.session() as s:
            return s.get(model, key)

    def filter(self, model: Any, *, order_by: Any = None, limit: int | None = None,
               **criteria: Any) -> list[Any]:
        with self.session() as s:
            q = s.query(model)
            for key, value in criteria.items():
                q = q.filter(getattr(model, key) == value)
            if order_by is not None:
                q = q.order_by(order_by)
            if limit is not None:
                q = q.limit(limit)
            return list(q.all())

    def update(self, model: Any, key: Any, **values: Any) -> bool:
        with self._lock, self.session() as s:
            obj = s.get(model, key)
            if obj is None:
                return False
            for k, v in values.items():
                setattr(obj, k, v)
            s.add(obj)
        return True

    def count(self, model: Any, **criteria: Any) -> int:
        with self.session() as s:
            q = s.query(func.count()).select_from(model)
            for key, value in criteria.items():
                q = q.filter(getattr(model, key) == value)
            return int(q.scalar() or 0)

    # -- Événements (SSE + rejeu) ------------------------------------------
    def add_event(self, mission_id: str, kind: str, stage: str = "",
                  **payload: Any) -> int:
        ev = EventRow(mission_id=mission_id, ts=time.time(), kind=kind,
                      stage=stage, payload=_safe_json(payload))
        with self._lock, self.session() as s:
            s.add(ev)
            s.flush()
            return int(ev.id)
        return 0  # pragma: no cover

    def events_after(self, mission_id: str, last_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as s:
            rows = (s.query(EventRow)
                    .filter(EventRow.mission_id == mission_id, EventRow.id > last_id)
                    .order_by(EventRow.id.asc()).limit(limit).all())
            return [{"id": r.id, "ts": r.ts, "kind": r.kind, "stage": r.stage,
                     "payload": r.payload or {}} for r in rows]

    # -- Journalisation -----------------------------------------------------
    def audit(self, actor: str, action: str, resource: str = "", **detail: Any) -> None:
        self.add(AuditLog(id=_id("audit"), ts=time.time(), actor=actor,
                          action=action, resource=resource, detail=_safe_json(detail)))

    def record_error(self, component: str, message: str, mission_id: str = "",
                     severity: str = "error") -> None:
        self.add(ErrorLog(id=_id("err"), ts=time.time(), mission_id=mission_id,
                          component=component, message=message[:4000], severity=severity))

    def record_metric(self, name: str, value: float, mission_id: str = "",
                      **detail: Any) -> None:
        self.add(Metric(id=_id("met"), ts=time.time(), mission_id=mission_id,
                        name=name, value=float(value), detail=_safe_json(detail)))

    def record_usage(self, provider: str, operation: str, status: str,
                     latency_ms: float, result_count: int, mission_id: str = "",
                     error: str = "") -> None:
        self.add(ProviderUsage(id=_id("use"), ts=time.time(), provider=provider,
                               operation=operation, status=status,
                               latency_ms=latency_ms, result_count=result_count,
                               mission_id=mission_id, error=error[:1000]))

    def usage_today(self, provider: str) -> int:
        since = time.time() - 86400
        with self.session() as s:
            return int(s.query(func.count()).select_from(ProviderUsage)
                       .filter(ProviderUsage.provider == provider,
                               ProviderUsage.ts >= since,
                               ProviderUsage.status != "quota_exceeded").scalar() or 0)

    # -- Réglages -----------------------------------------------------------
    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.get(SettingRow, key)
        return row.value if row is not None else default

    def set_setting(self, key: str, value: Any) -> None:
        with self._lock, self.session() as s:
            row = s.get(SettingRow, key)
            if row is None:
                s.add(SettingRow(key=key, value=_safe_json(value), updated_at=time.time()))
            else:
                row.value = _safe_json(value)
                row.updated_at = time.time()
                s.add(row)

    # -- Rétention / sauvegarde ---------------------------------------------
    def purge(self, cutoff_ts: float, confirm: str) -> dict[str, int]:
        """Suppression explicite et auditée. Sans confirm='PURGE' -> refus."""
        if confirm != "PURGE":
            raise ValueError("Confirmation PURGE requise (opération destructive)")
        deleted: dict[str, int] = {}
        with self._lock, self.session() as s:
            timestamped = (
                (Mission, Mission.created_at), (Source, Source.fetched_at),
                (Evidence, Evidence.collected_at), (ReportRow, ReportRow.created_at),
                (AuditLog, AuditLog.ts), (ErrorLog, ErrorLog.ts), (Metric, Metric.ts),
                (ProviderUsage, ProviderUsage.ts), (ResearchCache, ResearchCache.created_at),
                (EventRow, EventRow.ts),
            )
            for model, column in timestamped:
                deleted[model.__tablename__] = s.query(model).filter(column < cutoff_ts).delete()
            mission_ids = {m.id for m in s.query(Mission.id).all()}
            # Entités dont la mission a été purgée : suppression des orphelins.
            for model in (Task, ClaimRow, ContradictionRow):
                rows = s.query(model).all()
                n = 0
                for row in rows:
                    if row.mission_id not in mission_ids:
                        s.delete(row)
                        n += 1
                deleted[model.__tablename__] = n
        return deleted

    def backup(self, destination: str) -> str:
        if not self.database_url.startswith("sqlite"):
            raise NotImplementedError(
                "Sauvegarde PostgreSQL : utiliser scripts/backup_postgres.sh (pg_dump)"
            )
        src = self.database_url.split("///")[-1]
        if not src or src.startswith(":"):
            raise NotImplementedError("Base SQLite en mémoire : rien à sauvegarder")
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            shutil.copy2(src, destination)
        return destination

    def stats(self) -> dict[str, int]:
        return {model.__tablename__: self.count(model) for model in ALL_TABLES}

    def close(self) -> None:
        self.engine.dispose()


def _safe_json(value: Any) -> Any:
    """Garantit la sérialisabilité avant écriture en colonne JSON."""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return {"_unserializable": str(value)[:500]}


def sqlite_path(database_url: str) -> str:
    return database_url.split("///")[-1]


def database_kind(database_url: str) -> str:
    return "postgresql" if database_url.startswith("postgres") else "sqlite"


def env_database_url() -> str:
    return os.getenv("OMNI_DATABASE_URL", "sqlite:///./data/omni_research.db")
