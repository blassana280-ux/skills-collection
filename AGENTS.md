<!-- omnibrain-overlay:v2 -->

---

<!--
  Section locale du réseau blassana280-ux — ajoutée par OmniBrain.
  Les instructions upstream ci-dessus restent la seule autorité pour ce dépôt :
  cette section ajoute des règles de travail locales, elle n'en remplace aucune.
  Supprimez ce bloc avant toute contribution upstream si le dépôt ne l'accepte pas.
-->

# Couche locale — réseau OmniBrain

## Source de vérité de l'orchestrateur

> **blassana280-ux/omni-agents-framework** → `OMNIBRAIN.md`, `registry/`, `omni/orchestrator.py`, `tests/`

La référence historique `blassana280-ux/optimiser-mes-agents-IA` **n'a pas pu être vérifiée** (l'API GitHub
répond `403`, aucun accès en lecture) : elle ne doit plus être citée comme
existante.

## Règles de travail

1. **Classer avant d'agir** — simple → 1 agent ; moyenne → 1 à 3 ; complexe →
   escouade, dispatch dans une seule vague parallèle.
2. **Preuve fraîche obligatoire** — aucune affirmation sans sortie de commande,
   ligne de fichier ou réponse d'API. Verdict par défaut : « NEEDS WORK ».
3. **Réutiliser avant de créer** — chercher dans `registry/skills.json`
   (`python3 -m omni skills <termes>`) avant d'inventer un agent.
4. **Aucun secret dans le dépôt** — providers et tokens via environnement injecté,
   `*_FILE` privé, ou stockage runtime 0600 hors Git ; jamais dans le chat/commit/log.
5. **Jamais d'écriture directe sur `main`** — branche + Pull Request.
6. **Respect de l'upstream** — `CONTRIBUTING.md` du dépôt prévaut, y compris
   pour la déclaration d'assistance IA.

## Couche OMNIBRAIN SUPREME 1000 (2026-11-05, version 1.4.0)

> Source de vérité : `skills-collection/omni-agents-framework/supreme/` +
> `skills-collection/omni-agents-framework/docs/supreme/`.
> Point d'entrée : [`OMNIBRAIN-SUPREME.md`](OMNIBRAIN-SUPREME.md).

- 20 divisions × 50 spécialistes = **1000 profils** + 20 chefs ; registre SQLite, orchestrateur
  DAG, bus, mémoire 4 niveaux, routeur multi-modèles, politique de risque, API + dashboard mobile.
- **Activation sur preuve** : un agent n'est `operational` qu'après exécution réelle réussie.
  Ne jamais présenter 1000 agents enregistrés comme 1000 opérationnels.
- **Aucun fournisseur IA supposé connecté** ; détection réelle, aucune connexion simulée.
- Reprise du travail : `omni-agents-framework/docs/supreme/CONTINUITY.md`.
- Tests : `cd omni-agents-framework && python3 -m unittest discover -s tests` (**378 découverts = 105 V4 + 273 SUPREME ; 377 locaux verts + 1 opt-in réel ignoré**).
- Activation 1.4.0 : Mistral/Vide, découverte réelle, autorisation humaine bornée, paliers 5→20→60→100→…→960,
  preuve `external_api` obligatoire, quarantaine isolée. Aucun stub local ne peut activer un agent LLM.
- Durcissement 1.2.1 conservé : workers à baux/heartbeat/fencing, apprentissage périodique persistant,
  budget réservé avant appel, conseil sans contournement du routeur. Aucune fusion de PR sans accord.
