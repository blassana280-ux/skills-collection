# CI-EVIDENCE — OmniBrain v4 (sorties réelles, non éditées)

Généré le 2026-11-05T01:58:43+00:00 depuis `omni-agents-framework/`.

| # | Commande | Exit |
| --- | --- | --- |
| 1 | `python3 -m omnibrain validate` | 0 |
| 2 | `python3 tools/generate_agents.py --check` | 0 |
| 3 | `python3 -m unittest discover -s tests 2>&1 | tail -5` | 0 |
| 4 | `python3 scripts/demo-parallele.py 2>&1 | tail -10` | 0 |
| 5 | `python3 tools/benchmark.py --no-write` | 0 |
| 6 | `python3 tools/optimize_prompts.py --iterations 2 --db $TMP/gepa.sqlite3 --journal $TMP/gepa.jsonl` | 0 |
| 7 | `OMNIBRAIN_DB=$TMP/runtime.sqlite3 python3 -m omni.sandbox --max-ticks 1` | 0 |
| 8 | `python3 -m unittest tests.test_v4_integration -v 2>&1 | tail -5` | 0 |

## 1. validate

`$ python3 -m omnibrain validate`

```text
OK — 115 agents et 7 contrats validés
```

## 2. generator --check

`$ python3 tools/generate_agents.py --check`

```text
spécifications chargées : 103 agents
  - cloud-infra            10 agents
  - data-ai                13 agents
  - design-ux              8 agents
  - engineering            17 agents
  - finance-legal          12 agents
  - marketing-growth       10 agents
  - product-delivery       9 agents
  - qa-testing             6 agents
  - security               11 agents
  - west-africa-sectors    7 agents
agents à risque : 17

--check : aucune anomalie
```

## 3. suite 105 tests

`$ python3 -m unittest discover -s tests 2>&1 | tail -5`

```text
.........................................................................................................
----------------------------------------------------------------------
Ran 105 tests in 7.595s

OK
```

## 4. demo vague parallele

`$ python3 scripts/demo-parallele.py 2>&1 | tail -10`

```text
processus parallèles      : 2
  briefs émis au total      : 34 (tous en wave 0)
  agents mobilisés (exemples): 17/115
  agents non mobilisés mais routables sur mots-clés : 98
  contrats d'interface      : {'api-contract': 3, 'data-contract': 2, 'test-plan': 4, 'deployment-plan': 2, 'ui-components': 2, 'security-findings': 3, 'research-dossier': 2}
  temps parallèle           : 0.192s
  temps séquentiel          : 0.306s
  accélération observée     : x1.60

✅ Réseau cohérent : tous les agents sont activables et la vague parallèle fonctionne.
```

## 5. benchmarks 10 taches

`$ python3 tools/benchmark.py --no-write`

```text
{
  "fingerprint": "f1b8ae32bb28bdeb75b6e7714631f6dbbb5269d96c3d671c5777f65675f289ba",
  "gains": {
    "baseline": null,
    "gain_hit_rate_pp": 0.0,
    "gain_latency_pct": 0.0,
    "runs_in_history": 0
  },
  "hit_rate": 1.0,
  "mean_latency_ms": 50.7307,
  "passes": 1,
  "tasks": 10
}
```

## 6. GEPA 2 iterations

`$ python3 tools/optimize_prompts.py --iterations 2 --db $TMP/gepa.sqlite3 --journal $TMP/gepa.jsonl`

```text
{
  "accepted": 1,
  "evidence": {
    "error_types": [],
    "failure_count": 0,
    "missions": 0,
    "recettes": 0,
    "success_rate": 0.0,
    "successes": 0
  },
  "final_score": 0.7,
  "initial_score": 0.0,
  "iterations": 2,
  "journal_path": "$TMP/gepa.jsonl",
  "project_type": "generic"
}
```

## 7. runtime service

`$ OMNIBRAIN_DB=$TMP/runtime.sqlite3 python3 -m omni.sandbox --max-ticks 1`

```text
runtime arrêté : 0 mission(s) traitée(s), 3 entrées de log
```

## 8. integration v4

`$ python3 -m unittest tests.test_v4_integration -v 2>&1 | tail -5`

```text
----------------------------------------------------------------------
Ran 1 test in 0.596s

OK
```
