# Intégration OmniBrain — contrat réel, adaptateur v1

## 1. Ce qui a été réellement inspecté (lecture seule)

Le contrat n'a pas été imaginé : il a été lu via l'API GitHub dans le dépôt
public `blassana280-ux/omni-agents-framework` (aucun dépôt OmniBrain modifié) :

| Fichier | Apport |
|---|---|
| `OMNIBRAIN.md` | Source de vérité déclarée du contrat |
| `AGENTS.md` | Règles : jamais écrire `main`, pas de fausse intégration, `READY` impossible sans provider réel, stdlib + `unittest`, `python3 -m omni registry` |
| `registry/permissions.json` | `allowed_tools`, `max_parallel=1`, `allow_dangerous=false`, actions irréversibles interdites, `path_rules` (`.git/`, `.env`) |
| `omni/models.py`, `omni/messaging.py` | Dataclasses `Agent/Skill/Task/Brief/Assignment/Classification/Plan`, bus JSONL |
| `cyber-force-100/docs/OMNIBRAIN-INTEGRATION.md` | Phases (lecture/export → dispatch), sur-ensemble d'actions dangereuses, format d'export `registry/agents.json` |
| `cyber-force-100/cf100/bridges/omnibrain.py` | `OmniBrainBridge.export()` (`id,title,specialties,skills,provenance,boundaries,brief_template`), résultat `{agent, ok, result, evidence_hash}` |
| `cyber-force-100/cf100/bridges/omni_queue.py` | File réelle : `omni-inbox.jsonl`, `cf100-outbox.jsonl`, `omni-done.jsonl`, réponses `{in_response_to, agent, ok, result}` |
| `omni-agents-framework:docs/INTEGRATIONS.md` | Statuts `exécuté` / `source de compétence` / `non intégré` |
| `blassana280-ux/skills-collection:AGENTS.md` | Règle de routage du compte |

Le dépôt historique `optimiser-mes-agents-IA` a renvoyé **403** (`Resource not
accessible by integration`) ; `OMNIBRAIN.md` précise qu'il ne doit pas être
cité comme existant. Il n'a donc pas été utilisé.

## 2. Règles du contrat reprises dans la plateforme

- Classification `simple | medium | complex` → `FAST | DEEP | MAXIMUM`.
- Algorithme en 10 étapes `CLASSER → SÉLECTIONNER → PLANIFIER → DISPATCHER →
  SURVEILLER → CORRIGER → ARBITRER → VALIDER → ASSEMBLER → TRACER`.
- Échec : `retry → fallback → escalate`.
- Arbitrage : `nombre de preuves > exécution réelle > critères satisfaits >
  id de tâche` ; égalité parfaite ⇒ `resolved=false`
  (`app/brain/conflict_resolver.py`).
- Six gates `completeness, evidence, execution, arbitration, secrets, trace`
  (+ `real_provider`, exigée par `AGENTS.md`) ⇒ `READY` seulement si **toutes**
  passent, sinon `NEEDS_WORK`.
- Actions dangereuses `merge_pr, force_push, delete_repo, delete_branch,
  rotate_secret, write_main` (+ sur-ensemble CF100 `delete_data,
  change_permissions, disable_protection, purge_evidence, deploy_production`)
  : **aucune n'est exposée à l'agent** ; `dangerous_action_alignment()` le
  vérifie (`aligned: true`).
- `max_parallel` : la plateforme expose sa limite **mesurée** et les agents mis
  en file, sans prétendre à une simultanéité non supportée.

## 3. Adaptateur versionné (`app/api/omnibrain.py`)

`CONTRACT_VERSION = "1.0"`, préfixe `/api/omnibrain/v1`, authentification par
clé `X-OmniBrain-Key`, garde `X-OmniBrain-Contract` (toute autre version ⇒ 422).
Sens **unique** : depuis le nouveau dépôt vers OmniBrain, sans modifier les
dépôts existants. Aucun callback/URL fournie par l'appelant n'est contacté
(pas de SSRF).

| Méthode | Chemin | Fonction |
|---|---|---|
| GET | `/contract` | Version, sources du contrat, gates, actions refusées, format de file |
| GET | `/modes` | `simple/medium/complex → fast/deep/maximum` + ressources réelles |
| POST | `/missions` | Soumettre une mission (`skill`, `request`, `task`, `mode`, `context`) |
| GET | `/missions/{id}` | Suivi : état, étape, progression, agents actifs |
| DELETE | `/missions/{id}` | Annulation |
| GET | `/missions/{id}/results` | Résultats structurés, agents, union (+) des contradictions |
| GET | `/missions/{id}/report` | Rapport markdown/JSON + verdict |
| GET | `/missions/{id}/evidence` | Preuves, citations, empreintes SHA-256 |
| GET | `/queue/status` | État des 3 fichiers JSONL |
| POST | `/queue/process` | Consomme `omni-inbox.jsonl`, écrit `cf100-outbox.jsonl`, accuse dans `omni-done.jsonl` |

Les réponses contiennent `contract_version`, `evidence_hash` (SHA-256 des
preuves), `skills`, et l'alignement des permissions. Le rôle `omnibrain` n'a
**pas** les droits admin (test dédié).

## 4. Compatibilité de la file JSONL

`OmniQueueAdapter` utilise exactement les noms et formats lus dans
`omni_queue.py` :

- `omni-inbox.jsonl` : `{id, skill, request, task}` (+ `mode`, `context`
  tolérés) ;
- `cf100-outbox.jsonl` : `{in_response_to, agent, ok, result}` ;
- `omni-done.jsonl` : accusés de réception en append-only.

`POST /queue/process` mappe `skill/request/task` vers une mission OR100, lance
le pipeline, attend le résultat et écrit la réponse avec le `evidence_hash`.
Les messages déjà accusés ne sont jamais rejoués.

## 5. Export des agents au format OmniBrain

`GET /api/agents/export/omnibrain` produit des entrées `or100-*` avec `id`,
`title`, `specialties`, `skills`, `provenance`, `boundaries`,
`brief_template` — même forme que `OmniBrainBridge.export()`.
`dangerous_action_alignment()` garantit l'absence de `write_main`,
`merge_pr`, etc. dans les outils exportés (`allowed_tools` = `stats, memory,
verify, graph, search, extract, llm` uniquement).

## 6. Ce qui est vérifié, et ce qui ne l'est pas

**Vérifié** : contrat réel lu et transcrit ; 6 tests d'intégration
(`tests/test_omnibrain.py`) exécutés : rejet de mauvaise clé, conformité du
contrat aux sources inspectées, garde de version, cycle complet
`submit → mode → suivi → annulation → résultats → rapport → preuves`,
protocole JSONL (dépôt + traitement + réponse + accusé), absence de droits
admin. Export des 100 agents et alignement des actions dangereuses validés
par `tests/test_agent_registry.py`.

**Non vérifié** : exécution d'un orchestrateur OmniBrain **externe** contre
cette API (aucun de ses dépôts n'a été cloné ni modifié, conformément à la
consigne). L'intégration est donc classée
« **OPÉRATIONNELLE ET TESTÉE côté OR100, compatibilité validée par
conformité au contrat et tests ; interopérabilité inter-processus live
IMPLÉMENTÉE MAIS NON VÉRIFIÉE** ».
