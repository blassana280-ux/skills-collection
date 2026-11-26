"""Connexion de secrets sans les mettre dans le chat, Git, argv ou les journaux.

Ordre de résolution : variable d'environnement, fichier désigné par *_FILE,
fichier privé runtime 0600, ancien providers.json 0600 (compatibilité 1.2.1).
La saisie interactive utilise getpass (sans écho) et exige un vrai terminal.
Aucune fonction de ce module ne renvoie la clé dans un statut ou une exception.
"""
from __future__ import annotations

import getpass
import json
import os
import stat
import tempfile
from pathlib import Path

from .config import VAR_DIR, ensure_dirs

ENV_VARS = {
    "mistral": "MISTRAL_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY", "openai_compat": "SUPREME_OPENAI_COMPAT_API_KEY",
}
MAX_SECRET_BYTES = 16384


class CredentialError(ValueError):
    """Erreur de stockage lisible, sans contenu secret."""


def private_dir() -> Path:
    ensure_dirs()
    p = VAR_DIR / "secrets"
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    if p.is_symlink() or not p.is_dir():
        raise CredentialError("répertoire de secrets invalide")
    if p.stat().st_uid != os.getuid():
        raise CredentialError("répertoire de secrets non détenu par l'utilisateur courant")
    os.chmod(p, 0o700)
    return p


def secret_path(provider: str) -> Path:
    if provider not in ENV_VARS:
        raise CredentialError("fournisseur inconnu")
    return private_dir() / f"{provider}.key"


def _read_private_text(path: Path) -> str:
    try:
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise CredentialError("le fichier de secret doit être régulier, sans lien symbolique")
        if st.st_uid != os.getuid():
            raise CredentialError("fichier de secret non détenu par l'utilisateur courant")
        if st.st_mode & 0o077:
            raise CredentialError("permissions trop larges : chmod 600 requis")
        if st.st_size > MAX_SECRET_BYTES:
            raise CredentialError("fichier de secret trop volumineux")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CredentialError("fichier de secret illisible") from exc


def _read_file(path: Path) -> str:
    value = _read_private_text(path).strip()
    if not value or any(ord(c) < 33 or ord(c) == 127 for c in value):
        raise CredentialError("secret vide ou contenant des espaces/caractères de contrôle")
    return value


def _legacy_file() -> dict:
    p = VAR_DIR / "providers.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(_read_private_text(p))
        return {k: v for k, v in data.items() if isinstance(v, str) and v} if isinstance(data, dict) else {}
    except (CredentialError, json.JSONDecodeError):
        return {}


def resolve(provider: str, env_var: str | None = None) -> tuple[str, dict]:
    """Renvoie (secret, métadonnées sûres). Le secret reste strictement interne."""
    env_var = env_var or ENV_VARS.get(provider, "")
    meta = {"provider": provider, "configured": False, "source": None, "error": None}
    if env_var and os.environ.get(env_var, "").strip():
        value = os.environ[env_var].strip()
        if any(ord(c) < 33 or ord(c) == 127 for c in value):
            meta["error"] = "variable d'environnement invalide"
            return "", meta
        meta.update(configured=True, source="environment")
        return value, meta
    file_env = os.environ.get(env_var + "_FILE", "") if env_var else ""
    candidates = []
    if file_env:
        candidates.append(("environment_file", Path(file_env)))
    if provider in ENV_VARS:
        candidates.append(("private_file", VAR_DIR / "secrets" / f"{provider}.key"))
    for source, path in candidates:
        if path.exists() or path.is_symlink():
            try:
                value = _read_file(path)
                meta.update(configured=True, source=source)
                return value, meta
            except CredentialError as exc:
                meta["error"] = str(exc)
                return "", meta
    legacy = _legacy_file()
    value = legacy.get(provider) or legacy.get(env_var, "")
    if value:
        try:
            if any(ord(c) < 33 or ord(c) == 127 for c in value):
                raise CredentialError("secret hérité invalide")
            meta.update(configured=True, source="legacy_private_file")
            return value, meta
        except CredentialError as exc:
            meta["error"] = str(exc)
    return "", meta


def status(provider: str, env_var: str | None = None) -> dict:
    _, meta = resolve(provider, env_var)
    return meta


def store_interactive(provider: str, replace: bool = False, *, input_stream=None,
                      output_stream=None) -> dict:
    """Saisie locale sans écho ; aucun argument CLI contenant la clé n'est accepté."""
    import sys
    inp = input_stream or sys.stdin
    out = output_stream or sys.stderr
    if not hasattr(inp, "isatty") or not inp.isatty():
        raise CredentialError("saisie interactive refusée sans terminal privé (pas de pipe, chat ou journal)")
    path = secret_path(provider)
    if path.exists() and not replace:
        raise CredentialError("secret déjà présent ; utiliser --replace uniquement dans un terminal privé")
    first = getpass.getpass(f"Clé {provider} (saisie masquée, jamais affichée) : ", stream=out)
    second = getpass.getpass("Confirmer la clé : ", stream=out)
    if not first or first != second:
        raise CredentialError("saisie vide ou différentes saisies")
    if len(first) > MAX_SECRET_BYTES or any(ord(c) < 33 or ord(c) == 127 for c in first):
        raise CredentialError("format de secret invalide")
    directory = private_dir()
    fd, tmp = tempfile.mkstemp(prefix=f".{provider}-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(first)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        first = second = ""
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {"provider": provider, "stored": True, "permissions": "0600",
            "directory_permissions": "0700", "source": "private_file",
            "note": "Aucune clé n'a été affichée. Redémarrer le service pour recharger la configuration."}


def revoke_file(provider: str) -> dict:
    """Supprime uniquement le fichier privé local, après action humaine explicite.

    Ne révoque pas la clé chez le fournisseur et ne touche pas aux variables
    d'environnement ni aux fichiers externes désignés par *_FILE.
    """
    path = secret_path(provider)
    existed = path.is_file()
    if existed:
        path.unlink()
    return {"provider": provider, "local_file_removed": existed,
            "provider_side_revocation_required": True,
            "note": "Révoquer aussi la clé dans la console du fournisseur ; env/*_FILE restent inchangés."}
