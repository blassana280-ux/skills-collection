# 🧠 OMNIBRAIN SUPREME 1000

**Version SUPREME : 1.4.0** · Un cerveau central · 20 divisions · 1000 spécialistes · une intelligence collective mesurable.

Couche multi-agents construite au-dessus du framework OmniBrain V4 existant, dans
`skills-collection/omni-agents-framework/supreme/`. Python stdlib + SQLite, démarrage **gratuit**,
sans service externe requis. Le paquet V4 historique `omnibrain-framework` reste à `1.0.0` ;
la version de livraison de la couche SUPREME est **1.4.0**.

## Démarrage rapide
Depuis `skills-collection/omni-agents-framework/` :
```bash
python3 -m supreme catalog --check        # vérifie 1000 spécialistes + 20 chefs
python3 -m supreme sync                   # registre SQLite
python3 -m supreme evaluate --activate    # valide + active sur preuve réelle
python3 -m supreme serve --port 8765 --host 0.0.0.0   # API + dashboard mobile (preview/local)
python3 -m supreme worker --once --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme learn --periodic --interval 300 --max-cycles 10  # apprentissage périodique contrôlé
python3 -m supreme learn --status         # état ordonnanceur / erreurs / derniers rapports
python3 -m supreme audit                  # audit exécutable avec preuves JSON
python3 -m supreme providers --status     # statut fournisseurs sans secret (Mistral/Vide prioritaire)
python3 -m supreme activation --status    # paliers 5→20→60→100→…→960, campagnes, quarantaine
python3 -m unittest discover -s tests     # 378 découverts (105 V4 + 273 SUPREME), 1 opt-in réel ignoré sans clé
```
Arrêt propre des workers et de l'apprentissage périodique : `SIGINT` / `SIGTERM`.

## État réel (ne pas confondre enregistré et opérationnel)
- **1020 profils enregistrés** : 1000 spécialistes (20×50) + 20 chefs.
- Statuts SQLite réels : `registered=0`, `validated=960`, `monitored=60`, `operational=0`.
- **60 agents réellement opérationnels en local** sur preuve d'exécution déterministe, marqués `monitored`.
- **960 agents LLM en attente** : exécutables techniquement, mais **0 fournisseur IA réel connecté**
  tant qu'une clé et un appel API réel réussi ne sont pas disponibles.
- **0 cloud déployé** ; le serveur local/preview n'est pas un déploiement cloud.
- **0 doublon**, 27 champs + 7 évaluations par profil, contrôles automatiques.
- **378 tests découverts** : 105 V4/non-SUPREME + 273 SUPREME ; **377 locaux exécutés verts + 1 test réel opt-in ignoré**.
- Dernière mesure locale : 10 missions `completed`, 32 tâches `done`, coût fournisseur 0 USD.
- **Multi-modèles** : client HTTP testé contre stub local, réservation budgétaire avant appel,
  fallback, conseil sans contournement du routeur. Voir
  [PROVIDERS.md](omni-agents-framework/docs/supreme/PROVIDERS.md).

## Activation intelligence réelle 1.4.0
- **Mistral/Vide prioritaire** : adaptateur officiel, découverte de modèles, clé via terminal privé/env/fichier 0600,
  autorisation d'inférence humaine bornée, prix attestés, quotas, erreurs/délais, POST non rejoué automatiquement.
- **Activation progressive** : 5 → 20 → 60 → 100 → … → 960 agents LLM ; chaque agent exige une preuve
  `external_api` réussie et exploitable ; échec isolé en quarantaine ; pas de saut 60→1020.
- **Conseil/intelligence** : missions multi-spécialités cross-division, preuves référencées, second avis borné,
  `needs_review` si non vérifiable, mémoire avec provenance/contradictions, apprentissage mesuré avant/après.
- **Dashboard mobile** : fournisseurs, modèles, activation, décisions, performances/division, coûts/exposition, alertes.
- **État réel** : connecteurs écrits et testés localement ; **aucun fournisseur connecté, aucune inférence externe,
  aucune campagne réelle, aucune dépense** tant qu'une clé privée et une autorisation ne sont pas fournies.

## Durcissement 1.2.1 conservé
- Workers multi-processus : propriétaire, bail expirant, heartbeat, fencing, récupération exclusive,
  idempotence des résultats, reprise après `SIGKILL`, arrêt propre `SIGTERM`.
- Apprentissage périodique : fréquence configurable, verrou anti-double-cycle, rapports persistés,
  surveillance des erreurs, interruption propre et reprise.
- Budget strict : réservations atomiques avant appel, quotas centraux, limites tokens,
  comptabilisation réelle, appels interrompus conservés prudemment.
- Documentation et PR #5 synchronisées ; `master` intégré par merge propre, aucune fusion de PR.

## Documentation
- [Audit réel](omni-agents-framework/docs/supreme/AUDIT.md)
- [Architecture](omni-agents-framework/docs/supreme/ARCHITECTURE.md)
- [Catalogue des 1000 agents](omni-agents-framework/supreme/catalog/CATALOG-SUPREME.md)
- [API](omni-agents-framework/docs/supreme/API.md) · [Mémoire](omni-agents-framework/docs/supreme/MEMORY.md) · [Modèles](omni-agents-framework/docs/supreme/MODELS.md) · [Fournisseurs](omni-agents-framework/docs/supreme/PROVIDERS.md)
- [Sécurité](omni-agents-framework/docs/supreme/SECURITY.md) · [Déploiement](omni-agents-framework/docs/supreme/DEPLOYMENT.md) · [Maintenance](omni-agents-framework/docs/supreme/MAINTENANCE.md)
- [Sauvegarde/restauration](omni-agents-framework/docs/supreme/BACKUP-RESTORE.md) · [Dépannage](omni-agents-framework/docs/supreme/TROUBLESHOOTING.md)
- [Matrice des tests](omni-agents-framework/docs/supreme/TEST-MATRIX.md) · [Changelog](omni-agents-framework/docs/supreme/CHANGELOG-SUPREME.md)
- [Suivi durable](omni-agents-framework/docs/supreme/CONTINUITY.md) · [Rapport d'exécution](omni-agents-framework/docs/supreme/EXECUTION-REPORT.md) · [Écosystème](omni-agents-framework/docs/supreme/ECOSYSTEM.md)

## Principes
Réutiliser avant de reconstruire · preuve fraîche obligatoire · moindre privilège · aucune
connexion simulée · aucune valeur fabriquée · activation sur exécution réelle · branche dédiée + PR ·
aucune fusion automatique · aucune dépense ni exposition publique sans accord humain.
