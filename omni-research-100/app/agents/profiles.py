"""HANDLERS GÉNÉRÉS — ne pas éditer à la main.

100 fonctions distinctes, chacune exécutant un noyau d'analyse réel avec ses
propres paramètres. Source : scripts/gen_profiles.py."""
from __future__ import annotations

from . import kernels as K
from .base import AgentContext, AgentOutput, Finding, build_output
from .catalog_data import SPECS

_BY_ID = {spec.id: spec for spec in SPECS}

def web_01(ctx: AgentContext) -> AgentOutput:
    """WEB-01 — SERP Result Miner : Extraire et qualifier les résultats de recherche"""
    SPEC = _BY_ID['WEB-01']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    matches = K.focus_matches(ctx.evidence, ['result', 'search', 'résultat'])
    findings = [Finding(statement=s, score=min(1.0, 0.62 * (0.35 + 0.14 * len(t))),
                        evidence_ids=[d.id],
                        metadata={"matched_terms": t, "domain": d.domain,
                                  "provider": d.provider, "lens": 'SERP Result Miner'})
                for d, s, t in matches[:12]]
    cov = K.coverage(ctx.evidence, ['result', 'search', 'résultat'])
    metrics = {"matched": len(matches), "coverage": cov,
               "domains": sorted({d.domain for d, _, _ in matches})}
    summary = f"{len(matches)} énoncés qualifiés ; {cov['covered']}/{cov['total_terms']} angles couverts."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'SERP Result Miner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['result', 'search', 'résultat']
    metrics["profile_label"] = 'SERP Result Miner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_02(ctx: AgentContext) -> AgentOutput:
    """WEB-02 — Domain Authority Mapper : Cartographier les domaines et leur poids relatif"""
    SPEC = _BY_ID['WEB-02']
    ctx.tools.use('stats')
    ctx.tools.use('graph')
    dist = K.domain_distribution(ctx.evidence)
    prov = K.provenance(ctx.evidence)
    findings = [Finding(statement=f"{dom}: {count} source(s)",
                        score=min(1.0, 0.62 * count / max(1, len(ctx.evidence))),
                        evidence_ids=[d.id for d in ctx.evidence if d.domain == dom][:5],
                        metadata={"domain": dom, "count": count, "lens": 'Domain Authority Mapper'})
                for dom, count in sorted(dist.items(), key=lambda x: -x[1])[:12]]
    metrics = {"distribution": dist, **prov}
    summary = f"{len(dist)} domaines, entropie {prov['domain_entropy']}, "               f"{prov['provider_count']} fournisseurs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Domain Authority Mapper', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['domain', 'site', 'authority']
    metrics["profile_label"] = 'Domain Authority Mapper'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_03(ctx: AgentContext) -> AgentOutput:
    """WEB-03 — Crawl Frontier Planner : Regrouper les pages proches pour planifier l'exploration"""
    SPEC = _BY_ID['WEB-03']
    ctx.tools.use('stats')
    ctx.tools.use('graph')
    clusters = K.similarity_clusters(ctx.evidence, max(0.1, 0.05 * 3))
    findings = [Finding(statement=f"Groupe de {len(c)} sources : {c[0].title[:120]}",
                        score=min(1.0, 0.62 + 0.05 * len(c)),
                        evidence_ids=[d.id for d in c[:5]],
                        metadata={"size": len(c), "domains": sorted({d.domain for d in c}),
                                  "lens": 'Crawl Frontier Planner'})
                for c in clusters[:12]]
    metrics = {"clusters": len(clusters), "sizes": [len(c) for c in clusters],
               "similarity_threshold": 0.05}
    summary = f"{len(clusters)} groupes de sources similaires constitués."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Crawl Frontier Planner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['page', 'link', 'crawl']
    metrics["profile_label"] = 'Crawl Frontier Planner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_04(ctx: AgentContext) -> AgentOutput:
    """WEB-04 — Link Graph Analyst : Construire le graphe des liens entre domaines"""
    SPEC = _BY_ID['WEB-04']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, 0.62 * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": 'Link Graph Analyst'})
                for dom, count in graph["top_cited"][:12]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Link Graph Analyst', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['link', 'reference', 'href']
    metrics["profile_label"] = 'Link Graph Analyst'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_05(ctx: AgentContext) -> AgentOutput:
    """WEB-05 — Page Freshness Auditor : Évaluer la fraîcheur des pages datées"""
    SPEC = _BY_ID['WEB-05']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    scores = K.recency_scores(ctx.evidence)
    findings = [Finding(statement=f"Fraîcheur {score:.2f} — {d.title or d.domain}",
                        score=min(1.0, 0.62 * (0.4 + score)),
                        evidence_ids=[d.id],
                        metadata={"recency": score, "published_at": d.published_at,
                                  "domain": d.domain, "lens": 'Page Freshness Auditor'})
                for d, score in zip(ctx.evidence, scores) if score > 0][:12]
    metrics = {"recency_scores": scores,
               "dated_documents": sum(1 for s in scores if s > 0),
               "mean_recency": round(sum(scores) / max(1, len(scores)), 4)}
    summary = f"{metrics['dated_documents']} sources datées, fraîcheur moyenne "               f"{metrics['mean_recency']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Page Freshness Auditor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['published', 'updated', 'date']
    metrics["profile_label"] = 'Page Freshness Auditor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_06(ctx: AgentContext) -> AgentOutput:
    """WEB-06 — Web Archive Hunter : Repérer les versions archivées et les dates historiques"""
    SPEC = _BY_ID['WEB-06']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=0.62, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": 'Web Archive Hunter'})
                for r in rows[:12]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Web Archive Hunter', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['archive', 'snapshot', 'version']
    metrics["profile_label"] = 'Web Archive Hunter'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_07(ctx: AgentContext) -> AgentOutput:
    """WEB-07 — Sitemap & Robots Reader : Détecter les métadonnées d'indexation et de structure"""
    SPEC = _BY_ID['WEB-07']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Sitemap & Robots Reader'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Sitemap & Robots Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['sitemap', 'robots', 'index']
    metrics["profile_label"] = 'Sitemap & Robots Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_08(ctx: AgentContext) -> AgentOutput:
    """WEB-08 — Multilingual Web Scout : Estimer la langue des contenus collectés"""
    SPEC = _BY_ID['WEB-08']
    ctx.tools.use('stats')
    scores = K.language_guess(ctx.evidence)
    dominant = max(scores, key=scores.get) if scores else "inconnu"
    findings = [Finding(statement=f"Langue {lang} : ratio {ratio}",
                        score=min(1.0, 0.62 * ratio * 5),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"language": lang, "ratio": ratio, "lens": 'Multilingual Web Scout'})
                for lang, ratio in scores.items()]
    metrics = {"language_scores": scores, "dominant": dominant,
               "documents": len(ctx.evidence)}
    summary = f"Langue dominante estimée : {dominant} ({scores.get(dominant, 0)})."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Multilingual Web Scout', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['language', 'traduction', 'multilingue']
    metrics["profile_label"] = 'Multilingual Web Scout'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_09(ctx: AgentContext) -> AgentOutput:
    """WEB-09 — Landing Page Comparator : Comparer les longueurs et structures des pages"""
    SPEC = _BY_ID['WEB-09']
    ctx.tools.use('stats')
    stats = K.length_stats(ctx.evidence)
    ranked = sorted(ctx.evidence, key=lambda d: -len(d.evidence_text()))[:12]
    findings = [Finding(statement=f"{len(d.evidence_text())} caractères — {d.title or d.domain}",
                        score=min(1.0, 0.62 * len(d.evidence_text()) /
                                  max(1, len(ranked[0].evidence_text()) if ranked else 1)),
                        evidence_ids=[d.id],
                        metadata={"words": len(d.evidence_text().split()),
                                  "domain": d.domain, "lens": 'Landing Page Comparator'})
                for d in ranked]
    metrics = {**stats, "ranked_domains": [d.domain for d in ranked]}
    summary = f"{stats['documents']} documents, {stats['total_words']} mots, "               f"moyenne {stats['mean_words']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Landing Page Comparator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['landing', 'page', 'section']
    metrics["profile_label"] = 'Landing Page Comparator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def web_10(ctx: AgentContext) -> AgentOutput:
    """WEB-10 — Broken Reference Detector : Repérer les références et URLs suspectes"""
    SPEC = _BY_ID['WEB-10']
    ctx.tools.use('verify')
    ctx.tools.use('stats')
    ent = K.entities(ctx.evidence)
    findings = [Finding(statement=f"{kind}: {', '.join(values[:5])}",
                        score=0.62,
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"kind": kind, "values": values[:10], "lens": 'Broken Reference Detector'})
                for kind, values in ent.items() if values][:12]
    metrics = {"entity_counts": {k: len(v) for k, v in ent.items()},
               "emails": ent["emails"][:5]}
    summary = f"{sum(len(v) for v in ent.values())} entités nominatives ou techniques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Broken Reference Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['404', 'broken', 'reference']
    metrics["profile_label"] = 'Broken Reference Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_01(ctx: AgentContext) -> AgentOutput:
    """DEEP-01 — Question Decomposer : Extraire les affirmations constitutives de la question"""
    SPEC = _BY_ID['DEEP-01']
    ctx.tools.use('stats')
    rows = K.claim_sentences(ctx.evidence)
    findings = [Finding(statement=s[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"domain": d.domain, "provider": d.provider,
                                  "verified": d.verified, "lens": 'Question Decomposer'})
                for d, s in rows[:12]]
    metrics = {"claims": len(rows), "independent_domains":
               len({d.domain for d, _ in rows}),
               "supported_ratio": round(sum(1 for d, _ in rows if d.verified) /
                                        max(1, len(rows)), 4)}
    summary = f"{len(rows)} affirmations candidates, {metrics['independent_domains']} "               f"domaines indépendants."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Question Decomposer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['why', 'comment', 'impact']
    metrics["profile_label"] = 'Question Decomposer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_02(ctx: AgentContext) -> AgentOutput:
    """DEEP-02 — Literature Mapper : Cartographier les thèmes et leurs recouvrements"""
    SPEC = _BY_ID['DEEP-02']
    ctx.tools.use('stats')
    ctx.tools.use('graph')
    cov = K.coverage(ctx.evidence, ['study', 'étude', 'literature'])
    findings = [Finding(statement=f"{term} : {count} énoncé(s)",
                        score=min(1.0, 0.62 * count / max(1, max(cov["per_term"].values()))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"term": term, "count": count, "lens": 'Literature Mapper'})
                for term, count in cov["per_term"].items()]
    metrics = {"coverage": cov, "gap_count": len(cov["gaps"])}
    summary = f"{cov['covered']}/{cov['total_terms']} angles couverts, "               f"{len(cov['gaps'])} absents."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Literature Mapper', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['study', 'étude', 'literature']
    metrics["profile_label"] = 'Literature Mapper'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_03(ctx: AgentContext) -> AgentOutput:
    """DEEP-03 — Long-form Evidence Reader : Mesurer la densité des preuves longues"""
    SPEC = _BY_ID['DEEP-03']
    ctx.tools.use('stats')
    stats = K.length_stats(ctx.evidence)
    ranked = sorted(ctx.evidence, key=lambda d: -len(d.evidence_text()))[:12]
    findings = [Finding(statement=f"{len(d.evidence_text())} caractères — {d.title or d.domain}",
                        score=min(1.0, 0.62 * len(d.evidence_text()) /
                                  max(1, len(ranked[0].evidence_text()) if ranked else 1)),
                        evidence_ids=[d.id],
                        metadata={"words": len(d.evidence_text().split()),
                                  "domain": d.domain, "lens": 'Long-form Evidence Reader'})
                for d in ranked]
    metrics = {**stats, "ranked_domains": [d.domain for d in ranked]}
    summary = f"{stats['documents']} documents, {stats['total_words']} mots, "               f"moyenne {stats['mean_words']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Long-form Evidence Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['analysis', 'rapport', 'long']
    metrics["profile_label"] = 'Long-form Evidence Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_04(ctx: AgentContext) -> AgentOutput:
    """DEEP-04 — Argument Chain Builder : Repérer les co-occurrences formant des chaînes d'arguments"""
    SPEC = _BY_ID['DEEP-04']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    pairs = K.cooccurrence(ctx.evidence, ['because', 'therefore', 'donc'])
    findings = [Finding(statement=f"{x} ↔ {y} : {count} co-occurrences",
                        score=min(1.0, 0.62 * count / max(1, pairs[0][2] if pairs else 1)),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": 'Argument Chain Builder'})
                for x, y, count in pairs[:12]]
    metrics = {"pairs": pairs, "focus": ['because', 'therefore', 'donc']}
    summary = f"{len(pairs)} paires de termes co-occurrentes détectées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Argument Chain Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['because', 'therefore', 'donc']
    metrics["profile_label"] = 'Argument Chain Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_05(ctx: AgentContext) -> AgentOutput:
    """DEEP-05 — Assumption Identifier : Détecter les énoncés hypothétiques ou prudents"""
    SPEC = _BY_ID['DEEP-05']
    ctx.tools.use('stats')
    rows = K.hedge_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"hedge": cue, "domain": d.domain, "lens": 'Assumption Identifier'})
                for d, s, cue in rows[:12]]
    metrics = {"hedged_sentences": len(rows),
               "hedge_rate": round(len(rows) / max(1, len(K.sentences(ctx.evidence))), 4),
               "cues": sorted({cue for _, _, cue in rows})}
    summary = f"{len(rows)} énoncés prudents ou hypothétiques repérés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Assumption Identifier', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['assume', 'suppose', 'hypothèse']
    metrics["profile_label"] = 'Assumption Identifier'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_06(ctx: AgentContext) -> AgentOutput:
    """DEEP-06 — Research Gap Detector : Lister les angles non couverts par les preuves"""
    SPEC = _BY_ID['DEEP-06']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    gaps = K.evidence_gaps(ctx.evidence, ['gap', 'missing', 'lacune'])
    cov = K.coverage(ctx.evidence, ['gap', 'missing', 'lacune'])
    findings = [Finding(statement=f"Lacune : {gap}", score=0.62,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": 'Research Gap Detector'})
                for gap in gaps[:12]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture "               f"{cov['covered']}/{cov['total_terms']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Research Gap Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['gap', 'missing', 'lacune']
    metrics["profile_label"] = 'Research Gap Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_07(ctx: AgentContext) -> AgentOutput:
    """DEEP-07 — Methodology Critic : Repérer les descriptions de méthode et leurs limites"""
    SPEC = _BY_ID['DEEP-07']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Methodology Critic'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Methodology Critic', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['method', 'sample', 'protocol']
    metrics["profile_label"] = 'Methodology Critic'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_08(ctx: AgentContext) -> AgentOutput:
    """DEEP-08 — Chronology Builder : Ordonner les événements datés"""
    SPEC = _BY_ID['DEEP-08']
    ctx.tools.use('stats')
    rows = K.dates_in_text(ctx.evidence)
    findings = [Finding(statement=f"{date} — {d.title or d.domain}",
                        score=0.62, evidence_ids=[d.id],
                        metadata={"date": date, "domain": d.domain, "lens": 'Chronology Builder'})
                for d, date in rows[:12]]
    metrics = {"dated_mentions": len(rows),
               "unique_dates": sorted({date for _, date in rows})[:20],
               "recency": K.recency_scores(ctx.evidence)}
    summary = f"{len(rows)} mentions datées, {len(metrics['unique_dates'])} dates distinctes."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Chronology Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['2024', '2025', '2026']
    metrics["profile_label"] = 'Chronology Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_09(ctx: AgentContext) -> AgentOutput:
    """DEEP-09 — Cross-domain Bridge : Relier des domaines hétérogènes par co-occurrence"""
    SPEC = _BY_ID['DEEP-09']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    rows = K.correlation_signals(ctx.evidence)
    findings = [Finding(statement=f"{x} ↔ {y} : {count}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": 'Cross-domain Bridge'})
                for x, y, count in rows[:12]]
    metrics = {"signals": rows, "count": len(rows),
               "coverage": K.coverage(ctx.evidence, ['across', 'between', 'entre'])}
    summary = f"{len(rows)} signaux de corrélation lexicale relevés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Cross-domain Bridge', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['across', 'between', 'entre']
    metrics["profile_label"] = 'Cross-domain Bridge'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def deep_10(ctx: AgentContext) -> AgentOutput:
    """DEEP-10 — Open Question Tracker : Conserver les questions non résolues"""
    SPEC = _BY_ID['DEEP-10']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    rows = K.quotes(ctx.evidence)
    findings = [Finding(statement=quote[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"context": s[:200], "domain": d.domain,
                                  "lens": 'Open Question Tracker'})
                for d, quote, s in rows[:12]]
    metrics = {"quotes": len(rows), "domains": sorted({d.domain for d, _, _ in rows})}
    summary = f"{len(rows)} citations textuelles extraites avec leur contexte."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Open Question Tracker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['question', 'unknown', 'à déterminer']
    metrics["profile_label"] = 'Open Question Tracker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_01(ctx: AgentContext) -> AgentOutput:
    """NEWS-01 — Breaking Event Tracker : Isoler les événements datés récents"""
    SPEC = _BY_ID['NEWS-01']
    ctx.tools.use('stats')
    rows = K.dates_in_text(ctx.evidence)
    findings = [Finding(statement=f"{date} — {d.title or d.domain}",
                        score=0.62, evidence_ids=[d.id],
                        metadata={"date": date, "domain": d.domain, "lens": 'Breaking Event Tracker'})
                for d, date in rows[:12]]
    metrics = {"dated_mentions": len(rows),
               "unique_dates": sorted({date for _, date in rows})[:20],
               "recency": K.recency_scores(ctx.evidence)}
    summary = f"{len(rows)} mentions datées, {len(metrics['unique_dates'])} dates distinctes."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Breaking Event Tracker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['breaking', 'today', "aujourd'hui"]
    metrics["profile_label"] = 'Breaking Event Tracker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_02(ctx: AgentContext) -> AgentOutput:
    """NEWS-02 — Timeline Reconstructor : Reconstruire la chronologie des faits"""
    SPEC = _BY_ID['NEWS-02']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=0.62, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": 'Timeline Reconstructor'})
                for r in rows[:12]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Timeline Reconstructor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['yesterday', 'hier', 'then']
    metrics["profile_label"] = 'Timeline Reconstructor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_03(ctx: AgentContext) -> AgentOutput:
    """NEWS-03 — Wire Service Comparator : Comparer les couvertures par domaine de presse"""
    SPEC = _BY_ID['NEWS-03']
    ctx.tools.use('stats')
    dist = K.domain_distribution(ctx.evidence)
    prov = K.provenance(ctx.evidence)
    findings = [Finding(statement=f"{dom}: {count} source(s)",
                        score=min(1.0, 0.62 * count / max(1, len(ctx.evidence))),
                        evidence_ids=[d.id for d in ctx.evidence if d.domain == dom][:5],
                        metadata={"domain": dom, "count": count, "lens": 'Wire Service Comparator'})
                for dom, count in sorted(dist.items(), key=lambda x: -x[1])[:12]]
    metrics = {"distribution": dist, **prov}
    summary = f"{len(dist)} domaines, entropie {prov['domain_entropy']}, "               f"{prov['provider_count']} fournisseurs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Wire Service Comparator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['agency', 'wire', 'dépêche']
    metrics["profile_label"] = 'Wire Service Comparator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_04(ctx: AgentContext) -> AgentOutput:
    """NEWS-04 — Headline Framing Analyst : Analyser la structure des titres"""
    SPEC = _BY_ID['NEWS-04']
    ctx.tools.use('stats')
    rows = K.ngrams(ctx.evidence, n=2, top=12)
    findings = [Finding(statement=f"{phrase} ({count} occurrences)",
                        score=min(1.0, 0.62 * count / max(1, rows[0][1] if rows else 1)),
                        evidence_ids=[d.id for d in ctx.evidence
                                      if phrase.split()[0] in d.evidence_text().lower()][:3],
                        metadata={"ngram": phrase, "count": count, "lens": 'Headline Framing Analyst'})
                for phrase, count in rows]
    metrics = {"top_ngrams": rows, "distinct": len(rows)}
    summary = f"{len(rows)} n-grammes dominants, premier : "               f"{rows[0][0] if rows else 'aucun'}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Headline Framing Analyst', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['headline', 'titre', 'annonce']
    metrics["profile_label"] = 'Headline Framing Analyst'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_05(ctx: AgentContext) -> AgentOutput:
    """NEWS-05 — Recency Scorer : Noter la fraîcheur des sources"""
    SPEC = _BY_ID['NEWS-05']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    scores = K.recency_scores(ctx.evidence)
    findings = [Finding(statement=f"Fraîcheur {score:.2f} — {d.title or d.domain}",
                        score=min(1.0, 0.62 * (0.4 + score)),
                        evidence_ids=[d.id],
                        metadata={"recency": score, "published_at": d.published_at,
                                  "domain": d.domain, "lens": 'Recency Scorer'})
                for d, score in zip(ctx.evidence, scores) if score > 0][:12]
    metrics = {"recency_scores": scores,
               "dated_documents": sum(1 for s in scores if s > 0),
               "mean_recency": round(sum(scores) / max(1, len(scores)), 4)}
    summary = f"{metrics['dated_documents']} sources datées, fraîcheur moyenne "               f"{metrics['mean_recency']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Recency Scorer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['published', 'updated', 'hier']
    metrics["profile_label"] = 'Recency Scorer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_06(ctx: AgentContext) -> AgentOutput:
    """NEWS-06 — Local News Scanner : Repérer les mentions géographiques locales"""
    SPEC = _BY_ID['NEWS-06']
    ctx.tools.use('stats')
    ent = K.entities(ctx.evidence)
    findings = [Finding(statement=f"{kind}: {', '.join(values[:5])}",
                        score=0.62,
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"kind": kind, "values": values[:10], "lens": 'Local News Scanner'})
                for kind, values in ent.items() if values][:12]
    metrics = {"entity_counts": {k: len(v) for k, v in ent.items()},
               "emails": ent["emails"][:5]}
    summary = f"{sum(len(v) for v in ent.values())} entités nominatives ou techniques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Local News Scanner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['local', 'région', 'ville']
    metrics["profile_label"] = 'Local News Scanner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_07(ctx: AgentContext) -> AgentOutput:
    """NEWS-07 — Press Release Detector : Détecter le langage de communiqué"""
    SPEC = _BY_ID['NEWS-07']
    ctx.tools.use('stats')
    rows = K.stance_pairs(ctx.evidence,
                          [x.lower() for x in ['announces', 'annonce', 'declares']], ["not", "no", "never", "ne pas", "false"])
    counts = {"positive": 0, "negative": 0}
    findings = []
    for d, s, label in rows[:12]:
        counts[label] += 1
        findings.append(Finding(statement=f"[{label}] {s[:240]}", score=0.62,
                                evidence_ids=[d.id],
                                metadata={"stance": label, "domain": d.domain,
                                          "lens": 'Press Release Detector'}))
    metrics = {"stance_counts": {k: v for k, v in counts.items()},
               "total": len(rows)}
    summary = f"{len(rows)} énoncés polarisés : {counts['positive']} positifs, "               f"{counts['negative']} négatifs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Press Release Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['announces', 'annonce', 'declares']
    metrics["profile_label"] = 'Press Release Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_08(ctx: AgentContext) -> AgentOutput:
    """NEWS-08 — Event Deduplicator : Regrouper les doublons d'événements"""
    SPEC = _BY_ID['NEWS-08']
    ctx.tools.use('stats')
    clusters = K.similarity_clusters(ctx.evidence, max(0.1, 0.05 * 3))
    findings = [Finding(statement=f"Groupe de {len(c)} sources : {c[0].title[:120]}",
                        score=min(1.0, 0.62 + 0.05 * len(c)),
                        evidence_ids=[d.id for d in c[:5]],
                        metadata={"size": len(c), "domains": sorted({d.domain for d in c}),
                                  "lens": 'Event Deduplicator'})
                for c in clusters[:12]]
    metrics = {"clusters": len(clusters), "sizes": [len(c) for c in clusters],
               "similarity_threshold": 0.05}
    summary = f"{len(clusters)} groupes de sources similaires constitués."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Event Deduplicator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['same', 'identique', 'reprise']
    metrics["profile_label"] = 'Event Deduplicator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_09(ctx: AgentContext) -> AgentOutput:
    """NEWS-09 — Quote Attribution Checker : Extraire les citations et leur contexte"""
    SPEC = _BY_ID['NEWS-09']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    rows = K.quotes(ctx.evidence)
    findings = [Finding(statement=quote[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"context": s[:200], "domain": d.domain,
                                  "lens": 'Quote Attribution Checker'})
                for d, quote, s in rows[:12]]
    metrics = {"quotes": len(rows), "domains": sorted({d.domain for d, _, _ in rows})}
    summary = f"{len(rows)} citations textuelles extraites avec leur contexte."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Quote Attribution Checker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['said', 'selon', 'déclare']
    metrics["profile_label"] = 'Quote Attribution Checker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def news_10(ctx: AgentContext) -> AgentOutput:
    """NEWS-10 — Correction & Update Watcher : Repérer les correctifs et mises à jour"""
    SPEC = _BY_ID['NEWS-10']
    ctx.tools.use('stats')
    rows = K.negation_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"negation": cue, "domain": d.domain, "lens": 'Correction & Update Watcher'})
                for d, s, cue in rows[:12]]
    metrics = {"negated_sentences": len(rows), "cues": sorted({c for _, _, c in rows})}
    summary = f"{len(rows)} énoncés négatifs ou de démenti isolés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Correction & Update Watcher', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['correction', 'update', 'rectificatif']
    metrics["profile_label"] = 'Correction & Update Watcher'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_01(ctx: AgentContext) -> AgentOutput:
    """SCI-01 — Abstract Scanner : Extraire les énoncés de type résumé scientifique"""
    SPEC = _BY_ID['SCI-01']
    ctx.tools.use('stats')
    rows = K.claim_sentences(ctx.evidence)
    findings = [Finding(statement=s[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"domain": d.domain, "provider": d.provider,
                                  "verified": d.verified, "lens": 'Abstract Scanner'})
                for d, s in rows[:12]]
    metrics = {"claims": len(rows), "independent_domains":
               len({d.domain for d, _ in rows}),
               "supported_ratio": round(sum(1 for d, _ in rows if d.verified) /
                                        max(1, len(rows)), 4)}
    summary = f"{len(rows)} affirmations candidates, {metrics['independent_domains']} "               f"domaines indépendants."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Abstract Scanner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['abstract', 'objective', 'background']
    metrics["profile_label"] = 'Abstract Scanner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_02(ctx: AgentContext) -> AgentOutput:
    """SCI-02 — Methodology Extractor : Lire les paires clé/valeur méthodologiques"""
    SPEC = _BY_ID['SCI-02']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Methodology Extractor'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Methodology Extractor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['method', 'design', 'protocol']
    metrics["profile_label"] = 'Methodology Extractor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_03(ctx: AgentContext) -> AgentOutput:
    """SCI-03 — Sample Size Auditor : Repérer les effectifs et grandeurs numériques"""
    SPEC = _BY_ID['SCI-03']
    ctx.tools.use('stats')
    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in ['participants', 'sample', 'n =']])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": 'Sample Size Auditor'})
                for d, v, u, s in (focused or values)[:12]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Sample Size Auditor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['participants', 'sample', 'n =']
    metrics["profile_label"] = 'Sample Size Auditor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_04(ctx: AgentContext) -> AgentOutput:
    """SCI-04 — Statistical Result Reader : Lire les valeurs et unités statistiques"""
    SPEC = _BY_ID['SCI-04']
    ctx.tools.use('stats')
    conflicts = K.numeric_conflicts(ctx.evidence)
    values = K.numbers_with_units(ctx.evidence)
    findings = [Finding(statement=f"Valeurs divergentes : {c['value_a']} vs {c['value_b']} "
                                  f"(écart {c['relative_gap']})",
                        score=0.62, evidence_ids=[],
                        metadata={**c, "lens": 'Statistical Result Reader'})
                for c in conflicts[:12]]
    metrics = {"conflicts": len(conflicts), "numeric_mentions": len(values),
               "units": K.unit_distribution(ctx.evidence)}
    summary = f"{len(conflicts)} divergences numériques potentielles sur "               f"{len(values)} valeurs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Statistical Result Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['p-value', 'confidence', 'interval']
    metrics["profile_label"] = 'Statistical Result Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_05(ctx: AgentContext) -> AgentOutput:
    """SCI-05 — Citation Network Analyst : Construire le réseau de citations"""
    SPEC = _BY_ID['SCI-05']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, 0.62 * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": 'Citation Network Analyst'})
                for dom, count in graph["top_cited"][:12]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Citation Network Analyst', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['doi', 'cited', 'reference']
    metrics["profile_label"] = 'Citation Network Analyst'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_06(ctx: AgentContext) -> AgentOutput:
    """SCI-06 — Preprint Detector : Détecter les mentions de prépublication"""
    SPEC = _BY_ID['SCI-06']
    ctx.tools.use('stats')
    rows = K.version_mentions(ctx.evidence)
    findings = [Finding(statement=f"Version {ver} : {count} occurrence(s)",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence
                                                       if ver in d.evidence_text()][:3],
                        metadata={"version": ver, "count": count, "lens": 'Preprint Detector'})
                for ver, count in rows[:12]]
    metrics = {"versions": rows, "distinct": len(rows)}
    summary = f"{len(rows)} versions logicielles distinctes relevées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Preprint Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['preprint', 'arxiv', 'biorxiv']
    metrics["profile_label"] = 'Preprint Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_07(ctx: AgentContext) -> AgentOutput:
    """SCI-07 — Reproducibility Checker : Repérer les indices de reproductibilité"""
    SPEC = _BY_ID['SCI-07']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    gaps = K.evidence_gaps(ctx.evidence, ['replicate', 'code', 'dataset'])
    cov = K.coverage(ctx.evidence, ['replicate', 'code', 'dataset'])
    findings = [Finding(statement=f"Lacune : {gap}", score=0.62,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": 'Reproducibility Checker'})
                for gap in gaps[:12]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture "               f"{cov['covered']}/{cov['total_terms']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Reproducibility Checker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['replicate', 'code', 'dataset']
    metrics["profile_label"] = 'Reproducibility Checker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_08(ctx: AgentContext) -> AgentOutput:
    """SCI-08 — Peer Review Status Reader : Évaluer le niveau de validation des sources"""
    SPEC = _BY_ID['SCI-08']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    rows = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Score de crédibilité {score} pour {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"credibility": score, "lens": 'Peer Review Status Reader'})
                for sid, score in rows[:12]]
    metrics = {"scores": rows[:20],
               "mean": round(sum(s for _, s in rows) / max(1, len(rows)), 4),
               "types": K.source_types(ctx.evidence)}
    summary = f"Crédibilité moyenne {metrics['mean']} sur {len(rows)} sources."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Peer Review Status Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['peer-reviewed', 'reviewed', 'published']
    metrics["profile_label"] = 'Peer Review Status Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_09(ctx: AgentContext) -> AgentOutput:
    """SCI-09 — Conflict of Interest Scanner : Repérer les déclarations d'intérêts"""
    SPEC = _BY_ID['SCI-09']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Conflict of Interest Scanner'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Conflict of Interest Scanner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['funding', 'conflict', 'disclosure']
    metrics["profile_label"] = 'Conflict of Interest Scanner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def sci_10(ctx: AgentContext) -> AgentOutput:
    """SCI-10 — Evidence Grader : Noter la qualité des preuves scientifiques"""
    SPEC = _BY_ID['SCI-10']
    ctx.tools.use('stats')
    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": 'Evidence Grader'})
                for sid, score in cred[:12]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, "               f"ratio vérifié {prov['verified_ratio']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Evidence Grader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['evidence', 'grade', 'quality']
    metrics["profile_label"] = 'Evidence Grader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_01(ctx: AgentContext) -> AgentOutput:
    """TECH-01 — Release Note Reader : Extraire les versions et notes de version"""
    SPEC = _BY_ID['TECH-01']
    ctx.tools.use('stats')
    rows = K.version_mentions(ctx.evidence)
    findings = [Finding(statement=f"Version {ver} : {count} occurrence(s)",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence
                                                       if ver in d.evidence_text()][:3],
                        metadata={"version": ver, "count": count, "lens": 'Release Note Reader'})
                for ver, count in rows[:12]]
    metrics = {"versions": rows, "distinct": len(rows)}
    summary = f"{len(rows)} versions logicielles distinctes relevées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Release Note Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['release', 'shipped', 'version']
    metrics["profile_label"] = 'Release Note Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_02(ctx: AgentContext) -> AgentOutput:
    """TECH-02 — Version Tracker : Suivre l'évolution des numéros de version"""
    SPEC = _BY_ID['TECH-02']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    hits = K.regex_matches(ctx.evidence, '\\bv?\\d+\\.\\d+(?:\\.\\d+)?\\b')
    findings = [Finding(statement=f"{m} — {s[:220]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"match": m[:120], "domain": d.domain,
                                  "pattern": '\\bv?\\d+\\.\\d+(?:\\.\\d+)?\\b', "lens": 'Version Tracker'})
                for d, m, s in hits[:12]]
    metrics = {"regex_hits": len(hits), "pattern": '\\bv?\\d+\\.\\d+(?:\\.\\d+)?\\b',
               "domains": sorted({d.domain for d, _, _ in hits})}
    summary = f"{len(hits)} occurrences du motif analysées, {len(metrics['domains'])} domaines."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Version Tracker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['v1', 'v2', 'semver']
    metrics["profile_label"] = 'Version Tracker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_03(ctx: AgentContext) -> AgentOutput:
    """TECH-03 — API Surface Comparator : Comparer les surfaces d'API mentionnées"""
    SPEC = _BY_ID['TECH-03']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'API Surface Comparator'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'API Surface Comparator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['endpoint', 'parameter', 'response']
    metrics["profile_label"] = 'API Surface Comparator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_04(ctx: AgentContext) -> AgentOutput:
    """TECH-04 — Benchmark Interpreter : Lire les chiffres de performance"""
    SPEC = _BY_ID['TECH-04']
    ctx.tools.use('stats')
    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in ['latency', 'throughput', 'benchmark']])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": 'Benchmark Interpreter'})
                for d, v, u, s in (focused or values)[:12]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Benchmark Interpreter', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['latency', 'throughput', 'benchmark']
    metrics["profile_label"] = 'Benchmark Interpreter'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_05(ctx: AgentContext) -> AgentOutput:
    """TECH-05 — Dependency Graph Reader : Lire le graphe des dépendances citées"""
    SPEC = _BY_ID['TECH-05']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, 0.62 * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": 'Dependency Graph Reader'})
                for dom, count in graph["top_cited"][:12]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Dependency Graph Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['depends', 'package', 'module']
    metrics["profile_label"] = 'Dependency Graph Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_06(ctx: AgentContext) -> AgentOutput:
    """TECH-06 — Security Advisory Scanner : Détecter les avis de sécurité"""
    SPEC = _BY_ID['TECH-06']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    hits = K.regex_matches(ctx.evidence, '\\bCVE-\\d{4}-\\d{4,}\\b')
    findings = [Finding(statement=f"{m} — {s[:220]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"match": m[:120], "domain": d.domain,
                                  "pattern": '\\bCVE-\\d{4}-\\d{4,}\\b', "lens": 'Security Advisory Scanner'})
                for d, m, s in hits[:12]]
    metrics = {"regex_hits": len(hits), "pattern": '\\bCVE-\\d{4}-\\d{4,}\\b',
               "domains": sorted({d.domain for d, _, _ in hits})}
    summary = f"{len(hits)} occurrences du motif analysées, {len(metrics['domains'])} domaines."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Security Advisory Scanner', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['CVE', 'vulnerability', 'patch']
    metrics["profile_label"] = 'Security Advisory Scanner'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_07(ctx: AgentContext) -> AgentOutput:
    """TECH-07 — License Classifier : Classifier les licences mentionnées"""
    SPEC = _BY_ID['TECH-07']
    ctx.tools.use('stats')
    rows = K.licenses(ctx.evidence)
    findings = [Finding(statement=f"Licence {lic} : {count} mention(s)",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence
                                                       if lic.lower() in d.evidence_text().lower()][:3],
                        metadata={"license": lic, "count": count, "lens": 'License Classifier'})
                for lic, count in rows[:12]]
    metrics = {"licenses": rows, "distinct": len(rows)}
    summary = f"{len(rows)} licences distinctes détectées dans les preuves."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'License Classifier', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['license', 'MIT', 'Apache']
    metrics["profile_label"] = 'License Classifier'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_08(ctx: AgentContext) -> AgentOutput:
    """TECH-08 — Changelog Differ : Repérer les changements et contradictions"""
    SPEC = _BY_ID['TECH-08']
    ctx.tools.use('stats')
    signals = K.contradiction_signals(ctx.evidence)
    findings = [Finding(statement=f"Opposition (sim={s['similarity']}) : "
                                  f"{s['positive'][:110]} / {s['negative'][:110]}",
                        score=0.62, evidence_ids=s["evidence_ids"],
                        metadata={"cue": s["cue"], "domain_a": s["domain_a"],
                                  "domain_b": s["domain_b"], "lens": 'Changelog Differ'})
                for s in signals[:12]]
    metrics = {"signals": len(signals),
               "pairs": [(s["domain_a"], s["domain_b"]) for s in signals[:10]],
               "numeric_conflicts": K.numeric_conflicts(ctx.evidence)[:5]}
    summary = f"{len(signals)} signaux de contradiction inter-domaines."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Changelog Differ', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['added', 'removed', 'changed']
    metrics["profile_label"] = 'Changelog Differ'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_09(ctx: AgentContext) -> AgentOutput:
    """TECH-09 — Adoption Signal Reader : Mesurer les signaux d'adoption"""
    SPEC = _BY_ID['TECH-09']
    ctx.tools.use('stats')
    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in ['users', 'downloads', 'stars']])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": 'Adoption Signal Reader'})
                for d, v, u, s in (focused or values)[:12]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Adoption Signal Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['users', 'downloads', 'stars']
    metrics["profile_label"] = 'Adoption Signal Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def tech_10(ctx: AgentContext) -> AgentOutput:
    """TECH-10 — Deprecation Watcher : Repérer les mentions de dépréciation"""
    SPEC = _BY_ID['TECH-10']
    ctx.tools.use('stats')
    rows = K.negation_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"negation": cue, "domain": d.domain, "lens": 'Deprecation Watcher'})
                for d, s, cue in rows[:12]]
    metrics = {"negated_sentences": len(rows), "cues": sorted({c for _, _, c in rows})}
    summary = f"{len(rows)} énoncés négatifs ou de démenti isolés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Deprecation Watcher', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['deprecated', 'legacy', 'obsolete']
    metrics["profile_label"] = 'Deprecation Watcher'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_01(ctx: AgentContext) -> AgentOutput:
    """OSINT-01 — Repository Metadata Reader : Lire les métadonnées de dépôts"""
    SPEC = _BY_ID['OSINT-01']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Repository Metadata Reader'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Repository Metadata Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['repository', 'branch', 'license']
    metrics["profile_label"] = 'Repository Metadata Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_02(ctx: AgentContext) -> AgentOutput:
    """OSINT-02 — Commit Activity Analyst : Repérer l'activité de commits"""
    SPEC = _BY_ID['OSINT-02']
    ctx.tools.use('stats')
    rows = K.dates_in_text(ctx.evidence)
    findings = [Finding(statement=f"{date} — {d.title or d.domain}",
                        score=0.62, evidence_ids=[d.id],
                        metadata={"date": date, "domain": d.domain, "lens": 'Commit Activity Analyst'})
                for d, date in rows[:12]]
    metrics = {"dated_mentions": len(rows),
               "unique_dates": sorted({date for _, date in rows})[:20],
               "recency": K.recency_scores(ctx.evidence)}
    summary = f"{len(rows)} mentions datées, {len(metrics['unique_dates'])} dates distinctes."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Commit Activity Analyst', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['commit', 'merged', 'pushed']
    metrics["profile_label"] = 'Commit Activity Analyst'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_03(ctx: AgentContext) -> AgentOutput:
    """OSINT-03 — Maintainer Mapper : Cartographier les entités nommées"""
    SPEC = _BY_ID['OSINT-03']
    ctx.tools.use('stats')
    ent = K.entities(ctx.evidence)
    findings = [Finding(statement=f"{kind}: {', '.join(values[:5])}",
                        score=0.62,
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"kind": kind, "values": values[:10], "lens": 'Maintainer Mapper'})
                for kind, values in ent.items() if values][:12]
    metrics = {"entity_counts": {k: len(v) for k, v in ent.items()},
               "emails": ent["emails"][:5]}
    summary = f"{sum(len(v) for v in ent.values())} entités nominatives ou techniques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Maintainer Mapper', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['maintainer', 'author', 'contributor']
    metrics["profile_label"] = 'Maintainer Mapper'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_04(ctx: AgentContext) -> AgentOutput:
    """OSINT-04 — Issue Themes Extractor : Extraire les thèmes récurrents"""
    SPEC = _BY_ID['OSINT-04']
    ctx.tools.use('stats')
    rows = K.ngrams(ctx.evidence, n=2, top=12)
    findings = [Finding(statement=f"{phrase} ({count} occurrences)",
                        score=min(1.0, 0.62 * count / max(1, rows[0][1] if rows else 1)),
                        evidence_ids=[d.id for d in ctx.evidence
                                      if phrase.split()[0] in d.evidence_text().lower()][:3],
                        metadata={"ngram": phrase, "count": count, "lens": 'Issue Themes Extractor'})
                for phrase, count in rows]
    metrics = {"top_ngrams": rows, "distinct": len(rows)}
    summary = f"{len(rows)} n-grammes dominants, premier : "               f"{rows[0][0] if rows else 'aucun'}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Issue Themes Extractor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['issue', 'bug', 'feature']
    metrics["profile_label"] = 'Issue Themes Extractor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_05(ctx: AgentContext) -> AgentOutput:
    """OSINT-05 — Fork & Star Signals : Lire les signaux de popularité"""
    SPEC = _BY_ID['OSINT-05']
    ctx.tools.use('stats')
    values = [float(v) for _, v, _, _ in K.numbers_with_units(ctx.evidence)]
    rows = K.outliers(values, max(0.5, 0.05 * 10))
    findings = [Finding(statement=f"Valeur atypique {r['value']} (z={r['z']})",
                        score=0.62, evidence_ids=[],
                        metadata={**r, "lens": 'Fork & Star Signals'})
                for r in rows[:12]]
    metrics = {"outliers": rows, "values_tested": len(values),
               "mean": round(sum(values) / max(1, len(values)), 3)}
    summary = f"{len(rows)} valeurs aberrantes sur {len(values)} valeurs numériques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Fork & Star Signals', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['forks', 'stars', 'watchers']
    metrics["profile_label"] = 'Fork & Star Signals'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_06(ctx: AgentContext) -> AgentOutput:
    """OSINT-06 — Package Registry Checker : Repérer les paquets et versions"""
    SPEC = _BY_ID['OSINT-06']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    rows = K.version_mentions(ctx.evidence)
    findings = [Finding(statement=f"Version {ver} : {count} occurrence(s)",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence
                                                       if ver in d.evidence_text()][:3],
                        metadata={"version": ver, "count": count, "lens": 'Package Registry Checker'})
                for ver, count in rows[:12]]
    metrics = {"versions": rows, "distinct": len(rows)}
    summary = f"{len(rows)} versions logicielles distinctes relevées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Package Registry Checker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['npm', 'pypi', 'package']
    metrics["profile_label"] = 'Package Registry Checker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_07(ctx: AgentContext) -> AgentOutput:
    """OSINT-07 — Public Record Cross-check : Croiser les provenances des sources"""
    SPEC = _BY_ID['OSINT-07']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": 'Public Record Cross-check'})
                for sid, score in cred[:12]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, "               f"ratio vérifié {prov['verified_ratio']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Public Record Cross-check', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['record', 'registry', 'official']
    metrics["profile_label"] = 'Public Record Cross-check'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_08(ctx: AgentContext) -> AgentOutput:
    """OSINT-08 — Domain Chronology Reader : Ordonner les dates liées aux domaines"""
    SPEC = _BY_ID['OSINT-08']
    ctx.tools.use('stats')
    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=0.62, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": 'Domain Chronology Reader'})
                for r in rows[:12]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Domain Chronology Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['registered', 'created', 'expiry']
    metrics["profile_label"] = 'Domain Chronology Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_09(ctx: AgentContext) -> AgentOutput:
    """OSINT-09 — Geolocation Mention Extractor : Extraire les mentions géographiques"""
    SPEC = _BY_ID['OSINT-09']
    ctx.tools.use('stats')
    ent = K.entities(ctx.evidence)
    findings = [Finding(statement=f"{kind}: {', '.join(values[:5])}",
                        score=0.62,
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"kind": kind, "values": values[:10], "lens": 'Geolocation Mention Extractor'})
                for kind, values in ent.items() if values][:12]
    metrics = {"entity_counts": {k: len(v) for k, v in ent.items()},
               "emails": ent["emails"][:5]}
    summary = f"{sum(len(v) for v in ent.values())} entités nominatives ou techniques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Geolocation Mention Extractor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['Bamako', 'Paris', 'region']
    metrics["profile_label"] = 'Geolocation Mention Extractor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def osint_10(ctx: AgentContext) -> AgentOutput:
    """OSINT-10 — Source Provenance Tracer : Évaluer la traçabilité des preuves"""
    SPEC = _BY_ID['OSINT-10']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    rows = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Score de crédibilité {score} pour {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"credibility": score, "lens": 'Source Provenance Tracer'})
                for sid, score in rows[:12]]
    metrics = {"scores": rows[:20],
               "mean": round(sum(s for _, s in rows) / max(1, len(rows)), 4),
               "types": K.source_types(ctx.evidence)}
    summary = f"Crédibilité moyenne {metrics['mean']} sur {len(rows)} sources."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Source Provenance Tracer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['origin', 'trace', 'hash']
    metrics["profile_label"] = 'Source Provenance Tracer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_01(ctx: AgentContext) -> AgentOutput:
    """SOC-01 — Trend Signal Detector : Détecter les n-grammes émergents"""
    SPEC = _BY_ID['SOC-01']
    ctx.tools.use('stats')
    rows = K.ngrams(ctx.evidence, n=2, top=12)
    findings = [Finding(statement=f"{phrase} ({count} occurrences)",
                        score=min(1.0, 0.62 * count / max(1, rows[0][1] if rows else 1)),
                        evidence_ids=[d.id for d in ctx.evidence
                                      if phrase.split()[0] in d.evidence_text().lower()][:3],
                        metadata={"ngram": phrase, "count": count, "lens": 'Trend Signal Detector'})
                for phrase, count in rows]
    metrics = {"top_ngrams": rows, "distinct": len(rows)}
    summary = f"{len(rows)} n-grammes dominants, premier : "               f"{rows[0][0] if rows else 'aucun'}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Trend Signal Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['trend', 'viral', 'rising']
    metrics["profile_label"] = 'Trend Signal Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_02(ctx: AgentContext) -> AgentOutput:
    """SOC-02 — Post Cluster Analyst : Regrouper les publications similaires"""
    SPEC = _BY_ID['SOC-02']
    ctx.tools.use('stats')
    clusters = K.similarity_clusters(ctx.evidence, max(0.1, 0.05 * 3))
    findings = [Finding(statement=f"Groupe de {len(c)} sources : {c[0].title[:120]}",
                        score=min(1.0, 0.62 + 0.05 * len(c)),
                        evidence_ids=[d.id for d in c[:5]],
                        metadata={"size": len(c), "domains": sorted({d.domain for d in c}),
                                  "lens": 'Post Cluster Analyst'})
                for c in clusters[:12]]
    metrics = {"clusters": len(clusters), "sizes": [len(c) for c in clusters],
               "similarity_threshold": 0.05}
    summary = f"{len(clusters)} groupes de sources similaires constitués."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Post Cluster Analyst', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['post', 'thread', 'reply']
    metrics["profile_label"] = 'Post Cluster Analyst'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_03(ctx: AgentContext) -> AgentOutput:
    """SOC-03 — Hashtag Co-occurrence : Mesurer les co-occurrences de mots-clés"""
    SPEC = _BY_ID['SOC-03']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    pairs = K.cooccurrence(ctx.evidence, ['#', 'hashtag', 'tag'])
    findings = [Finding(statement=f"{x} ↔ {y} : {count} co-occurrences",
                        score=min(1.0, 0.62 * count / max(1, pairs[0][2] if pairs else 1)),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": 'Hashtag Co-occurrence'})
                for x, y, count in pairs[:12]]
    metrics = {"pairs": pairs, "focus": ['#', 'hashtag', 'tag']}
    summary = f"{len(pairs)} paires de termes co-occurrentes détectées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Hashtag Co-occurrence', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['#', 'hashtag', 'tag']
    metrics["profile_label"] = 'Hashtag Co-occurrence'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_04(ctx: AgentContext) -> AgentOutput:
    """SOC-04 — Sentiment Lexicon Scorer : Noter la polarité lexicale"""
    SPEC = _BY_ID['SOC-04']
    ctx.tools.use('stats')
    rows = K.stance_pairs(ctx.evidence,
                          [x.lower() for x in ['good', 'bad', 'excellent']], ["not", "no", "never", "ne pas", "false"])
    counts = {"positive": 0, "negative": 0}
    findings = []
    for d, s, label in rows[:12]:
        counts[label] += 1
        findings.append(Finding(statement=f"[{label}] {s[:240]}", score=0.62,
                                evidence_ids=[d.id],
                                metadata={"stance": label, "domain": d.domain,
                                          "lens": 'Sentiment Lexicon Scorer'}))
    metrics = {"stance_counts": {k: v for k, v in counts.items()},
               "total": len(rows)}
    summary = f"{len(rows)} énoncés polarisés : {counts['positive']} positifs, "               f"{counts['negative']} négatifs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Sentiment Lexicon Scorer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['good', 'bad', 'excellent']
    metrics["profile_label"] = 'Sentiment Lexicon Scorer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_05(ctx: AgentContext) -> AgentOutput:
    """SOC-05 — Bot Pattern Heuristic : Repérer les valeurs atypiques"""
    SPEC = _BY_ID['SOC-05']
    ctx.tools.use('stats')
    values = [float(v) for _, v, _, _ in K.numbers_with_units(ctx.evidence)]
    rows = K.outliers(values, max(0.5, 0.05 * 10))
    findings = [Finding(statement=f"Valeur atypique {r['value']} (z={r['z']})",
                        score=0.62, evidence_ids=[],
                        metadata={**r, "lens": 'Bot Pattern Heuristic'})
                for r in rows[:12]]
    metrics = {"outliers": rows, "values_tested": len(values),
               "mean": round(sum(values) / max(1, len(values)), 3)}
    summary = f"{len(rows)} valeurs aberrantes sur {len(values)} valeurs numériques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Bot Pattern Heuristic', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['automated', 'bot', 'repeat']
    metrics["profile_label"] = 'Bot Pattern Heuristic'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_06(ctx: AgentContext) -> AgentOutput:
    """SOC-06 — Influencer Reach Estimator : Lire les chiffres d'audience"""
    SPEC = _BY_ID['SOC-06']
    ctx.tools.use('stats')
    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in ['followers', 'views', 'reach']])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": 'Influencer Reach Estimator'})
                for d, v, u, s in (focused or values)[:12]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Influencer Reach Estimator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['followers', 'views', 'reach']
    metrics["profile_label"] = 'Influencer Reach Estimator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_07(ctx: AgentContext) -> AgentOutput:
    """SOC-07 — Discourse Frame Mapper : Cartographier les cadres de discours"""
    SPEC = _BY_ID['SOC-07']
    ctx.tools.use('stats')
    cov = K.coverage(ctx.evidence, ['frame', 'narrative', 'discourse'])
    findings = [Finding(statement=f"{term} : {count} énoncé(s)",
                        score=min(1.0, 0.62 * count / max(1, max(cov["per_term"].values()))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"term": term, "count": count, "lens": 'Discourse Frame Mapper'})
                for term, count in cov["per_term"].items()]
    metrics = {"coverage": cov, "gap_count": len(cov["gaps"])}
    summary = f"{cov['covered']}/{cov['total_terms']} angles couverts, "               f"{len(cov['gaps'])} absents."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Discourse Frame Mapper', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['frame', 'narrative', 'discourse']
    metrics["profile_label"] = 'Discourse Frame Mapper'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_08(ctx: AgentContext) -> AgentOutput:
    """SOC-08 — Viral Timeline Builder : Ordonner la propagation dans le temps"""
    SPEC = _BY_ID['SOC-08']
    ctx.tools.use('stats')
    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=0.62, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": 'Viral Timeline Builder'})
                for r in rows[:12]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Viral Timeline Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['first', 'then', 'spread']
    metrics["profile_label"] = 'Viral Timeline Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_09(ctx: AgentContext) -> AgentOutput:
    """SOC-09 — Community Overlap : Repérer les chevauchements de communautés"""
    SPEC = _BY_ID['SOC-09']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, 0.62 * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": 'Community Overlap'})
                for dom, count in graph["top_cited"][:12]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Community Overlap', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['community', 'group', 'subreddit']
    metrics["profile_label"] = 'Community Overlap'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def soc_10(ctx: AgentContext) -> AgentOutput:
    """SOC-10 — Rumor Propagation Tracer : Suivre les énoncés incertains"""
    SPEC = _BY_ID['SOC-10']
    ctx.tools.use('stats')
    rows = K.hedge_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"hedge": cue, "domain": d.domain, "lens": 'Rumor Propagation Tracer'})
                for d, s, cue in rows[:12]]
    metrics = {"hedged_sentences": len(rows),
               "hedge_rate": round(len(rows) / max(1, len(K.sentences(ctx.evidence))), 4),
               "cues": sorted({cue for _, _, cue in rows})}
    summary = f"{len(rows)} énoncés prudents ou hypothétiques repérés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Rumor Propagation Tracer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['allegedly', 'rumor', 'unconfirmed']
    metrics["profile_label"] = 'Rumor Propagation Tracer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_01(ctx: AgentContext) -> AgentOutput:
    """FACT-01 — Claim Extractor : Extraire les affirmations vérifiables"""
    SPEC = _BY_ID['FACT-01']
    ctx.tools.use('stats')
    rows = K.claim_sentences(ctx.evidence)
    findings = [Finding(statement=s[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"domain": d.domain, "provider": d.provider,
                                  "verified": d.verified, "lens": 'Claim Extractor'})
                for d, s in rows[:12]]
    metrics = {"claims": len(rows), "independent_domains":
               len({d.domain for d, _ in rows}),
               "supported_ratio": round(sum(1 for d, _ in rows if d.verified) /
                                        max(1, len(rows)), 4)}
    summary = f"{len(rows)} affirmations candidates, {metrics['independent_domains']} "               f"domaines indépendants."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Claim Extractor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['is', 'are', 'est']
    metrics["profile_label"] = 'Claim Extractor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_02(ctx: AgentContext) -> AgentOutput:
    """FACT-02 — Independent Corroborator : Compter les domaines indépendants"""
    SPEC = _BY_ID['FACT-02']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    dist = K.domain_distribution(ctx.evidence)
    prov = K.provenance(ctx.evidence)
    findings = [Finding(statement=f"{dom}: {count} source(s)",
                        score=min(1.0, 0.62 * count / max(1, len(ctx.evidence))),
                        evidence_ids=[d.id for d in ctx.evidence if d.domain == dom][:5],
                        metadata={"domain": dom, "count": count, "lens": 'Independent Corroborator'})
                for dom, count in sorted(dist.items(), key=lambda x: -x[1])[:12]]
    metrics = {"distribution": dist, **prov}
    summary = f"{len(dist)} domaines, entropie {prov['domain_entropy']}, "               f"{prov['provider_count']} fournisseurs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Independent Corroborator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['according', 'selon', 'reports']
    metrics["profile_label"] = 'Independent Corroborator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_03(ctx: AgentContext) -> AgentOutput:
    """FACT-03 — Primary Source Seeker : Repérer les sources primaires"""
    SPEC = _BY_ID['FACT-03']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": 'Primary Source Seeker'})
                for sid, score in cred[:12]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, "               f"ratio vérifié {prov['verified_ratio']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Primary Source Seeker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['official', 'primary', 'dataset']
    metrics["profile_label"] = 'Primary Source Seeker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_04(ctx: AgentContext) -> AgentOutput:
    """FACT-04 — Numeric Consistency Checker : Comparer les chiffres divergents"""
    SPEC = _BY_ID['FACT-04']
    ctx.tools.use('stats')
    conflicts = K.numeric_conflicts(ctx.evidence)
    values = K.numbers_with_units(ctx.evidence)
    findings = [Finding(statement=f"Valeurs divergentes : {c['value_a']} vs {c['value_b']} "
                                  f"(écart {c['relative_gap']})",
                        score=0.62, evidence_ids=[],
                        metadata={**c, "lens": 'Numeric Consistency Checker'})
                for c in conflicts[:12]]
    metrics = {"conflicts": len(conflicts), "numeric_mentions": len(values),
               "units": K.unit_distribution(ctx.evidence)}
    summary = f"{len(conflicts)} divergences numériques potentielles sur "               f"{len(values)} valeurs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Numeric Consistency Checker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['percent', 'million', 'rate']
    metrics["profile_label"] = 'Numeric Consistency Checker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_05(ctx: AgentContext) -> AgentOutput:
    """FACT-05 — Date Consistency Checker : Comparer les dates divergentes"""
    SPEC = _BY_ID['FACT-05']
    ctx.tools.use('stats')
    rows = K.dates_in_text(ctx.evidence)
    findings = [Finding(statement=f"{date} — {d.title or d.domain}",
                        score=0.62, evidence_ids=[d.id],
                        metadata={"date": date, "domain": d.domain, "lens": 'Date Consistency Checker'})
                for d, date in rows[:12]]
    metrics = {"dated_mentions": len(rows),
               "unique_dates": sorted({date for _, date in rows})[:20],
               "recency": K.recency_scores(ctx.evidence)}
    summary = f"{len(rows)} mentions datées, {len(metrics['unique_dates'])} dates distinctes."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Date Consistency Checker', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['2024', '2025', '2026']
    metrics["profile_label"] = 'Date Consistency Checker'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_06(ctx: AgentContext) -> AgentOutput:
    """FACT-06 — Quote Verifier : Vérifier les citations et leur attribution"""
    SPEC = _BY_ID['FACT-06']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    rows = K.quotes(ctx.evidence)
    findings = [Finding(statement=quote[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"context": s[:200], "domain": d.domain,
                                  "lens": 'Quote Verifier'})
                for d, quote, s in rows[:12]]
    metrics = {"quotes": len(rows), "domains": sorted({d.domain for d, _, _ in rows})}
    summary = f"{len(rows)} citations textuelles extraites avec leur contexte."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Quote Verifier', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['said', 'quoted', 'citation']
    metrics["profile_label"] = 'Quote Verifier'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_07(ctx: AgentContext) -> AgentOutput:
    """FACT-07 — Context Omission Detector : Détecter les énoncés prudentiels et omissions"""
    SPEC = _BY_ID['FACT-07']
    ctx.tools.use('stats')
    rows = K.hedge_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"hedge": cue, "domain": d.domain, "lens": 'Context Omission Detector'})
                for d, s, cue in rows[:12]]
    metrics = {"hedged_sentences": len(rows),
               "hedge_rate": round(len(rows) / max(1, len(K.sentences(ctx.evidence))), 4),
               "cues": sorted({cue for _, _, cue in rows})}
    summary = f"{len(rows)} énoncés prudents ou hypothétiques repérés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Context Omission Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['however', 'but', 'cependant']
    metrics["profile_label"] = 'Context Omission Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_08(ctx: AgentContext) -> AgentOutput:
    """FACT-08 — Misleading Headline Detector : Repérer les titres à polarité forte"""
    SPEC = _BY_ID['FACT-08']
    ctx.tools.use('stats')
    rows = K.stance_pairs(ctx.evidence,
                          [x.lower() for x in ['shocking', 'exclusive', 'urgent']], ["not", "no", "never", "ne pas", "false"])
    counts = {"positive": 0, "negative": 0}
    findings = []
    for d, s, label in rows[:12]:
        counts[label] += 1
        findings.append(Finding(statement=f"[{label}] {s[:240]}", score=0.62,
                                evidence_ids=[d.id],
                                metadata={"stance": label, "domain": d.domain,
                                          "lens": 'Misleading Headline Detector'}))
    metrics = {"stance_counts": {k: v for k, v in counts.items()},
               "total": len(rows)}
    summary = f"{len(rows)} énoncés polarisés : {counts['positive']} positifs, "               f"{counts['negative']} négatifs."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Misleading Headline Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['shocking', 'exclusive', 'urgent']
    metrics["profile_label"] = 'Misleading Headline Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_09(ctx: AgentContext) -> AgentOutput:
    """FACT-09 — Verdict Aggregator : Agrégér les signaux contradictoires"""
    SPEC = _BY_ID['FACT-09']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    signals = K.contradiction_signals(ctx.evidence)
    findings = [Finding(statement=f"Opposition (sim={s['similarity']}) : "
                                  f"{s['positive'][:110]} / {s['negative'][:110]}",
                        score=0.62, evidence_ids=s["evidence_ids"],
                        metadata={"cue": s["cue"], "domain_a": s["domain_a"],
                                  "domain_b": s["domain_b"], "lens": 'Verdict Aggregator'})
                for s in signals[:12]]
    metrics = {"signals": len(signals),
               "pairs": [(s["domain_a"], s["domain_b"]) for s in signals[:10]],
               "numeric_conflicts": K.numeric_conflicts(ctx.evidence)[:5]}
    summary = f"{len(signals)} signaux de contradiction inter-domaines."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Verdict Aggregator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['confirmed', 'false', 'unverified']
    metrics["profile_label"] = 'Verdict Aggregator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def fact_10(ctx: AgentContext) -> AgentOutput:
    """FACT-10 — Evidence Coverage Auditor : Auditer la couverture des preuves"""
    SPEC = _BY_ID['FACT-10']
    ctx.tools.use('stats')
    gaps = K.evidence_gaps(ctx.evidence, ['evidence', 'source', 'support'])
    cov = K.coverage(ctx.evidence, ['evidence', 'source', 'support'])
    findings = [Finding(statement=f"Lacune : {gap}", score=0.62,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": 'Evidence Coverage Auditor'})
                for gap in gaps[:12]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture "               f"{cov['covered']}/{cov['total_terms']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Evidence Coverage Auditor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['evidence', 'source', 'support']
    metrics["profile_label"] = 'Evidence Coverage Auditor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_01(ctx: AgentContext) -> AgentOutput:
    """DATA-01 — Dataset Metadata Reader : Lire les métadonnées de jeux de données"""
    SPEC = _BY_ID['DATA-01']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Dataset Metadata Reader'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Dataset Metadata Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['columns', 'rows', 'format']
    metrics["profile_label"] = 'Dataset Metadata Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_02(ctx: AgentContext) -> AgentOutput:
    """DATA-02 — Unit Normalizer : Classifier les unités et valeurs"""
    SPEC = _BY_ID['DATA-02']
    ctx.tools.use('stats')
    values = K.numbers_with_units(ctx.evidence)
    focused = [(d, v, u, s) for d, v, u, s in values
               if any(t in s.lower() for t in [x.lower() for x in ['kg', 'km', 'percent']])]
    findings = [Finding(statement=f"{v:g} {u} — {s[:200]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"value": v, "unit": u, "domain": d.domain,
                                  "lens": 'Unit Normalizer'})
                for d, v, u, s in (focused or values)[:12]]
    metrics = {"numeric_mentions": len(values), "focused_mentions": len(focused),
               "units": K.unit_distribution(ctx.evidence),
               "outliers": K.outliers([v for _, v, _, _ in values])}
    summary = f"{len(values)} valeurs numériques extraites, {len(focused)} ciblées."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Unit Normalizer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['kg', 'km', 'percent']
    metrics["profile_label"] = 'Unit Normalizer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_03(ctx: AgentContext) -> AgentOutput:
    """DATA-03 — Time Series Spotter : Repérer les séries temporelles"""
    SPEC = _BY_ID['DATA-03']
    ctx.tools.use('stats')
    rows = K.timeline(ctx.evidence)
    findings = [Finding(statement=f"{r['date']} — {r['title'][:120] or r['domain']}",
                        score=0.62, evidence_ids=[r["evidence_id"]],
                        metadata={"date": r["date"], "domain": r["domain"],
                                  "lens": 'Time Series Spotter'})
                for r in rows[:12]]
    metrics = {"events": len(rows), "first": rows[0]["date"] if rows else None,
               "last": rows[-1]["date"] if rows else None}
    summary = f"Chronologie de {len(rows)} événements datés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Time Series Spotter', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['monthly', 'quarterly', 'annual']
    metrics["profile_label"] = 'Time Series Spotter'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_04(ctx: AgentContext) -> AgentOutput:
    """DATA-04 — Outlier Detector : Détecter les valeurs aberrantes"""
    SPEC = _BY_ID['DATA-04']
    ctx.tools.use('stats')
    values = [float(v) for _, v, _, _ in K.numbers_with_units(ctx.evidence)]
    rows = K.outliers(values, max(0.5, 0.05 * 10))
    findings = [Finding(statement=f"Valeur atypique {r['value']} (z={r['z']})",
                        score=0.62, evidence_ids=[],
                        metadata={**r, "lens": 'Outlier Detector'})
                for r in rows[:12]]
    metrics = {"outliers": rows, "values_tested": len(values),
               "mean": round(sum(values) / max(1, len(values)), 3)}
    summary = f"{len(rows)} valeurs aberrantes sur {len(values)} valeurs numériques."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Outlier Detector', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['outlier', 'anomaly', 'spike']
    metrics["profile_label"] = 'Outlier Detector'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_05(ctx: AgentContext) -> AgentOutput:
    """DATA-05 — Missing Data Auditor : Lister les champs absents"""
    SPEC = _BY_ID['DATA-05']
    ctx.tools.use('stats')
    cov = K.coverage(ctx.evidence, ['missing', 'null', 'unknown'])
    findings = [Finding(statement=f"{term} : {count} énoncé(s)",
                        score=min(1.0, 0.62 * count / max(1, max(cov["per_term"].values()))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"term": term, "count": count, "lens": 'Missing Data Auditor'})
                for term, count in cov["per_term"].items()]
    metrics = {"coverage": cov, "gap_count": len(cov["gaps"])}
    summary = f"{cov['covered']}/{cov['total_terms']} angles couverts, "               f"{len(cov['gaps'])} absents."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Missing Data Auditor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['missing', 'null', 'unknown']
    metrics["profile_label"] = 'Missing Data Auditor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_06(ctx: AgentContext) -> AgentOutput:
    """DATA-06 — Schema Inference : Inférer un schéma à partir des paires clé/valeur"""
    SPEC = _BY_ID['DATA-06']
    ctx.tools.use('stats')
    pairs = K.key_values(ctx.evidence)
    inferred: dict[str, int] = {}
    for key, _ in pairs:
        inferred[key] = inferred.get(key, 0) + 1
    findings = [Finding(statement=f"{key}: {value[:120]}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:2],
                        metadata={"field": key, "occurrences": inferred.get(key, 0),
                                  "lens": 'Schema Inference'})
                for key, value in pairs[:12]]
    metrics = {"pairs": len(pairs), "fields": len(inferred),
               "top_fields": sorted(inferred.items(), key=lambda x: -x[1])[:10]}
    summary = f"{len(pairs)} paires clé/valeur, {len(inferred)} champs inférés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Schema Inference', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['type', 'field', 'value']
    metrics["profile_label"] = 'Schema Inference'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_07(ctx: AgentContext) -> AgentOutput:
    """DATA-07 — Statistical Summary : Produire les statistiques descriptives"""
    SPEC = _BY_ID['DATA-07']
    ctx.tools.use('stats')
    stats = K.length_stats(ctx.evidence)
    ranked = sorted(ctx.evidence, key=lambda d: -len(d.evidence_text()))[:12]
    findings = [Finding(statement=f"{len(d.evidence_text())} caractères — {d.title or d.domain}",
                        score=min(1.0, 0.62 * len(d.evidence_text()) /
                                  max(1, len(ranked[0].evidence_text()) if ranked else 1)),
                        evidence_ids=[d.id],
                        metadata={"words": len(d.evidence_text().split()),
                                  "domain": d.domain, "lens": 'Statistical Summary'})
                for d in ranked]
    metrics = {**stats, "ranked_domains": [d.domain for d in ranked]}
    summary = f"{stats['documents']} documents, {stats['total_words']} mots, "               f"moyenne {stats['mean_words']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Statistical Summary', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['mean', 'median', 'std']
    metrics["profile_label"] = 'Statistical Summary'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_08(ctx: AgentContext) -> AgentOutput:
    """DATA-08 — Correlation Signal Reader : Repérer les signaux de corrélation"""
    SPEC = _BY_ID['DATA-08']
    ctx.tools.use('stats')
    ctx.tools.use('graph')
    rows = K.correlation_signals(ctx.evidence)
    findings = [Finding(statement=f"{x} ↔ {y} : {count}",
                        score=0.62, evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"pair": [x, y], "count": count, "lens": 'Correlation Signal Reader'})
                for x, y, count in rows[:12]]
    metrics = {"signals": rows, "count": len(rows),
               "coverage": K.coverage(ctx.evidence, ['correlation', 'linked', 'associated'])}
    summary = f"{len(rows)} signaux de corrélation lexicale relevés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Correlation Signal Reader', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['correlation', 'linked', 'associated']
    metrics["profile_label"] = 'Correlation Signal Reader'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_09(ctx: AgentContext) -> AgentOutput:
    """DATA-09 — Data Source Lineage : Tracer l'origine des données"""
    SPEC = _BY_ID['DATA-09']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": 'Data Source Lineage'})
                for sid, score in cred[:12]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, "               f"ratio vérifié {prov['verified_ratio']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Data Source Lineage', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['source', 'origin', 'collected']
    metrics["profile_label"] = 'Data Source Lineage'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def data_10(ctx: AgentContext) -> AgentOutput:
    """DATA-10 — Reproducibility Pack Builder : Vérifier la complétude du paquet reproductible"""
    SPEC = _BY_ID['DATA-10']
    ctx.tools.use('stats')
    ctx.tools.use('memory')
    gaps = K.evidence_gaps(ctx.evidence, ['seed', 'version', 'script'])
    cov = K.coverage(ctx.evidence, ['seed', 'version', 'script'])
    findings = [Finding(statement=f"Lacune : {gap}", score=0.62,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": 'Reproducibility Pack Builder'})
                for gap in gaps[:12]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture "               f"{cov['covered']}/{cov['total_terms']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Reproducibility Pack Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['seed', 'version', 'script']
    metrics["profile_label"] = 'Reproducibility Pack Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_01(ctx: AgentContext) -> AgentOutput:
    """SYN-01 — Theme Clusterer : Regrouper les thèmes proches"""
    SPEC = _BY_ID['SYN-01']
    ctx.tools.use('stats')
    clusters = K.similarity_clusters(ctx.evidence, max(0.1, 0.05 * 3))
    findings = [Finding(statement=f"Groupe de {len(c)} sources : {c[0].title[:120]}",
                        score=min(1.0, 0.62 + 0.05 * len(c)),
                        evidence_ids=[d.id for d in c[:5]],
                        metadata={"size": len(c), "domains": sorted({d.domain for d in c}),
                                  "lens": 'Theme Clusterer'})
                for c in clusters[:12]]
    metrics = {"clusters": len(clusters), "sizes": [len(c) for c in clusters],
               "similarity_threshold": 0.05}
    summary = f"{len(clusters)} groupes de sources similaires constitués."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Theme Clusterer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['theme', 'topic', 'thème']
    metrics["profile_label"] = 'Theme Clusterer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_02(ctx: AgentContext) -> AgentOutput:
    """SYN-02 — Consensus Builder : Construire la liste des affirmations convergentes"""
    SPEC = _BY_ID['SYN-02']
    ctx.tools.use('stats')
    rows = K.claim_sentences(ctx.evidence)
    findings = [Finding(statement=s[:300], score=0.62,
                        evidence_ids=[d.id],
                        metadata={"domain": d.domain, "provider": d.provider,
                                  "verified": d.verified, "lens": 'Consensus Builder'})
                for d, s in rows[:12]]
    metrics = {"claims": len(rows), "independent_domains":
               len({d.domain for d, _ in rows}),
               "supported_ratio": round(sum(1 for d, _ in rows if d.verified) /
                                        max(1, len(rows)), 4)}
    summary = f"{len(rows)} affirmations candidates, {metrics['independent_domains']} "               f"domaines indépendants."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Consensus Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['consensus', 'agree', 'converge']
    metrics["profile_label"] = 'Consensus Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_03(ctx: AgentContext) -> AgentOutput:
    """SYN-03 — Conflict Arbitrator : Appliquer la règle d'arbitrage aux contradictions"""
    SPEC = _BY_ID['SYN-03']
    ctx.tools.use('stats')
    ctx.tools.use('graph')
    signals = K.contradiction_signals(ctx.evidence)
    findings = [Finding(statement=f"Opposition (sim={s['similarity']}) : "
                                  f"{s['positive'][:110]} / {s['negative'][:110]}",
                        score=0.62, evidence_ids=s["evidence_ids"],
                        metadata={"cue": s["cue"], "domain_a": s["domain_a"],
                                  "domain_b": s["domain_b"], "lens": 'Conflict Arbitrator'})
                for s in signals[:12]]
    metrics = {"signals": len(signals),
               "pairs": [(s["domain_a"], s["domain_b"]) for s in signals[:10]],
               "numeric_conflicts": K.numeric_conflicts(ctx.evidence)[:5]}
    summary = f"{len(signals)} signaux de contradiction inter-domaines."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Conflict Arbitrator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['however', 'versus', 'opposite']
    metrics["profile_label"] = 'Conflict Arbitrator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_04(ctx: AgentContext) -> AgentOutput:
    """SYN-04 — Citation Formatter : Construire la table des références"""
    SPEC = _BY_ID['SYN-04']
    ctx.tools.use('graph')
    ctx.tools.use('stats')
    graph = K.citation_graph(ctx.evidence)
    findings = [Finding(statement=f"{dom} cité {count} fois",
                        score=min(1.0, 0.62 * count /
                                  max(1, graph['top_cited'][0][1] if graph['top_cited'] else 1)),
                        evidence_ids=[d.id for d in ctx.evidence if dom in d.evidence_text()][:3],
                        metadata={"target": dom, "inbound": count, "lens": 'Citation Formatter'})
                for dom, count in graph["top_cited"][:12]]
    metrics = {"edges": graph["edges"], "nodes": graph["nodes"],
               "top_cited": graph["top_cited"]}
    summary = f"Graphe : {graph['nodes']} nœuds, {graph['edges']} arcs de référence."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Citation Formatter', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['reference', 'citation', 'source']
    metrics["profile_label"] = 'Citation Formatter'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_05(ctx: AgentContext) -> AgentOutput:
    """SYN-05 — Executive Summary Writer : Sélectionner les énoncés les plus denses"""
    SPEC = _BY_ID['SYN-05']
    ctx.tools.use('stats')
    ctx.tools.use('llm')
    stats = K.length_stats(ctx.evidence)
    ranked = sorted(ctx.evidence, key=lambda d: -len(d.evidence_text()))[:12]
    findings = [Finding(statement=f"{len(d.evidence_text())} caractères — {d.title or d.domain}",
                        score=min(1.0, 0.62 * len(d.evidence_text()) /
                                  max(1, len(ranked[0].evidence_text()) if ranked else 1)),
                        evidence_ids=[d.id],
                        metadata={"words": len(d.evidence_text().split()),
                                  "domain": d.domain, "lens": 'Executive Summary Writer'})
                for d in ranked]
    metrics = {**stats, "ranked_domains": [d.domain for d in ranked]}
    summary = f"{stats['documents']} documents, {stats['total_words']} mots, "               f"moyenne {stats['mean_words']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Executive Summary Writer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['summary', 'key', 'essential']
    metrics["profile_label"] = 'Executive Summary Writer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_06(ctx: AgentContext) -> AgentOutput:
    """SYN-06 — Limitations Writer : Lister les limites méthodologiques"""
    SPEC = _BY_ID['SYN-06']
    ctx.tools.use('stats')
    gaps = K.evidence_gaps(ctx.evidence, ['limitation', 'caveat', 'bias'])
    cov = K.coverage(ctx.evidence, ['limitation', 'caveat', 'bias'])
    findings = [Finding(statement=f"Lacune : {gap}", score=0.62,
                        evidence_ids=[],
                        metadata={"gap": gap, "lens": 'Limitations Writer'})
                for gap in gaps[:12]]
    metrics = {"gaps": gaps, "coverage": cov, "source_count": len(ctx.evidence)}
    summary = f"{len(gaps)} lacunes identifiées ; couverture "               f"{cov['covered']}/{cov['total_terms']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Limitations Writer', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['limitation', 'caveat', 'bias']
    metrics["profile_label"] = 'Limitations Writer'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_07(ctx: AgentContext) -> AgentOutput:
    """SYN-07 — Confidence Calibrator : Noter la crédibilité globale"""
    SPEC = _BY_ID['SYN-07']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    rows = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Score de crédibilité {score} pour {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"credibility": score, "lens": 'Confidence Calibrator'})
                for sid, score in rows[:12]]
    metrics = {"scores": rows[:20],
               "mean": round(sum(s for _, s in rows) / max(1, len(rows)), 4),
               "types": K.source_types(ctx.evidence)}
    summary = f"Crédibilité moyenne {metrics['mean']} sur {len(rows)} sources."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Confidence Calibrator', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['confidence', 'certainty', 'probability']
    metrics["profile_label"] = 'Confidence Calibrator'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_08(ctx: AgentContext) -> AgentOutput:
    """SYN-08 — Evidence Table Builder : Construire une table preuve/affirmation"""
    SPEC = _BY_ID['SYN-08']
    ctx.tools.use('stats')
    cov = K.coverage(ctx.evidence, ['evidence', 'claim', 'support'])
    findings = [Finding(statement=f"{term} : {count} énoncé(s)",
                        score=min(1.0, 0.62 * count / max(1, max(cov["per_term"].values()))),
                        evidence_ids=[d.id for d in ctx.evidence][:3],
                        metadata={"term": term, "count": count, "lens": 'Evidence Table Builder'})
                for term, count in cov["per_term"].items()]
    metrics = {"coverage": cov, "gap_count": len(cov["gaps"])}
    summary = f"{cov['covered']}/{cov['total_terms']} angles couverts, "               f"{len(cov['gaps'])} absents."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Evidence Table Builder', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['evidence', 'claim', 'support']
    metrics["profile_label"] = 'Evidence Table Builder'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_09(ctx: AgentContext) -> AgentOutput:
    """SYN-09 — Narrative Coherence Editor : Vérifier la cohérence des énoncés"""
    SPEC = _BY_ID['SYN-09']
    ctx.tools.use('stats')
    ctx.tools.use('llm')
    rows = K.hedge_sentences(ctx.evidence)
    findings = [Finding(statement=f"[{cue}] {s[:240]}", score=0.62,
                        evidence_ids=[d.id],
                        metadata={"hedge": cue, "domain": d.domain, "lens": 'Narrative Coherence Editor'})
                for d, s, cue in rows[:12]]
    metrics = {"hedged_sentences": len(rows),
               "hedge_rate": round(len(rows) / max(1, len(K.sentences(ctx.evidence))), 4),
               "cues": sorted({cue for _, _, cue in rows})}
    summary = f"{len(rows)} énoncés prudents ou hypothétiques repérés."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Narrative Coherence Editor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['therefore', 'thus', 'ainsi']
    metrics["profile_label"] = 'Narrative Coherence Editor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

def syn_10(ctx: AgentContext) -> AgentOutput:
    """SYN-10 — Final Report Auditor : Auditer la traçabilité finale"""
    SPEC = _BY_ID['SYN-10']
    ctx.tools.use('stats')
    ctx.tools.use('verify')
    ctx.tools.use('memory')
    prov = K.provenance(ctx.evidence)
    cred = K.credibility(ctx.evidence)
    findings = [Finding(statement=f"Crédibilité {score:.2f} — {sid}",
                        score=min(1.0, 0.62 * (0.3 + score)),
                        evidence_ids=[sid],
                        metadata={"provider_distribution": prov["provider_distribution"],
                                  "lens": 'Final Report Auditor'})
                for sid, score in cred[:12]]
    metrics = {**prov, "credibility": cred[:10]}
    summary = f"{prov['provider_count']} fournisseurs, {prov['domain_count']} domaines, "               f"ratio vérifié {prov['verified_ratio']}."
    findings = [f for f in findings if f.score >= 0.05]
    if not findings:
        findings.append(Finding(
            statement="Aucun signal détecté pour ce profil dans les preuves disponibles.",
            score=0.0, evidence_ids=[],
            metadata={"lens": 'Final Report Auditor', "empty": True, "documents": len(ctx.evidence)}))
    metrics["profile_focus"] = ['audit', 'trace', 'verified']
    metrics["profile_label"] = 'Final Report Auditor'
    metrics["profile_bias"] = 0.62
    return build_output(ctx, SPEC, findings, metrics, summary)

HANDLERS = {
    'WEB-01': web_01,
    'WEB-02': web_02,
    'WEB-03': web_03,
    'WEB-04': web_04,
    'WEB-05': web_05,
    'WEB-06': web_06,
    'WEB-07': web_07,
    'WEB-08': web_08,
    'WEB-09': web_09,
    'WEB-10': web_10,
    'DEEP-01': deep_01,
    'DEEP-02': deep_02,
    'DEEP-03': deep_03,
    'DEEP-04': deep_04,
    'DEEP-05': deep_05,
    'DEEP-06': deep_06,
    'DEEP-07': deep_07,
    'DEEP-08': deep_08,
    'DEEP-09': deep_09,
    'DEEP-10': deep_10,
    'NEWS-01': news_01,
    'NEWS-02': news_02,
    'NEWS-03': news_03,
    'NEWS-04': news_04,
    'NEWS-05': news_05,
    'NEWS-06': news_06,
    'NEWS-07': news_07,
    'NEWS-08': news_08,
    'NEWS-09': news_09,
    'NEWS-10': news_10,
    'SCI-01': sci_01,
    'SCI-02': sci_02,
    'SCI-03': sci_03,
    'SCI-04': sci_04,
    'SCI-05': sci_05,
    'SCI-06': sci_06,
    'SCI-07': sci_07,
    'SCI-08': sci_08,
    'SCI-09': sci_09,
    'SCI-10': sci_10,
    'TECH-01': tech_01,
    'TECH-02': tech_02,
    'TECH-03': tech_03,
    'TECH-04': tech_04,
    'TECH-05': tech_05,
    'TECH-06': tech_06,
    'TECH-07': tech_07,
    'TECH-08': tech_08,
    'TECH-09': tech_09,
    'TECH-10': tech_10,
    'OSINT-01': osint_01,
    'OSINT-02': osint_02,
    'OSINT-03': osint_03,
    'OSINT-04': osint_04,
    'OSINT-05': osint_05,
    'OSINT-06': osint_06,
    'OSINT-07': osint_07,
    'OSINT-08': osint_08,
    'OSINT-09': osint_09,
    'OSINT-10': osint_10,
    'SOC-01': soc_01,
    'SOC-02': soc_02,
    'SOC-03': soc_03,
    'SOC-04': soc_04,
    'SOC-05': soc_05,
    'SOC-06': soc_06,
    'SOC-07': soc_07,
    'SOC-08': soc_08,
    'SOC-09': soc_09,
    'SOC-10': soc_10,
    'FACT-01': fact_01,
    'FACT-02': fact_02,
    'FACT-03': fact_03,
    'FACT-04': fact_04,
    'FACT-05': fact_05,
    'FACT-06': fact_06,
    'FACT-07': fact_07,
    'FACT-08': fact_08,
    'FACT-09': fact_09,
    'FACT-10': fact_10,
    'DATA-01': data_01,
    'DATA-02': data_02,
    'DATA-03': data_03,
    'DATA-04': data_04,
    'DATA-05': data_05,
    'DATA-06': data_06,
    'DATA-07': data_07,
    'DATA-08': data_08,
    'DATA-09': data_09,
    'DATA-10': data_10,
    'SYN-01': syn_01,
    'SYN-02': syn_02,
    'SYN-03': syn_03,
    'SYN-04': syn_04,
    'SYN-05': syn_05,
    'SYN-06': syn_06,
    'SYN-07': syn_07,
    'SYN-08': syn_08,
    'SYN-09': syn_09,
    'SYN-10': syn_10,
}


def handler_for(agent_id: str):
    return HANDLERS[agent_id]
