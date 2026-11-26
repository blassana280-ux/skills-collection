"""Corpus de TEST hors ligne.

CECI N'EST PAS UN RÉSULTAT DE RECHERCHE RÉEL. Ce jeu de données est utilisé
exclusivement par les tests, via un double de test HTTP déclaré
`test_double=True`. Le code de production ne contient aucune donnée de ce type
et ne fabrique jamais de résultat de recherche.
"""
from __future__ import annotations

CORPUS: list[dict[str, str]] = [
    {
        "url": "https://example.org/research/2025-report",
        "title": "Rapport 2025 sur les API et les études",
        "content": ("Une étude publiée le 2025-03-01 montre une hausse de 12 % des API. "
                    "Selon le rapport officiel, la version 2.3.1 corrige CVE-2024-1234. "
                    "Method: randomized sample, n = 240. DOI: 10.1234/example.2025. "
                    "Les résultats ne sont pas concluants. https://docs.example.org/api"),
        "published": "2025-03-01",
        "engine": "fixture",
    },
    {
        "url": "https://news.example/2025-04-12-update",
        "title": "Actualité : correction et communiqué",
        "content": ("Le communiqué annonce une baisse de 8 % mais une autre source affirme "
                    "que ce n'est pas confirmé. « Nous vérifions », a déclaré le porte-parole. "
                    "Update 2025-04-12 : correction publiée. However the claim is unverified. "
                    "Contact: press@news.example"),
        "published": "2025-04-12",
        "engine": "fixture",
    },
    {
        "url": "https://docs.example.org/release-1-4-0",
        "title": "Release notes 1.4.0",
        "content": ("Release 1.4.0, license MIT, endpoint GET /v1/search, latency 45 ms. "
                    "Added: pagination. Removed: legacy endpoint. Deprecated: v0.9. "
                    "Dependencies: httpx>=0.28. Benchmark: 1300 requests/s. "
                    "See https://example.org/research/2025-report"),
        "published": "2025-01-10",
        "engine": "fixture",
    },
    {
        "url": "https://data.example/dataset-metadata",
        "title": "Dataset metadata",
        "content": ("columns: id, value, date; rows: 1000; mean 4.2; median 3.1; "
                    "missing: none. Source: official registry. The dataset is licensed "
                    "under Apache-2.0. Values: 4, 8, 15, 16, 23, 42, 108. "
                    "Correlation is associated with growth."),
        "published": "2024-11-02",
        "engine": "fixture",
    },
    {
        "url": "https://sci.example/peer-review-2026",
        "title": "Peer-reviewed study",
        "content": ("However the peer-reviewed study is not conclusive. It might suggest "
                    "a correlation, but the result is unverified. Published 2026-01-05. "
                    "Abstract: objective and background of the study. Sample size: 512 "
                    "participants; p-value 0.03; confidence 95 %."),
        "published": "2026-01-05",
        "engine": "fixture",
    },
    {
        "url": "https://social.example/trend-thread",
        "title": "Community thread about the trend",
        "content": ("#trending post: users report good results but others say it is bad. "
                    "Followers 12000, views 45000. The rumor is allegedly unconfirmed. "
                    "First post 2025-06-01, then spread 2025-06-03. Community r/research."),
        "published": "2025-06-01",
        "engine": "fixture",
    },
    {
        "url": "https://tech.example/api-changelog",
        "title": "API changelog and security advisory",
        "content": ("Version 3.0.2 shipped with CVE-2025-9999 patch. Changelog: added "
                    "auth, fixed timeout, removed deprecated code. Benchmark 12 ms "
                    "versus 45 ms. Package registry: pypi. Maintainer Alice Martin. "
                    "https://github.com/example/project"),
        "published": "2025-09-15",
        "engine": "fixture",
    },
    {
        "url": "https://osint.example/repository-provenance",
        "title": "Repository provenance record",
        "content": ("Repository metadata: branch main, license GPL-3.0, commits 1284. "
                    "WHOIS registered 2019-02-11. Domain: osint.example. "
                    "Origin: official public record, hash sha256. "
                    "It is not a primary source, however it is verifiable."),
        "published": "2023-07-20",
        "engine": "fixture",
    },
]
