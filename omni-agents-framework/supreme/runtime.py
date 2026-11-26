"""Execution Runtime SUPREME — pool de workers réutilisables, concurrence bornée,
timeouts, annulation, backpressure. Pas de processus permanent par agent.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RuntimeConfig:
    max_workers: int = 4
    queue_limit: int = 64
    default_timeout_s: float = 30.0


class WorkerPool:
    def __init__(self, config: RuntimeConfig | None = None):
        self.config = config or RuntimeConfig()
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self._active = 0
        self._lock = threading.Lock()
        self._cancelled: set[str] = set()

    def submit(self, fn: Callable, *args, timeout: float | None = None, mission_id: str | None = None, **kwargs):
        with self._lock:
            if self._active >= self.config.queue_limit:
                raise RuntimeError("backpressure : file de workers saturée")
            self._active += 1
        start = time.monotonic()
        future = self._executor.submit(fn, *args, **kwargs)
        try:
            result = future.result(timeout=timeout or self.config.default_timeout_s)
            return {"ok": True, "result": result, "duration_ms": (time.monotonic() - start) * 1000}
        except FutureTimeout:
            future.cancel()
            return {"ok": False, "error": "timeout", "duration_ms": (time.monotonic() - start) * 1000}
        except Exception as e:
            return {"ok": False, "error": str(e), "duration_ms": (time.monotonic() - start) * 1000}
        finally:
            with self._lock:
                self._active -= 1

    def cancel_mission(self, mission_id: str) -> None:
        self._cancelled.add(mission_id)

    def is_cancelled(self, mission_id: str) -> bool:
        return mission_id in self._cancelled

    def stats(self) -> dict:
        with self._lock:
            return {"max_workers": self.config.max_workers, "active": self._active,
                    "queue_limit": self.config.queue_limit}

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
