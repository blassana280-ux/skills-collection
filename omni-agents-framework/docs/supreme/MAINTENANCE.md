# Guide de maintenance OMNIBRAIN SUPREME

## Ajouter / modifier un agent
1. Modifier la ligne dans `supreme/divisions/divNN.py` (ou utiliser l'Agent Factory pour un agent temporaire).
2. `python3 -m supreme catalog` (régénère le catalogue ; échoue si doublon/incomplet).
3. `python3 -m supreme sync` puis `python3 -m supreme evaluate --activate`.
4. Commit sur la branche dédiée + PR. La CI vérifie la régénération.

## Règles de qualité du catalogue
- 20 divisions × 50 spécialistes exactement ; 20 chefs.
- IDs, noms, objectifs, tâches représentatives uniques ; pas de clones.
- 27 champs obligatoires + 7 évaluations par profil.
- Permissions moindre privilège ; outils existants dans le Tool Registry.

## Mettre à jour un outil
Modifier `supreme/tools.py` (fonction + fixture + critère). Les tests `test_supreme_tools`
vérifient chaque fixture et la gestion des entrées vides. Régénérer le catalogue si les
allowlists de division changent.

## Surveillance continue
- `python3 -m supreme status` / `report` : état réel.
- KPIs via `/api/kpis` ; null = indisponible (ne pas inventer de valeur).
- Le Learning Engine analyse échecs récurrents et agents peu performants ; propose des
  stratégies versionnées, acceptées seulement sur gain mesuré, avec rollback.

## Versions
- Profils : `version` + `changelog` ; l'Agent Factory conserve les versions (`agent_versions`)
  et permet `rollback`.
- Catalogue : source de vérité `divisions/`, sortie `catalog/` régénérable et vérifiée en CI.
