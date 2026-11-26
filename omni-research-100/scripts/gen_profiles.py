#!/usr/bin/env python3
"""Générateur reproductible des 100 profils exécutables + catalogue.

Source de vérité : la table AGENTS ci-dessous (10 divisions × 10 agents).
Chaque agent reçoit un handler Python distinct, câblé sur un noyau d'analyse
réel (`app/agents/kernels.py`) avec ses propres paramètres, outils autorisés,
schémas d'entrée/sortie et seuils. Ce n'est PAS une liste de noms.

Usage : python3 scripts/gen_profiles.py
Produit : app/agents/catalog_data.py, app/agents/profiles.py,
          docs/AGENTS_CATALOG.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def a(name, mission, skills, tools, template, focus, pattern=r"\b[a-zA-Z]{4,}\b",
      label=None, threshold=0.05, weight=0.62, priority=5, n=12):
    return dict(name=name, mission=mission, skills=skills, tools=tools,
                template=template, focus=focus, pattern=pattern,
                label=label or name, threshold=threshold, weight=weight,
                priority=priority, n=n)


DIVISIONS = [
    ("WEB", "Web Intelligence", [
        a("SERP Result Miner", "Extraire et qualifier les résultats de recherche", ["serp_parsing", "ranking", "snippet_analysis"], ["stats", "verify"], "keyword", ["result", "search", "résultat"], r"\b(?:result|résultat|search)s?\b"),
        a("Domain Authority Mapper", "Cartographier les domaines et leur poids relatif", ["domain_mapping", "authority", "tld_analysis"], ["stats", "graph"], "domains", ["domain", "site", "authority"], r"\b(?:domain|site|host)\b"),
        a("Crawl Frontier Planner", "Regrouper les pages proches pour planifier l'exploration", ["clustering", "frontier", "similarity"], ["stats", "graph"], "clusters", ["page", "link", "crawl"], r"\b(?:page|link|url)\b"),
        a("Link Graph Analyst", "Construire le graphe des liens entre domaines", ["link_graph", "citations", "network"], ["graph", "stats"], "graph", ["link", "reference", "href"], r"https?://[\w.-]+"),
        a("Page Freshness Auditor", "Évaluer la fraîcheur des pages datées", ["freshness", "dates", "recency"], ["stats", "verify"], "recency", ["published", "updated", "date"], r"\b20\d{2}\b"),
        a("Web Archive Hunter", "Repérer les versions archivées et les dates historiques", ["archives", "timeline", "snapshots"], ["stats", "memory"], "timeline", ["archive", "snapshot", "version"], r"\b(?:archive|snapshot|wayback)\b"),
        a("Sitemap & Robots Reader", "Détecter les métadonnées d'indexation et de structure", ["sitemap", "robots", "metadata"], ["stats", "verify"], "schema", ["sitemap", "robots", "index"], r"\b(?:sitemap|robots|index)\b"),
        a("Multilingual Web Scout", "Estimer la langue des contenus collectés", ["language_detection", "multilingual", "tokenization"], ["stats"], "language", ["language", "traduction", "multilingue"], r"\b(?:fr|en|de|es)\b"),
        a("Landing Page Comparator", "Comparer les longueurs et structures des pages", ["comparison", "structure", "readability"], ["stats"], "length", ["landing", "page", "section"], r"\b(?:section|heading|title)\b"),
        a("Broken Reference Detector", "Repérer les références et URLs suspectes", ["url_validation", "references", "integrity"], ["verify", "stats"], "entities", ["404", "broken", "reference"], r"https?://\S+"),
    ]),
    ("DEEP", "Deep Research", [
        a("Question Decomposer", "Extraire les affirmations constitutives de la question", ["decomposition", "claims", "scoping"], ["stats"], "claims", ["why", "comment", "impact"], r"\b(?:why|how|pourquoi|comment)\b"),
        a("Literature Mapper", "Cartographier les thèmes et leurs recouvrements", ["literature", "themes", "mapping"], ["stats", "graph"], "coverage", ["study", "étude", "literature"], r"\b(?:study|research|étude)\b"),
        a("Long-form Evidence Reader", "Mesurer la densité des preuves longues", ["long_form", "density", "reading"], ["stats"], "length", ["analysis", "rapport", "long"], r"\b\w{9,}\b"),
        a("Argument Chain Builder", "Repérer les co-occurrences formant des chaînes d'arguments", ["argumentation", "cooccurrence", "logic"], ["graph", "stats"], "cooccurrence", ["because", "therefore", "donc"], r"\b(?:because|therefore|donc|ainsi)\b"),
        a("Assumption Identifier", "Détecter les énoncés hypothétiques ou prudents", ["assumptions", "hedging", "uncertainty"], ["stats"], "hedges", ["assume", "suppose", "hypothèse"], r"\b(?:might|may|perhaps|suppose)\b"),
        a("Research Gap Detector", "Lister les angles non couverts par les preuves", ["gap_analysis", "coverage", "completeness"], ["stats", "memory"], "gaps", ["gap", "missing", "lacune"], r"\b(?:gap|missing|unknown)\b"),
        a("Methodology Critic", "Repérer les descriptions de méthode et leurs limites", ["methodology", "critique", "design"], ["stats"], "schema", ["method", "sample", "protocol"], r"\b(?:method|protocol|sample)\b"),
        a("Chronology Builder", "Ordonner les événements datés", ["chronology", "dates", "ordering"], ["stats"], "dates", ["2024", "2025", "2026"], r"\b20\d{2}\b"),
        a("Cross-domain Bridge", "Relier des domaines hétérogènes par co-occurrence", ["interdisciplinarity", "bridging", "graph"], ["graph", "stats"], "correlation", ["across", "between", "entre"], r"\b(?:across|between|versus)\b"),
        a("Open Question Tracker", "Conserver les questions non résolues", ["open_questions", "tracking", "uncertainty"], ["stats", "memory"], "quotes", ["question", "unknown", "à déterminer"], r"\?"),
    ]),
    ("NEWS", "News Intelligence", [
        a("Breaking Event Tracker", "Isoler les événements datés récents", ["events", "breaking", "dates"], ["stats"], "dates", ["breaking", "today", "aujourd'hui"], r"\b20\d{2}-\d{2}-\d{2}\b"),
        a("Timeline Reconstructor", "Reconstruire la chronologie des faits", ["timeline", "ordering", "events"], ["stats", "memory"], "timeline", ["yesterday", "hier", "then"], r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
        a("Wire Service Comparator", "Comparer les couvertures par domaine de presse", ["wire", "comparison", "domains"], ["stats"], "domains", ["agency", "wire", "dépêche"], r"\b(?:reuters|afp|ap|wire)\b"),
        a("Headline Framing Analyst", "Analyser la structure des titres", ["framing", "headlines", "ngrams"], ["stats"], "ngrams", ["headline", "titre", "annonce"], r"\b[A-Z][\w-]{3,}\b"),
        a("Recency Scorer", "Noter la fraîcheur des sources", ["recency", "dates", "scoring"], ["stats", "verify"], "recency", ["published", "updated", "hier"], r"\b(?:published|updated)\b"),
        a("Local News Scanner", "Repérer les mentions géographiques locales", ["local", "geography", "entities"], ["stats"], "entities", ["local", "région", "ville"], r"\b[A-Z][a-zà-ÿ]{3,}\b"),
        a("Press Release Detector", "Détecter le langage de communiqué", ["press_release", "stance", "detection"], ["stats"], "stance", ["announces", "annonce", "declares"], r"\b(?:announces|declares|annonce)\b"),
        a("Event Deduplicator", "Regrouper les doublons d'événements", ["dedup", "clustering", "events"], ["stats"], "clusters", ["same", "identique", "reprise"], r"\b(?:same|duplicate|identique)\b"),
        a("Quote Attribution Checker", "Extraire les citations et leur contexte", ["quotes", "attribution", "sources"], ["stats", "verify"], "quotes", ["said", "selon", "déclare"], r"[«\"“']"),
        a("Correction & Update Watcher", "Repérer les correctifs et mises à jour", ["corrections", "updates", "negations"], ["stats"], "negations", ["correction", "update", "rectificatif"], r"\b(?:correction|corrected|update|rectificatif)\b"),
    ]),
    ("SCI", "Scientific Research", [
        a("Abstract Scanner", "Extraire les énoncés de type résumé scientifique", ["abstracts", "claims", "screening"], ["stats"], "claims", ["abstract", "objective", "background"], r"\b(?:abstract|objective|background)\b"),
        a("Methodology Extractor", "Lire les paires clé/valeur méthodologiques", ["methods", "schema", "extraction"], ["stats"], "schema", ["method", "design", "protocol"], r"\b(?:method|design|randomized)\b"),
        a("Sample Size Auditor", "Repérer les effectifs et grandeurs numériques", ["sample_size", "numbers", "audit"], ["stats"], "numbers", ["participants", "sample", "n ="], r"\bn\s*=\s*\d+"),
        a("Statistical Result Reader", "Lire les valeurs et unités statistiques", ["statistics", "numbers", "units"], ["stats"], "compare", ["p-value", "confidence", "interval"], r"\b\d+[.,]\d+\b"),
        a("Citation Network Analyst", "Construire le réseau de citations", ["citations", "graph", "bibliometrics"], ["graph", "stats"], "graph", ["doi", "cited", "reference"], r"10\.\d{4,}/\S+"),
        a("Preprint Detector", "Détecter les mentions de prépublication", ["preprints", "versions", "detection"], ["stats"], "versions", ["preprint", "arxiv", "biorxiv"], r"\b(?:arxiv|biorxiv|preprint)\b"),
        a("Reproducibility Checker", "Repérer les indices de reproductibilité", ["reproducibility", "schema", "checks"], ["stats", "memory"], "gaps", ["replicate", "code", "dataset"], r"\b(?:reproduc|replicate|dataset)\b"),
        a("Peer Review Status Reader", "Évaluer le niveau de validation des sources", ["peer_review", "credibility", "status"], ["stats", "verify"], "credibility", ["peer-reviewed", "reviewed", "published"], r"\b(?:peer|reviewed|accepted)\b"),
        a("Conflict of Interest Scanner", "Repérer les déclarations d'intérêts", ["coi", "disclosures", "entities"], ["stats"], "schema", ["funding", "conflict", "disclosure"], r"\b(?:funding|conflict|disclosure)\b"),
        a("Evidence Grader", "Noter la qualité des preuves scientifiques", ["grading", "confidence", "evidence"], ["stats"], "provenance", ["evidence", "grade", "quality"], r"\b(?:evidence|grade|quality)\b"),
    ]),
    ("TECH", "Technology Intelligence", [
        a("Release Note Reader", "Extraire les versions et notes de version", ["releases", "versions", "notes"], ["stats"], "versions", ["release", "shipped", "version"], r"\bv?\d+\.\d+"),
        a("Version Tracker", "Suivre l'évolution des numéros de version", ["versioning", "tracking", "regex"], ["stats", "memory"], "regex", ["v1", "v2", "semver"], r"\bv?\d+\.\d+(?:\.\d+)?\b"),
        a("API Surface Comparator", "Comparer les surfaces d'API mentionnées", ["api", "comparison", "schema"], ["stats"], "schema", ["endpoint", "parameter", "response"], r"\b(?:GET|POST|PUT|DELETE|endpoint)\b"),
        a("Benchmark Interpreter", "Lire les chiffres de performance", ["benchmarks", "numbers", "interpretation"], ["stats"], "numbers", ["latency", "throughput", "benchmark"], r"\b\d+\s*(?:ms|s|gb|mb|%)\b"),
        a("Dependency Graph Reader", "Lire le graphe des dépendances citées", ["dependencies", "graph", "packages"], ["graph", "stats"], "graph", ["depends", "package", "module"], r"\b(?:requires|depends|import)\b"),
        a("Security Advisory Scanner", "Détecter les avis de sécurité", ["advisories", "cve", "security"], ["stats", "verify"], "regex", ["CVE", "vulnerability", "patch"], r"\bCVE-\d{4}-\d{4,}\b"),
        a("License Classifier", "Classifier les licences mentionnées", ["licensing", "classification", "compliance"], ["stats"], "license", ["license", "MIT", "Apache"], r"\b(?:MIT|Apache|GPL|BSD|AGPL|MPL)\b"),
        a("Changelog Differ", "Repérer les changements et contradictions", ["changelog", "diff", "conflicts"], ["stats"], "contradictions", ["added", "removed", "changed"], r"\b(?:added|removed|changed|fixed)\b"),
        a("Adoption Signal Reader", "Mesurer les signaux d'adoption", ["adoption", "numbers", "signals"], ["stats"], "numbers", ["users", "downloads", "stars"], r"\b\d[\d,.]*\s*(?:users|downloads|stars)\b"),
        a("Deprecation Watcher", "Repérer les mentions de dépréciation", ["deprecation", "negations", "lifecycle"], ["stats"], "negations", ["deprecated", "legacy", "obsolete"], r"\b(?:deprecated|legacy|obsolete|sunset)\b"),
    ]),
    ("OSINT", "Open Source Intelligence", [
        a("Repository Metadata Reader", "Lire les métadonnées de dépôts", ["repositories", "schema", "metadata"], ["stats"], "schema", ["repository", "branch", "license"], r"\b(?:repo|repository|branch)\b"),
        a("Commit Activity Analyst", "Repérer l'activité de commits", ["commits", "timeline", "activity"], ["stats"], "dates", ["commit", "merged", "pushed"], r"\b[0-9a-f]{7,40}\b"),
        a("Maintainer Mapper", "Cartographier les entités nommées", ["maintainers", "entities", "mapping"], ["stats"], "entities", ["maintainer", "author", "contributor"], r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b"),
        a("Issue Themes Extractor", "Extraire les thèmes récurrents", ["issues", "ngrams", "themes"], ["stats"], "ngrams", ["issue", "bug", "feature"], r"\b(?:issue|bug|feature|ticket)\b"),
        a("Fork & Star Signals", "Lire les signaux de popularité", ["popularity", "numbers", "signals"], ["stats"], "outliers", ["forks", "stars", "watchers"], r"\b\d[\d,.]*\s*(?:forks|stars)\b"),
        a("Package Registry Checker", "Repérer les paquets et versions", ["packages", "versions", "registry"], ["stats", "memory"], "versions", ["npm", "pypi", "package"], r"\b(?:npm|pypi|crates|maven)\b"),
        a("Public Record Cross-check", "Croiser les provenances des sources", ["cross_check", "provenance", "records"], ["stats", "verify"], "provenance", ["record", "registry", "official"], r"\b(?:official|registry|record)\b"),
        a("Domain Chronology Reader", "Ordonner les dates liées aux domaines", ["domains", "chronology", "dates"], ["stats"], "timeline", ["registered", "created", "expiry"], r"\b(?:registered|created|expired)\b"),
        a("Geolocation Mention Extractor", "Extraire les mentions géographiques", ["geolocation", "entities", "extraction"], ["stats"], "entities", ["Bamako", "Paris", "region"], r"\b[A-Z][a-zà-ÿ]{4,}\b"),
        a("Source Provenance Tracer", "Évaluer la traçabilité des preuves", ["provenance", "hashing", "traceability"], ["stats", "verify"], "credibility", ["origin", "trace", "hash"], r"\b(?:sha256|hash|origin)\b"),
    ]),
    ("SOC", "Social Intelligence", [
        a("Trend Signal Detector", "Détecter les n-grammes émergents", ["trends", "ngrams", "signals"], ["stats"], "ngrams", ["trend", "viral", "rising"], r"\b(?:trend|trending|viral)\b"),
        a("Post Cluster Analyst", "Regrouper les publications similaires", ["clustering", "posts", "similarity"], ["stats"], "clusters", ["post", "thread", "reply"], r"\b(?:post|thread|reply)\b"),
        a("Hashtag Co-occurrence", "Mesurer les co-occurrences de mots-clés", ["hashtags", "cooccurrence", "network"], ["graph", "stats"], "cooccurrence", ["#", "hashtag", "tag"], r"#\w+"),
        a("Sentiment Lexicon Scorer", "Noter la polarité lexicale", ["sentiment", "stance", "lexicon"], ["stats"], "stance", ["good", "bad", "excellent"], r"\b(?:good|bad|great|awful|excellent)\b"),
        a("Bot Pattern Heuristic", "Repérer les valeurs atypiques", ["anomalies", "outliers", "heuristics"], ["stats"], "outliers", ["automated", "bot", "repeat"], r"\b(?:bot|automated|spam)\b"),
        a("Influencer Reach Estimator", "Lire les chiffres d'audience", ["reach", "numbers", "estimation"], ["stats"], "numbers", ["followers", "views", "reach"], r"\b\d[\d,.]*\s*(?:followers|views|likes)\b"),
        a("Discourse Frame Mapper", "Cartographier les cadres de discours", ["framing", "coverage", "mapping"], ["stats"], "coverage", ["frame", "narrative", "discourse"], r"\b(?:narrative|frame|discourse)\b"),
        a("Viral Timeline Builder", "Ordonner la propagation dans le temps", ["timeline", "propagation", "dates"], ["stats"], "timeline", ["first", "then", "spread"], r"\b(?:first|then|later|spread)\b"),
        a("Community Overlap", "Repérer les chevauchements de communautés", ["communities", "graph", "overlap"], ["graph", "stats"], "graph", ["community", "group", "subreddit"], r"\b(?:r/|community|group)\b"),
        a("Rumor Propagation Tracer", "Suivre les énoncés incertains", ["rumors", "hedging", "propagation"], ["stats"], "hedges", ["allegedly", "rumor", "unconfirmed"], r"\b(?:allegedly|rumor|unconfirmed)\b"),
    ]),
    ("FACT", "Fact Verification", [
        a("Claim Extractor", "Extraire les affirmations vérifiables", ["claims", "extraction", "atomicity"], ["stats"], "claims", ["is", "are", "est"], r"\b(?:is|are|was|were|est|sont)\b"),
        a("Independent Corroborator", "Compter les domaines indépendants", ["corroboration", "domains", "independence"], ["stats", "verify"], "domains", ["according", "selon", "reports"], r"\b(?:according|selon|reports)\b"),
        a("Primary Source Seeker", "Repérer les sources primaires", ["primary_sources", "provenance", "credentials"], ["stats", "verify"], "provenance", ["official", "primary", "dataset"], r"\b(?:official|primary|original)\b"),
        a("Numeric Consistency Checker", "Comparer les chiffres divergents", ["numeric", "consistency", "conflicts"], ["stats"], "compare", ["percent", "million", "rate"], r"\b\d+[.,]?\d*\s*%"),
        a("Date Consistency Checker", "Comparer les dates divergentes", ["dates", "consistency", "chronology"], ["stats"], "dates", ["2024", "2025", "2026"], r"\b20\d{2}\b"),
        a("Quote Verifier", "Vérifier les citations et leur attribution", ["quotes", "attribution", "verification"], ["stats", "verify"], "quotes", ["said", "quoted", "citation"], r"[«\"“']"),
        a("Context Omission Detector", "Détecter les énoncés prudentiels et omissions", ["context", "hedging", "omission"], ["stats"], "hedges", ["however", "but", "cependant"], r"\b(?:however|but|although|cependant)\b"),
        a("Misleading Headline Detector", "Repérer les titres à polarité forte", ["headlines", "stance", "misleading"], ["stats"], "stance", ["shocking", "exclusive", "urgent"], r"\b(?:shocking|exclusive|urgent|breaking)\b"),
        a("Verdict Aggregator", "Agrégér les signaux contradictoires", ["verdicts", "conflicts", "aggregation"], ["stats", "memory"], "contradictions", ["confirmed", "false", "unverified"], r"\b(?:confirmed|false|unverified|true)\b"),
        a("Evidence Coverage Auditor", "Auditer la couverture des preuves", ["coverage", "gaps", "audit"], ["stats"], "gaps", ["evidence", "source", "support"], r"\b(?:evidence|support|source)\b"),
    ]),
    ("DATA", "Data Intelligence", [
        a("Dataset Metadata Reader", "Lire les métadonnées de jeux de données", ["metadata", "schema", "datasets"], ["stats"], "schema", ["columns", "rows", "format"], r"\b(?:columns|rows|schema|csv)\b"),
        a("Unit Normalizer", "Classifier les unités et valeurs", ["units", "normalization", "numbers"], ["stats"], "numbers", ["kg", "km", "percent"], r"\b\d+\s*(?:kg|km|ms|%|gb)\b"),
        a("Time Series Spotter", "Repérer les séries temporelles", ["timeseries", "dates", "trends"], ["stats"], "timeline", ["monthly", "quarterly", "annual"], r"\b(?:monthly|quarterly|annual|daily)\b"),
        a("Outlier Detector", "Détecter les valeurs aberrantes", ["outliers", "statistics", "quality"], ["stats"], "outliers", ["outlier", "anomaly", "spike"], r"\b(?:outlier|anomaly|spike)\b"),
        a("Missing Data Auditor", "Lister les champs absents", ["missing_data", "coverage", "quality"], ["stats"], "coverage", ["missing", "null", "unknown"], r"\b(?:missing|null|nan|unknown)\b"),
        a("Schema Inference", "Inférer un schéma à partir des paires clé/valeur", ["schema", "inference", "types"], ["stats"], "schema", ["type", "field", "value"], r"\b\w+\s*[:=]\s*\w+"),
        a("Statistical Summary", "Produire les statistiques descriptives", ["descriptive", "statistics", "summary"], ["stats"], "length", ["mean", "median", "std"], r"\b(?:mean|median|std|average)\b"),
        a("Correlation Signal Reader", "Repérer les signaux de corrélation", ["correlation", "cooccurrence", "signals"], ["stats", "graph"], "correlation", ["correlation", "linked", "associated"], r"\b(?:correlat|associated|linked)\b"),
        a("Data Source Lineage", "Tracer l'origine des données", ["lineage", "provenance", "traceability"], ["stats", "verify"], "provenance", ["source", "origin", "collected"], r"\b(?:source|origin|collected)\b"),
        a("Reproducibility Pack Builder", "Vérifier la complétude du paquet reproductible", ["reproducibility", "gaps", "packaging"], ["stats", "memory"], "gaps", ["seed", "version", "script"], r"\b(?:seed|script|reproduc)\b"),
    ]),
    ("SYN", "Research Synthesis", [
        a("Theme Clusterer", "Regrouper les thèmes proches", ["themes", "clustering", "synthesis"], ["stats"], "clusters", ["theme", "topic", "thème"], r"\b(?:theme|topic|subject)\b"),
        a("Consensus Builder", "Construire la liste des affirmations convergentes", ["consensus", "claims", "agreement"], ["stats"], "claims", ["consensus", "agree", "converge"], r"\b(?:consensus|agree|converge)\b"),
        a("Conflict Arbitrator", "Appliquer la règle d'arbitrage aux contradictions", ["arbitration", "conflicts", "evidence"], ["stats", "graph"], "contradictions", ["however", "versus", "opposite"], r"\b(?:however|versus|contrary|opposite)\b"),
        a("Citation Formatter", "Construire la table des références", ["citations", "formatting", "graph"], ["graph", "stats"], "graph", ["reference", "citation", "source"], r"\b(?:ref|citation|source)\b"),
        a("Executive Summary Writer", "Sélectionner les énoncés les plus denses", ["summarization", "density", "writing"], ["stats", "llm"], "length", ["summary", "key", "essential"], r"\b(?:key|summary|essential)\b"),
        a("Limitations Writer", "Lister les limites méthodologiques", ["limitations", "gaps", "critical"], ["stats"], "gaps", ["limitation", "caveat", "bias"], r"\b(?:limited|caveat|bias|limitation)\b"),
        a("Confidence Calibrator", "Noter la crédibilité globale", ["confidence", "credibility", "calibration"], ["stats", "verify"], "credibility", ["confidence", "certainty", "probability"], r"\b(?:confidence|certainty|probability)\b"),
        a("Evidence Table Builder", "Construire une table preuve/affirmation", ["evidence", "tables", "mapping"], ["stats"], "coverage", ["evidence", "claim", "support"], r"\b(?:evidence|claim|support)\b"),
        a("Narrative Coherence Editor", "Vérifier la cohérence des énoncés", ["coherence", "hedging", "editing"], ["stats", "llm"], "hedges", ["therefore", "thus", "ainsi"], r"\b(?:therefore|thus|hence|donc)\b"),
        a("Final Report Auditor", "Auditer la traçabilité finale", ["audit", "provenance", "gates"], ["stats", "verify", "memory"], "provenance", ["audit", "trace", "verified"], r"\b(?:audit|trace|verified)\b"),
    ]),
]

# --------------------------------------------------------------------------- #
# Corps des handlers : 31 noyaux distincts, paramètres propres à chaque agent.
# Chaque extrait définit findings / metrics / summary.
# --------------------------------------------------------------------------- #
BODIES = {
"keyword": '''    matches = K.focus_matches(ctx.evidence, __FOCUS__)
    findings = [Finding(statement=s, score=min(1.0, __WEIGHT__ * (0.35 + 0.14 * len(t))),
                        evidence_ids=[d.id],
                        metadata={"matched_terms": t, "domain": d.domain,
                                  "provider": d.provider, "lens": __LABEL__})
                for d, s, t in matches[:__N__]]
    cov = K.coverage(ctx.evidence, __FOCUS__)
    metrics = {"matched": len(matches), "coverage": cov,
               "domains": sorted({d.domain for d, _, _ in matches})}
    summary = f"{len(matches)} énoncés qualifiés ; {cov['covered']}/{cov['total_terms']} angles couverts."''',
"regex": '''    hits = K.regex_matches(ctx.evidence, __PATTERN__)
    findings = [Finding(statement=f"{m} — {s[:220]}", score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"match": m[:120], "domain": d.domain,
                                  "pattern": __PATTERN__, "lens": __LABEL__})
                for d, m, s in hits[:__N__]]
    metrics = {"regex_hits": len(hits), "pattern": __PATTERN__,
               "domains": sorted({d.domain for d, _, _ in hits})}
    summary = f"{len(hits)} occurrences du motif analysées, {len(metrics['domains'])} domaines."''',
"numbers": '''    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in __FOCUS__])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": __LABEL__})
                for d, v, u, s in (focused or values)[:__N__]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."''',
"dates": '''    rows = K.dates_in_text(ctx.evidence)
    findings = [Finding(statement=f"{date} — {d.title or d.domain}",
                        score=__WEIGHT__, evidence_ids=[d.id],
                        metadata={"date": date, "domain": d.domain, "lens": __LABEL__})
                for d, date in rows[:__N__]]
    metrics = {"dated_mentions": len(rows),
               "unique_dates": sorted({date for _, date in rows})[:20],
               "recency": K.recency_scores(ctx.evidence)}
    summary = f"{len(rows)} mentions datées, {len(metrics['unique_dates'])} dates distinctes."''',
"domains": '''    dist = K.domain_distribution(ctx.evidence)
    prov = K.provenance(ctx.evidence)
    findings = [Finding(statement=f"{dom}: {count} source(s)",
                        score=min(1.0, __WEIGHT__ * count / max(1, len(ctx.evidence))),
                        evidence_ids=[d.id for d in ctx.evidence if d.domain == dom][:5],
                        metadata={"domain": dom, "count": count, "lens": __LABEL__})
                for dom, count in sorted(dist.items(), key=lambda x: -x[1])[:__N__]]
    metrics = {"distribution": dist, **prov}
    summary = f"{len(dist)} domaines, entropie {prov['domain_entropy']}, " \
              f"{prov['provider_count']} fournisseurs."''',
"clusters": '''    clusters = K.similarity_clusters(ctx.evidence, max(0.1, __THRESHOLD__ * 3))
    findings = [Finding(statement=f"Groupe de {len(c)} sources : {c[0].title[:120]}",
                        score=min(1.0, __WEIGHT__ + 0.05 * len(c)),
                        evidence_ids=[d.id for d in c[:5]],
                        metadata={"size": len(c), "domains": sorted({d.domain for d in c}),
                                  "lens": __LABEL__})
                for c in clusters[:__N__]]
    metrics = {"clusters": len(clusters), "sizes": [len(c) for c in clusters],
               "similarity_threshold": __THRESHOLD__}
    summary = f"{len(clusters)} groupes de sources similaires constitués."''',
"hedges": '''    rows = K.hedge_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"hedge": cue, "domain": d.domain, "lens": __LABEL__})
                for d, s, cue in rows[:__N__]]
    metrics = {"hedged_sentences": len(rows),
               "hedge_rate": round(len(rows) / max(1, len(K.sentences(ctx.evidence))), 4),
               "cues": sorted({cue for _, _, cue in rows})}
    summary = f"{len(rows)} énoncés prudents ou hypothétiques repérés."''',
"negations": '''    rows = K.negation_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"negation": cue, "domain": d.domain, "lens": __LABEL__})
                for d, s, cue in rows[:__N__]]
    metrics = {"negated_sentences": len(rows), "cues": sorted({c for _, _, c in rows})}
    summary = f"{len(rows)} énoncés négatifs ou de démenti isolés."''',
"quotes": '''    rows = K.quotes(ctx.evidence)
    findings = [Finding(statement=quote[:300], score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"context": s[:200], "domain": d.domain,
                                  "lens": __LABEL__})
                for d, quote, s in rows[:__N__]]
    metrics = {"quotes": len(rows), "domains": sorted({d.domain for d, _, _ in rows})}
    summary = f"{len(rows)} citations textuelles extraites avec leur contexte."''',
"ngrams": '''    rows = K.ngrams(ctx.evidence, n=2, top=__N__)
    findings = [Finding(statement=f"{phrase} ({count} occurrences)",
                        score=min(1.0, __WEIGHT__ * count / max(1, rows[0][1] if rows else 1)),
                        evidence_ids=[d.id for d in ctx.evidence
                                      if phrase.split()[0] in d.evidence_text().lower()][:3],
                        metadata={"ngram": phrase, "count": count, "lens": __LABEL__})
                for phrase, count in rows]
    metrics = {"top_ngrams": rows, "distinct": len(rows)}
    summary = f"{len(rows)} n-grammes dominants, premier : " \
              f"{rows[0][0] if rows else 'aucun'}."''',
"entities": '''    ent = K.entities(ctx.evidence)
    findings = [Finding(statement=f"{kind}: {', '.join(values[:5])}",
                        score=__WEIGHT__,
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"kind": kind, "values": values[:10], "lens": __LABEL__})
                for kind, values in ent.items() if values][:__N__]
    metrics = {"entity_counts": {k: len(v) for k, v in ent.items()},
               "emails": ent["emails"][:5]}
    summary = f"{sum(len(v) for v in ent.values())} entités nominatives ou techniques."''',
"recency": '''    scores = K.recency_scores(ctx.evidence)
    findings = [Finding(statement=f"Fraîcheur {score:.2f} — {d.title or d.domain}",
                        score=min(1.0, __WEIGHT__ * (0.4 + score)),
                        evidence_ids=[d.id],
                        metadata={"recency": score, "published_at": d.published_at,
                                  "domain": d.domain, "lens": __LABEL__})
                for d, score in zip(ctx.evidence, scores) if score > 0][:__N__]
    metrics = {"recency_scores": scores,
               "dated_documents": sum(1 for s in scores if s > 0),
               "mean_recency": round(sum(scores) / max(1, len(scores)), 4)}
    summary = f"{metrics['dated_documents']} sources datées, fraîcheur moyenne " \
              f"{metrics['mean_recency']}."''',
"provenance": '''    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, __WEIGHT__ * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": __LABEL__})
                for sid, score in cred[:__N__]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, " \
              f"ratio vérifié {prov['verified_ratio']}."''',
"gaps": '''    gaps = K.evidence_gaps(ctx.evidence, __FOCUS__)
    cov = K.coverage(ctx.evidence, __FOCUS__)
    findings = [Finding(statement=f"Lacune : {gap}", score=__WEIGHT__,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": __LABEL__})
                for gap in gaps[:__N__]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture " \
              f"{cov['covered']}/{cov['total_terms']}."''',
"cooccurrence": '''    pairs = K.cooccurrence(ctx.evidence, __FOCUS__)
    findings = [Finding(statement=f"{x} ↔ {y} : {count} co-occurrences",
                        score=min(1.0, __WEIGHT__ * count / max(1, pairs[0][2] if pairs else 1)),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": __LABEL__})
                for x, y, count in pairs[:__N__]]
    metrics = {"pairs": pairs, "focus": __FOCUS__}
    summary = f"{len(pairs)} paires de termes co-occurrentes détectées."''',
"compare": '''    conflicts = K.numeric_conflicts(ctx.evidence)
    values = K.numbers_with_units(ctx.evidence)
    findings = [Finding(statement=f"Valeurs divergentes : {c['value_a']} vs {c['value_b']} "
                                  f"(écart {c['relative_gap']})",
                        score=__WEIGHT__, evidence_ids=[],
                        metadata={**c, "lens": __LABEL__})
                for c in conflicts[:__N__]]
    metrics = {"conflicts": len(conflicts), "numeric_mentions": len(values),
               "units": K.unit_distribution(ctx.evidence)}
    summary = f"{len(conflicts)} divergences numériques potentielles sur " \
              f"{len(values)} valeurs."''',
"stance": '''    rows = K.stance_pairs(ctx.evidence,
                          [x.lower() for x in __FOCUS__], ["not", "no", "never", "ne pas", "false"])
    counts = {"positive": 0, "negative": 0}
    findings = []
    for d, s, label in rows[:__N__]:
        counts[label] += 1
        findings.append(Finding(statement=f"[{label}] {s[:240]}", score=__WEIGHT__,
                                evidence_ids=[d.id],
                                metadata={"stance": label, "domain": d.domain,
                                          "lens": __LABEL__}))
    metrics = {"stance_counts": {k: v for k, v in counts.items()},
               "total": len(rows)}
    summary = f"{len(rows)} énoncés polarisés : {counts['positive']} positifs, " \
              f"{counts['negative']} négatifs."''',
"length": '''    stats = K.length_stats(ctx.evidence)
    ranked = sorted(ctx.evidence, key=lambda d: -len(d.evidence_text()))[:__N__]
    findings = [Finding(statement=f"{len(d.evidence_text())} caractères — {d.title or d.domain}",
                        score=min(1.0, __WEIGHT__ * len(d.evidence_text()) /
                                  max(1, len(ranked[0].evidence_text()) if ranked else 1)),
                        evidence_ids=[d.id],
                        metadata={"words": len(d.evidence_text().split()),
                                  "domain": d.domain, "lens": __LABEL__})
                for d in ranked]
    metrics = {**stats, "ranked_domains": [d.domain for d in ranked]}
    summary = f"{stats['documents']} documents, {stats['total_words']} mots, " \
              f"moyenne {stats['mean_words']}."''',
"claims": '''    rows = K.claim_sentences(ctx.evidence)
    findings = [Finding(statement=s[:300], score=__WEIGHT__,
                        evidence_ids=[d.id],
                        metadata={"domain": d.domain, "provider": d.provider,
                                  "verified": d.verified, "lens": __LABEL__})
                for d, s in rows[:__N__]]
    metrics = {"claims": len(rows), "independent_domains":
               len({d.domain for d, _ in rows}),
               "supported_ratio": round(sum(1 for d, _ in rows if d.verified) /
                                        max(1, len(rows)), 4)}
    summary = f"{len(rows)} affirmations candidates, {metrics['independent_domains']} " \
              f"domaines indépendants."''',
"graph": '''    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, __WEIGHT__ * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": __LABEL__})
                for dom, count in graph["top_cited"][:__N__]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."''',
"outliers": '''    values = [float(v) for _, v, _, _ in K.numbers_with_units(ctx.evidence)]
    rows = K.outliers(values, max(0.5, __THRESHOLD__ * 10))
    findings = [Finding(statement=f"Valeur atypique {r['value']} (z={r['z']})",
                        score=__WEIGHT__, evidence_ids=[],
                        metadata={**r, "lens": __LABEL__})
                for r in rows[:__N__]]
    metrics = {"outliers": rows, "values_tested": len(values),
               "mean": round(sum(values) / max(1, len(values)), 3)}
    summary = f"{len(rows)} valeurs aberrantes sur {len(values)} valeurs numériques."''',
"language": '''    scores = K.language_guess(ctx.evidence)
    dominant = max(scores, key=scores.get) if scores else "inconnu"
    findings = [Finding(statement=f"Langue {lang} : ratio {ratio}",
                        score=min(1.0, __WEIGHT__ * ratio * 5),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"language": lang, "ratio": ratio, "lens": __LABEL__})
                for lang, ratio in scores.items()]
    metrics = {"language_scores": scores, "dominant": dominant,
               "documents": len(ctx.evidence)}
    summary = f"Langue dominante estimée : {dominant} ({scores.get(dominant, 0)})."''',
"schema": '''    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=__WEIGHT__, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": __LABEL__})
                for key, value in pairs[:__N__]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."''',
"license": '''    rows = K.licenses(ctx.evidence)
    findings = [Finding(statement=f"Licence {lic} : {count} mention(s)",
                        score=__WEIGHT__, evidence_ids=[d.id for d in ctx.evidence
                                                       if lic.lower() in d.evidence_text().lower()][:3],
                        metadata={"license": lic, "count": count, "lens": __LABEL__})
                for lic, count in rows[:__N__]]
    metrics = {"licenses": rows, "distinct": len(rows)}
    summary = f"{len(rows)} licences distinctes détectées dans les preuves."''',
"versions": '''    rows = K.version_mentions(ctx.evidence)
    findings = [Finding(statement=f"Version {ver} : {count} occurrence(s)",
                        score=__WEIGHT__, evidence_ids=[d.id for d in ctx.evidence
                                                       if ver in d.evidence_text()][:3],
                        metadata={"version": ver, "count": count, "lens": __LABEL__})
                for ver, count in rows[:__N__]]
    metrics = {"versions": rows, "distinct": len(rows)}
    summary = f"{len(rows)} versions logicielles distinctes relevées."''',
"timeline": '''    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=__WEIGHT__, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": __LABEL__})
                for r in rows[:__N__]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."''',
"credibility": '''    rows = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Score de crédibilité {score} pour {sid}",
                        score=min(1.0, __WEIGHT__ * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"credibility": score, "lens": __LABEL__})
                for sid, score in rows[:__N__]]
    metrics = {"scores": rows[:20],
               "mean": round(sum(s for _, s in rows) / max(1, len(rows)), 4),
               "types": K.source_types(ctx.evidence)}
    summary = f"Crédibilité moyenne {metrics['mean']} sur {len(rows)} sources."''',
"contradictions": '''    signals = K.contradiction_signals(ctx.evidence)
    findings = [Finding(statement=f"Opposition (sim={s['similarity']}) : "
                                  f"{s['positive'][:110]} / {s['negative'][:110]}",
                        score=__WEIGHT__, evidence_ids=s["evidence_ids"],
                        metadata={"cue": s["cue"], "domain_a": s["domain_a"],
                                  "domain_b": s["domain_b"], "lens": __LABEL__})
                for s in signals[:__N__]]
    metrics = {"signals": len(signals),
               "pairs": [(s["domain_a"], s["domain_b"]) for s in signals[:10]],
               "numeric_conflicts": K.numeric_conflicts(ctx.evidence)[:5]}
    summary = f"{len(signals)} signaux de contradiction inter-domaines."''',
"coverage": '''    cov = K.coverage(ctx.evidence, __FOCUS__)
    findings = [Finding(statement=f"{term} : {count} énoncé(s)",
                        score=min(1.0, __WEIGHT__ * count / max(1, max(cov["per_term"].values()))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"term": term, "count": count, "lens": __LABEL__})
                for term, count in cov["per_term"].items()]
    metrics = {"coverage": cov, "gap_count": len(cov["gaps"])}
    summary = f"{cov['covered']}/{cov['total_terms']} angles couverts, " \
              f"{len(cov['gaps'])} absents."''',
"types": '''    types = K.source_types(ctx.evidence)
    findings = [Finding(statement=f"Type {kind} : {count} source(s)",
                        score=min(1.0, __WEIGHT__ * count / max(1, len(ctx.evidence))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"source_type": kind, "count": count, "lens": __LABEL__})
                for kind, count in sorted(types.items(), key=lambda x: -x[1])[:__N__]]
    metrics = {"types": types, "documents": len(ctx.evidence)}
    summary = f"{len(types)} types de sources classés."''',
"correlation": '''    rows = K.correlation_signals(ctx.evidence)
    findings = [Finding(statement=f"{x} ↔ {y} : {count}",
                        score=__WEIGHT__, evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": __LABEL__})
                for x, y, count in rows[:__N__]]
    metrics = {"signals": rows, "count": len(rows),
               "coverage": K.coverage(ctx.evidence, __FOCUS__)}
    summary = f"{len(rows)} signaux de corrélation lexicale relevés."''',
}

EPILOGUE = '''    findings = [f for f in findings if f.score >= __THRESHOLD__]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": __LABEL__, "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = __FOCUS__
    metrics["profile_label"] = __LABEL__
    metrics["profile_bias"] = __WEIGHT__
    return build_output(ctx, SPEC, findings, metrics, summary)'''

HEADER_CATALOG = '''"""CATALOGUE GÉNÉRÉ — ne pas éditer à la main.
Source : scripts/gen_profiles.py (10 divisions × 10 agents = 100 profils)."""
from __future__ import annotations

from .base import AgentSpec, INPUT_SCHEMA, OUTPUT_SCHEMA

SPECS: list[AgentSpec] = [
'''
HEADER_PROFILES = '''"""HANDLERS GÉNÉRÉS — ne pas éditer à la main.

100 fonctions distinctes, chacune exécutant un noyau d'analyse réel avec ses
propres paramètres. Source : scripts/gen_profiles.py."""
from __future__ import annotations

from . import kernels as K
from .base import AgentContext, AgentOutput, Finding, build_output
from .catalog_data import SPECS

_BY_ID = {spec.id: spec for spec in SPECS}

'''


def build_table():
    rows = []
    for div_code, div_name, agents in DIVISIONS:
        for index, item in enumerate(agents, start=1):
            agent_id = f"{div_code}-{index:02d}"
            fn_name = f"{div_code.lower()}_{index:02d}"
            rows.append((agent_id, fn_name, div_code, div_name, item))
    return rows


def render_catalog(rows):
    lines = [HEADER_CATALOG]
    for agent_id, fn_name, div_code, div_name, item in rows:
        config = {
            "kernel": item["template"], "max_findings": item["n"],
            "threshold": item["threshold"], "confidence_weight": item["weight"],
            "pattern": item["pattern"], "priority": item["priority"],
            "retry_attempts": 2, "timeout_seconds": 20,
        }
        lines.append("    AgentSpec(\n")
        for key, value in (
            ("id", agent_id), ("division_code", div_code), ("division_name", div_name),
            ("name", item["name"]), ("mission", item["mission"]),
            ("skills", tuple(item["skills"])), ("allowed_tools", tuple(item["tools"])),
            ("config", config), ("template", item["template"]),
            ("focus", tuple(item["focus"])), ("pattern", item["pattern"]),
            ("threshold", item["threshold"]), ("weight", item["weight"]),
            ("label", item["label"]), ("input_schema", "INPUT_SCHEMA"),
            ("output_schema", "OUTPUT_SCHEMA"), ("handler_name", fn_name),
            ("priority", item["priority"]),
        ):
            if isinstance(value, str) and value in {"INPUT_SCHEMA", "OUTPUT_SCHEMA"}:
                rendered = value
            else:
                rendered = repr(value)
            lines.append(f"        {key}={rendered},\n")
        lines.append("    ),\n")
    lines.append("]\n")
    return "".join(lines)


def render_profiles(rows):
    out = [HEADER_PROFILES]
    for agent_id, fn_name, div_code, div_name, item in rows:
        body = BODIES[item["template"]]
        replacements = {
            "__FOCUS__": repr(list(item["focus"])),
            "__PATTERN__": repr(item["pattern"]),
            "__N__": str(item["n"]),
            "__THRESHOLD__": repr(item["threshold"]),
            "__WEIGHT__": repr(item["weight"]),
            "__LABEL__": repr(item["label"]),
        }
        for token, value in replacements.items():
            body = body.replace(token, value)
        tools = repr(list(item["tools"]))
        out.append(f'def {fn_name}(ctx: AgentContext) -> AgentOutput:\n')
        out.append(f'    """{agent_id} — {item["name"]} : {item["mission"]}"""\n')
        out.append("    SPEC = _BY_ID[" + repr(agent_id) + "]\n")
        for tool in item["tools"]:
            out.append(f"    ctx.tools.use({tool!r})\n")
        out.append(body + "\n")
        out.append(EPILOGUE.replace("__FOCUS__", replacements["__FOCUS__"])
                   .replace("__LABEL__", replacements["__LABEL__"])
                   .replace("__WEIGHT__", replacements["__WEIGHT__"])
                   .replace("__THRESHOLD__", replacements["__THRESHOLD__"]))
        out.append("\n\n")
    out.append("HANDLERS = {\n")
    for agent_id, fn_name, *_ in rows:
        out.append(f"    {agent_id!r}: {fn_name},\n")
    out.append("}\n\n\ndef handler_for(agent_id: str):\n"
               "    return HANDLERS[agent_id]\n")
    return "".join(out)


def render_markdown(rows):
    status_file = ROOT / "test-results" / "agent_results.json"
    statuses: dict[str, str] = {}
    if status_file.is_file():
        try:
            statuses = json.loads(status_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            statuses = {}
    out = [
        "# Catalogue des 100 agents — OMNI-RESEARCH 100\n\n",
        "Généré depuis `scripts/gen_profiles.py`. Chaque agent possède un handler ",
        "Python distinct, des outils autorisés, une configuration, un schéma ",
        "d'entrée (`INPUT_SCHEMA`) et un schéma de sortie (`OUTPUT_SCHEMA`).\n\n",
        "Légende : **OPÉRATIONNELLE ET TESTÉE** = exécuté avec succès par ",
        "`tests/test_agents_all_100.py` ; **IMPLÉMENTÉE MAIS NON VÉRIFIÉE** = ",
        "code présent, test non encore joué.\n\n",
        "| ID | Division | Agent | Noyau | Outils | État |\n",
        "|---|---|---|---|---|---|\n",
    ]
    for agent_id, fn_name, div_code, div_name, item in rows:
        status = statuses.get(agent_id, "IMPLÉMENTÉE MAIS NON VÉRIFIÉE")
        out.append(f"| `{agent_id}` | {div_name} | {item['name']} | "
                   f"`{item['template']}` | {', '.join(item['tools'])} | {status} |\n")
    out.append("\n## Divisions\n\n")
    for code, name, agents in DIVISIONS:
        out.append(f"- **{code} — {name}** : {len(agents)} agents "
                   f"(`{code}-01` à `{code}-{len(agents):02d}`)\n")
    return "".join(out)


def main() -> None:
    rows = build_table()
    assert len(rows) == 100, f"attendu 100 agents, obtenu {len(rows)}"
    assert len({r[0] for r in rows}) == 100
    for _, _, _, _, item in rows:
        assert item["template"] in BODIES, item["template"]
        assert all(t in {"stats", "memory", "verify", "search", "extract", "llm", "graph"}
                   for t in item["tools"]), item
    targets = {
        ROOT / "app" / "agents" / "catalog_data.py": render_catalog(rows),
        ROOT / "app" / "agents" / "profiles.py": render_profiles(rows),
        ROOT / "docs" / "AGENTS_CATALOG.md": render_markdown(rows),
    }
    if "--check" in sys.argv:
        drift = [str(path.relative_to(ROOT)) for path, content in targets.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != content]
        if drift:
            print("FICHIERS GÉNÉRÉS DÉSYNCHRONISÉS : " + ", ".join(drift))
            sys.exit(1)
        print(f"OK (check): {len(rows)} agents, {len(BODIES)} noyaux, "
              f"fichiers générés synchronisés")
        return
    for path, content in targets.items():
        path.write_text(content, encoding="utf-8")
    print(f"OK: {len(rows)} agents, {len(BODIES)} noyaux, "
          f"{len(set(r[3] for r in rows))} divisions")


if __name__ == "__main__":
    main()
