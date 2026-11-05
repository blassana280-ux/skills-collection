# Contrats d'interface — schémas de référence

> Un contrat n'est émis par le dispatcher que si son producteur ET au moins
> un consommateur font partie de l'escouade. Voir `matrix.toml` [[contracts]].

## api-contract

- **Producteur :** `backend-api` — **Consommateurs :** `frontend-ui`, `qa-test`, `security`
- Schéma : OpenAPI versionné (endpoints, méthodes, authentification, schémas requête/réponse, codes d'erreur, pagination, idempotence).
- Règle : tout changement breaking exige une nouvelle version ; le gel du contrat précède l'implémentation.

## data-contract

- **Producteur :** `data-ai` — **Consommateurs :** `backend-api`, `product-delivery`, `qa-test`
- Schéma : nom du jeu de données, champs/types/unités, fenêtre temporelle, fraîcheur (SLA), propriété, niveaux de sensibilité.
- Règle : rupture de contrat = alerte bloquante dans le pipeline, jamais de correction silencieuse.

## test-plan

- **Producteur :** `qa-test` — **Consommateurs :** `backend-api`, `frontend-ui`, `devops-sre`
- Schéma : exigence → cas de test → couche (unitaire/intégration/E2E) → donnée → résultat attendu → preuve datée.
- Règle : chaque bug corrigé entre dans le plan avec un test qui échoue d'abord.

## deployment-plan

- **Producteur :** `devops-sre` — **Consommateurs :** `security`, `qa-test`, `backend-api`
- Schéma : artefacts, environnements, ordre de déploiement, migrations, fenêtre, rollback testé, seuils d'alerte.
- Règle : pas de mise en production sans rollback écrit et exécuté à blanc.

## ui-contract

- **Producteur :** `frontend-ui` — **Consommateurs :** `product-delivery`, `qa-test`
- Schéma : inventaire de composants, props et états (chargement/vide/succès/erreur), tokens utilisés, critères WCAG, points de rupture responsive.
- Règle : aucun composant hors design system sans dérogation documentée.

## security-contract

- **Producteur :** `security` — **Consommateurs :** `backend-api`, `devops-sre`, `adversarial-reviewer`
- Schéma : finding, sévérité (CVSS ou grille maison), preuve reproductible, impact, correctif minimal, délai de traitement.
- Règle : toute sévérité critique/élevée bloque la mise en production.

## research-contract

- **Producteur :** `research-intel` — **Consommateurs :** `product-delivery`, `marketing-growth`, `ohada-finance`
- Schéma : question de recherche, réponse, niveau de confiance, sources (éditeur, date de publication, date de consultation).
- Règle : un fait sensible exige deux sources indépendantes ; sinon il reste étiqueté source unique.
