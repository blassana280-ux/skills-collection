# Sauvegarde & restauration OMNIBRAIN SUPREME

## Sauvegarde
```bash
python3 -m supreme backup
# ou API : POST /api/backup {"label":"avant-migration"}
```
- API de backup SQLite (cohérente à chaud) vers `var/supreme/backups/<id>/supreme.db`.
- Copie du catalogue versionné (`catalog/`).
- Vérification `PRAGMA integrity_check` ; métadonnées `meta.json`.

## Restauration
```python
from supreme.backup import BackupManager
BackupManager().restore("<backup_id>")   # écrase la base courante
```
- Refuse une sauvegarde corrompue (`integrity_check != ok`).
- Sauvegarde de sécurité de l'état courant avant écrasement (`.pre-restore.db`).
- Cible optionnelle pour restaurer vers un fichier séparé (testé).

## Bonnes pratiques
- Sauvegarder avant toute migration ou modification de masse.
- Les sauvegardes contiennent des données runtime ; ne pas les commiter (`var/` ignoré).
- Tester la restauration périodiquement (test `test_supreme_backup`).

## Migration historique 1.2.1 (schéma v2 additif)
- Avant durcissement : sauvegarde `bk-20261105T163835-22f858`, intégrité `ok`.
- La migration ajoute colonnes/tables sans supprimer les données existantes.
- Test de non-régression : `omni-agents-framework/tests/test_supreme_hardening.py::TestSchemaMigration`.

## Migration 1.3.0 (schéma v3 additif)
- Arrêter les écrivains, sauvegarder, puis laisser `init_db` ajouter les 7 tables fournisseurs/activation.
- Aucune suppression de données ; les campagnes et preuves restent privées (`0600`).
- Auditer après migration : `python3 -m supreme audit` (`schema_version=3`).
- Toujours exécuter `python3 -m supreme backup` avant une migration ou restauration.
