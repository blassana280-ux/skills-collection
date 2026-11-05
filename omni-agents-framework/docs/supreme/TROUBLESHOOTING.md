# Dépannage OMNIBRAIN SUPREME

| Symptôme | Cause probable | Solution |
| --- | --- | --- |
| Mission `blocked` « aucun fournisseur IA configuré » | Tâche LLM sans clé | Fournir une clé (action humaine) ou utiliser une tâche outil déterministe |
| `PermissionError` bus « usurpation » | `sender != authenticated_as` | Authentifier l'expéditeur réel ; seul le cerveau peut envoyer pour autrui |
| `PermissionError` bus « hors division » | ACL bus | Passer par le chef de division ou le cerveau central |
| Mémoire `lecture refusée` | ACL niveau/propriétaire | Vérifier le niveau et le propriétaire ; individuel = propriétaire seul |
| Agent reste `validated` non `operational` | Mission représentative LLM différée | Configurer un fournisseur, ou l'agent n'a pas d'outil représentatif hors ligne |
| Catalogue échoue « doublon » | Nom/objectif/tâche dupliqué | Corriger la ligne dans `divisions/divNN.py` |
| CI « catalogue non régénéré » | `catalog/` désynchronisé | `python3 -m supreme catalog` puis commit |
| API 401 sur écriture | Jeton absent/invalide | Fournir `X-API-Token` (voir `var/supreme/api_token.txt`) |
| `backpressure : file saturée` | Trop de tâches simultanées | Réduire la concurrence ou augmenter `queue_limit` |
| Fournisseur `unreachable` | Réseau sortant limité | Vérifier l'accès réseau réel ; le sandbox limite aux hôtes autorisés |

## Journalisation
Événements structurés dans la table `events` (+ export `var/supreme/events.jsonl`),
corrélés aux missions. Secrets rédigés. `/api/trace/{id}` pour la trace complète.

## 1.2.1 — workers, baux, apprentissage, budget
| Symptôme | Cause probable | Action sûre |
| --- | --- | --- |
| HTTP 409 sur `/api/missions/{id}/run` | mission déjà détenue par un worker actif | attendre le worker ou inspecter le bail ; ne pas forcer |
| mission `running` après crash | bail pas encore expiré / worker silencieux | attendre expiration + heartbeat stale ; `worker --once` récupère exclusivement |
| tâche LLM `blocked` après crash | réservation incertaine, risque de double facturation | réconciliation humaine avec preuve fournisseur avant nouvelle tentative |
| `learn` retourne `skipped` | un cycle est déjà actif | inspecter `learn --status` ; ne pas lancer deux ordonnanceurs |
| conseil `unavailable` avec erreurs budget | borne de coût > budget restant / quota central | augmenter quota uniquement avec autorisation, ou réduire modèles/tokens |
| audit exit 1 | catalogue/sécurité/schéma/budget incohérent | lire le JSON sauvegardé, corriger sur branche + tests + PR |
