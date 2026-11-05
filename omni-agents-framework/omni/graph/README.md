# `omni/graph` — workflows critiques déterministes (Phase 3.1)

Graphe d'état type LangGraph **sans dépendance externe** : nœuds déclarés,
arêtes explicites, ordre topologique stable, cycles rejetés, transitions
tracées dans `GraphState.history`.

```
spec → implementation → revue_adverse → tests(qa) → verification(expert risque)
```

- `revue_adverse`, `tests`, `verification` sont **protégés** :
  `remove_node()` lève `ProtectedNodeError` (renforts jamais évincés).
- Gates `human-in-the-loop` après la revue adverse et à la vérification :
  sans `human_approvals[node] = True`, le graphe **s'arrête**, verdict
  `NEEDS WORK`, `pending_human=True`, escalade datée vers **Lassana**.
- Gates techniques : spécification non vide, aucun placeholder/secret détecté
  par la revue, suite de tests `OK`.

```python
from omni.graph import build_pipeline, run_pipeline

result = run_pipeline(
    "Durcir la CI", project_type="devops",
    approvals={"revue_adverse": True, "verification": True},
    artifacts_dir="var/reports",
)
result.state.verdict                  # PASS
result.telemetry_json_path            # JSON de télémétrie
result.report_md_path                 # rapport markdown dérivé du JSON
```

Le runner de tests, le sandbox et le store sont injectables : aucun réseau,
aucun provider simulé, aucune approbation implicite.
