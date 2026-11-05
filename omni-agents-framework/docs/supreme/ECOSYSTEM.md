# Écosystème OMNIBRAIN — organisation, PR et infrastructure hybride

**Date : 2026-11-05** · Inspection réelle via `gh repo list` / `gh pr view`.

## 1. Dépôts inspectés (46)
- **1 dépôt propre** : `omni-agents-framework` (branche `main`, non fork). Le code SUPREME vit
  dans `omni-agents-framework/` **vendorisé dans `skills-collection`** (dépôt de travail de la
  session). Promotion vers le dépôt autonome `omni-agents-framework` : **bloquée 403** (jeton
  GitHub App sans droit d'écriture réel malgré `push=true` dans l'API) — documenté, non contourné.
- **45 forks** : `skills-collection` (MIT, dépôt de travail), `Open-Agents`, `agency-agents`,
  `agentskills`, `antigravity-skills`, `mem0`, `cognee`, `OmniRoute`, `9router`, etc.
  Ce sont des bibliothèques de référence / skills, pas des déploiements actifs.
- Aucun dépôt supprimé, aucune branche ni historique altérés.

## 2. PR ouvertes — analyse de compatibilité (Phase 12)
| PR | Projet | Emplacement | Pile | Agents | Statut |
| --- | --- | --- | --- | --- | --- |
| **#5** (cette branche) | **OMNIBRAIN SUPREME 1000** | `omni-agents-framework/supreme/` | stdlib + SQLite | 1000 + 20 chefs | OPEN, 6/6 CI verte |
| **#2** | OMNI-RESEARCH 100 | `omni-research-100/` | FastAPI + Docker | 100, OmniBrain v1 | OPEN |

### Constat
- **Aucun conflit de fichiers** : les deux projets vivent dans des répertoires distincts
  (`omni-agents-framework/supreme/` vs `omni-research-100/`). Ils peuvent coexister techniquement.
- **Duplication conceptuelle** : deux implémentations d'« OmniBrain » (registre, routeur, API,
  agents). Risque de versions concurrentes divergentes à long terme.

### Recommandation (sans fusion automatique)
1. **SUPREME (#5) = plateforme canonique** 1000 agents, la plus complète et testée (294 tests).
2. **OMNI-RESEARCH 100 (#2) = sous-projet de recherche distinct** 100 agents. Deux options :
   - le garder comme projet séparé clairement délimité (préfixe `omni-research-100/`), ou
   - converger ses idées utiles (ex. moteur Internet, UI FastAPI) vers SUPREME via des PR dédiées.
3. **Ne pas fusionner #2 dans #5** sans décision humaine : ce sont deux visions. Aucune fusion
   automatique n'est effectuée. L'utilisateur arbitre.
4. Éviter toute nouvelle version concurrente : tout nouveau développement multi-agents passe
   par SUPREME (`omni-agents-framework/supreme/`) sauf décision contraire.

## 3. Infrastructure hybride (Phase 9) — état honnête
| Couche | État réel |
| --- | --- |
| GitHub (code + collaboration + CI) | **Opérationnel** : branche dédiée, PR #5, CI 3.11/3.12/3.13 verte |
| Exécution locale | **Opérationnelle** : SQLite WAL, pool de workers, file de missions, outils déterministes |
| API centrale | **Opérationnelle en local** : `http.server` stdlib, bind 0.0.0.0, jeton 0600 |
| Stockage persistant | **Opérationnel** : SQLite + sauvegardes (`backup.py`, intégrité vérifiée) |
| Monitoring | **Opérationnel** : 15 KPIs réels, journal d'accès expurgé, alertes |
| **Cloud** | **NON déployé** : aucune infrastructure cloud créée. Architecture extensible prête (workers séparables, API stateless hors SQLite, file de tâches). Déploiement = **autorisation humaine requise** (dépense/exposition publique). |

### Principe de montée en charge (conçu, non déployé)
- L'orchestrateur utilise un **pool de workers borné** (pas 1000 processus). Les agents sont des
  profils activés à la demande, pas des processus permanents.
- Pour passer à l'échelle : extraire les workers dans des processus/conteneurs séparés consommant
  la même file de missions SQLite (ou migrer vers une file distribuée), garder l'API comme point
  d'entrée, répliquer le stockage. **Rien de tout cela n'est déployé ni prétendu déployé.**
- Priorité au gratuit : local d'abord ; cloud seulement si nécessaire et autorisé.

## 4. Ce qui nécessite une autorisation humaine
- Fusion de #5 ou #2 dans `master`.
- Connexion d'un fournisseur IA payant / toute dépense.
- Déploiement cloud / exposition publique de l'API.
- Promotion vers le dépôt autonome `omni-agents-framework` (bloqué 403, nécessite un jeton avec
  droits d'écriture réels ou une action manuelle de l'utilisateur).
- Toute suppression de dépôt/branche/historique.
