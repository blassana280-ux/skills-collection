---
name: omnibrain-orchestration
description: "Orchestre une demande en escouade d'agents spécialisés : classification simple/moyenne/complexe, routage par matrice, briefs parallèles en une seule vague, contrats d'interface et gates qualité. Utiliser pour toute demande multi-compétences ou à risque (sécurité, finance OHADA, mise en production)."
---

# OmniBrain Orchestration — Skill

## Quand activer ce skill

- La demande couvre plusieurs domaines (ex. frontend + backend + données).
- La demande touche un domaine à risque : sécurité, DevOps/mise en production, finance OHADA.
- La demande est formulée comme un programme (`refonte`, `migration`, `audit complet`, `bout en bout`).
- Une contre-expertise indépendante est nécessaire avant livraison.

## Procédure

### 1. Classer

```bash
omnibrain classify "la demande"
```

- `simple` → un seul agent.
- `moyenne` → 1 à 3 agents.
- `complexe` → escouade de 4 à 8 agents.

Le score est expliqué par des signaux (domaines, connecteurs, lexique de complexité, risque, longueur).

### 2. Router

```bash
omnibrain route "la demande"
```

La matrice `matrix.toml` sélectionne les agents par mots-clés et domaines.
Renforts automatiques :

- tout domaine code → `qa-test` ;
- demande complexe → `adversarial-reviewer` ;
- domaine à risque → expert dédié (`security`, `devops-sre`, `ohada-finance`).

L'orchestrateur `omnibrain` ne fait jamais partie d'une escouade.

### 3. Dispatcher en une seule vague

```bash
omnibrain plan task-intake.md -o plan.md
omnibrain plan task-intake.md --format json -o plan.json
```

Chaque agent reçoit un brief autonome : objectif, contexte isolé, entrées,
sorties, contrats d'interface, obligations gates, budget tokens.
**Tous les briefs partent en parallèle** — jamais d'exécution séquentielle.

### 4. Surveiller les gates

```bash
omnibrain gates livrable.md --expect backend-api,qa-test,adversarial-reviewer
```

- G1 Complétude (pas de placeholder, tous les agents couverts)
- G2 Preuve fraîche (faits temporels sourcés et datés)
- G3 Revue adverse (section + verdict)
- G4 Intégration (synthèse, contrats respectés)

Le verdict par défaut est **NEEDS WORK** : un gate ne passe que sur preuve.

### 5. Assembler

Livrer un seul document cohérent selon `templates/orchestration-report.md`,
avec le tableau des gates et les réserves. L'utilisateur voit un seul
interlocuteur.

## Règles réseau

1. Compétence manquante → chercher d'abord dans les collections du compte
   (`agent-skills-index`, `awesome-agent-skills`) avant de réinventer.
2. Économie de tokens : chaque agent ne lit que son brief et ses contrats.
3. Cause racine avant tout correctif ; aucune affirmation sans preuve fraîche.
4. En cas de doute sur la complexité, monter d'un cran puis restreindre sur
   preuve — jamais l'inverse.

## Références

- Matrice : `matrix.toml`
- Fiches agents : `specialized/`
- Contrats : `templates/interface-contract.md`
- Rapport type : `templates/orchestration-report.md`
