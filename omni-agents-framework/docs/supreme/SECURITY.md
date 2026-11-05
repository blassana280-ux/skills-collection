# Guide de sécurité OMNIBRAIN SUPREME

## Principes appliqués (testés)
- **Moindre privilège** : chaque profil a `network=deny`, `github_write=false`, `secrets=none`,
  `spawn_agents=false`. Vérifié par `validate_catalog` et le test `permissions` de chaque profil.
- **Anti-usurpation** : le bus refuse `sender != authenticated_as` (sauf cerveau central). Testé.
- **ACL bus** : un spécialiste ne peut écrire qu'à sa division, ses chefs ou le cerveau. Testé.
- **ACL mémoire** : lecture/écriture par niveau et propriétaire ; isolement individuel. Testé.
- **Rédaction des secrets** : réutilise `omni.memory.store.redact` (V4) avant toute persistance
  (mémoire, bus, événements). Testé : aucun secret en clair dans les événements.
- **Anti-injection de prompt** : `security.scan_injection` + `wrap_untrusted`. Tout contenu externe
  est marqué « DONNÉE NON FIABLE » et jamais traité comme instruction. Testé.
- **Gouvernance par risque** : `policy.py` classe chaque action (low/medium/high/critical).
  Les actions protégées (`change_policy`, `merge_pr`, `deploy`, `delete_data`, `spend`, `write_main`,
  `write_secret`) sont refusées aux machines ; approbation humaine obligatoire. Testé.
- **RBAC V4 réutilisé** : `omni.sandbox.runtime.RBAC`, actions irréversibles réservées à l'humain.
- **Auto-modification interdite** : le Learning Engine refuse toute stratégie ciblant le noyau
  ou les politiques. Testé.
- **Outils sans code arbitraire** : les 41 outils sont des fonctions pures déterministes ; aucun
  n'exécute de code non fiable. Le sandbox V4 (`python -I`) reste disponible pour les futurs
  besoins d'exécution isolée.

## API
- Authentification par jeton (`X-API-Token` / Bearer). Écritures = jeton admin requis.
- Lecture anonyme possible uniquement si `SUPREME_ALLOW_ANON_READ=1` (opt-in explicite, preview).
- Jeton généré aléatoirement (`secrets.token_urlsafe`), stocké `var/api_token.txt` (chmod 600),
  jamais commité (var/ ignoré).
- Validation des entrées de mission (`validate_mission_input`).

## Ce qui n'est PAS fait (honnête)
- Pas de fournisseur IA connecté : aucune clé dans l'environnement, réseau sortant du sandbox
  limité. Le routeur rapporte `not_configured` ; aucune connexion simulée.
- Pas de déploiement production, pas de modification de permissions/secrets GitHub (403 documenté).
- L'exécution de code non fiable via sandbox n'est pas encore câblée dans l'orchestrateur
  (aucun outil actuel ne le requiert) ; brique V4 prête.

## Risques restants
- Un fournisseur IA configuré plus tard devra être testé (auth, quotas, coût) avant usage.
- La recherche sémantique par embeddings n'est pas active (pas de fournisseur) ; FTS5 lexical réel.
- Le conseil multi-modèles nécessite des appels API réels pour produire ses analyses.
