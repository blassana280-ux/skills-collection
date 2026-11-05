# AGENTS.md — routage au niveau du compte `blassana280-ux`

> Ce fichier est le **contenu exact** à copier dans le dépôt public
> `blassana280-ux/.github` sous le nom `AGENTS.md` (voir
> `RAPPORT-PHASE1.md` §1.4). Il complète le `README.md` de profil, il ne
> remplace aucune instruction propre à un dépôt.

## Source de vérité

- `blassana280-ux/omni-agents-framework` → `OMNIBRAIN.md`, `registry/`,
  `omni/orchestrator.py` (orchestrateur de référence).
- Couche v4 livrée sur la branche Arena de `blassana280-ux/skills-collection` :
  `omni-agents-framework/omni/{memory,graph,sandbox,telemetry}` + `docs/V4.md`.
- La référence historique `blassana280-ux/optimiser-mes-agents-IA` renvoie
  `403 Resource not accessible by integration` : elle n'a jamais pu être lue et
  ne doit pas être citée comme existante.

## Règles de routage

1. **Classer avant d'agir** : simple → 1 agent ; moyenne → 1 à 3 ; complexe →
   escouade, déclarée puis dispatchée en une seule vague parallèle.
2. **AGENTS.md du dépôt prévaut** sur ce fichier de compte ; en cas de
   divergence, l'upstream (`CONTRIBUTING.md`, spécification du dépôt) gagne.
3. **Réutiliser avant de créer** : chercher dans `registry/skills.json`
   (`python3 -m omni skills <termes>`) avant d'ajouter un agent.
4. **Renforts jamais évincés** : revue adverse indépendante, QA, expert risque.
5. **Preuve fraîche** : aucune affirmation sans sortie de commande, ligne de
   fichier ou réponse d'API. Verdict par défaut : `NEEDS WORK`.
6. **Aucun secret dans le dépôt** : providers et jetons par variables
   d'environnement uniquement ; la mémoire SQLite rédige les secrets.
7. **Jamais d'écriture directe sur `main`/`master`** : branche + PR. Les gates
   human-in-the-loop escaladent vers **Lassana** ; aucune fusion automatique.
8. **Blocage ≠ succès** : un `403`, une permission manquante ou un provider
   absent est documenté et remonté, jamais simulé.

## Vérification minimale avant toute PR

```bash
python3 -m unittest discover -s tests -v
python3 -m omnibrain validate
python3 -m omni registry
```
