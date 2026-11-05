# Suivi durable OMNIBRAIN SUPREME 1000

**Dernière mise à jour : 2026-11-05** · Branche : `arena/ffc77bf1-skills-collection` (base `4500e93`, `master`).
Ce document permet à un autre agent IA de reprendre le travail sans perdre le contexte.

## État actuel
- Couche SUPREME 1.0.0 livrée dans `omni-agents-framework/supreme/`.
- **1000 spécialistes + 20 chefs** générés, validés ; **60 opérationnels/surveillés** sur preuve réelle.
- **244 tests verts** (105 V4 + 139 SUPREME). CI dédiée ajoutée.
- API + tableau de bord mobile fonctionnels sur données réelles.
- 0 fournisseur IA configuré (honnête) ; routeur/conseil implémentés mais indisponibles sans clés.
- **Sécurité (1.0.2)** : jeton API régénéré (rotation), stocké uniquement dans
  `var/supreme/api_token.txt` (`0600`, gitignoré, jamais commité, jamais affiché). Journal d'accès
  expurgé `var/supreme/access.log`. Rotation : `python3 -m supreme rotate-token` puis redémarrer
  `serve`. Le secret n'est communiqué à personne et n'apparaît dans aucun rapport. Voir `SECURITY.md`.

## Architecture retenue
Voir `ARCHITECTURE.md`. Python stdlib + SQLite, couche au-dessus de V4, 30 composants implémentés.
Source de vérité des profils : `supreme/divisions/divNN.py` → `supreme/catalog/agents.json`.

## Décisions prises
1. Réutiliser V4 (mémoire, RBAC, sandbox, télémétrie) plutôt que réécrire.
2. Stdlib uniquement, SQLite unique, démarrage gratuit sans service externe.
3. 1000 profils = données versionnées, pas 1000 processus ; pool de workers à la demande.
4. Activation sur preuve réelle ; missions LLM différées sans fournisseur (jamais comptées réussies).
5. Aucun fournisseur supposé connecté ; détection réelle, aucune connexion simulée.
6. Travail sur la branche Arena de session ; promotion vers le dépôt autonome bloquée (403).
7. Outils déterministes réels (42) pour l'exécution hors ligne ; skills documentaires séparés.

## Phases
- **Terminées** : 1 audit, 2 conception, 3 fondations, 4 mémoire, 5 routeur/conseil (implémenté),
  6 runtime, 7 divisions, 8 catalogue 1000, 9 activation/tests, 10 apprentissage, 11 interface,
  12 validation globale (tests + rapport).
- **En attente d'autorisation / clés** : connexion réelle des fournisseurs IA (action humaine),
  production d'analyses du conseil via appels API, déploiement cloud, promotion vers dépôt autonome.
- **Restantes (évolution)** : recherche sémantique par embeddings, exécution de code non fiable
  câblée au sandbox dans l'orchestrateur, convergence avec PR #2 `omni-research-100` (décision Lassana).

## Branches / PR
- Travail : `arena/ffc77bf1-skills-collection` (nom fixe de session).
- PR : ouverte vers `master` (voir rapport). Aucune fusion automatique.
- PR #2 `omni-research-100` : projet parallèle non fusionné, non touché.

## Tests
`cd omni-agents-framework && python3 -m unittest discover -s tests` → 244 verts.
CI : `.github/workflows/omnibrain-supreme.yml`.

## Problèmes / permissions manquantes
- Push `omni-agents-framework` autonome : **403** (jeton GitHub App). Lecture seule.
- `optimiser-mes-agents-IA` : 403 lecture. Création de dépôt : 403.
- Aucune clé fournisseur IA dans l'environnement ; réseau sortant sandbox limité.

## Prochaines tâches
1. Fournir des clés IA (humain) → `POST /api/providers/check` → activer les 960 agents LLM.
2. Câbler les appels API réels du conseil multi-modèles.
3. Décider la convergence avec `omni-research-100` (PR #2).
4. Promouvoir vers le dépôt autonome quand le token le permettra (humain).
5. Étendre les outils exécutables pour activer davantage d'agents hors ligne.

## Commandes de reprise
```bash
cd omni-agents-framework
python3 -m supreme catalog --check
python3 -m supreme sync && python3 -m supreme evaluate --activate
python3 -m supreme status
python3 -m supreme serve --port 8765
python3 -m unittest discover -s tests
```
