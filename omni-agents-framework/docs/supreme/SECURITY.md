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
- Validation des entrées de mission (`validate_mission_input`).

## Gestion du jeton API (secret)
- **Génération** : `secrets.token_urlsafe(32)` (256 bits d'entropie).
- **Stockage sécurisé uniquement** : `var/supreme/api_token.txt`, permissions `0600`,
  répertoire `var/` gitignoré. Le fichier n'est **jamais** suivi par Git (vérifié : aucun
  commit dans l'historique, aucune correspondance dans les fichiers suivis).
- **Jamais affiché** : ni au démarrage du serveur, ni dans les rapports, ni dans les journaux.
  Le serveur n'imprime que le chemin du fichier. Aucune chaîne `print(... admin_token ...)`.
- **Pas en clair dans l'environnement par défaut** : `SUPREME_API_TOKEN` peut surcharger le
  fichier (usage avancé) ; s'il est défini, il prend le pas et doit être géré comme un secret.

### Rotation / révocation (procédure)
```bash
cd omni-agents-framework
python3 -m supreme rotate-token   # écrit un nouveau jeton 0600, n'affiche que des métadonnées
# puis redémarrer le serveur pour révoquer l'ancien jeton EN MÉMOIRE :
python3 -m supreme serve --port 8765
```
- `rotate_token()` renvoie uniquement des métadonnées non sensibles (chemin, longueur,
  empreinte SHA-256 tronquée) — **jamais le jeton en clair**.
- L'ancien jeton est révoqué sur disque dès la rotation, et en mémoire au redémarrage.
- Vérifier la révocation : une écriture avec l'ancien jeton doit renvoyer `401`.
- Tout jeton ayant fuité (affiché, journalisé, commité) doit être considéré comme compromis
  et révoqué immédiatement par rotation.

## Journal d'accès (auditable, expurgé)
- Chaque requête HTTP est journalisée dans `var/supreme/access.log` (`0600`, gitignoré) :
  horodatage UTC, IP client, méthode, chemin, code statut.
- **Aucun secret n'est jamais journalisé** : ni jeton, ni en-têtes, ni corps. Le paramètre
  d'URL `?token=…` est remplacé par `REDACTED`. Testé (`test_access_log_written_and_token_redacted`).
- La journalisation n'échoue jamais une requête (best-effort).

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
