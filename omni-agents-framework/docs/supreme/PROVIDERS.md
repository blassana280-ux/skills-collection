# Fournisseurs IA — SUPREME 1.3.0

> **État réel à cette livraison : 0 fournisseur IA connecté, 0 modèle externe vérifié,
> 0 inférence externe réussie, 0 agent LLM opérationnel, 0 dépense.** Les adaptateurs sont
> implémentés et testés localement contre un stub HTTP ; cela n'est pas une intégration réelle.
> Une clé enregistrée ne suffit pas : il faut une vérification API réussie. Une découverte GET
> ne prouve pas la génération. L'activation d'un agent exige en plus une inférence réelle exploitable.

## 1. Priorité Mistral — ce qui est implémenté
- Adaptateur HTTP JSON vers l'API officielle `https://api.mistral.ai/v1` :
  `GET /models`, `POST /chat/completions` non streamé, `response_format=json_object`.
- Authentification `Authorization: Bearer …` uniquement en en-tête, jamais dans l'URL.
- Parsing des cartes modèles : `id`, `capabilities`, `max_context_length`, `aliases`, `owned_by`.
- Sélection d'un modèle compatible chat + sortie JSON, contexte suffisant pour la tâche.
- Usage fournisseur obligatoire pour solder le coût ; réponse sans usage = incertaine, pas un succès bon marché.
- Timeouts bornés, retries uniquement sur découverte GET, **aucun retry automatique d'un POST d'inférence**.
- Redirections refusées ; TLS vérifié ; secret expurgé des erreurs ; endpoint HTTPS hors loopback en production.
- Contrat confronté au SDK officiel accessible `mistralai/client-python`, commit
  `d3da3bd3c63d0502449e1e765bc2d3c16d0d2f1d` : modèles `/v1/models`, chat completion, capacités/contexte.

Dans le catalogue existant, « Vide (Mistral AI) » est l'affichage du connecteur `mistral`.
Il n'est pas traité comme un second endpoint distinct : aucune URL, clé ou tarification séparée n'est inventée.

## 2. Connecter Mistral sans communiquer la clé dans la conversation
Ne collez jamais une clé dans le chat, une issue, une PR, un commit, une commande shell historisée,
un fichier versionné ou un journal. Trois chemins sûrs sont prévus :

### A. Terminal privé de l'opérateur (recommandé)
Sur la machine qui héberge SUPREME, dans un vrai terminal :
```bash
cd skills-collection/omni-agents-framework
python3 -m supreme providers --connect mistral
```
Le programme demande la clé avec `getpass` (pas d'écho), refuse les pipes/entrées non interactives,
écrit `var/supreme/secrets/mistral.key` en **0600** dans un répertoire **0700**, vérifie propriétaire,
symlinks et permissions, puis affiche seulement des métadonnées. La clé n'est pas affichée en retour.

### B. Secret manager / fichier monté privé
```bash
export MISTRAL_API_KEY_FILE=/chemin/prive/mistral.key
# exigences : fichier régulier, propriétaire courant, 0600 ou plus strict, répertoires non partageables
```

### C. Variable d'environnement injectée par l'hébergeur
```bash
# Injecter MISTRAL_API_KEY via le mécanisme de secrets de l'hébergeur, pas via le dépôt.
python3 -m supreme providers --status
```
Ordre de résolution : variable d'environnement → `MISTRAL_API_KEY_FILE` → fichier runtime privé →
ancien `providers.json` 0600 hérité. Les métadonnées publiques indiquent seulement présence/source/préfixe non secret.

### Vérification réelle
```bash
python3 -m supreme providers --verify mistral
python3 -m supreme providers --sync-models mistral
```
`--verify` tente un GET `/models`. Un succès TLS/HTTP/authentifié marque `api_reachable`,
`auth_validated`, `models_listed`, puis `connected` uniquement si des modèles sont listés.
Un échec réseau reste `unreachable` ; un 401/403 reste `auth_failed`. **Aucune inférence payante n'est lancée.**

Dans le sandbox de livraison, l'egress vers `api.mistral.ai` a échoué au handshake TLS avant HTTP.
Ce n'est pas une preuve d'authentification invalide ; c'est une limitation réseau documentée.
Aucune clé utilisateur n'était présente. Connecteur Arena `mistral` : non disponible.

## 3. Autoriser une inférence réelle bornée
Découverte et génération sont séparées. Après connexion vérifiée, l'opérateur doit :

1. Choisir un modèle découvert compatible chat/JSON et contexte suffisant.
2. Attester les prix publics depuis une source officielle HTTPS, sans les inventer :
```bash
python3 -m supreme providers --set-prices mistral --model MODELE_DECOUVERT \
  --input-per-million USD --output-per-million USD \
  --source https://SOURCE_OFFICIELLE_DE_PRIX --confirm 'JE CONFIRME LES PRIX'
```
3. Autoriser explicitement une fenêtre d'inférence courte et bornée :
```bash
python3 -m supreme providers --authorize mistral --budget-usd 0.25 --max-calls 5 --hours 1 \
  --confirm 'AUTORISER INFERENCE'
```
La garde vérifie à chaque réservation : fournisseur connecté, modèle découvert, contrôle actif non expiré,
prix frais ≤30 jours, contexte connu, quota central disponible, plafond d'appels et exposition USD.
Sans cette autorisation, toute inférence externe est refusée **avant réseau**.

Révocation :
```bash
python3 -m supreme providers --revoke mistral --confirm 'REVOQUER INFERENCE'
```
L'API HTTP locale ne peut pas accorder/révoquer cette autorisation ni écrire une clé. Elle utilise les
contrôles accordés en CLI privé. Les actions sensibles du dashboard exigent une confirmation explicite.

## 4. Activation progressive des agents LLM
Catalogue réel : **1 020 profils = 1 000 spécialistes + 20 chefs**, dont **960 profils LLM** et
60 outils déterministes. Les 960 LLM restent non opérationnels tant qu'ils n'ont pas leur preuve individuelle.

Paliers cumulatifs stricts : **5 → 20 → 60 → 100 → 200 → … → 900 → 960**.
```bash
python3 -m supreme activation --status
python3 -m supreme activation --prepare 5 --provider mistral --model MODELE_DECOUVERT
python3 -m supreme activation --run CAMPAGNE_ID
python3 -m supreme activation --release-quarantine AGENT_ID --confirm 'JE CONFIRME LA REVUE'
```
Pour chaque agent : permissions `inference:call` + modèle autorisé, budget réservé, appel réel `external_api`,
HTTP 200, texte JSON exploitable, usage/coût soldé, preuve privée 0600, activation atomique avec bail fencé.
Un échec isolé met l'agent en quarantaine ; les autres continuent. Une panne fournisseur interrompt la campagne.
Une campagne interrompue est reprenable ; un membre déjà vérifié n'est pas rappelé. Pas de saut 60→1020.

**Aucune campagne réelle n'a été lancée à cette livraison** : pas de clé, pas d'autorisation d'inférence,
pas de modèle découvert, egress limité. Les tests de campagne utilisent des stubs locaux explicitement non activants.

## 5. Conseil multi-modèles et intelligence
- `CouncilEngine` confronte les analyses réellement produites par les représentants disponibles.
- Seules les références vers les preuves fournies comptent ; une confiance auto-déclarée ne suffit pas.
- Désaccord → second avis borné à un appel supplémentaire si le budget le permet ; sinon `needs_review`.
- Une décision non vérifiée n'est pas mémorisée comme vérité centrale.
- Les missions complexes peuvent sélectionner plusieurs divisions ; le vérificateur est indépendant du producteur.
- La vérification automatique est structurelle/traçable, pas une preuve absolue de vérité métier.
- Mémoire : provenance par mission/tâche/agent, contradictions sur `subject_key` + `claim_key` + `claim_value`.
- Apprentissage : cycles persistés, comparaison mesurée avant/après ; baseline initiale ≠ gain ; pas de modification du noyau.

DeepSeek/OpenAI/Gemini/Anthropic/etc. ne seront ajoutés au conseil que lorsqu'ils auront une preuve API réelle,
un modèle découvert, des prix attestés et une autorisation. Aucun fournisseur n'est déclaré connecté par défaut.

## 6. Coûts, quotas et états honnêtes
- `registered`/`validated`/`operational`/`connected` sont distincts dans l'API et le dashboard.
- Coût réel = usage fournisseur × prix attesté ; une estimation de réservation n'est pas une dépense.
- Une réponse reçue mais non exploitable peut avoir un coût réel ; elle est tracée comme telle.
- Après timeout/5xx/réponse ambiguë, l'exposition reste réservée (`uncertain`) jusqu'à revue ; pas de double POST automatique.
- Quotas centraux : appels/minute et jour, budget global/projet/fournisseur ; garde atomique dans la transaction de réservation.
- Les rapports publics n'exposent ni clé, ni préfixe de clé, ni chemin privé complet.

## 7. Sources et limites
- SDK officiel consulté : `https://github.com/mistralai/client-python` à `d3da3bd3…`.
- Les prix ne sont pas codés en dur : ils doivent être attestés par l'opérateur depuis une source officielle fraîche.
- Les modèles disponibles changent ; SUPREME les découvre au lieu d'inventer une liste.
- « Local » dans les tests signifie SQLite/subprocess/HTTP loopback, jamais cloud.
