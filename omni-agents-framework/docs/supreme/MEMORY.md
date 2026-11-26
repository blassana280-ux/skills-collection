# Memory Engine OMNIBRAIN SUPREME

## 4 niveaux
- **central** : connaissances communes, décisions globales (écriture : chefs/cerveau).
- **individual** : expériences propres à chaque agent (lecture/écriture : propriétaire seul).
- **division** : savoir partagé d'une division (membres de la division).
- **collective** : résultats validés, erreurs, enseignements (écriture : chefs/cerveau).

## 8 types
`working`, `episodic`, `semantic`, `procedural`, `historical`, `decision`, `error`, `skill`.

## Fonctions réelles (testées)
- Recherche plein texte **FTS5** (repli LIKE si FTS5 absent) + filtres métadonnées.
- **Graphe de connaissances** : `relate(src,dst,relation)`, `neighbors`.
- **Provenance** : champ `source` ; **confiance** : `confidence` ∈ [0,1].
- **Versionnement** : `update` crée une version liée (`parent_id`), l'ancienne est marquée supprimée.
- **TTL** : `expires_at` + `expire()` (suppression des informations périmées).
- **Détection de contradictions** : même `subject_key`, contenus différents.
- **ACL** : lecture/écriture par niveau + propriétaire.
- **Suppression contrôlée** : soft-delete avec raison.
- **Rédaction des secrets** avant persistance ; **contenu non fiable** encapsulé et marqué.

## Recherche sémantique
Interface présente ; **indisponible sans fournisseur d'embeddings configuré**. Le moteur
retourne `semantic_available=false` avec une note explicite. Aucune fausse recherche sémantique.

## Politique de stockage
- Pas de stockage automatique de toutes les conversations.
- Secrets et données personnelles inutiles exclus (rédaction + minimisation).
- Instructions malveillantes externes traitées comme données, jamais comme instructions.

## Recherche contextuelle TF-IDF (Phase F, locale réelle)
En plus de FTS5 (plein texte) et du repli LIKE, un mode `tfidf` offre une **recherche
contextuelle locale réelle** sans fournisseur :
```python
mem.search("omnibrain-core", query="latence réseau", mode="tfidf")
# -> {"mode": "tfidf", "tfidf_available": true, "results": [... scores _tfidf ...]}
```
- Rappel large par tokens (LIKE sur chaque terme) puis **re-ranking par similarité cosinus
  TF-IDF** (`supreme/memory.py:tfidf_rank`). Fonctionne hors ligne, sans clé.
- Ce n'est **pas** des embeddings neuronaux : `semantic_available=false` reste signalé
  honnêtement tant qu'aucun fournisseur d'embeddings n'est configuré. Le TF-IDF est un rappel
  contextuel lexical pondéré, réellement testé (3 tests).
- Modes disponibles : `auto` (FTS5→LIKE), `fts`, `tfidf`, `metadata` (sans requête).
