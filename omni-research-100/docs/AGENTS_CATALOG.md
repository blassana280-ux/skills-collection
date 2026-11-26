# Catalogue des 100 agents — OMNI-RESEARCH 100

Généré depuis `scripts/gen_profiles.py`. Chaque agent possède un handler Python distinct, des outils autorisés, une configuration, un schéma d'entrée (`INPUT_SCHEMA`) et un schéma de sortie (`OUTPUT_SCHEMA`).

Légende : **OPÉRATIONNELLE ET TESTÉE** = exécuté avec succès par `tests/test_agents_all_100.py` ; **IMPLÉMENTÉE MAIS NON VÉRIFIÉE** = code présent, test non encore joué.

| ID | Division | Agent | Noyau | Outils | État |
|---|---|---|---|---|---|
| `WEB-01` | Web Intelligence | SERP Result Miner | `keyword` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `WEB-02` | Web Intelligence | Domain Authority Mapper | `domains` | stats, graph | OPÉRATIONNELLE ET TESTÉE |
| `WEB-03` | Web Intelligence | Crawl Frontier Planner | `clusters` | stats, graph | OPÉRATIONNELLE ET TESTÉE |
| `WEB-04` | Web Intelligence | Link Graph Analyst | `graph` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `WEB-05` | Web Intelligence | Page Freshness Auditor | `recency` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `WEB-06` | Web Intelligence | Web Archive Hunter | `timeline` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `WEB-07` | Web Intelligence | Sitemap & Robots Reader | `schema` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `WEB-08` | Web Intelligence | Multilingual Web Scout | `language` | stats | OPÉRATIONNELLE ET TESTÉE |
| `WEB-09` | Web Intelligence | Landing Page Comparator | `length` | stats | OPÉRATIONNELLE ET TESTÉE |
| `WEB-10` | Web Intelligence | Broken Reference Detector | `entities` | verify, stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-01` | Deep Research | Question Decomposer | `claims` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-02` | Deep Research | Literature Mapper | `coverage` | stats, graph | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-03` | Deep Research | Long-form Evidence Reader | `length` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-04` | Deep Research | Argument Chain Builder | `cooccurrence` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-05` | Deep Research | Assumption Identifier | `hedges` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-06` | Deep Research | Research Gap Detector | `gaps` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-07` | Deep Research | Methodology Critic | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-08` | Deep Research | Chronology Builder | `dates` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-09` | Deep Research | Cross-domain Bridge | `correlation` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `DEEP-10` | Deep Research | Open Question Tracker | `quotes` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-01` | News Intelligence | Breaking Event Tracker | `dates` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-02` | News Intelligence | Timeline Reconstructor | `timeline` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-03` | News Intelligence | Wire Service Comparator | `domains` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-04` | News Intelligence | Headline Framing Analyst | `ngrams` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-05` | News Intelligence | Recency Scorer | `recency` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-06` | News Intelligence | Local News Scanner | `entities` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-07` | News Intelligence | Press Release Detector | `stance` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-08` | News Intelligence | Event Deduplicator | `clusters` | stats | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-09` | News Intelligence | Quote Attribution Checker | `quotes` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `NEWS-10` | News Intelligence | Correction & Update Watcher | `negations` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-01` | Scientific Research | Abstract Scanner | `claims` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-02` | Scientific Research | Methodology Extractor | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-03` | Scientific Research | Sample Size Auditor | `numbers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-04` | Scientific Research | Statistical Result Reader | `compare` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-05` | Scientific Research | Citation Network Analyst | `graph` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-06` | Scientific Research | Preprint Detector | `versions` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-07` | Scientific Research | Reproducibility Checker | `gaps` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `SCI-08` | Scientific Research | Peer Review Status Reader | `credibility` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `SCI-09` | Scientific Research | Conflict of Interest Scanner | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SCI-10` | Scientific Research | Evidence Grader | `provenance` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-01` | Technology Intelligence | Release Note Reader | `versions` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-02` | Technology Intelligence | Version Tracker | `regex` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `TECH-03` | Technology Intelligence | API Surface Comparator | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-04` | Technology Intelligence | Benchmark Interpreter | `numbers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-05` | Technology Intelligence | Dependency Graph Reader | `graph` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-06` | Technology Intelligence | Security Advisory Scanner | `regex` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `TECH-07` | Technology Intelligence | License Classifier | `license` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-08` | Technology Intelligence | Changelog Differ | `contradictions` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-09` | Technology Intelligence | Adoption Signal Reader | `numbers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `TECH-10` | Technology Intelligence | Deprecation Watcher | `negations` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-01` | Open Source Intelligence | Repository Metadata Reader | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-02` | Open Source Intelligence | Commit Activity Analyst | `dates` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-03` | Open Source Intelligence | Maintainer Mapper | `entities` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-04` | Open Source Intelligence | Issue Themes Extractor | `ngrams` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-05` | Open Source Intelligence | Fork & Star Signals | `outliers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-06` | Open Source Intelligence | Package Registry Checker | `versions` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-07` | Open Source Intelligence | Public Record Cross-check | `provenance` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-08` | Open Source Intelligence | Domain Chronology Reader | `timeline` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-09` | Open Source Intelligence | Geolocation Mention Extractor | `entities` | stats | OPÉRATIONNELLE ET TESTÉE |
| `OSINT-10` | Open Source Intelligence | Source Provenance Tracer | `credibility` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `SOC-01` | Social Intelligence | Trend Signal Detector | `ngrams` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-02` | Social Intelligence | Post Cluster Analyst | `clusters` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-03` | Social Intelligence | Hashtag Co-occurrence | `cooccurrence` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-04` | Social Intelligence | Sentiment Lexicon Scorer | `stance` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-05` | Social Intelligence | Bot Pattern Heuristic | `outliers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-06` | Social Intelligence | Influencer Reach Estimator | `numbers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-07` | Social Intelligence | Discourse Frame Mapper | `coverage` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-08` | Social Intelligence | Viral Timeline Builder | `timeline` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-09` | Social Intelligence | Community Overlap | `graph` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `SOC-10` | Social Intelligence | Rumor Propagation Tracer | `hedges` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-01` | Fact Verification | Claim Extractor | `claims` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-02` | Fact Verification | Independent Corroborator | `domains` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `FACT-03` | Fact Verification | Primary Source Seeker | `provenance` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `FACT-04` | Fact Verification | Numeric Consistency Checker | `compare` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-05` | Fact Verification | Date Consistency Checker | `dates` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-06` | Fact Verification | Quote Verifier | `quotes` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `FACT-07` | Fact Verification | Context Omission Detector | `hedges` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-08` | Fact Verification | Misleading Headline Detector | `stance` | stats | OPÉRATIONNELLE ET TESTÉE |
| `FACT-09` | Fact Verification | Verdict Aggregator | `contradictions` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `FACT-10` | Fact Verification | Evidence Coverage Auditor | `gaps` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-01` | Data Intelligence | Dataset Metadata Reader | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-02` | Data Intelligence | Unit Normalizer | `numbers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-03` | Data Intelligence | Time Series Spotter | `timeline` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-04` | Data Intelligence | Outlier Detector | `outliers` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-05` | Data Intelligence | Missing Data Auditor | `coverage` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-06` | Data Intelligence | Schema Inference | `schema` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-07` | Data Intelligence | Statistical Summary | `length` | stats | OPÉRATIONNELLE ET TESTÉE |
| `DATA-08` | Data Intelligence | Correlation Signal Reader | `correlation` | stats, graph | OPÉRATIONNELLE ET TESTÉE |
| `DATA-09` | Data Intelligence | Data Source Lineage | `provenance` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `DATA-10` | Data Intelligence | Reproducibility Pack Builder | `gaps` | stats, memory | OPÉRATIONNELLE ET TESTÉE |
| `SYN-01` | Research Synthesis | Theme Clusterer | `clusters` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SYN-02` | Research Synthesis | Consensus Builder | `claims` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SYN-03` | Research Synthesis | Conflict Arbitrator | `contradictions` | stats, graph | OPÉRATIONNELLE ET TESTÉE |
| `SYN-04` | Research Synthesis | Citation Formatter | `graph` | graph, stats | OPÉRATIONNELLE ET TESTÉE |
| `SYN-05` | Research Synthesis | Executive Summary Writer | `length` | stats, llm | OPÉRATIONNELLE ET TESTÉE |
| `SYN-06` | Research Synthesis | Limitations Writer | `gaps` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SYN-07` | Research Synthesis | Confidence Calibrator | `credibility` | stats, verify | OPÉRATIONNELLE ET TESTÉE |
| `SYN-08` | Research Synthesis | Evidence Table Builder | `coverage` | stats | OPÉRATIONNELLE ET TESTÉE |
| `SYN-09` | Research Synthesis | Narrative Coherence Editor | `hedges` | stats, llm | OPÉRATIONNELLE ET TESTÉE |
| `SYN-10` | Research Synthesis | Final Report Auditor | `provenance` | stats, verify, memory | OPÉRATIONNELLE ET TESTÉE |

## Divisions

- **WEB — Web Intelligence** : 10 agents (`WEB-01` à `WEB-10`)
- **DEEP — Deep Research** : 10 agents (`DEEP-01` à `DEEP-10`)
- **NEWS — News Intelligence** : 10 agents (`NEWS-01` à `NEWS-10`)
- **SCI — Scientific Research** : 10 agents (`SCI-01` à `SCI-10`)
- **TECH — Technology Intelligence** : 10 agents (`TECH-01` à `TECH-10`)
- **OSINT — Open Source Intelligence** : 10 agents (`OSINT-01` à `OSINT-10`)
- **SOC — Social Intelligence** : 10 agents (`SOC-01` à `SOC-10`)
- **FACT — Fact Verification** : 10 agents (`FACT-01` à `FACT-10`)
- **DATA — Data Intelligence** : 10 agents (`DATA-01` à `DATA-10`)
- **SYN — Research Synthesis** : 10 agents (`SYN-01` à `SYN-10`)
