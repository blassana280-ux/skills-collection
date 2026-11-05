# Routeur multi-modèles & Conseil OMNIBRAIN SUPREME

## Fournisseurs examinés
OpenAI, Mistral, DeepSeek, Google Gemini, OpenRouter, Anthropic, Ollama (local),
compatibles OpenAI. **Aucun n'est connecté actuellement** (aucune clé dans l'environnement,
réseau sortant du sandbox limité à GitHub/npm/PyPI).

## Détection réelle
- `router.detect()` : inspecte la **présence** des variables d'environnement (jamais leur valeur).
- `router.check_availability()` : appel HTTP réel **seulement si configuré** ; statuts
  `not_configured`, `available`, `auth_error`, `unreachable`, `network_disabled`.
- Aucune connexion simulée ; aucun identifiant fabriqué.

## Routage intelligent
Score = capacité (0.5) + qualité historique (0.3) + coût (0.1) − latence (0.1).
Contraintes : `privacy=local-only` (modèles locaux seuls), `tools_required`, `max_cost_usd`.
Fallback : liste des modèles alternatifs classés. Sans fournisseur : `available=false` avec
raison explicite et repli vers outil déterministe local si la tâche le permet.

## Conseil multi-modèles
Protocole : formulation → analyses indépendantes → arguments → comparaison → vérification →
désaccords → évaluation des preuves → synthèse → décision. **Décision fondée sur preuves +
indépendance des sources, pas sur la majorité seule** (testé : une réponse minoritaire mais
prouvée bat une majorité sans preuve). Budget et tours bornés (`CouncilConfig`).
Sans fournisseur : statut `unavailable`. La production d'analyses via appels API réels reste
à câbler quand des clés seront fournies (non simulée).

## Activation (action humaine requise)
Fournir les clés via variables d'environnement / secrets GitHub, puis :
```bash
python3 -m supreme serve   # ou POST /api/providers/check
```
Le routeur détectera et testera réellement les fournisseurs. Aucune dépense sans accord.

## Client réel (v1.1+)
Le routeur ne se limite plus à la détection : `ModelRouter.complete()` effectue de VRAIS appels
HTTP (voir `PROVIDERS.md`), avec fallback multi-fournisseurs, budget réel et priorité Mistral/Vide.
Les agents LLM et le conseil s'exécutent réellement dès qu'un fournisseur est configuré et
répond ; sans fournisseur, tout est bloqué/indisponible honnêtement. `configured != available` :
seul un appel réussi prouve la disponibilité.

## Budget strict 1.2.1
- `ModelRouter.complete` réserve une borne supérieure de coût avant chaque tentative,
  puis solde sur l'usage réel. Les tentatives sont tracées (fournisseur, modèle, statut,
  coût, réservation). Les dépassements individuels sont bloqués avant HTTP.
- `Council.deliberate` utilise `router.complete` avec un plafond collectif conservateur
  fondé sur les bornes de coût et sans fallback interne ; il ne contourne pas les quotas centraux.
- Les erreurs réseau/5xx incertaines conservent une réservation `interrupted` par prudence ;
  les rejets explicites avant traitement (ex. 401) libèrent la réservation.
- `max_tokens` doit être positif et tenir dans le contexte ; sinon l'appel est bloqué avant HTTP.
