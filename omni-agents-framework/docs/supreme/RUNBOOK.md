# Runbook d'exploitation OMNIBRAIN SUPREME 1.4.0

**Public** : l'humain qui exploite la plateforme. **Périmètre** : démarrage, arrêt,
sauvegarde, restauration, rétention, surveillance, maintenance, récupération.
Tout est local et gratuit par défaut. Aucune étape ne publie sur Internet ni ne dépense.

---

## 1. Principe de sûreté

| Règle | Conséquence opérationnelle |
| --- | --- |
| Local par défaut | `SUPREME_BIND=127.0.0.1`, ports Docker liés à `127.0.0.1` |
| Inférence fermée par défaut | Une clé ne suffit pas : autorisation humaine bornée obligatoire |
| Aucune suppression implicite | Rétention en simulation tant que `--apply --confirm` n'est pas donné |
| Aucun secret en dépôt | Clé via TTY masqué, `*_FILE` 0600 hors dépôt, ou gestionnaire de secrets |
| Données = source de vérité | Un statut « opérationnel » exige une preuve persistée |

---

## 2. Démarrage / arrêt (sans root, sans Docker)

```bash
cd omni-agents-framework
./ops/supreme-ctl.sh start     # api + worker(s) + learn + guardian
./ops/supreme-ctl.sh status    # PIDs + état réel SQLite
./ops/supreme-ctl.sh logs      # 50 dernières lignes par service
./ops/supreme-ctl.sh stop      # SIGTERM, arrêt propre, pas de SIGKILL
```

Variables utiles (voir `ops/env.example`) : `SUPREME_VAR_DIR`, `SUPREME_PORT`,
`SUPREME_WORKERS`, `SUPREME_PYTHON`. Les journaux vont dans `var/supreme/logs/`,
les PID dans `var/supreme/run/`, permissions `0700`.

**Ordre d'arrêt** : guardian → learn → workers → api. Les baux et jetons de fencing
garantissent qu'un worker interrompu ne corrompt pas une mission reprise.

## 3. Service systemd utilisateur (durable, redémarrage automatique)

```bash
./ops/supreme-ctl.sh install-units      # installe, ne démarre rien
systemctl --user daemon-reload
systemctl --user enable --now supreme-api.service supreme-worker@1.service \
                              supreme-learn.service supreme-guardian.service
systemctl --user enable --now supreme-backup.timer supreme-audit.timer
loginctl enable-linger "$USER"          # survit à la déconnexion
systemctl --user list-timers            # vérifier la planification
```

Durcissement appliqué : `UMask=0077`, `NoNewPrivileges`, `PrivateTmp`,
`ProtectSystem=strict`, `ProtectHome=read-only`, `ReadWritePaths=…/var`,
`Restart=on-failure`. Pour plusieurs workers : `supreme-worker@2.service`, etc.

## 4. Conteneurs (alternative, non exécutée dans le sandbox)

```bash
docker build -f ops/Dockerfile -t omnibrain-supreme:1.4.0 .
docker compose -f ops/compose.yaml up -d          # api/worker/learn/guardian
docker compose -f ops/compose.yaml run --rm backup
```

Non-root `10001`, `read_only: true`, `no-new-privileges`, volume persistant `/data`,
`HEALTHCHECK` intégré, port publié sur `127.0.0.1` uniquement.
**État vérifié** : YAML validé syntaxiquement ; `docker` absent du sandbox, donc
**aucune image construite ni exécutée ici**. À valider sur la machine cible.

## 5. Sauvegardes

```bash
python3 -m supreme backup                 # crée une sauvegarde vérifiée 0600/0700
python3 -m supreme backup --verify        # intégrité + permissions de toutes
python3 -m supreme backup --prune 7       # SIMULATION : liste ce qui serait retiré
python3 -m supreme backup --prune 7 --apply \
        --confirm 'SUPPRIMER ANCIENNES SAUVEGARDES'   # suppression explicite
```

Chaque sauvegarde contient `supreme.db` (copie à chaud SQLite), `meta.json` et le
catalogue. `integrity_check` est exécuté à la création **et** à la vérification.
Une sauvegarde corrompue n'est **jamais** supprimée par la rétention : elle est
protégée et signalée pour examen. La plus récente est toujours conservée.

Automatisation : `supreme-backup.timer` (quotidien, `Persistent=true`, délai
aléatoire 5 min). Aucune rétention automatique n'est activée par défaut.

## 6. Restauration

```bash
# 1) arrêter les services
./ops/supreme-ctl.sh stop
# 2) lister et vérifier
python3 -m supreme backup --verify
# 3) restaurer (crée automatiquement une copie .pre-restore.db)
./ops/supreme-ctl.sh restore bk-YYYYMMDDTHHMMSS-xxxxxx 'CONFIRMER RESTAURATION'
# 4) contrôler puis redémarrer
python3 -m supreme audit
./ops/supreme-ctl.sh start
```

Une sauvegarde corrompue est refusée. La copie de sécurité `.pre-restore.db`
permet de revenir en arrière ; elle est en `0600`.

## 7. Surveillance

```bash
python3 ops/healthcheck.py --url http://127.0.0.1:8765
python3 ops/healthcheck.py --require-guardian      # échoue si constat bloquant
python3 -m supreme guardian                        # scan ponctuel
python3 -m supreme guardian --findings             # constats ouverts
python3 -m supreme audit                           # audit complet
```

Codes retour : `0` sain, `1` dégradé. Le Guardian couvre secrets versionnés,
permissions des fichiers secrets, intégrité du noyau, dépendances non stdlib,
actions refusées/injections, anomalies budget, doubles exécutions, sauvegardes,
quarantaines, dérive fournisseur, permissions GitHub (opt-in `--allow-github`).

### Après un changement de code légitime

Le Guardian signale `core_file_modified` : c'est attendu. Après revue humaine :

```bash
python3 -m supreme guardian --rebaseline-core \
  --approved-by vous --reason 'livraison 1.4.0' --evidence 'PR #5 / commit <sha>' \
  --confirm 'REVUE HUMAINE EFFECTUEE'
```

Les empreintes précédentes sont journalisées dans `events` : rien n'est perdu.

### Clore un constat

```bash
python3 -m supreme guardian --resolve FND-xxxx \
  --resolution 'analyse et décision' --acknowledged-by vous \
  --confirm 'REVUE HUMAINE EFFECTUEE'
```

## 8. Maintenance courante

| Besoin | Commande |
| --- | --- |
| État global réel | `python3 -m supreme status` |
| Rapport global | `python3 -m supreme report` |
| Régénérer le jeton API | `python3 -m supreme rotate-token` (jamais affiché ; redémarrer `serve`) |
| Vérifier le catalogue | `python3 -m supreme catalog --check` |
| Resynchroniser le registre | `python3 -m supreme sync` |
| Cycle d'apprentissage | `python3 -m supreme learn` |
| Migration de schéma | automatique et additive au démarrage, **après sauvegarde** |

**Migration** : toujours `stop` → `backup` → `start`. Le schéma v4 est additif
(33 tables déclarées) ; aucune table ni colonne n'est supprimée.

## 9. Récupération après incident

| Incident | Conduite |
| --- | --- |
| Worker tué pendant une mission | Le bail expire ; un autre worker reprend via jeton de fencing. Vérifier `status`. |
| Campagne d'activation interrompue | `activation --status`, puis `--run ID` ; un propriétaire vivant n'est jamais dépossédé. |
| Campagne bloquée sur un fournisseur | `activation --respecify ID --new-provider … --confirm 'RECONFIGURER CAMPAGNE' --approved-by vous` |
| Membre en échec qui bloque un palier | `activation --reconcile ID --member AID --resolution … --evidence … --acknowledged-by vous --confirm 'REVUE HUMAINE EFFECTUEE'` (un remplaçant prend sa place, le palier ne rétrécit pas) |
| Agent en quarantaine | Revue humaine puis `activation --release-quarantine AID --evidence … --confirm 'REVUE HUMAINE EFFECTUEE'` ; une nouvelle preuve externe est requise. |
| Réservation budgétaire incertaine | Elle reste exposée. Réconcilier avec la preuve fournisseur avant toute nouvelle tentative payante. |
| Base corrompue | `backup --verify`, puis restauration §6. |
| Constat de sécurité critique | Traiter la cause, puis `--resolve` avec preuve. Ne jamais désactiver le Guardian. |

## 10. Activation progressive réelle (nécessite l'humain)

Guide complet, y compris depuis Android : **`MISTRAL-ENROLLMENT.md`**.
Enrôlement guidé avec test de joignabilité préalable : `./ops/enroll-mistral.sh`.
Budget par palier sans tarif inventé : `python3 ops/budget-plan.py`.

```bash
# 1) clé sans jamais la communiquer dans une conversation
python3 -m supreme providers --connect mistral          # saisie masquée, TTY privé
# 2) découverte GET réelle (gratuite, sans génération)
python3 -m supreme providers --verify mistral
# 3) prix attestés depuis la documentation officielle (HTTPS, ≤30 jours)
python3 -m supreme providers --set-prices mistral --model MODELE \
  --input-per-million X --output-per-million Y --source https://… \
  --confirm 'JE CONFIRME LES PRIX'
# 4) contexte si l'API ne l'expose pas (HTTPS, ≤90 jours)
python3 -m supreme providers --attest-context mistral --model MODELE \
  --context-tokens N --source https://… --confirm 'JE CONFIRME LE CONTEXTE'
# 5) autorisation bornée d'inférence (≤24 h)
python3 -m supreme providers --authorize mistral --budget-usd 0.25 --max-calls 5 \
  --hours 1 --approved-by vous --confirm 'AUTORISER INFERENCE'
# 6) palier pilote
python3 -m supreme activation --prepare 5 --provider mistral
python3 -m supreme activation --run act-XXXX
```

Paliers : **5 → 20 → 60 → 100 → 200 → 400 → 600 → 800 → 960**. Chaque agent exige
sa propre preuve : `external_api` + HTTP 200 + sortie exploitable + permissions +
budget soldé. Un test local ne peut pas activer un agent.

Révocation immédiate : `providers --revoke mistral --confirm 'REVOQUER INFERENCE'`.

## 11. Ce qui exige une autorisation humaine explicite

Connexion d'un fournisseur, attestation de prix/contexte, autorisation d'inférence,
dépense, exposition publique, déploiement cloud, suppression de sauvegardes,
restauration, levée de quarantaine, re-baseline d'intégrité, clôture de constat,
fusion de PR, modification de permissions ou de règles de sécurité.
