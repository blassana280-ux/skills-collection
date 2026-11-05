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
