# Routeur multi-modèles & Conseil — SUPREME 1.3.0

> État réel : aucun fournisseur connecté, aucun modèle externe découvert en production,
> aucune inférence externe réussie. Le code est implémenté et testé localement ; la connexion
> réelle reste bloquée par l'absence d'identifiant privé et par l'egress du sandbox.

## Découverte et catalogue
- `ModelRouter.discover_provider(provider)` tente un GET réel de catalogue seulement si une clé est configurée.
- `sync_catalog(provider)` persiste les modèles découverts dans `provider_models` avec capacités,
  contexte, aliases, prix attestés éventuels et date de vérification. Une liste vide n'est pas une connexion.
- `routable_models(task)` ne propose que des modèles découverts, compatibles avec la tâche, le contexte,
  la confidentialité, les outils, le coût maximal et le fournisseur demandé.
- Sans fournisseur : `available=false`, raison explicite, aucun modèle inventé. Un outil déterministe
  local ne peut servir que si la tâche l'autorise explicitement ; un agent LLM ne reçoit pas de substitut simulé.

## Routage intelligent
Score = capacité + qualité historique + coût + latence, avec contraintes dures :
`privacy=local-only`, `tools_required`, `max_cost_usd`, contexte, provider demandé, modèle autorisé.
Mistral est prioritaire quand il est réellement disponible. Les fallbacks sont bornés et tracés.
Chaque tentative expose `category`, `endpoint_host`, `request_id`, statut, coût et réservation.
Seule une tentative `external_api` réussie peut compter comme preuve fournisseur.

## Garde d'inférence
Avant tout POST externe : contrôle humain actif, non expiré, plafond USD et nombre d'appels,
prix attestés frais, modèle découvert, contexte connu, quota central. La garde est évaluée dans
la transaction de réservation pour éviter les courses. Découverte GET ≠ génération payante.
Les POST ne sont pas rejoués automatiquement ; les redirections sont refusées ; TLS vérifié.

## Conseil multi-modèles
1. Chaque représentant produit une analyse réelle via son agent/modèle autorisé.
2. Le conseil compare les arguments et les références vers les preuves fournies.
3. Une référence inventée ou une confiance auto-déclarée ne vérifie pas une décision.
4. Désaccord → second avis borné à un appel supplémentaire si le budget restant le permet.
5. Sans consensus vérifiable : `needs_review`, pas de fausse décision ni de mémoire centrale présentée comme vérité.
6. Les coûts sont soldés sur l'usage réel ; une réponse sans usage est incertaine.

## Activation progressive
Voir `PROVIDERS.md` : paliers 5→20→60→100→…→960, preuve individuelle `external_api`,
permissions/budget, quarantaine isolée, reprise contrôlée. Aucun saut direct vers 1020.
Les 60 outils déterministes existants restent séparés des 960 profils LLM.

## Sources
Contrat Mistral confronté au SDK officiel `mistralai/client-python` à `d3da3bd3…`.
Les prix et modèles disponibles ne sont pas inventés : découverte réelle + attestation humaine des prix.
