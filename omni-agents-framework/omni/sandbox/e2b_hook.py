"""Hook d'exécution isolée E2B (``runCode``) avec fallback local (Phase 3.2).

E2B n'est **jamais** une dépendance obligatoire : le SDK est importé paresseusement,
la clé vient de ``E2B_API_KEY`` (jamais du dépôt). Toute indisponibilité (SDK
absent, clé absente, erreur réseau/API, timeout) bascule sur un sous-processus
Python local isolé et **tracé** (``backend='local'`` + ``fallback_reason``).

Le fallback local applique : ``python -I``, environnement minimal, répertoire de
travail temporaire, timeout et limites POSIX (CPU / mémoire) quand disponibles.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxResult:
    backend: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    error: str = ""
    fallback_reason: str = ""
    heavy: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.error

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend, "stdout": self.stdout, "stderr": self.stderr,
            "exit_code": self.exit_code, "duration_ms": round(self.duration_ms, 3),
            "error": self.error, "fallback_reason": self.fallback_reason,
            "heavy": self.heavy, "ok": self.ok,
        }


def _limits() -> None:
    """Limites POSIX best-effort appliquées au sous-processus local."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    except (ImportError, ValueError, OSError):  # pragma: no cover - dépend de l'hôte
        pass


@dataclass
class Sandbox:
    api_key: str | None = None
    timeout_s: float = 5.0
    e2b_factory: Any | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("E2B_API_KEY")

    def run_code(self, code: str, *, heavy: bool = False, language: str = "python") -> SandboxResult:
        """Exécute ``code`` : E2B si disponible, sinon fallback local tracé."""
        if language != "python":
            return SandboxResult(
                backend="none", exit_code=2, heavy=heavy,
                error=f"langage non supporté par le hook : {language}",
                fallback_reason="unsupported_language",
            )
        self._fallback_reason = "e2b_not_configured"
        result = self._try_e2b(code, heavy=heavy)
        if result is not None:
            self.events.append({"attempt": "e2b", **result.as_dict()})
            return result
        local = self._run_local(code, heavy=heavy)
        self.events.append({"attempt": "local", **local.as_dict()})
        return local

    # ------------------------------------------------------------------ E2B
    def _try_e2b(self, code: str, *, heavy: bool) -> SandboxResult | None:
        if not self.api_key and self.e2b_factory is None:
            return None
        started = time.perf_counter()
        try:
            if self.e2b_factory is not None:
                sandbox = self.e2b_factory()
            else:
                from e2b import Sandbox as E2BSandbox  # import paresseux, dépendance optionnelle

                sandbox = E2BSandbox.create(api_key=self.api_key)
            runner = getattr(sandbox, "run_code", None) or getattr(sandbox, "runCode", None)
            if runner is None:
                raise RuntimeError("SDK E2B sans méthode runCode/run_code")
            execution = runner(code)
            stdout = getattr(execution, "stdout", None)
            stderr = getattr(execution, "stderr", None)
            if isinstance(execution, dict):
                stdout, stderr = execution.get("stdout", ""), execution.get("stderr", "")
            elif stdout is None and isinstance(execution, str):
                stdout = execution
            return SandboxResult(
                backend="e2b", stdout=str(stdout or ""), stderr=str(stderr or ""),
                exit_code=int(getattr(execution, "exit_code", 0) or 0),
                duration_ms=(time.perf_counter() - started) * 1000, heavy=heavy,
            )
        except Exception as exc:  # indisponibilité E2B -> fallback honnête
            self._fallback_reason = f"e2b_unavailable:{type(exc).__name__}:{exc}"
            return None

    # --------------------------------------------------------------- local
    def _run_local(self, code: str, *, heavy: bool) -> SandboxResult:
        reason = getattr(self, "_fallback_reason", "e2b_not_configured")
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="omnibrain-sandbox-") as tmp:
            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONHASHSEED": "0",
                "HOME": tmp,
                "LANG": "C.UTF-8",
            }
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", code],
                    capture_output=True, text=True, timeout=self.timeout_s,
                    cwd=tmp, env=env, preexec_fn=_limits if os.name == "posix" else None,
                )
                return SandboxResult(
                    backend="local", stdout=proc.stdout, stderr=proc.stderr,
                    exit_code=proc.returncode,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    fallback_reason=reason, heavy=heavy,
                )
            except subprocess.TimeoutExpired:
                return SandboxResult(
                    backend="local", exit_code=124, duration_ms=(time.perf_counter() - started) * 1000,
                    error=f"timeout local après {self.timeout_s}s", fallback_reason=reason, heavy=heavy,
                )
            except OSError as exc:
                return SandboxResult(
                    backend="local", exit_code=2, duration_ms=(time.perf_counter() - started) * 1000,
                    error=str(exc), fallback_reason=reason, heavy=heavy,
                )
