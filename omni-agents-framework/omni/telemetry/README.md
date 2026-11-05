# `omni/telemetry` — observabilité des vagues (Phase 4.1)

`WaveTelemetry` collecte par agent : vague, durée mesurée, `tokens_in`,
`tokens_out`, statut, verdict, erreur. Le rapport markdown est **toujours
dérivé du JSON** (une seule source de vérité).

```python
from omni.telemetry import WaveTelemetry, write_mission_report
t = WaveTelemetry("mission-1", project_type="fintech")
t.record("backend-api", wave=1, duration_ms=42, tokens_in=100, tokens_out=320)
t.record("revue_adverse", wave=2, status="failed", error="preuve manquante")
json_path, md_path = write_mission_report(t, "var/reports")
```

- `summary()` : totaux, `failure_rate`, vagues, drapeaux des renforts obligatoires.
- `export_json(path)` : JSON trié, reproductible, même pour une vague vide.
- `from_memory(store, mission_id)` : reconstruit la télémétrie depuis `resultats`.
- `run_pipeline(..., artifacts_dir=...)` génère automatiquement les deux fichiers
  par mission (`telemetry-<id>.json`, `rapport-mission-<id>.md`).
