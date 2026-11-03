# Sécurité

## 1. Authentification et permissions

- JWT HS256 signé (`OMNI_AUTH_SECRET`, ≥ 32 octets), expiration configurable,
  `jti` unique ; mots de passe hachés **PBKDF2-SHA256, 180 000 itérations**,
  comparaison en temps constant.
- RBAC : `admin`, `researcher`, `viewer`, `omnibrain`. Matrice consultable via
  `GET /api/auth/permissions` ; chaque dépendance `require(permission)` vérifie
  la permission avant l'accès. Le rôle `omnibrain` n'a aucun droit
  d'administration (test `test_omnibrain_role_has_no_admin_permissions`).
- Clé d'adaptateur `X-OmniBrain-Key` indépendante des comptes utilisateurs.
- `RateLimiter` en mémoire par acteur/IP (`OMNI_RATE_LIMIT_PER_MINUTE`) et
  limite globale de missions concurrentes.

## 2. Validation des entrées

- Schémas Pydantic stricts : `extra="forbid"`, longueur de requête bornée,
  mode dans une énumération, `max_sources` borné, `language` contrôlé, options
  typées.
- `AgentRunner` valide les types et valeurs des entrées structurées (chaînes
  obligatoires non vides, bornes numériques, listes) et refuse les outils hors
  liste blanche (`ToolFacade`).
- Erreurs typées `OmniError` : aucune trace interne ni secret renvoyé au
  client.

## 3. Contenus Internet = données non fiables

- `app/core/security.py` : détection des tentatives d'injection de prompt
  (instructions, jetons de rôle, délimiteurs, exfiltration, balises
  cachées) ; `neutralize_injections()` les remplace par
  `[INSTRUCTION_NEUTRALISEE:…]`. `sanitize_untrusted_text()` et
  `as_untrusted_block()` utilisent le marqueur
  `<<<DONNÉES NON FIABLES>>> ... <<<FIN DONNÉES NON FIABLES>>>`.
- `app/providers/extractor.py` : suppression des `<script>`, `<style>`,
  formulaires et attributs d'événements, taille bornée, encodage explicite.
- **Aucun code trouvé dans une source n'est exécuté** : pas d'`eval`, pas de
  `exec`, pas de désérialisation, pas de sous-processus, pas de `pickle`.
  Les agents n'ont que 7 outils non exécutables (`stats, memory, verify,
  graph, search, extract, llm`).
- `ResearchSynthesizer` n'accepte que les citations `[S#]` présentes dans la
  table des preuves ; les marqueurs inconnus sont retirés.
- UI : création de nœuds via `textContent`/`createElement`, **aucun
  `innerHTML`** (test Node dédié). En-têtes CSP, `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.

## 4. SSRF et réseau

- `validate_public_http_url()` : schéma `http/https` uniquement, refus des
  identifiants dans l'URL, des hôtes locaux, des plages privées/réservées,
  des noms `.local`/`.internal` ; avec `OMNI_DNS_SSRF_CHECK=true`, résolution
  DNS puis contrôle de **toutes** les adresses retournées avant le fetch.
- Suivi de redirections borné, timeouts HTTP explicites, taille de réponse
  bornée, nombre d'extractions par mission borné.
- L'adaptateur OmniBrain n'appelle **aucune URL fournie par l'appelant** :
  pas de callback, pas de webhook.

## 5. Concurrence et quotas

- Sémaphores réels (`OMNI_MAX_PARALLEL_AGENTS`, nombre d'extractions),
  `OMNI_MAX_CONCURRENT_MISSIONS` sur le commander, quotas persistés par
  fournisseur, disjoncteur après échecs répétés, reprise unique puis
  *dead-letter* tracée.
- Le pic de concurrence est **mesuré**, pas supposé ; les agents en attente
  sont annoncés comme tels.

## 6. Journalisation, audit et secrets

- Journal JSON structuré (`app/core/logging_conf.py`) avec rédaction
  automatique des secrets.
- `audit_logs` : authentification, création/annulation, réglages, sauvegarde,
  purge, tests de fournisseur, soumissions OmniBrain.
- `redact()` / `redact_report()` : secrets, jetons et URL avec identifiants
  retirés des réponses, journaux et rapports.
- `.env` exclu de Git ; `.env.example` ne contient que des valeurs factices.
- `dangerous_action_alignment()` : vérifie qu'aucune action irréversible
  d'OmniBrain n'est exposée.

## 7. Sauvegarde / reprise

Voir `RETENTION.md` et `DEPLOYMENT.md`. Toute suppression exige une
confirmation explicite, un rôle admin et une trace d'audit.

## 8. Limites de sécurité connues

- Le `RateLimiter`, la file et l'index vectoriel en repli sont **par
  processus** : derrière plusieurs workers, utiliser Redis (et un rate-limiter
  partagé) pour une limite globale stricte. Le Dockerfile lance donc
  volontairement `--workers 1`.
- Le contrôle DNS SSRF n'a pas été exécuté contre un serveur DNS réel dans ce
  sandbox (`OMNI_DNS_SSRF_CHECK=false` pour les tests hors ligne) : les
  contrôles syntaxiques et de plages IP sont testés, la résolution DNS reste
  « IMPLÉMENTÉE MAIS NON VÉRIFIÉE » en conditions réelles.
- Aucun audit de pénétration externe n'a été mené.
