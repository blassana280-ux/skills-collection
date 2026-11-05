# Fournisseurs IA OMNIBRAIN SUPREME — connexion sécurisée

**Règle d'or : un fournisseur *configuré* n'est pas *opérationnel*.** Seul un **appel API réel
réussi** rend un fournisseur opérationnel. Aucune disponibilité ni réponse n'est inventée.

## État actuel (vérifié)
- **0 fournisseur connecté** dans l'environnement de développement (aucune clé, egress limité).
- Le client HTTP est **réel et testé** (23 tests, dont un vrai aller-retour HTTP vers un stub local).
- **Mistral / Vide est le fournisseur prioritaire** (`priority=1`). Il ne sera déclaré opérationnel
  qu'après un premier appel API réussi avec votre clé.

## Fournisseurs supportés
| Priorité | Fournisseur | Variable d'environnement | Famille d'API |
| --- | --- | --- | --- |
| 1 | **Vide (Mistral AI)** | `MISTRAL_API_KEY` | openai-compatible |
| 2 | Groq | `GROQ_API_KEY` | openai-compatible |
| 3 | DeepSeek | `DEEPSEEK_API_KEY` | openai-compatible |
| 4 | OpenAI | `OPENAI_API_KEY` | openai-compatible |
| 5 | OpenRouter | `OPENROUTER_API_KEY` | openai-compatible |
| 6 | Google Gemini | `GEMINI_API_KEY` | gemini |
| 7 | Anthropic | `ANTHROPIC_API_KEY` | anthropic |
| 8 | Ollama (local) | `OLLAMA_HOST` | ollama |
| 9 | Compatible OpenAI personnalisé | `SUPREME_OPENAI_COMPAT_API_KEY` + `SUPREME_OPENAI_COMPAT_BASE_URL` + `SUPREME_OPENAI_COMPAT_MODEL` | openai-compatible |

## Connecter un fournisseur SANS exposer de secret

### Option A — Variables d'environnement (recommandé)
Définissez la clé dans l'environnement du processus serveur, **jamais dans le dépôt** :
```bash
# Exemple : Mistral/Vide (ne collez JAMAIS la clé dans un fichier commité)
export MISTRAL_API_KEY="<votre-clé>"      # à saisir dans votre shell, pas dans le dépôt
cd omni-agents-framework
python3 -m supreme providers --check     # appel RÉEL de disponibilité (affiche le statut, pas la clé)
python3 -m supreme serve --port 8765     # le serveur lit la clé depuis l'env
```
Le routeur détecte la clé, tente un appel réel, et ne rapporte `available` que si l'appel réussit.

### Option B — Fichier de secrets gitignoré (0600)
```bash
python3 -m supreme providers --init-secrets   # crée var/supreme/providers.json VIDE (0600, gitignoré)
# Éditez ce fichier HORS dépôt et renseignez vos clés. Il n'est jamais commité.
```
Format (valeurs à remplir par vous, jamais par l'assistant) :
```json
{ "mistral": "", "groq": "", "deepseek": "", "openai": "", "openrouter": "",
  "gemini": "", "anthropic": "", "openai_compat": "" }
```
L'environnement a priorité sur le fichier. Les clés ne sont **jamais** journalisées ni affichées.

### Option C — API compatible OpenAI / passerelle (ex. OmniRoute)
```bash
export SUPREME_OPENAI_COMPAT_BASE_URL="https://votre-passerelle/v1"
export SUPREME_OPENAI_COMPAT_API_KEY="<clé>"
export SUPREME_OPENAI_COMPAT_MODEL="nom-du-modèle"
```

## Vérifier et utiliser
```bash
python3 -m supreme providers              # statut (configuré oui/non), SANS les clés
python3 -m supreme providers --check      # appel réel /models -> available/auth_error/unreachable
```
- `available` : appel HTTP réel réussi → le fournisseur peut être routé.
- `auth_error` : clé invalide (401/403).
- `unreachable` : réseau injoignable (egress sandbox limité vers les API IA).
- `not_configured` : aucune clé.

Une fois un fournisseur `available`, les **tâches LLM des 960 agents** s'exécutent réellement
via le routeur (sélection par capacité/coût/qualité/latence + priorité Mistral/Vide), avec
**fallback** multi-fournisseurs et **budget** réel. Le conseil multi-modèles produit alors de
vraies analyses indépendantes.

## Sécurité des clés (testé)
- Clés lues uniquement depuis l'env ou le fichier gitignoré `0600`.
- **Jamais** dans le dépôt, les commits, les journaux, les rapports, l'API.
- Expurgées de toute erreur (`redact`) ; jamais dans l'URL (Gemini en en-tête `x-goog-api-key`).
- Tests : `test_supreme_providers.py` (client, fallback, budget, expurgation, anti-fuite) +
  `test_supreme_security_audit.py` (scan du dépôt, fichiers secrets non suivis).

## Gratuit d'abord
- **Ollama** (local) : gratuit si vous avez un modèle local (`OLLAMA_HOST`).
- **Groq / Mistral / DeepSeek / Gemini / OpenRouter** : offres gratuites/quota selon fournisseur.
  Aucune dépense ni abonnement n'est créé sans votre accord. Le `BudgetController` applique
  quotas, alertes (90 %) et coupure ; le coût réel est enregistré par mission/agent/fournisseur.

## Ce qui reste à faire (action humaine)
1. Fournir une clé (env ou fichier gitignoré) — **l'assistant ne demande jamais la clé en clair**.
2. Lancer `providers --check` pour prouver la disponibilité réelle.
3. Autoriser toute dépense éventuelle. Tant qu'aucune clé n'est fournie, le système reste
   honnêtement en mode « aucun fournisseur connecté » (outils déterministes locaux uniquement).
