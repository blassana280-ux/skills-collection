# Brief agent — `{{agent_id}}` ({{agent_name}})

> Modèle de référence. Le dispatcher génère ces briefs automatiquement dans
> le plan d'orchestration (`omnibrain plan`). Cette fiche sert à rédiger
> un brief manuel ou à comprendre la structure attendue.

## Objectif

{{objective}}

## Contexte isolé

{{context_scope}}

## Entrées

{{inputs}}

## Sorties attendues

{{expected_outputs}}

## Contrats d'interface applicables

_Référencer chaque contrat (`artifact`) émis dans le plan, producteur et
consommateurs, et le schéma correspondant._

## Obligations gates

- G1 Complétude : tous les artefacts du brief livrés, aucun placeholder.
- G2 Preuve fraîche : affirmations factuelles sourcées et datées.
- G3 Revue adverse : se soumettre aux conclusions de l'Adversarial Reviewer.
- G4 Intégration : respect strict des contrats d'interface.

## Budget tokens

{{token_budget}}

## Verdict par défaut

Tout élément non vérifié est marqué **NEEDS WORK**, jamais supposé juste.
