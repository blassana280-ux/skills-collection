# Guide de déploiement OMNIBRAIN SUPREME

## Démarrage gratuit (local / sandbox)
```bash
cd omni-agents-framework
python3 -m supreme catalog          # génère le catalogue 1000 agents
python3 -m supreme sync             # charge le registre SQLite
python3 -m supreme evaluate --activate   # valide + active sur preuve
python3 -m supreme serve --port 8765     # API + tableau de bord
```
Aucune dépendance externe, aucun compte, aucun abonnement. SQLite local (`var/supreme/`).

## Preview navigateur (Android compatible)
Le serveur bind `0.0.0.0`. Dashboard mobile-first sur `/`. Jeton admin affiché au démarrage
et stocké dans `var/supreme/api_token.txt`. Pour la lecture anonyme en preview :
`SUPREME_ALLOW_ANON_READ=1`. Les écritures exigent le jeton.

## GitHub
- Code, profils, compétences, configurations versionnés dans le dépôt.
- CI `.github/workflows/omnibrain-supreme.yml` : catalogue + tests sur Python 3.11/3.12/3.13.
- Pull Requests documentées ; **aucune fusion automatique** (décision humaine).
- Promotion vers `omni-agents-framework` autonome : **bloquée par 403** (jeton GitHub App),
  documentée dans `docs/PROMOTION-403.md`, jamais contournée.

## Cloud (évolution, sur autorisation)
L'architecture SQLite/stdlib peut évoluer vers un service managé (Postgres, file de messages,
workers) sans réécriture des interfaces. Aucun fournisseur cloud n'est déployé ni payé
actuellement. Toute dépense nécessite une approbation humaine explicite (niveau critique).

## Variables d'environnement
| Variable | Rôle |
| --- | --- |
| `SUPREME_VAR_DIR` | Répertoire des données runtime (défaut `var/supreme`) |
| `SUPREME_API_TOKEN` | Jeton admin API (sinon généré) |
| `SUPREME_ALLOW_ANON_READ` | `1` = lecture anonyme (preview) |
| `OPENAI_API_KEY` / `MISTRAL_API_KEY` / … | Fournisseurs IA (optionnels, non configurés) |
