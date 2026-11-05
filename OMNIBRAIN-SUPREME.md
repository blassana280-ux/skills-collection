# 🧠 OMNIBRAIN SUPREME 1000

**Un cerveau central · 20 divisions · 1000 spécialistes · une intelligence collective mesurable.**

Couche multi-agents opérationnelle construite au-dessus du framework OmniBrain V4 existant,
dans `omni-agents-framework/supreme/`. Python stdlib + SQLite, démarrage **gratuit**, sans
service externe requis.

## Démarrage rapide
```bash
cd omni-agents-framework
python3 -m supreme catalog --check        # vérifie 1000 spécialistes + 20 chefs
python3 -m supreme sync                   # registre SQLite
python3 -m supreme evaluate --activate    # valide + active sur preuve réelle
python3 -m supreme serve --port 8765      # API + tableau de bord mobile
python3 -m supreme worker --once          # worker séparé consommant la file (Phase G)
python3 -m supreme audit                  # audit exécutable avec preuves JSON (Phase I)
python3 -m supreme learn                  # cycle d'amélioration contrôlée (PR = humain)
python3 -m supreme providers              # statut fournisseurs (Mistral/Vide prioritaire)
python3 -m unittest discover -s tests     # 318 tests (105 V4 + 213 SUPREME)
```

## État réel (ne pas confondre enregistré et opérationnel)
- **1000 spécialistes** enregistrés et validés (20 divisions × 50) + **20 chefs**.
- **60 agents opérationnels/surveillés** ayant exécuté réellement leur mission représentative.
- **960 agents LLM exécutables** dès qu'un fournisseur est configuré (client HTTP réel,
  Mistral/Vide prioritaire) ; **0 fournisseur connecté** à ce stade → bloqués honnêtement.
- **0 doublon**, 27 champs + 7 évaluations par profil, contrôles automatiques.
- **318 tests verts**, 5 missions réelles exécutées (coût 0.0 USD).
- **Multi-modèles réel** : client HTTP testé (stub local), fallback + budget ; connexion
  sécurisée des clés sans exposition — voir [PROVIDERS.md](omni-agents-framework/docs/supreme/PROVIDERS.md).

## Documentation
- [Audit réel](omni-agents-framework/docs/supreme/AUDIT.md)
- [Architecture (30 composants)](omni-agents-framework/docs/supreme/ARCHITECTURE.md)
- [Catalogue des 1000 agents](omni-agents-framework/supreme/catalog/CATALOG-SUPREME.md)
- [API](omni-agents-framework/docs/supreme/API.md) · [Mémoire](omni-agents-framework/docs/supreme/MEMORY.md) · [Modèles](omni-agents-framework/docs/supreme/MODELS.md) · [**Fournisseurs (connexion sécurisée)**](omni-agents-framework/docs/supreme/PROVIDERS.md)
- [Sécurité](omni-agents-framework/docs/supreme/SECURITY.md) · [Déploiement](omni-agents-framework/docs/supreme/DEPLOYMENT.md) · [Maintenance](omni-agents-framework/docs/supreme/MAINTENANCE.md)
- [Sauvegarde/restauration](omni-agents-framework/docs/supreme/BACKUP-RESTORE.md) · [Dépannage](omni-agents-framework/docs/supreme/TROUBLESHOOTING.md)
- [Matrice des tests](omni-agents-framework/docs/supreme/TEST-MATRIX.md) · [Changelog](omni-agents-framework/docs/supreme/CHANGELOG-SUPREME.md)
- [Suivi durable (reprise)](omni-agents-framework/docs/supreme/CONTINUITY.md)
- [Rapport d'exécution](omni-agents-framework/docs/supreme/EXECUTION-REPORT.md)

## Principes
Réutiliser avant de reconstruire · preuve fraîche obligatoire · moindre privilège · aucune
connexion simulée · aucune valeur fabriquée · activation sur exécution réelle · travail sur
branche dédiée + PR · aucune fusion automatique · aucune dépense sans accord humain.
