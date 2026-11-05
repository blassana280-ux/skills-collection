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
