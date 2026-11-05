"""Noyaux d'analyse déterministes utilisés par les 100 agents.

Chaque fonction fait un calcul réel sur les preuves collectées (textes, URL,
dates, nombres, domaines). Aucune ne produit de « résultat de recherche » :
elles transforment uniquement des preuves déjà obtenues.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from ..core.schemas import SourceRecord

_SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n+")
_NUMBER = re.compile(r"(?<![\w])(-?\d[\d\s.,]*)\s*(%|percent|million|milliard|billion|"
                     r"km|kg|ms|s|gb|mb|tb|€|\$|usd|eur|px|x)?", re.I)
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
                   r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}|"
                   r"\b(?:19|20)\d{2}\b)", re.I)
_QUOTE = re.compile(r"[«\"“']([^»\"”']{15,300})[»\"”']")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_VERSION = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?(?:[-.][a-z0-9]+)?\b", re.I)
_CAPITALIZED = re.compile(r"\b[A-ZÀ-Ý][\wÀ-ÿ-]{2,}(?:\s+[A-ZÀ-Ý][\wÀ-ÿ-]{2,}){0,3}\b")
_KEYVALUE = re.compile(r"\b([A-Za-z_][\w .-]{1,40})\s*[:=]\s*([^\n;]{1,120})")

_HEDGES = ("peut-être", "possible", "semble", "pourrait", "probablement", "selon",
           "might", "may", "could", "appears", "suggests", "possibly", "unclear",
           "allegedly", "reportedly", "estimé", "incertain")
_NEGATIONS = ("ne pas", "n'est pas", "no ", "not ", "never", "aucun", "aucune",
              "false", "incorrect", "dément", "denied", "refuted", "contrary")
_ASSERTIONS = ("est ", "sont ", "a ", "ont ", "is ", "are ", "shows", "confirms",
               "démontre", "établit", "rapporte", "indique", "selon")
_STOPWORDS = {
    "fr": {"le", "la", "les", "de", "des", "du", "et", "en", "un", "une", "que", "dans",
           "pour", "est", "sur", "par", "au", "aux", "avec", "ce", "cette", "plus"},
    "en": {"the", "and", "of", "to", "in", "a", "is", "are", "for", "on", "with",
           "that", "this", "by", "as", "from", "it", "was", "be"},
}
_LICENSES = ("MIT", "Apache-2.0", "GPL", "AGPL", "BSD", "MPL", "LGPL", "CC-BY",
             "proprietary", "ISC", "Unlicense")
_UNITS = {"%": "ratio", "percent": "ratio", "million": "count", "milliard": "count",
          "billion": "count", "km": "distance", "kg": "mass", "ms": "time",
          "gb": "storage", "mb": "storage", "tb": "storage", "€": "money",
          "$": "money", "usd": "money", "eur": "money"}


def doc_text(doc: SourceRecord) -> str:
    return doc.evidence_text()


def sentences(docs: Iterable[SourceRecord], limit: int = 400) -> list[tuple[SourceRecord, str]]:
    out: list[tuple[SourceRecord, str]] = []
    for doc in docs:
        for sentence in _SENT_SPLIT.split(doc_text(doc)):
            sentence = " ".join(sentence.split())
            if 20 <= len(sentence) <= 600:
                out.append((doc, sentence))
    return out[:limit]


def shannon_entropy(counts: Iterable[int]) -> float:
    values = [c for c in counts if c > 0]
    total = sum(values)
    if not total:
        return 0.0
    return round(-sum((v / total) * math.log2(v / total) for v in values), 4)


def focus_matches(docs: list[SourceRecord], terms: list[str],
                  limit: int = 60) -> list[tuple[SourceRecord, str, list[str]]]:
    lowered = [t.lower() for t in terms]
    out: list[tuple[SourceRecord, str, list[str]]] = []
    for doc, sentence in sentences(docs):
        low = sentence.lower()
        matched = [t for t, lt in zip(terms, lowered) if lt in low]
        if matched:
            out.append((doc, sentence, matched))
    return out[:limit]


def regex_matches(docs: list[SourceRecord], pattern: str,
                  limit: int = 60) -> list[tuple[SourceRecord, str, str]]:
    compiled = re.compile(pattern, re.I)
    out: list[tuple[SourceRecord, str, str]] = []
    for doc, sentence in sentences(docs):
        m = compiled.search(sentence)
        if m:
            out.append((doc, m.group(0), sentence))
    return out[:limit]


def numbers_with_units(docs: list[SourceRecord]) -> list[tuple[SourceRecord, float, str, str]]:
    out: list[tuple[SourceRecord, float, str, str]] = []
    for doc, sentence in sentences(docs):
        for raw, unit in _NUMBER.findall(sentence):
            try:
                value = float(raw.replace(" ", "").replace(",", "."))
            except ValueError:
                continue
            if abs(value) < 1e12:
                out.append((doc, value, (unit or "").lower(), sentence))
    return out


def dates_in_text(docs: list[SourceRecord]) -> list[tuple[SourceRecord, str]]:
    out: list[tuple[SourceRecord, str]] = []
    for doc, sentence in sentences(docs):
        for match in _DATE.finditer(sentence):
            out.append((doc, match.group(1)))
    return out


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value)[:40].strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y",
                "%d-%m-%Y", "%Y"):
        try:
            return datetime.strptime(text.split("T")[0] if fmt.startswith("%Y-%m-%d") else text, fmt)
        except ValueError:
            continue
    year = re.search(r"\b(19|20)\d{2}\b", text)
    if year:
        try:
            return datetime(int(year.group(0)), 1, 1)
        except ValueError:
            return None
    return None


def domain_distribution(docs: list[SourceRecord]) -> dict[str, int]:
    return dict(Counter(d.domain or "inconnu" for d in docs))


def jaccard(a: str, b: str) -> float:
    sa, sb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    if not sa or not sb:
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 4)


def similarity_clusters(docs: list[SourceRecord],
                        threshold: float = 0.35) -> list[list[SourceRecord]]:
    clusters: list[list[SourceRecord]] = []
    for doc in docs:
        placed = False
        for cluster in clusters:
            if jaccard(doc.title + " " + doc.snippet,
                       cluster[0].title + " " + cluster[0].snippet) >= threshold:
                cluster.append(doc)
                placed = True
                break
        if not placed:
            clusters.append([doc])
    return clusters


def hedge_sentences(docs: list[SourceRecord]) -> list[tuple[SourceRecord, str, str]]:
    out = []
    for doc, sentence in sentences(docs):
        low = sentence.lower()
        for hedge in _HEDGES:
            if hedge in low:
                out.append((doc, sentence, hedge))
                break
    return out


def negation_sentences(docs: list[SourceRecord]) -> list[tuple[SourceRecord, str, str]]:
    out = []
    for doc, sentence in sentences(docs):
        low = sentence.lower()
        for neg in _NEGATIONS:
            if neg in low:
                out.append((doc, sentence, neg))
                break
    return out


def contradiction_signals(docs: list[SourceRecord],
                          limit: int = 40) -> list[dict[str, Any]]:
    affirm, negations = [], negation_sentences(docs)
    for doc, sentence in sentences(docs):
        if any(a in sentence.lower() for a in _ASSERTIONS):
            affirm.append((doc, sentence))
    out: list[dict[str, Any]] = []
    for doc_a, positive in affirm:
        for doc_b, negative, cue in negations:
            if doc_a.domain == doc_b.domain:
                continue
            sim = jaccard(positive, negative)
            if sim >= 0.18:
                out.append({"positive": positive, "negative": negative, "cue": cue,
                            "similarity": sim, "domain_a": doc_a.domain,
                            "domain_b": doc_b.domain,
                            "evidence_ids": [doc_a.id, doc_b.id]})
        if len(out) >= limit:
            break
    return out


def quotes(docs: list[SourceRecord]) -> list[tuple[SourceRecord, str, str]]:
    out = []
    for doc, sentence in sentences(docs):
        for quote in _QUOTE.findall(sentence):
            out.append((doc, quote.strip(), sentence))
    return out


def ngrams(docs: list[SourceRecord], n: int = 2, top: int = 20) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for doc in docs:
        words = [w for w in re.findall(r"[a-zà-ÿ0-9]+", doc_text(doc).lower()) if len(w) > 2]
        for i in range(max(0, len(words) - n + 1)):
            counter[" ".join(words[i:i + n])] += 1
    return counter.most_common(top)


def entities(docs: list[SourceRecord]) -> dict[str, list[str]]:
    emails: set[str] = set()
    versions: set[str] = set()
    names: set[str] = set()
    for doc in docs:
        text = doc_text(doc)
        emails.update(_EMAIL.findall(text))
        versions.update(_VERSION.findall(text))
        names.update(m.group(0) for m in _CAPITALIZED.finditer(text))
    return {"emails": sorted(emails)[:30], "versions": sorted(versions)[:30],
            "named_entities": sorted(names)[:40]}


def key_values(docs: list[SourceRecord]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for doc in docs:
        for key, value in _KEYVALUE.findall(doc_text(doc)):
            out.append((key.strip().lower()[:40], value.strip()[:80]))
    return out[:100]


def recency_scores(docs: list[SourceRecord], now: datetime | None = None) -> list[float]:
    now = now or datetime.utcnow()
    scores = []
    for doc in docs:
        parsed = parse_date(doc.published_at)
        if parsed is None:
            scores.append(0.0)
            continue
        days = max(0, (now - parsed).days)
        scores.append(round(max(0.0, 1.0 - days / 730.0), 4))
    return scores


def provenance(docs: list[SourceRecord]) -> dict[str, Any]:
    providers = Counter(d.provider or "inconnu" for d in docs)
    domains = Counter(d.domain for d in docs)
    return {
        "provider_count": len(providers),
        "provider_distribution": dict(providers),
        "domain_count": len(domains),
        "domain_entropy": shannon_entropy(domains.values()),
        "verified_ratio": round(sum(1 for d in docs if d.verified) / len(docs), 4) if docs else 0.0,
        "https_ratio": round(sum(1 for d in docs if d.url.startswith("https://")) / len(docs), 4)
        if docs else 0.0,
        "injection_flags": sum(len(d.injection_flags) for d in docs),
    }


def coverage(docs: list[SourceRecord], terms: list[str]) -> dict[str, Any]:
    per_term = {t: sum(1 for _, s, _ in focus_matches(docs, [t], limit=1000))
                for t in terms}
    return {"per_term": per_term, "covered": sum(1 for v in per_term.values() if v),
            "total_terms": len(terms),
            "gaps": [t for t, v in per_term.items() if v == 0]}


def cooccurrence(docs: list[SourceRecord], terms: list[str]) -> list[tuple[str, str, int]]:
    counts: Counter[tuple[str, str]] = Counter()
    for _, sentence, matched in focus_matches(docs, terms, limit=1000):
        for i, a in enumerate(sorted(matched)):
            for b in sorted(matched)[i + 1:]:
                counts[(a, b)] += 1
    return [(a, b, c) for (a, b), c in counts.most_common(20)]


def numeric_conflicts(docs: list[SourceRecord]) -> list[dict[str, Any]]:
    by_domain: dict[str, set[float]] = defaultdict(set)
    for doc, value, unit, sentence in numbers_with_units(docs):
        if unit in {"", "ratio"} or "%" in unit:
            by_domain[doc.domain].add(round(value, 3))
    conflicts = []
    values = sorted({v for s in by_domain.values() for v in s})
    for i, a in enumerate(values):
        for b in values[i + 1:]:
            if a and b and abs(a - b) / max(abs(a), abs(b)) > 0.25:
                conflicts.append({"value_a": a, "value_b": b,
                                  "relative_gap": round(abs(a - b) / max(abs(a), abs(b)), 3)})
    return conflicts[:20]


def stance_pairs(docs: list[SourceRecord], positive: list[str],
                 negative: list[str]) -> list[tuple[SourceRecord, str, str]]:
    out = []
    for doc, sentence in sentences(docs):
        low = sentence.lower()
        pos = sum(1 for p in positive if p in low)
        neg = sum(1 for n in negative if n in low)
        if pos or neg:
            out.append((doc, sentence, "positive" if pos >= neg else "negative"))
    return out


def length_stats(docs: list[SourceRecord]) -> dict[str, float]:
    lengths = [len(re.findall(r"\w+", doc_text(d))) for d in docs]
    if not lengths:
        return {"documents": 0, "mean_words": 0.0, "max_words": 0,
                "min_words": 0, "total_words": 0}
    return {"documents": len(lengths), "mean_words": round(sum(lengths) / len(lengths), 2),
            "max_words": max(lengths), "min_words": min(lengths),
            "total_words": sum(lengths)}


def claim_sentences(docs: list[SourceRecord]) -> list[tuple[SourceRecord, str]]:
    return [(d, s) for d, s in sentences(docs)
            if any(a in s.lower() for a in _ASSERTIONS) and len(s) > 30]


def citation_graph(docs: list[SourceRecord]) -> dict[str, Any]:
    edges: Counter[tuple[str, str]] = Counter()
    for doc in docs:
        for other in re.findall(r"https?://([\w.-]+)", doc_text(doc)):
            target = other.lower().removeprefix("www.")
            if target != doc.domain:
                edges[(doc.domain, target)] += 1
    indegree: Counter[str] = Counter()
    for (_, target), count in edges.items():
        indegree[target] += count
    return {"edges": len(edges), "top_cited": indegree.most_common(10),
            "nodes": len({d.domain for d in docs} | set(indegree))}


def outliers(values: list[float], z_threshold: float = 1.8) -> list[dict[str, float]]:
    if len(values) < 3:
        return []
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) or 1.0
    return [{"index": float(i), "value": v, "z": round((v - mean) / std, 3)}
            for i, v in enumerate(values) if abs(v - mean) / std > z_threshold]


def language_guess(docs: list[SourceRecord]) -> dict[str, float]:
    tokens = [w.lower() for w in re.findall(r"[a-zà-ÿ]+", " ".join(doc_text(d) for d in docs))]
    if not tokens:
        return {"fr": 0.0, "en": 0.0}
    return {lang: round(sum(1 for t in tokens if t in words) / len(tokens), 4)
            for lang, words in _STOPWORDS.items()}


def licenses(docs: list[SourceRecord]) -> list[tuple[str, int]]:
    text = " ".join(doc_text(d) for d in docs).lower()
    return [(lic, text.count(lic.lower())) for lic in _LICENSES if lic.lower() in text]


def version_mentions(docs: list[SourceRecord]) -> list[tuple[str, int]]:
    return Counter(v for d in docs for v in _VERSION.findall(doc_text(d))).most_common(20)


def timeline(docs: list[SourceRecord]) -> list[dict[str, Any]]:
    rows = []
    for doc, date in dates_in_text(docs):
        parsed = parse_date(date)
        rows.append({"date": date, "sortable": parsed.isoformat() if parsed else "",
                     "domain": doc.domain, "title": doc.title,
                     "evidence_id": doc.id})
    return sorted(rows, key=lambda r: r["sortable"] or "9999")[:40]


def credibility(docs: list[SourceRecord]) -> list[tuple[str, float]]:
    out = []
    for doc in docs:
        score = 0.2
        if doc.url.startswith("https://"):
            score += 0.15
        if doc.verified:
            score += 0.2
        if any(tld in doc.domain for tld in (".gov", ".edu", ".org", ".int")):
            score += 0.2
        if doc.published_at:
            score += 0.1
        if doc.provider:
            score += 0.1
        score -= min(0.2, 0.05 * len(doc.injection_flags))
        out.append((doc.id, round(min(1.0, score), 3)))
    return out


def source_types(docs: list[SourceRecord]) -> dict[str, int]:
    buckets: Counter[str] = Counter()
    for doc in docs:
        low = doc_text(doc).lower()
        if any(k in low for k in ("abstract", "methodology", "peer review", "doi")):
            buckets["scientific"] += 1
        elif any(k in low for k in ("press release", "communiqué", "journalist")):
            buckets["press"] += 1
        elif any(k in low for k in ("release notes", "changelog", "api", "github")):
            buckets["technical"] += 1
        elif any(k in low for k in ("dataset", "csv", "table", "statistics")):
            buckets["data"] += 1
        else:
            buckets["web_general"] += 1
    return dict(buckets)


def unit_distribution(docs: list[SourceRecord]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for _, _, unit, _ in numbers_with_units(docs):
        counter[_UNITS.get(unit, unit or "unspecified")] += 1
    return dict(counter)


def evidence_gaps(docs: list[SourceRecord], terms: list[str]) -> list[str]:
    cov = coverage(docs, terms)
    gaps = list(cov["gaps"])
    if not docs:
        gaps.append("aucune_source")
    if len({d.domain for d in docs}) < 2:
        gaps.append("independance_des_sources_insuffisante")
    if not any(d.verified for d in docs):
        gaps.append("sources_non_verifiees_http")
    return gaps


def correlation_signals(docs: list[SourceRecord]) -> list[tuple[str, str, int]]:
    return cooccurrence(docs, ["increase", "decrease", "hausse", "baisse", "correlation",
                               "linked", "associated", "impact", "growth"])
