# Alignement inter-dépôts — SUPREME ↔ MISTRAL/Vide ↔ OmniRouteLite

**Date : 2026-11-06** · **Version SUPREME : 1.4.0**
Document de continuité destiné à **tous les agents** (Arena, Mistral/Vide, autre)
qui travaillent sur cet écosystème. À relire avant tout audit.

> Objet : éviter qu'une session conclue à tort qu'un composant « n'existe pas »,
> et éviter deux implémentations divergentes du même besoin.

---

## 1. Correction factuelle importante

Le document `mistral/MISTRAL_SUPREME_CONNECT.md` du dépôt
`blassana280-ux/omni-agents-framework`, branche `feature/mistral-connect-securise`
(commit `26f6b4d`, 2026-11-05T22:30:52Z), affirme :

> « **OmniBrain SUPREME 1.3.0 : INTROUVABLE.** Recherche code `SUPREME` /
> `MISTRAL_API_KEY_FILE` / `"providers --connect"` sur le compte : 0 résultat […]
> Aucune branche, PR ou fichier ne porte ce nom. »

**Cette conclusion est inexacte.** SUPREME existe, il est réel, testé et livré.
L'agent auteur avait lui-même signalé la réserve « forks non indexés » : c'est
exactement la cause de l'échec de recherche.

### Pourquoi la recherche GitHub n'a rien retourné — trois causes cumulées

| Cause | Vérification |
| --- | --- |
| SUPREME vit dans **`skills-collection`, qui est un fork** | `gh repo view … --json isFork` → `true`. La recherche de code GitHub **n'indexe pas les forks**. |
| Il n'est **pas sur la branche par défaut** | `git ls-tree -d origin/master omni-agents-framework/supreme` → **0** (absent de `master`) |
| La PR n'est **pas fusionnée** | PR #5 de `skills-collection` → **OPEN** |

### Où SUPREME se trouve réellement

- Dépôt : **`blassana280-ux/skills-collection`** (fork)
- Chemin : **`omni-agents-framework/supreme/`** — **37 entrées** versionnées
- Branche : **`arena/ffc77bf1-skills-collection`**
- PR : **[#5](https://github.com/blassana280-ux/skills-collection/pull/5)**, **OPEN**, non fusionnée
- Version : **1.4.0** (1.3.0 livrée auparavant, PV conservé dans `EXECUTION-REPORT.md`)
- Schéma SQLite **v4**, **451 tests**, CI **6/6** sur Python 3.11/3.12/3.13
- Dernier commit vérifié : `77d5b37` (kit d'enrôlement), CI verte

### Attention : deux « PR #5 » distinctes

| Dépôt | PR #5 | État | Contenu |
| --- | --- | --- | --- |
| `skills-collection` | [#5](https://github.com/blassana280-ux/skills-collection/pull/5) | **OPEN** | **OMNIBRAIN SUPREME 1.4.0** |
| `omni-agents-framework` | [#5](https://github.com/blassana280-ux/omni-agents-framework/pull/5) | **MERGED** le 2026-11-04T20:02:16Z | miroir de configuration MISTRAL EVOLUTION MAX v0.1.0 |

Le document de continuité Mistral a examiné la **seconde** et en a déduit que la
première n'existait pas. **Toujours qualifier une PR par son dépôt.**

---

## 2. Deux implémentations parallèles du même besoin

Le besoin « enregistrer une clé fournisseur sans jamais l'exposer » a été traité
des deux côtés, pour **deux piles différentes**. Ce n'est pas un doublon à
supprimer : ce sont deux systèmes distincts.

| Aspect | SUPREME (ce dépôt) | OmniRouteLite (`omni-agents-framework`) |
| --- | --- | --- |
| Pile | Python 3.11+, stdlib, SQLite | Node.js zéro dépendance |
| Branche | `arena/ffc77bf1-skills-collection` | `feature/mistral-connect-securise` |
| Commande | `python3 -m supreme providers --connect mistral` | `node cli.js providers --connect mistral` |
| Vérification | `providers --verify mistral` (GET `/v1/models`) | `cli.js providers --verify mistral` (GET `/v1/models`) |
| Stockage | `var/supreme/secrets/mistral.key` `0600`/`0700` | `OmniRouteLite/secrets/mistral.key` `0600`/`0700` |
| Résolution | `MISTRAL_API_KEY` → `MISTRAL_API_KEY_FILE` → fichier privé → hérité | `apiKeyEnv` → `apiKeyFile` → `apiKey` en clair (hérité) |
| Saisie | **`getpass`, deux fois, TTY obligatoire** | **stdin** (méthode A), `--key-file` (C), env (B) |
| Garde-fou réseau | test de joignabilité **avant** saisie, arrêt si bloqué | non documenté |
| Budget | `ops/budget-plan.py`, aucun prix par défaut | tarifs à re-vérifier sur la doc officielle |
| Guide Android | `docs/supreme/MISTRAL-ENROLLMENT.md` | `OmniRouteLite/SECURITY-KEYS.md` |

**Convergence de fond** : même ordre de résolution, mêmes permissions `0600`/`0700`,
même vérification gratuite par GET `/v1/models`, même refus d'afficher la clé,
mêmes règles « aucune inférence payante sans accord ». Les deux approches sont cohérentes.

### Différence de sécurité à connaître (factuelle, sans jugement)

- SUPREME **refuse** toute saisie hors terminal privé (`isatty`) et demande la clé
  deux fois sans écho. Une clé ne peut donc pas arriver par un pipe, un argument
  ou une redirection.
- OmniRouteLite accepte **stdin**, et sa documentation présente aussi
  `MISTRAL_API_KEY=<clé> node cli.js …` en méthode B, en signalant elle-même que
  l'historique Termux conserve alors la clé. La méthode C (`--key-file`) laisse
  une copie sur `/sdcard` jusqu'à suppression.
- Recommandation pour un durcissement ultérieur d'OmniRouteLite : lecture masquée
  sans écho plutôt que stdin brut, et retrait de la méthode B de la documentation.
  **Aucune modification n'a été faite dans ce dépôt** : ce n'est pas mon périmètre
  et cela requiert l'accord du propriétaire.

---

## 3. État réel de la connexion Mistral — identique des deux côtés

| Élément | SUPREME (vérifié ici) | OmniRouteLite (d'après son propre document) |
| --- | --- | --- |
| Clé enregistrée | **non** (`configured: false`) | **à faire** (Phase 3) |
| `--verify` réussi | **non** (`not_configured`, exit 1) | **à faire** |
| Modèles découverts | **0** | non listés |
| Tarifs attestés | **0**, aucun tarif inventé | « à re-vérifier sur docs.mistral.ai » |
| Inférence payante | **0** | aucune sans accord |
| Dépense | **0,00 USD** | non engagée |

Les deux documents convergent donc sur le fond : **personne n'a encore connecté
réellement Mistral**, et cela ne peut pas se faire depuis un sandbox sans accès
réseau. Raison mesurée côté Arena : `api.mistral.ai` est **injoignable** (TLS fermée
avant HTTP), alors que `api.github.com` répond `200` — voir
`MISTRAL-ENROLLMENT.md` §0 et `validation/egress-control-test.json`.

Côté Vide, la raison invoquée est l'absence d'accès réseau brut et au système de
fichiers de l'appareil. **Deux sandboxes différents, même conclusion : l'enrôlement
doit se faire sur l'appareil de l'opérateur.**

---

## 4. Règles de coordination proposées (à valider par le propriétaire)

1. **Qualifier toujours dépôt + branche + PR.** « PR #5 » seul est ambigu.
2. **Ne pas conclure « introuvable » sur la seule recherche de code GitHub** :
   elle n'indexe ni les forks ni les branches non par défaut. Vérifier par
   `git ls-tree`, `gh api …/branches`, `gh pr list` sur le dépôt précis.
3. **Ne pas réécrire le travail de l'autre pile.** SUPREME (Python) et OmniRouteLite
   (Node) restent distincts ; une convergence fonctionnelle se décide humainement.
4. **Un seul point de vérité par composant** : SUPREME → ce dépôt, branche Arena,
   PR #5 ; OmniRouteLite → `omni-agents-framework`.
5. **Aucune fusion sans accord explicite**, dans l'un ou l'autre dépôt.
6. **Continuité** : toute session qui audite l'écosystème relit ce fichier,
   `docs/supreme/CONTINUITY.md` et `mistral/MISTRAL_SUPREME_CONNECT.md`, puis
   vérifie l'état réel avant de conclure.

---

## 5. Vérifications effectuées pour ce document (lecture seule)

Aucune écriture dans `omni-agents-framework`. Aucune fusion. Aucune branche créée
là-bas. Constats issus de :

```bash
gh repo view blassana280-ux/skills-collection --json isFork,defaultBranchRef
git ls-tree -d origin/master omni-agents-framework/supreme      # → absent
git ls-tree -d HEAD omni-agents-framework/supreme               # → présent
gh pr view 5 --repo blassana280-ux/skills-collection            # → OPEN
gh pr view 5 --repo blassana280-ux/omni-agents-framework        # → MERGED 2026-11-04
gh api repos/blassana280-ux/omni-agents-framework/branches
gh api repos/.../commits/26f6b4d                                # branche Mistral
gh api repos/.../contents/mistral/MISTRAL_SUPREME_CONNECT.md?ref=feature/mistral-connect-securise
gh api repos/.../contents/OmniRouteLite/SECURITY-KEYS.md?ref=feature/mistral-connect-securise
```

Accès refusés, documentés et non contournés : liste des **secrets** et des
**variables** GitHub Actions → **403 Resource not accessible by integration**.
Impossible de dire si un secret `MISTRAL_API_KEY` a été ajouté côté Actions ;
**aucune supposition n'est faite là-dessus**.
