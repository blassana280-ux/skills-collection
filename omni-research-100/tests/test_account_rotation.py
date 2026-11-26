"""Rotation des mots de passe locaux : la configuration doit faire foi.

Défaut observé lors de la reprise du preview : les comptes étaient semés une
seule fois dans la base persistante ; modifier OMNI_ADMIN_PASSWORD puis
redémarrer laissait l'ancien hash actif et rendait la connexion impossible.
"""
from __future__ import annotations

import pytest

from app.core.db import Store, UserRow
from app.core.security import verify_password


def _url(tmp_path, name="rotation.db"):
    return f"sqlite:///{tmp_path}/{name}"


@pytest.mark.unit
def test_password_rotation_takes_effect_on_restart(tmp_path):
    url = _url(tmp_path)
    first = Store(url, admin_password="ancien-mot-de-passe",
                  user_password="ancien-utilisateur")
    first.init()
    with first.session() as session:
        session.add(UserRow(username="tiers", password_hash="hash-externe",
                            role="viewer"))
    original_created_at = first.get(UserRow, "admin").created_at

    second = Store(url, admin_password="nouveau-mot-de-passe",
                   user_password="nouvel-utilisateur")
    second.init()

    admin = second.get(UserRow, "admin")
    researcher = second.get(UserRow, "researcher")
    assert verify_password("nouveau-mot-de-passe", admin.password_hash)
    assert not verify_password("ancien-mot-de-passe", admin.password_hash)
    assert verify_password("nouvel-utilisateur", researcher.password_hash)
    assert admin.role == "admin" and researcher.role == "researcher"
    # Pas de suppression de données : compte existant et tiers conservés.
    assert admin.created_at == original_created_at
    assert second.get(UserRow, "tiers").role == "viewer"
    first.close()
    second.close()


@pytest.mark.unit
def test_init_is_idempotent_when_the_password_is_unchanged(tmp_path):
    url = _url(tmp_path, "idem.db")
    first = Store(url, admin_password="stable", user_password="stable-user")
    first.init()
    original = first.get(UserRow, "admin").password_hash
    second = Store(url, admin_password="stable", user_password="stable-user")
    second.init()
    assert second.get(UserRow, "admin").password_hash == original
    first.close()
    second.close()
