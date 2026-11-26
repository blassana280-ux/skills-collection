# Politique de rétention et suppression

## Données conservées

15 tables SQL : `missions`, `tasks`, `sources`, `evidence`, `claims`,
`contradictions`, `reports`, `audit_logs`, `error_logs`, `metrics`,
`provider_usage`, `research_cache`, `events`, `settings`, `users`.

- Missions, sources, preuves et rapports : conservés **90 jours** par défaut
  (`OMNI_RETENTION_DAYS`, modifiable via `PATCH /api/settings`).
- Journaux d'audit et d'erreurs : conservés pour la traçabilité ; purgés
  uniquement sur demande explicite.
- `events` : journal rejouable, base du flux SSE et de la reprise après
  incident.
- `research_cache` : réutilisation par empreinte de requête + similarité
  vectorielle ; `reusable_researches` publié dans l'état mémoire.
- `provider_usage` : quotas glissants sur 24 h.

## Suppression

- **Aucune suppression automatique** au démarrage ou à l'exécution d'une
  mission.
- `POST /api/retention/purge` exige : rôle `admin`, `older_than_days > 0` et
  `confirm == "PURGE"`. Sans ces trois conditions : refus.
- `Store.purge(older_than_days, confirm="PURGE")` parcourt explicitement les
  tables concernées, journalise un événement d'audit `purged` et retourne le
  nombre de lignes supprimées par table.
- Les actions `purge_evidence`, `delete_data`, `delete_repo`,
  `delete_branch`, `disable_protection`, `force_push`, `merge_pr`,
  `rotate_secret`, `write_main` sont **refusées aux agents** et à l'adaptateur
  OmniBrain (`dangerous_action_alignment()`).
- Sauvegarde avant toute purge : `POST /api/backup` ou
  `deploy/backup_postgres.sh`.
- La restauration (`deploy/restore_postgres.sh`) demande une confirmation
  interactive et est documentée comme destructive.

## Secrets et données personnelles

Aucune donnée personnelle n'est collectée au-delà du nom d'utilisateur local.
Les mots de passe sont hachés PBKDF2. Les clés API restent dans `.env` et ne
sont jamais journalisées ni incluses dans les rapports (`redact()`,
`redact_report()`). Le contenu des sources est conservé tel quel mais
**marqué `untrusted`** avec ses drapeaux d'injection.
