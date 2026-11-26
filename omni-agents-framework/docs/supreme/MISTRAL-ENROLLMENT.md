# Enregistrer une clé Mistral en sécurité — depuis Android

**Version SUPREME : 1.4.0** (le mécanisme est identique à 1.3.0, avec l'attestation
de contexte en plus). Document destiné à l'opérateur humain.

> **Ne collez jamais votre clé dans une conversation, une issue, une PR, un commit,
> un fichier du dépôt ou un journal.** Aucune procédure ci-dessous ne vous le demande.

---

## 0. Résultat mesuré du sandbox Arena — à lire avant tout

Test réel effectué le 2026-11-05, même méthode GET pour tous les hôtes :

| Hôte | Joignable | Résultat |
| --- | :---: | --- |
| `api.github.com` | **oui** | HTTP 200 |
| `api.mistral.ai` | **non** | TLS fermé avant HTTP (`EOF`) |
| `api.openai.com` | **non** | TLS fermé avant HTTP (`EOF`) |
| `console.mistral.ai` | **non** | TLS fermé avant HTTP (`EOF`) |

Le DNS résout correctement, mais la connexion TLS est coupée par la politique
d'egress du sandbox. **Ce n'est pas un échec d'authentification** : aucune requête
HTTP n'atteint Mistral.

**Conséquence decisive : enregistrer la clé dans le sandbox Arena ne permettrait
aucune vérification réelle.** La clé doit être enregistrée sur la machine où
SUPREME s'exécutera vraiment et qui peut joindre `api.mistral.ai`.

Preuves : `var/supreme/validation/mistral-egress-test.json`,
`egress-control-test.json`, `verify-mistral-nocred.json`.

---

Une implémentation parallèle existe pour **OmniRouteLite** (Node) dans le dépôt
`omni-agents-framework`, branche `feature/mistral-connect-securise`. Elle cible une
autre pile ; ne pas la confondre avec SUPREME. Comparaison détaillée et correction
d'une erreur de continuité : **`ECOSYSTEM-ALIGNMENT.md`**.

## 1. Voie recommandée : Termux sur votre Android

La clé ne quitte **jamais** votre téléphone : pas de proxy, pas de serveur tiers,
pas de transit réseau. C'est l'option la plus sûre et elle est gratuite.

### 1.1 Préparer Termux

Installez **Termux** depuis F-Droid (la version du Play Store est obsolète), puis :

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git
python --version          # 3.11 ou plus
```

### 1.2 Récupérer le code

```bash
cd ~
git clone https://github.com/blassana280-ux/skills-collection.git
cd skills-collection/omni-agents-framework
```

Si le dépôt est privé, authentifiez-vous **sur votre appareil** avec vos propres
moyens GitHub (par ex. `pkg install gh` puis `gh auth login`). Ne communiquez aucun
jeton dans une conversation.

### 1.3 Vérifier que votre téléphone joint Mistral

```bash
python -c "import urllib.request,urllib.error;\
u='https://api.mistral.ai/v1/models';\
exec('try:\n urllib.request.urlopen(u,timeout=20).close();print(\"reachable 200\")\nexcept urllib.error.HTTPError as e:\n print(\"reachable\",e.code)\nexcept Exception as e:\n print(\"BLOCKED\",e)')"
```

Un résultat `reachable 401` est **normal et attendu** : sans clé, Mistral répond
« non autorisé ». Cela prouve que le réseau passe. Si vous obtenez `BLOCKED`,
changez de réseau (données mobiles plutôt qu'un Wi-Fi filtré) avant de continuer.

### 1.4 Créer la clé chez Mistral

Sur `console.mistral.ai`, depuis le navigateur de votre téléphone : créez une clé,
copiez-la dans le presse-papiers. **Ne la collez nulle part ailleurs que dans le
terminal à l'étape suivante.** Prévoyez une limite de dépense côté console si
l'option existe : c'est une protection indépendante de SUPREME.

### 1.5 Enrôlement sécurisé, vérification et découverte

```bash
cd ~/skills-collection/omni-agents-framework
./ops/enroll-mistral.sh
```

Le script :
1. refuse de démarrer sans terminal privé (donc jamais depuis un pipe ou un chat) ;
2. vérifie que le stockage est hors dépôt et ignoré par Git ;
3. **teste la joignabilité réelle avant toute saisie** et s'arrête si l'hôte est bloqué ;
4. demande la clé **deux fois, sans écho** (`getpass`) — elle ne s'affiche pas ;
5. écrit `var/supreme/secrets/mistral.key` en `0600`, répertoire `0700` ;
6. audite les permissions réellement appliquées ;
7. lance `providers --verify mistral` — **GET `/v1/models`, gratuit, sans génération** ;
8. affiche les **modèles réellement découverts**, leur contexte et leurs capacités ;
9. s'arrête là. **Aucune inférence payante n'est déclenchée.**

Si la vérification échoue, le script le dit explicitement : la clé est enregistrée
mais **le fournisseur n'est pas connecté**. Il ne prétend jamais le contraire.

### 1.6 Choisir le modèle, attester les prix, calculer le budget

Les prix ne sont **jamais** devinés par SUPREME. Relevez-les sur la page tarifaire
officielle de Mistral, puis :

```bash
python -m supreme providers --set-prices mistral --model MODELE_DECOUVERT \
  --input-per-million PRIX_ENTREE --output-per-million PRIX_SORTIE \
  --source https://PAGE_OFFICIELLE --confirm 'JE CONFIRME LES PRIX'

# Si l'API n'expose pas la fenêtre de contexte du modèle :
python -m supreme providers --attest-context mistral --model MODELE_DECOUVERT \
  --context-tokens N --source https://PAGE_OFFICIELLE --confirm 'JE CONFIRME LE CONTEXTE'

# Plan de budget par palier, à partir des prix que vous venez d'attester :
python ops/budget-plan.py --from-attested mistral --model MODELE_DECOUVERT
```

`budget-plan.py` affiche le coût estimé par agent et pour chaque palier
(5 → 20 → 60 → 100 → 200 → 400 → 600 → 800 → 960), avec une marge conseillée.
C'est une **estimation arithmétique**, pas un devis ; le coût réellement facturé
est enregistré dans `budget_ledger` après chaque appel.

### 1.7 Autoriser l'inférence — seulement après votre décision

Rien ne part sans cette commande explicite, bornée en durée, en montant et en
nombre d'appels :

```bash
python -m supreme providers --authorize mistral --budget-usd 0.25 --max-calls 5 \
  --hours 1 --approved-by VOTRE_NOM --confirm 'AUTORISER INFERENCE'

python -m supreme activation --prepare 5 --provider mistral --model MODELE_DECOUVERT
python -m supreme activation --run act-XXXX
```

Révocation immédiate :

```bash
python -m supreme providers --revoke mistral --confirm 'REVOQUER INFERENCE'
```

---

## 2. Voie « gestionnaire de secrets » : `MISTRAL_API_KEY_FILE`

Si votre environnement dispose déjà d'un coffre (Vault, `pass`, `sops`, secrets
systemd, Docker secrets, coffre d'un hébergeur), n'écrivez pas la clé vous-même :
faites-la matérialiser dans un fichier privé et pointez dessus.

```bash
# Exemple avec pass (le secret n'apparaît jamais dans le shell)
install -d -m 700 ~/.config/supreme
umask 077
pass show mistral/api-key > ~/.config/supreme/mistral.key
chmod 600 ~/.config/supreme/mistral.key

export MISTRAL_API_KEY_FILE="$HOME/.config/supreme/mistral.key"
python3 -m supreme providers --verify mistral
```

Ordre de résolution appliqué par SUPREME :
`MISTRAL_API_KEY` (variable) → `MISTRAL_API_KEY_FILE` → `var/supreme/secrets/mistral.key`
→ ancien fichier privé hérité.

Contrôles appliqués à la lecture : fichier régulier, pas de lien symbolique,
permissions non groupées/mondiales, propriétaire = vous, taille bornée. Un fichier
trop permissif est **refusé**, pas lu.

Pour un service systemd, préférez `LoadCredential=`/`SetCredential=` plutôt qu'un
fichier persistant, et pointez `MISTRAL_API_KEY_FILE` vers le chemin fourni.

---

## 3. Voie « interface d'administration protégée »

Le dashboard actuel **ne permet volontairement pas** d'écrire une clé : l'API n'a
aucun endpoint d'écriture de secret, précisément pour qu'une clé ne transite pas par
HTTP ni n'apparaisse dans un journal d'accès.

Une interface web d'enrôlement n'est justifiée que si SUPREME tourne sur un serveur
distant et que vous voulez l'enrôler depuis le navigateur d'Android. Elle exige
alors **tous** les éléments suivants, sans exception :

- HTTPS avec certificat valide (jamais HTTP simple) ;
- authentification admin + jeton d'enrôlement à usage unique et expiration courte ;
- endpoint désactivé par défaut, activé explicitement pour la durée de l'opération ;
- champ de saisie masqué, jamais de valeur renvoyée au client ;
- corps de requête **jamais journalisé**, en-têtes expurgés ;
- écriture immédiate en `0600` hors dépôt, puis désactivation de l'endpoint ;
- limitation de débit et journal d'audit sans secret.

**Cette interface n'est pas construite à ce jour.** Elle nécessite votre accord
explicite, car elle implique de faire transiter un secret par le réseau — ce que
la voie Termux évite complètement. Dites-le si vous en avez besoin.

---

## 4. Ce qui est vérifié, et ce qui ne l'est pas

| Élément | État |
| --- | --- |
| Mécanisme de saisie masquée (`getpass`, double saisie) | **testé en pseudo-terminal réel**, clé factice, aucune fuite dans la sortie |
| Permissions `0600` / répertoire `0700` | **vérifiées** après écriture |
| Refus sans terminal privé | **vérifié** |
| Refus d'enrôler si l'hôte est injoignable | **vérifié** (arrêt code 5 dans le sandbox) |
| `ops/enroll-mistral.sh` de bout en bout | **prêt**, parcours complet jusqu'au blocage réseau réel |
| `ops/budget-plan.py` | **testé**, refuse tout prix par défaut |
| Clé Mistral enregistrée | **non — aucune clé n'existe encore** |
| `providers --verify mistral` réussi | **non — `not_configured`, exit 1** |
| Modèles Mistral découverts | **non — 0** |
| Tarifs vérifiés | **non — aucun prix attesté, aucun tarif inventé** |
| Fournisseur réellement connecté | **NON** |

Aucune connexion n'a été simulée. Aucune inférence n'a été lancée. Aucune dépense.
