"""Journalisation structurée, sans secret, avec corrélation par mission."""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

from .security import redact

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _CONFIGURED = True


def log_event(component: str, event: str, *, mission_id: str = "", level: str = "INFO",
              **fields: Any) -> None:
    record = {
        "ts": round(time.time(), 3),
        "level": level,
        "component": component,
        "event": event,
        "mission_id": mission_id,
        **{k: redact(str(v)) if isinstance(v, str) else v for k, v in fields.items()},
    }
    logging.getLogger("omni").log(
        getattr(logging, level.upper(), logging.INFO), json.dumps(record, ensure_ascii=False)
    )
