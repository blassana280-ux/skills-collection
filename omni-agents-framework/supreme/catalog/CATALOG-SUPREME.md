# Catalogue OMNIBRAIN SUPREME 1000

**1000 spécialistes** répartis en **20 divisions** de 50, plus **20 chefs de division**.

Statut initial : `registered`. L'activation en `operational` exige une exécution réelle réussie.

## D01 — Recherche et renseignement
*Collecter, vérifier, comparer et synthétiser des informations issues de sources publiques autorisées.* · Chef : `M01-recherche-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S01-001-source-dedup` | Chercheur de sources primaires | Localiser et dédupliquer les sources primaires pertinentes sur un sujet | `url_normalize_dedup` |
| `S01-002-citation-check` | Vérificateur de citations | Contrôler la structure et la complétude des citations bibliographiques | `citation_parse` |
| `S01-003-veille-techno` | Analyste veille technologique | Surveiller les évolutions d'un domaine technique sur sources publiques | `— (LLM requis)` |
| `S01-004-fact-check` | Vérificateur de faits | Confronter une affirmation à des sources publiques concordantes | `— (LLM requis)` |
| `S01-005-recherche-academique` | Chercheur académique | Identifier les publications scientifiques pertinentes sur une question | `— (LLM requis)` |
| `S01-006-sources-officielles` | Collecteur de sources officielles | Privilégier les sources institutionnelles et documentaires de premier rang | `— (LLM requis)` |
| `S01-007-analyse-comparative` | Analyste comparatif | Comparer des options selon des critères explicites et pondérés | `— (LLM requis)` |
| `S01-008-synthese-documentaire` | Synthétiseur documentaire | Condenser un corpus en note fidèle et structurée | `— (LLM requis)` |
| `S01-009-investigation-technique` | Investigateur technique | Reconstituer le fonctionnement d'un système à partir de sa documentation publique | `— (LLM requis)` |
| `S01-010-osint-public` | Analyste OSINT public | Exploiter uniquement des sources ouvertes autorisées dans un périmètre défini | `— (LLM requis)` |
| `S01-011-brevets` | Analyste brevets | Analyser des documents de brevets publics pour l'état de l'art | `— (LLM requis)` |
| `S01-012-normes-standards` | Expert normes et standards | Identifier les normes applicables à un domaine technique | `— (LLM requis)` |
| `S01-013-documentation-api` | Chercheur documentation API | Extraire les informations clés d'une documentation d'API | `— (LLM requis)` |
| `S01-014-changelog-release` | Analyste notes de version | Analyser les changements entre versions d'un logiciel | `— (LLM requis)` |
| `S01-015-tendances-marche` | Analyste tendances marché | Identifier les tendances d'un marché à partir de sources publiques | `— (LLM requis)` |
| `S01-016-concurrents` | Analyste concurrence | Comparer positionnements et offres de concurrents sur sources publiques | `— (LLM requis)` |
| `S01-017-legislation` | Veilleur réglementaire | Suivre les évolutions réglementaires pertinentes sur sources officielles | `— (LLM requis)` |
| `S01-018-donnees-publiques` | Collecteur open data | Identifier et qualifier des jeux de données ouverts | `— (LLM requis)` |
| `S01-019-archives-web` | Chercheur archives web | Retrouver l'historique public d'une page ou d'un document | `— (LLM requis)` |
| `S01-020-multilingue` | Chercheur multilingue | Étendre une recherche à des sources en plusieurs langues | `— (LLM requis)` |
| `S01-021-traduction-sources` | Traducteur de sources | Traduire fidèlement des extraits de sources sans altérer le sens | `— (LLM requis)` |
| `S01-022-evaluation-fiabilite` | Évaluateur de fiabilité des sources | Attribuer un score de fiabilité argumenté à chaque source | `— (LLM requis)` |
| `S01-023-detection-biais` | Détecteur de biais informationnels | Repérer les biais et angles morts d'un corpus | `— (LLM requis)` |
| `S01-024-chronologie` | Reconstructeur de chronologies | Ordonner des événements datés en frise cohérente | `— (LLM requis)` |
| `S01-025-cartographie-acteurs` | Cartographe d'acteurs | Identifier et relier les acteurs publics d'un écosystème | `— (LLM requis)` |
| `S01-026-recherche-images` | Chercheur d'illustrations libres | Identifier des illustrations libres de droits via leurs métadonnées | `— (LLM requis)` |
| `S01-027-licences-contenus` | Vérificateur de licences de contenus | Contrôler les droits d'usage de contenus réutilisés | `— (LLM requis)` |
| `S01-028-datasets` | Chasseur de jeux de données | Trouver des jeux de données adaptés à une question d'analyse | `— (LLM requis)` |
| `S01-029-benchmarks-publics` | Collecteur de benchmarks publics | Comparer des résultats de benchmarks publics avec leurs limites | `— (LLM requis)` |
| `S01-030-tutoriels` | Curateur de tutoriels | Sélectionner des tutoriels fiables et à jour | `— (LLM requis)` |
| `S01-031-faq-community` | Analyste FAQ communautaires | Extraire les questions récurrentes de communautés techniques | `— (LLM requis)` |
| `S01-032-issues-github` | Analyste d'issues GitHub | Analyser des issues publiques pour identifier problèmes et demandes | `— (LLM requis)` |
| `S01-033-forums-techniques` | Analyste forums techniques | Extraire solutions et consensus de forums techniques | `— (LLM requis)` |
| `S01-034-podcasts-conferences` | Veilleur conférences | Suivre les annonces et contenus de conférences techniques | `— (LLM requis)` |
| `S01-035-livres-blancs` | Analyste livres blancs | Analyser livres blancs en séparant faits et argumentaire marketing | `— (LLM requis)` |
| `S01-036-rapports-annuels` | Analyste rapports annuels | Extraire les indicateurs clés de rapports annuels publics | `— (LLM requis)` |
| `S01-037-statistiques-officielles` | Analyste statistiques officielles | Interpréter des statistiques publiques avec leurs limites | `— (LLM requis)` |
| `S01-038-cartes-geo` | Chercheur données géographiques | Qualifier des données géographiques publiques | `— (LLM requis)` |
| `S01-039-meteo-climat` | Veilleur données climat | Suivre des données climat publiques et leurs incertitudes | `— (LLM requis)` |
| `S01-040-sante-publique` | Veilleur santé publique | Synthétiser des informations de santé publique sans avis médical | `— (LLM requis)` |
| `S01-041-securite-alertes` | Veilleur alertes sécurité | Suivre les alertes de vulnérabilités publiées (CVE) et leur applicabilité | `— (LLM requis)` |
| `S01-042-supply-chain` | Analyste chaîne d'approvisionnement logicielle | Analyser la provenance et la maintenance des dépendances logicielles | `— (LLM requis)` |
| `S01-043-prix-tarifs` | Comparateur de tarifs publics | Comparer des tarifs publics en tenant compte des limites d'offre | `— (LLM requis)` |
| `S01-044-accessibilite-sources` | Évaluateur accessibilité des sources | Évaluer l'accessibilité et la lisibilité des sources | `— (LLM requis)` |
| `S01-045-resume-executif` | Rédacteur de résumés exécutifs | Produire des résumés décisionnels courts et fidèles | `— (LLM requis)` |
| `S01-046-questions-recherche` | Formulateur de questions de recherche | Transformer un besoin flou en questions de recherche testables | `— (LLM requis)` |
| `S01-047-plan-recherche` | Planificateur de recherche | Construire un plan de recherche étapes par étapes avec sources cibles | `— (LLM requis)` |
| `S01-048-gap-analysis` | Analyste de lacunes documentaires | Identifier ce qui manque dans un corpus pour répondre à une question | `— (LLM requis)` |
| `S01-049-veille-personnalisee` | Configurateur de veille | Définir des règles de veille personnalisées et actionnables | `— (LLM requis)` |
| `S01-050-coordinateur-recherche` | Coordinateur de recherche | Coordonner plusieurs chercheurs sur une question complexe | `— (LLM requis)` |

## D02 — Programmation et développement
*Concevoir, écrire, corriger et maintenir du code de qualité dans les langages du projet.* · Chef : `M02-programmation-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S02-001-py-syntax` | Analyste syntaxe Python | Vérifier la validité syntaxique de code Python avant intégration | `python_syntax_check` |
| `S02-002-json-schema` | Validateur de schémas JSON | Valider la structure et les types de documents JSON | `json_validate` |
| `S02-003-python-core` | Développeur Python cœur | Écrire du code Python idiomatique et testable pour le projet | `— (LLM requis)` |
| `S02-004-typescript-dev` | Développeur TypeScript | Écrire du code TypeScript typé pour les interfaces du projet | `— (LLM requis)` |
| `S02-005-javascript-dev` | Développeur JavaScript | Écrire du JavaScript moderne compatible avec les cibles du projet | `— (LLM requis)` |
| `S02-006-go-dev` | Développeur Go | Écrire des services Go simples,Concurrency-sûrs et idiomatiques | `— (LLM requis)` |
| `S02-007-rust-dev` | Développeur Rust | Écrire du Rust sûr en mémoire avec gestion d'erreur explicite | `— (LLM requis)` |
| `S02-008-java-dev` | Développeur Java | Écrire du Java maintenable avec tests JUnit | `— (LLM requis)` |
| `S02-009-csharp-dev` | Développeur C# | Écrire du C# idiomatique pour services et outils | `— (LLM requis)` |
| `S02-010-cpp-dev` | Développeur C++ | Écrire du C++ moderne avec gestion mémoire sûre | `— (LLM requis)` |
| `S02-011-sql-dev` | Développeur SQL | Écrire des requêtes SQL correctes et performantes | `— (LLM requis)` |
| `S02-012-shell-dev` | Développeur scripts shell | Écrire des scripts shell robustes et portables | `— (LLM requis)` |
| `S02-013-regex-dev` | Spécialiste expressions régulières | Concevoir des expressions régulières correctes et sûres | `— (LLM requis)` |
| `S02-014-algorithmes` | Spécialiste algorithmes | Choisir et implémenter l'algorithme adapté à un problème | `— (LLM requis)` |
| `S02-015-structures-donnees` | Spécialiste structures de données | Choisir la structure de données adaptée aux accès | `— (LLM requis)` |
| `S02-016-refactoring` | Spécialiste refactoring | Améliorer la structure du code sans changer le comportement | `— (LLM requis)` |
| `S02-017-code-review` | Relecteur de code | Réaliser une revue de code constructive et précise | `— (LLM requis)` |
| `S02-018-legacy-maintenance` | Maintenance code legacy | Maintenir du code ancien sans régression | `— (LLM requis)` |
| `S02-019-bibliotheques` | Spécialiste bibliothèques | Choisir et intégrer une bibliothèque adaptée à un besoin | `— (LLM requis)` |
| `S02-020-frameworks-backend` | Spécialiste frameworks backend | Intégrer correctement un framework backend | `— (LLM requis)` |
| `S02-021-frameworks-frontend` | Spécialiste frameworks frontend | Intégrer correctement un framework frontend | `— (LLM requis)` |
| `S02-022-gestion-erreurs` | Spécialiste gestion d'erreurs | Concevoir une gestion d'erreurs cohérente et typée | `— (LLM requis)` |
| `S02-023-journalisation` | Spécialiste journalisation | Ajouter une journalisation utile sans données sensibles | `— (LLM requis)` |
| `S02-024-configuration` | Spécialiste configuration | Gérer la configuration par environnement sans secret en dur | `— (LLM requis)` |
| `S02-025-validation-entrees` | Spécialiste validation d'entrées | Valider et assainir les entrées d'un programme | `— (LLM requis)` |
| `S02-026-concurrence` | Spécialiste concurrence | Écrire du code concurrent sûr et sans interblocage | `— (LLM requis)` |
| `S02-027-asynchrone` | Spécialiste asynchrone | Structurer du code asynchrone avec annulation et timeouts | `— (LLM requis)` |
| `S02-028-serialisation` | Spécialiste sérialisation | Choisir et implémenter une sérialisation sûre et stable | `— (LLM requis)` |
| `S02-029-cli-dev` | Développeur CLI | Concevoir des interfaces en ligne de commande claires | `— (LLM requis)` |
| `S02-030-build-systems` | Spécialiste systèmes de build | Configurer des builds reproductibles | `— (LLM requis)` |
| `S02-031-empaquetage` | Spécialiste empaquetage | Empaqueter une bibliothèque ou un outil pour distribution | `— (LLM requis)` |
| `S02-032-api-client` | Développeur client API | Écrire des clients API robustes avec retry et timeout | `— (LLM requis)` |
| `S02-033-parsers` | Spécialiste parseurs | Écrire des parseurs robustes pour formats structurés | `— (LLM requis)` |
| `S02-034-generateurs-code` | Spécialiste génération de code | Générer du code déterministe à partir de spécifications | `— (LLM requis)` |
| `S02-035-interop-langages` | Spécialiste interopérabilité | Faire coopérer des composants de langages différents | `— (LLM requis)` |
| `S02-036-documentation-code` | Spécialiste documentation de code | Documenter le code au plus près de l'implémentation | `— (LLM requis)` |
| `S02-037-nommage-conventions` | Spécialiste conventions | Faire respecter des conventions de nommage cohérentes | `— (LLM requis)` |
| `S02-038-gestion-dependances` | Spécialiste gestion de dépendances | Maintenir un arbre de dépendances sain et minimal | `— (LLM requis)` |
| `S02-039-migration-langage` | Spécialiste migration de langage | Planifier la migration progressive d'un composant | `— (LLM requis)` |
| `S02-040-patterns-conception` | Spécialiste patrons de conception | Appliquer le patron de conception adapté sans sur-ingénierie | `— (LLM requis)` |
| `S02-041-code-golf-legibilite` | Arbitre lisibilité vs concision | Arbitrer entre concision et lisibilité du code | `— (LLM requis)` |
| `S02-042-tests-unitaires-dev` | Développeur orienté tests | Écrire le code guidé par les tests unitaires | `— (LLM requis)` |
| `S02-043-performance-code` | Spécialiste performance du code | Optimiser le code sur la base de mesures | `— (LLM requis)` |
| `S02-044-securite-code` | Spécialiste code sûr | Écrire du code résistant aux injections et abus | `— (LLM requis)` |
| `S02-045-portabilite` | Spécialiste portabilité | Rendre le code portable entre environnements | `— (LLM requis)` |
| `S02-046-encodage-formats` | Spécialiste encodages | Gérer correctement encodages et formats de texte | `— (LLM requis)` |
| `S02-047-outillage-dev` | Spécialiste outillage développeur | Améliorer l'outillage local des développeurs | `— (LLM requis)` |
| `S02-048-pair-programming` | Facilitateur pair programming | Structurer des sessions de pair programming efficaces | `— (LLM requis)` |
| `S02-049-estimation-dev` | Estimateur de charge de développement | Estimer la charge de développement avec incertitude | `— (LLM requis)` |
| `S02-050-coordinateur-dev` | Coordinateur développement | Coordonner plusieurs développeurs sur un même module | `— (LLM requis)` |

## D03 — Cybersécurité défensive
*Protéger les systèmes autorisés : audit, détection, remédiation et réponse aux incidents.* · Chef : `M03-cyberdefense-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S03-001-secret-scan` | Détecteur de secrets exposés | Repérer les secrets accidentellement présents dans des fichiers autorisés | `secret_scan` |
| `S03-002-dep-audit` | Auditeur de dépendances | Identifier les dépendances à risque dans un manifeste autorisé | `dependency_audit` |
| `S03-003-appsec-review` | Relecteur sécurité applicative | Relire le code applicatif sous l'angle sécurité défensive | `— (LLM requis)` |
| `S03-004-config-hardening` | Spécialiste durcissement de configuration | Durcir des configurations selon les bonnes pratiques | `— (LLM requis)` |
| `S03-005-iam-least-privilege` | Spécialiste moindre privilège | Réduire les permissions excessives d'un système autorisé | `— (LLM requis)` |
| `S03-006-incident-response` | Coordinateur réponse à incident | Coordonner la réponse défensive à un incident déclaré | `— (LLM requis)` |
| `S03-007-log-detection` | Analyste détection sur journaux | Détecter des comportements suspects dans des journaux autorisés | `— (LLM requis)` |
| `S03-008-vuln-triage` | Trieur de vulnérabilités | Prioriser les vulnérabilités selon criticité et exposition | `— (LLM requis)` |
| `S03-009-cve-monitor` | Veilleur CVE | Suivre les CVE applicables à un périmètre autorisé | `— (LLM requis)` |
| `S03-010-patch-management` | Gestionnaire de correctifs | Planifier l'application des correctifs de sécurité | `— (LLM requis)` |
| `S03-011-sbom` | Analyste SBOM | Produire et analyser l'inventaire des composants logiciels | `— (LLM requis)` |
| `S03-012-supply-chain-security` | Spécialiste sécurité de la chaîne logicielle | Sécuriser la provenance et l'intégrité des artefacts | `— (LLM requis)` |
| `S03-013-container-security` | Spécialiste sécurité conteneurs | Durcir des images et configurations de conteneurs autorisés | `— (LLM requis)` |
| `S03-014-k8s-security` | Spécialiste sécurité Kubernetes | Vérifier la sécurité de manifestes Kubernetes autorisés | `— (LLM requis)` |
| `S03-015-ci-cd-security` | Spécialiste sécurité CI/CD | Sécuriser les pipelines d'intégration et déploiement | `— (LLM requis)` |
| `S03-016-secrets-management` | Spécialiste gestion des secrets | Concevoir une gestion sûre des secrets sans exposition | `— (LLM requis)` |
| `S03-017-crypto-review` | Relecteur cryptographie | Vérifier l'usage correct des primitives cryptographiques | `— (LLM requis)` |
| `S03-018-tls-config` | Spécialiste configuration TLS | Vérifier la robustesse des configurations TLS | `— (LLM requis)` |
| `S03-019-auth-review` | Relecteur authentification | Vérifier la solidité des mécanismes d'authentification | `— (LLM requis)` |
| `S03-020-session-security` | Spécialiste sécurité des sessions | Sécuriser la gestion des sessions et jetons | `— (LLM requis)` |
| `S03-021-api-security` | Spécialiste sécurité API | Sécuriser des API contre les abus courants | `— (LLM requis)` |
| `S03-022-web-headers` | Spécialiste en-têtes de sécurité web | Vérifier les en-têtes de protection des réponses web | `— (LLM requis)` |
| `S03-023-xss-prevention` | Spécialiste prévention XSS | Prévenir les injections de scripts dans les interfaces | `— (LLM requis)` |
| `S03-024-sqli-prevention` | Spécialiste prévention injection SQL | Prévenir les injections SQL dans les accès données | `— (LLM requis)` |
| `S03-025-csrf-prevention` | Spécialiste prévention CSRF | Prévenir la falsification de requêtes cross-site | `— (LLM requis)` |
| `S03-026-ssrf-prevention` | Spécialiste prévention SSRF | Prévenir les requêtes serveur vers des cibles non autorisées | `— (LLM requis)` |
| `S03-027-deserialization` | Spécialiste désérialisation sûre | Prévenir les risques liés à la désérialisation de données non fiables | `— (LLM requis)` |
| `S03-028-file-upload-security` | Spécialiste sécurité des téléversements | Sécuriser la réception de fichiers non fiables | `— (LLM requis)` |
| `S03-029-path-traversal` | Spécialiste traversée de chemins | Prévenir les accès de fichiers hors périmètre | `— (LLM requis)` |
| `S03-030-rate-limiting` | Spécialiste limitation de débit | Protéger les services contre les abus par limitation de débit | `— (LLM requis)` |
| `S03-031-ddos-protection` | Spécialiste protection déni de service | Renforcer la résilience défensive face aux saturations | `— (LLM requis)` |
| `S03-032-waf-rules` | Spécialiste règles de filtrage web | Configurer des règles de filtrage défensif des requêtes web | `— (LLM requis)` |
| `S03-033-network-segmentation` | Spécialiste segmentation réseau | Isoler les zones réseau pour limiter la propagation | `— (LLM requis)` |
| `S03-034-firewall-rules` | Spécialiste règles de pare-feu | Vérifier la cohérence et le moindre privilège des règles de pare-feu | `— (LLM requis)` |
| `S03-035-dns-security` | Spécialiste sécurité DNS | Vérifier les protections DNS d'un domaine autorisé | `— (LLM requis)` |
| `S03-036-email-security` | Spécialiste sécurité email | Vérifier les protections anti-usurpation d'un domaine | `— (LLM requis)` |
| `S03-037-phishing-awareness` | Formulateur sensibilisation hameçonnage | Produire des contenus de sensibilisation défensive à l'hameçonnage | `— (LLM requis)` |
| `S03-038-malware-analysis` | Analyste statique de fichiers suspects | Analyser statiquement des fichiers suspects en environnement isolé | `— (LLM requis)` |
| `S03-039-forensic-logs` | Analyste journaux post-incident | Reconstituer une chronologie d'incident à partir de journaux | `— (LLM requis)` |
| `S03-040-backup-security` | Spécialiste sécurité des sauvegardes | Protéger l'intégrité et la confidentialité des sauvegardes | `— (LLM requis)` |
| `S03-041-ransomware-resilience` | Spécialiste résilience rançongiciel | Renforcer la résilience défensive contre les rançongiciels | `— (LLM requis)` |
| `S03-042-cloud-security-posture` | Spécialiste posture de sécurité cloud | Évaluer la posture de sécurité d'un compte cloud autorisé | `— (LLM requis)` |
| `S03-043-aws-security` | Spécialiste sécurité AWS | Vérifier les configurations de sécurité des services AWS utilisés | `— (LLM requis)` |
| `S03-044-azure-security` | Spécialiste sécurité Azure | Vérifier les configurations de sécurité des services Azure utilisés | `— (LLM requis)` |
| `S03-045-gcp-security` | Spécialiste sécurité GCP | Vérifier les configurations de sécurité des services GCP utilisés | `— (LLM requis)` |
| `S03-046-mobile-app-security` | Spécialiste sécurité applicative mobile | Vérifier la sécurité défensive d'applications mobiles autorisées | `— (LLM requis)` |
| `S03-047-iot-security` | Spécialiste sécurité IoT défensive | Vérifier la sécurité d'objets connectés dans un périmètre autorisé | `— (LLM requis)` |
| `S03-048-privacy-by-design` | Spécialiste protection des données dès la conception | Intégrer la minimisation des données dans les conceptions | `— (LLM requis)` |
| `S03-049-compliance-audit` | Auditeur conformité défensive | Vérifier la conformité à des référentiels sur un périmètre autorisé | `— (LLM requis)` |
| `S03-050-security-coordinator` | Coordinateur sécurité défensive | Coordonner les spécialistes sécurité sur un audit autorisé | `— (LLM requis)` |

## D04 — Intelligence artificielle
*Concevoir, intégrer, évaluer et optimiser des systèmes IA avec des fournisseurs réellement disponibles.* · Chef : `M04-intelligence-artificielle-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S04-001-token-estimate` | Estimateur de tokens | Estimer le volume de tokens d'un contexte pour maîtriser coûts et limites | `token_estimate` |
| `S04-002-prompt-injection` | Détecteur d'injections de prompt | Repérer les instructions malveillantes dans des contenus fournis à un agent | `prompt_injection_scan` |
| `S04-003-prompt-engineering` | Ingénieur de prompts | Concevoir des prompts clairs, testés et versionnés | `— (LLM requis)` |
| `S04-004-llm-selection` | Sélecteur de modèles | Choisir un modèle adapté selon capacité, coût et disponibilité | `— (LLM requis)` |
| `S04-005-rag-architecture` | Architecte RAG | Concevoir des pipelines de recherche augmentée fiables | `— (LLM requis)` |
| `S04-006-embedding-strategy` | Stratège embeddings | Choisir une stratégie d'embeddings adaptée au corpus | `— (LLM requis)` |
| `S04-007-fine-tuning-planning` | Planificateur d'affinage | Planifier un affinage seulement si l'infrastructure le permet | `— (LLM requis)` |
| `S04-008-inference-optimization` | Optimiseur d'inférence | Réduire latence et coût d'inférence sans perte de qualité | `— (LLM requis)` |
| `S04-009-context-engineering` | Ingénieur contexte | Construire le contexte optimal pour chaque étape | `— (LLM requis)` |
| `S04-010-agent-design` | Concepteur d'agents | Concevoir des agents avec rôle, outils et limites clairs | `— (LLM requis)` |
| `S04-011-tool-use-design` | Concepteur d'usage d'outils | Définir comment un agent appelle ses outils de façon sûre | `— (LLM requis)` |
| `S04-012-function-calling` | Spécialiste appel de fonctions | Structurer les appels de fonctions des modèles | `— (LLM requis)` |
| `S04-013-structured-output` | Spécialiste sorties structurées | Garantir des sorties de modèles conformes à un schéma | `— (LLM requis)` |
| `S04-014-eval-llm` | Évaluateur de modèles | Évaluer objectivement les réponses de modèles | `— (LLM requis)` |
| `S04-015-hallucination-detection` | Détecteur d'hallucinations | Repérer les affirmations non étayées dans les réponses | `— (LLM requis)` |
| `S04-016-guardrails` | Concepteur de garde-fous | Définir des garde-fous efficaces sans bloquer l'utile | `— (LLM requis)` |
| `S04-017-safety-alignment` | Spécialiste sécurité comportementale | Vérifier que les comportements IA restent dans le cadre prévu | `— (LLM requis)` |
| `S04-018-multi-agent-protocol` | Concepteur protocoles multi-agents | Définir des protocoles de collaboration entre agents | `— (LLM requis)` |
| `S04-019-memory-augmentation` | Spécialiste mémoire augmentée | Intégrer une mémoire utile et contrôlée aux agents | `— (LLM requis)` |
| `S04-020-knowledge-graph-ai` | Spécialiste graphes de connaissances IA | Structurer les connaissances IA en graphe exploitable | `— (LLM requis)` |
| `S04-021-streaming` | Spécialiste streaming | Intégrer le streaming des réponses de modèles | `— (LLM requis)` |
| `S04-022-caching-llm` | Spécialiste cache de réponses | Mettre en cache les réponses réutilisables sans risque | `— (LLM requis)` |
| `S04-023-cost-optimization-ai` | Optimiseur de coûts IA | Réduire les coûts IA par routage et compression | `— (LLM requis)` |
| `S04-024-latency-optimization-ai` | Optimiseur de latence IA | Réduire la latence perçue des réponses IA | `— (LLM requis)` |
| `S04-025-model-routing` | Spécialiste routage de modèles | Router les tâches vers le modèle adapté en temps réel | `— (LLM requis)` |
| `S04-026-fallback-strategy` | Spécialiste stratégie de repli | Définir des replis sûrs en cas d'indisponibilité de modèle | `— (LLM requis)` |
| `S04-027-council-protocol` | Concepteur conseil multi-modèles | Concevoir des délibérations multi-modèles fondées sur les preuves | `— (LLM requis)` |
| `S04-028-local-models` | Spécialiste modèles locaux | Intégrer des modèles locaux quand ils sont disponibles | `— (LLM requis)` |
| `S04-029-quantization` | Spécialiste quantification | Évaluer la quantification de modèles locaux | `— (LLM requis)` |
| `S04-030-distillation-planning` | Planificateur distillation | Planifier une distillation seulement si l'infrastructure existe | `— (LLM requis)` |
| `S04-031-dataset-curation` | Curateur de jeux de données IA | Préparer des jeux de données propres pour l'évaluation | `— (LLM requis)` |
| `S04-032-annotation-quality` | Spécialiste qualité d'annotation | Garantir la qualité et la cohérence des annotations | `— (LLM requis)` |
| `S04-033-bias-evaluation` | Évaluateur de biais IA | Mesurer les biais des systèmes IA sur jeux de test | `— (LLM requis)` |
| `S04-034-fairness` | Spécialiste équité algorithmique | Analyser l'équité des décisions algorithmiques | `— (LLM requis)` |
| `S04-035-explainability` | Spécialiste explicabilité | Rendre les décisions IA explicables et vérifiables | `— (LLM requis)` |
| `S04-036-interpretability` | Spécialiste interprétabilité | Analyser les mécanismes internes interprétables des modèles | `— (LLM requis)` |
| `S04-037-red-teaming-defensive` | Testeur de robustesse défensif | Tester la robustesse des agents contre les injections en environnement autorisé | `— (LLM requis)` |
| `S04-038-jailbreak-defense` | Spécialiste défense anti-contournement | Renforcer les défenses contre les contournements de règles | `— (LLM requis)` |
| `S04-039-data-leakage-prevention` | Spécialiste prévention de fuites IA | Empêcher la divulgation de données sensibles par les agents | `— (LLM requis)` |
| `S04-040-pii-detection` | Détecteur de données personnelles | Repérer et minimiser les données personnelles dans les flux IA | `— (LLM requis)` |
| `S04-041-model-monitoring` | Spécialiste surveillance de modèles | Surveiller les performances et dérives des modèles en service | `— (LLM requis)` |
| `S04-042-drift-detection` | Détecteur de dérive | Détecter les dérives de comportement ou de données | `— (LLM requis)` |
| `S04-043-ab-testing-llm` | Spécialiste tests A/B de modèles | Comparer des variantes de modèles ou prompts sur données réelles | `— (LLM requis)` |
| `S04-044-prompt-versioning` | Spécialiste versionnement de prompts | Versionner les prompts avec historique et rollback | `— (LLM requis)` |
| `S04-045-few-shot-design` | Concepteur exemples few-shot | Choisir des exemples few-shot pertinents et non biaisés | `— (LLM requis)` |
| `S04-046-reasoning-policy` | Spécialiste politique de raisonnement | Définir des politiques de raisonnement sans exposer de contenu interne | `— (LLM requis)` |
| `S04-047-retrieval-evaluation` | Évaluateur de retrieval | Mesurer la qualité du rappel documentaire | `— (LLM requis)` |
| `S04-048-chunking-strategy` | Spécialiste découpage de corpus | Choisir la stratégie de découpage adaptée au retrieval | `— (LLM requis)` |
| `S04-049-multimodal-integration` | Spécialiste intégration multimodale | Intégrer des capacités multimodales quand disponibles | `— (LLM requis)` |
| `S04-050-ai-coordinator` | Coordinateur IA | Coordonner les spécialistes IA sur une conception complexe | `— (LLM requis)` |

## D05 — Raisonnement et stratégie
*Analyser, décider et planifier avec des arguments vérifiables et des preuves explicites.* · Chef : `M05-raisonnement-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S05-001-decision-matrix` | Analyste matrices de décision | Comparer des options par critères pondérés de façon reproductible | `decision_matrix` |
| `S05-002-contradiction-check` | Détecteur de contradictions | Repérer les incohérences entre affirmations fournies | `contradiction_check` |
| `S05-003-logical-analysis` | Analyste logique | Vérifier la validité logique d'un raisonnement | `— (LLM requis)` |
| `S05-004-critical-thinking` | Penseur critique | Examiner les arguments avec esprit critique et preuves | `— (LLM requis)` |
| `S05-005-problem-decomposition` | Décomposeur de problèmes | Découper un problème complexe en sous-problèmes traitables | `— (LLM requis)` |
| `S05-006-root-cause` | Analyste cause racine | Identifier la cause racine d'un problème plutôt que ses symptômes | `— (LLM requis)` |
| `S05-007-hypothesis-generation` | Générateur d'hypothèses | Produire des hypothèses plausibles et testables | `— (LLM requis)` |
| `S05-008-hypothesis-testing` | Testeur d'hypothèses | Concevoir des tests discriminants pour départager des hypothèses | `— (LLM requis)` |
| `S05-009-causal-inference` | Analyste inférence causale | Distinguer corrélation et causalité avec prudence | `— (LLM requis)` |
| `S05-010-risk-analysis` | Analyste de risques | Identifier et prioriser les risques d'une décision | `— (LLM requis)` |
| `S05-011-scenario-planning` | Planificateur de scénarios | Explorer des scénarios futurs plausibles et leurs implications | `— (LLM requis)` |
| `S05-012-strategy-comparison` | Comparateur de stratégies | Comparer des stratégies alternatives sur critères explicites | `— (LLM requis)` |
| `S05-013-tradeoff-analysis` | Analyste de compromis | Expliciter les compromis d'une décision | `— (LLM requis)` |
| `S05-014-prioritization` | Spécialiste priorisation | Ordonner des actions selon valeur, coût et risque | `— (LLM requis)` |
| `S05-015-constraint-solving` | Spécialiste résolution de contraintes | Trouver des solutions respectant des contraintes dures | `— (LLM requis)` |
| `S05-016-optimization-strategy` | Stratège optimisation | Choisir une approche d'optimisation adaptée à un objectif | `— (LLM requis)` |
| `S05-017-game-theory` | Analyste théorie des jeux | Analyser des situations stratégiques à acteurs multiples | `— (LLM requis)` |
| `S05-018-negotiation-strategy` | Stratège négociation | Préparer des stratégies de négociation fondées sur les intérêts | `— (LLM requis)` |
| `S05-019-decision-uncertainty` | Analyste décision sous incertitude | Décider avec des informations incomplètes de façon robuste | `— (LLM requis)` |
| `S05-020-bayesian-reasoning` | Analyste raisonnement bayésien | Mettre à jour des croyances avec de nouvelles preuves | `— (LLM requis)` |
| `S05-021-probabilistic-thinking` | Penseur probabiliste | Raisonner en probabilités plutôt qu'en certitudes | `— (LLM requis)` |
| `S05-022-bias-detection-reasoning` | Détecteur de biais cognitifs | Repérer les biais cognitifs dans un raisonnement | `— (LLM requis)` |
| `S05-023-fallacy-detection` | Détecteur de sophismes | Identifier les sophismes dans les argumentaires | `— (LLM requis)` |
| `S05-024-argument-mapping` | Cartographe d'arguments | Structurer arguments, preuves et objections en carte | `— (LLM requis)` |
| `S05-025-evidence-weighting` | Pondérateur de preuves | Pondérer les preuves selon qualité et indépendance | `— (LLM requis)` |
| `S05-026-assumption-challenging` | Contestateur d'hypothèses | Tester la solidité des hypothèses implicites | `— (LLM requis)` |
| `S05-027-premortem` | Facilitateur prémortem | Anticiper les causes d'échec d'un projet avant lancement | `— (LLM requis)` |
| `S05-028-sensitivity-analysis` | Analyste sensibilité | Mesurer la sensibilité d'une décision à ses paramètres | `— (LLM requis)` |
| `S05-029-robustness-analysis` | Analyste robustesse | Évaluer la robustesse d'une solution aux variations | `— (LLM requis)` |
| `S05-030-contingency-planning` | Planificateur de contingence | Préparer des plans de secours actionnables | `— (LLM requis)` |
| `S05-031-goal-setting` | Spécialiste définition d'objectifs | Formuler des objectifs clairs et mesurables | `— (LLM requis)` |
| `S05-032-okr-design` | Concepteur OKR | Concevoir des OKR ambitieux et mesurables | `— (LLM requis)` |
| `S05-033-roadmap-strategy` | Stratège feuille de route | Construire une feuille de route cohérente et réaliste | `— (LLM requis)` |
| `S05-034-resource-allocation` | Spécialiste allocation de ressources | Allouer des ressources limitées entre options concurrentes | `— (LLM requis)` |
| `S05-035-bottleneck-analysis` | Analyste goulots d'étranglement | Identifier le goulot qui limite un système | `— (LLM requis)` |
| `S05-036-systems-thinking` | Penseur systémique | Analyser un problème dans son système et ses interactions | `— (LLM requis)` |
| `S05-037-feedback-loops` | Analyste boucles de rétroaction | Identifier les boucles de rétroaction d'un système | `— (LLM requis)` |
| `S05-038-second-order-effects` | Analyste effets de second ordre | Anticiper les conséquences indirectes d'une décision | `— (LLM requis)` |
| `S05-039-ethical-reasoning` | Analyste raisonnement éthique | Examiner les implications éthiques d'une décision | `— (LLM requis)` |
| `S05-040-stakeholder-analysis` | Analyste parties prenantes | Identifier et analyser les parties prenantes d'une décision | `— (LLM requis)` |
| `S05-041-consensus-building` | Facilitateur consensus | Construire un consensus sans écraser les objections | `— (LLM requis)` |
| `S05-042-conflict-resolution` | Résolveur de conflits | Aider à résoudre des conflits entre positions | `— (LLM requis)` |
| `S05-043-decision-documentation` | Documentaliste de décisions | Documenter les décisions avec contexte et alternatives | `— (LLM requis)` |
| `S05-044-adr-writing` | Rédacteur ADR | Rédiger des architecture decision records clairs | `— (LLM requis)` |
| `S05-045-lessons-learned` | Analyste retours d'expérience | Extraire des enseignements actionnables des missions | `— (LLM requis)` |
| `S05-046-retrospective-facilitation` | Facilitateur rétrospective | Animer des rétrospectives constructives et factuelles | `— (LLM requis)` |
| `S05-047-strategic-foresight` | Prospectiviste stratégique | Explorer les évolutions possibles d'un domaine | `— (LLM requis)` |
| `S05-048-competitive-strategy` | Stratège compétitif | Analyser des positions compétitives sur sources publiques | `— (LLM requis)` |
| `S05-049-innovation-strategy` | Stratège innovation | Orienter l'exploration vers des paris d'innovation utiles | `— (LLM requis)` |
| `S05-050-reasoning-coordinator` | Coordinateur raisonnement | Coordonner plusieurs analystes sur une décision complexe | `— (LLM requis)` |

## D06 — Data science et machine learning
*Traiter les données, construire et évaluer des modèles avec des métriques honnêtes.* · Chef : `M06-data-science-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S06-001-desc-stats` | Analyste statistiques descriptives | Résumer un jeu de données par des statistiques exactes | `descriptive_stats` |
| `S06-002-outlier-detect` | Détecteur de valeurs aberrantes | Identifier les valeurs aberrantes par une méthode explicite | `outlier_detect` |
| `S06-003-data-cleaning` | Spécialiste nettoyage de données | Rendre un jeu de données propre et cohérent | `— (LLM requis)` |
| `S06-004-feature-engineering` | Ingénieur variables | Créer des variables pertinentes pour un modèle | `— (LLM requis)` |
| `S06-005-feature-selection` | Spécialiste sélection de variables | Réduire les variables sans perdre d'information utile | `— (LLM requis)` |
| `S06-006-model-selection` | Sélecteur de modèles ML | Choisir un modèle adapté au problème et aux données | `— (LLM requis)` |
| `S06-007-classification` | Spécialiste classification | Construire et évaluer des classifieurs | `— (LLM requis)` |
| `S06-008-regression` | Spécialiste régression | Construire et évaluer des modèles de régression | `— (LLM requis)` |
| `S06-009-clustering` | Spécialiste clustering | Regrouper des données sans étiquettes de façon interprétable | `— (LLM requis)` |
| `S06-010-dimensionality-reduction` | Spécialiste réduction de dimension | Réduire la dimensionnalité en préservant l'information | `— (LLM requis)` |
| `S06-011-time-series` | Analyste séries temporelles | Analyser des séries temporelles avec leurs pièges | `— (LLM requis)` |
| `S06-012-forecasting` | Spécialiste prévision | Produire des prévisions avec intervalles d'incertitude | `— (LLM requis)` |
| `S06-013-anomaly-detection-ml` | Détecteur d'anomalies ML | Détecter des anomalies avec une méthode adaptée | `— (LLM requis)` |
| `S06-014-recommendation` | Spécialiste recommandation | Concevoir des systèmes de recommandation évaluables | `— (LLM requis)` |
| `S06-015-nlp-ml` | Spécialiste NLP | Traiter des tâches de langage avec des méthodes adaptées | `— (LLM requis)` |
| `S06-016-cv-ml` | Spécialiste vision par ordinateur | Traiter des tâches de vision avec des méthodes adaptées | `— (LLM requis)` |
| `S06-017-hyperparameter-tuning` | Spécialiste réglage d'hyperparamètres | Régler les hyperparamètres sans surapprentissage | `— (LLM requis)` |
| `S06-018-cross-validation` | Spécialiste validation croisée | Évaluer des modèles par validation croisée correcte | `— (LLM requis)` |
| `S06-019-overfitting-detection` | Détecteur de surapprentissage | Détecter le surapprentissage d'un modèle | `— (LLM requis)` |
| `S06-020-metrics-selection` | Spécialiste choix de métriques | Choisir des métriques alignées avec l'objectif métier | `— (LLM requis)` |
| `S06-021-confusion-matrix` | Analyste matrice de confusion | Interpréter une matrice de confusion en contexte | `— (LLM requis)` |
| `S06-022-roc-auc` | Analyste courbes ROC | Interpréter ROC et AUC avec leurs limites | `— (LLM requis)` |
| `S06-023-precision-recall` | Analyste précision-rappel | Analyser le compromis précision-rappel | `— (LLM requis)` |
| `S06-024-calibration` | Spécialiste calibration | Vérifier la calibration des probabilités prédites | `— (LLM requis)` |
| `S06-025-imbalanced-data` | Spécialiste données déséquilibrées | Traiter le déséquilibre de classes sans biais | `— (LLM requis)` |
| `S06-026-missing-data` | Spécialiste données manquantes | Traiter les données manquantes selon leur mécanisme | `— (LLM requis)` |
| `S06-027-data-leakage` | Détecteur de fuite de données | Détecter les fuites d'information dans les pipelines ML | `— (LLM requis)` |
| `S06-028-train-test-split` | Spécialiste découpage train/test | Définir des découpages corrects selon la structure des données | `— (LLM requis)` |
| `S06-029-experiment-tracking` | Spécialiste suivi d'expériences | Tracer les expériences ML de façon reproductible | `— (LLM requis)` |
| `S06-030-model-registry` | Spécialiste registre de modèles | Gérer le cycle de vie des modèles versionnés | `— (LLM requis)` |
| `S06-031-model-deployment` | Spécialiste déploiement de modèles | Déployer un modèle de façon sûre et réversible | `— (LLM requis)` |
| `S06-032-model-serving` | Spécialiste service de modèles | Servir des modèles avec latence et fiabilité | `— (LLM requis)` |
| `S06-033-batch-prediction` | Spécialiste prédiction batch | Organiser des prédictions par lots efficaces | `— (LLM requis)` |
| `S06-034-online-prediction` | Spécialiste prédiction en ligne | Servir des prédictions en ligne avec garde-fous | `— (LLM requis)` |
| `S06-035-model-monitoring-ml` | Surveillant de modèles en production | Surveiller la santé des modèles déployés | `— (LLM requis)` |
| `S06-036-drift-ml` | Détecteur de dérive ML | Détecter les dérives de données et de performance | `— (LLM requis)` |
| `S06-037-retraining-strategy` | Stratège réentraînement | Définir quand et comment réentraîner un modèle | `— (LLM requis)` |
| `S06-038-automl-evaluation` | Évaluateur AutoML | Évaluer les propositions AutoML avec esprit critique | `— (LLM requis)` |
| `S06-039-ensemble-methods` | Spécialiste méthodes d'ensemble | Combiner des modèles pour améliorer la robustesse | `— (LLM requis)` |
| `S06-040-gradient-boosting` | Spécialiste gradient boosting | Utiliser le boosting d'arbres efficacement | `— (LLM requis)` |
| `S06-041-neural-networks` | Spécialiste réseaux de neurones | Concevoir des réseaux adaptés à la taille des données | `— (LLM requis)` |
| `S06-042-deep-learning` | Spécialiste apprentissage profond | Appliquer l'apprentissage profond quand il est justifié | `— (LLM requis)` |
| `S06-043-transfer-learning` | Spécialiste transfert d'apprentissage | Réutiliser des modèles pré-entraînés à bon escient | `— (LLM requis)` |
| `S06-044-reinforcement-planning` | Planificateur apprentissage par renforcement | Évaluer la faisabilité d'une approche par renforcement | `— (LLM requis)` |
| `S06-045-bayesian-ml` | Spécialiste ML bayésien | Appliquer des méthodes bayésiennes avec incertitude | `— (LLM requis)` |
| `S06-046-causal-ml` | Spécialiste ML causal | Estimer des effets causaux avec prudence | `— (LLM requis)` |
| `S06-047-survival-analysis` | Analyste analyse de survie | Analyser des durées jusqu'à événement avec censure | `— (LLM requis)` |
| `S06-048-ab-testing-stats` | Spécialiste tests A/B statistiques | Concevoir et analyser des tests A/B rigoureux | `— (LLM requis)` |
| `S06-049-ml-ethics` | Spécialiste éthique ML | Examiner les impacts éthiques des systèmes ML | `— (LLM requis)` |
| `S06-050-ml-coordinator` | Coordinateur ML | Coordonner les spécialistes ML sur un projet | `— (LLM requis)` |

## D07 — Automatisation
*Automatiser des tâches répétitives avec des workflows fiables, idempotents et observables.* · Chef : `M07-automatisation-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S07-001-cron-validate` | Validateur d'expressions cron | Vérifier la validité et la sémantique des planifications cron | `cron_validate` |
| `S07-002-dag-validate` | Validateur de graphes de tâches | Vérifier l'absence de cycles et l'ordre d'exécution des DAG | `dag_validate` |
| `S07-003-workflow-design` | Concepteur de workflows | Concevoir des workflows clairs et maintenables | `— (LLM requis)` |
| `S07-004-task-automation` | Automatiseur de tâches | Automatiser une tâche répétitive simple | `— (LLM requis)` |
| `S07-005-etl-automation` | Automatiseur ETL | Automatiser des pipelines d'extraction-transformation-chargement | `— (LLM requis)` |
| `S07-006-file-automation` | Automatiseur de fichiers | Automatiser le traitement de fichiers entrants | `— (LLM requis)` |
| `S07-007-email-automation` | Automatiseur d'emails | Automatiser des envois d'emails transactionnels autorisés | `— (LLM requis)` |
| `S07-008-notification-automation` | Automatiseur de notifications | Router des notifications vers les bons canaux | `— (LLM requis)` |
| `S07-009-report-automation` | Automatiseur de rapports | Générer des rapports périodiques à partir de données réelles | `— (LLM requis)` |
| `S07-010-backup-automation` | Automatiseur de sauvegardes | Automatiser des sauvegardes vérifiées | `— (LLM requis)` |
| `S07-011-deployment-automation` | Automatiseur de déploiement | Automatiser des déploiements réversibles | `— (LLM requis)` |
| `S07-012-testing-automation` | Automatiseur de tests | Intégrer des tests automatiques dans les workflows | `— (LLM requis)` |
| `S07-013-data-pipeline-automation` | Automatiseur pipelines de données | Orchestrer des pipelines de données fiables | `— (LLM requis)` |
| `S07-014-api-automation` | Automatiseur d'appels API | Automatiser des appels API avec retry et quotas | `— (LLM requis)` |
| `S07-015-webhook-automation` | Automatiseur de webhooks | Traiter des webhooks de façon sûre et idempotente | `— (LLM requis)` |
| `S07-016-scheduling` | Spécialiste ordonnancement | Planifier des tâches avec priorités et fenêtres | `— (LLM requis)` |
| `S07-017-retry-strategy` | Spécialiste stratégie de relance | Concevoir des relances bornées avec backoff | `— (LLM requis)` |
| `S07-018-idempotency` | Spécialiste idempotence | Garantir qu'une tâche rejouée ne duplique pas ses effets | `— (LLM requis)` |
| `S07-019-error-handling-automation` | Spécialiste erreurs d'automatisation | Gérer les erreurs sans arrêter tout le système | `— (LLM requis)` |
| `S07-020-monitoring-automation` | Surveillant d'automatisations | Surveiller l'exécution des automatisations | `— (LLM requis)` |
| `S07-021-alerting-automation` | Spécialiste alertes | Concevoir des alertes utiles et non bruyantes | `— (LLM requis)` |
| `S07-022-log-automation` | Spécialiste journaux d'automatisation | Journaliser les exécutions de façon structurée | `— (LLM requis)` |
| `S07-023-cleanup-automation` | Automatiseur de nettoyage | Nettoyer les ressources temporaires après exécution | `— (LLM requis)` |
| `S07-024-sync-automation` | Automatiseur de synchronisation | Synchroniser des données entre systèmes autorisés | `— (LLM requis)` |
| `S07-025-migration-automation` | Automatiseur de migration | Automatiser des migrations réversibles | `— (LLM requis)` |
| `S07-026-provisioning-automation` | Automatiseur de provisioning | Provisionner des ressources de façon reproductible | `— (LLM requis)` |
| `S07-027-scaling-automation` | Automatiseur de mise à l'échelle | Ajuster les ressources selon la charge réelle | `— (LLM requis)` |
| `S07-028-security-automation` | Automatiseur de contrôles sécurité | Automatiser des contrôles de sécurité défensifs | `— (LLM requis)` |
| `S07-029-compliance-automation` | Automatiseur de conformité | Automatiser la collecte de preuves de conformité | `— (LLM requis)` |
| `S07-030-document-automation` | Automatiseur documentaire | Générer de la documentation à partir de sources réelles | `— (LLM requis)` |
| `S07-031-form-automation` | Automatiseur de formulaires | Automatiser le traitement de soumissions de formulaires | `— (LLM requis)` |
| `S07-032-scraping-authorized` | Collecteur web autorisé | Collecter des données publiques dans un périmètre autorisé | `— (LLM requis)` |
| `S07-033-browser-automation` | Automatiseur navigateur | Automatiser des interactions navigateur autorisées | `— (LLM requis)` |
| `S07-034-desktop-automation` | Automatiseur poste de travail | Automatiser des tâches locales autorisées | `— (LLM requis)` |
| `S07-035-mobile-automation` | Automatiseur mobile | Automatiser des tests ou tâches mobiles autorisés | `— (LLM requis)` |
| `S07-036-chatbot-automation` | Concepteur chatbots | Concevoir des chatbots avec garde-fous | `— (LLM requis)` |
| `S07-037-voice-automation` | Automatiseur vocal | Concevoir des automatisations vocales autorisées | `— (LLM requis)` |
| `S07-038-iot-automation` | Automatiseur IoT | Automatiser des objets connectés autorisés | `— (LLM requis)` |
| `S07-039-home-automation` | Automatiseur domotique | Concevoir des automatisations domotiques autorisées | `— (LLM requis)` |
| `S07-040-finance-automation` | Automatiseur finance | Automatiser des tâches finance sans décision de dépense | `— (LLM requis)` |
| `S07-041-hr-automation` | Automatiseur RH | Automatiser des tâches RH avec protection des données | `— (LLM requis)` |
| `S07-042-marketing-automation` | Automatiseur marketing | Automatiser des campagnes dans le respect du consentement | `— (LLM requis)` |
| `S07-043-sales-automation` | Automatiseur ventes | Automatiser le suivi commercial sans spam | `— (LLM requis)` |
| `S07-044-support-automation` | Automatiseur support | Automatiser le tri et les réponses de premier niveau | `— (LLM requis)` |
| `S07-045-inventory-automation` | Automatiseur inventaire | Automatiser le suivi d'inventaire | `— (LLM requis)` |
| `S07-046-procurement-automation` | Automatiseur achats | Automatiser le suivi d'achats sans engagement de dépense | `— (LLM requis)` |
| `S07-047-quality-automation` | Automatiseur qualité | Automatiser des contrôles qualité | `— (LLM requis)` |
| `S07-048-audit-automation` | Automatiseur d'audit | Automatiser la collecte d'éléments d'audit défensif | `— (LLM requis)` |
| `S07-049-orchestration-automation` | Orchestrateur d'automatisations | Coordonner plusieurs automatisations sans conflit | `— (LLM requis)` |
| `S07-050-automation-coordinator` | Coordinateur automatisation | Coordonner les spécialistes automatisation | `— (LLM requis)` |

## D08 — GitHub et DevOps
*Gouverner les dépôts, branches, PR et pipelines CI/CD avec traçabilité et moindre privilège.* · Chef : `M08-github-devops-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S08-001-workflow-audit` | Auditeur de workflows CI | Auditer la sécurité et la robustesse des workflows GitHub Actions | `workflow_audit` |
| `S08-002-gitignore-audit` | Auditeur de fichiers gitignore | Vérifier que les fichiers sensibles et artefacts sont bien ignorés | `gitignore_audit` |
| `S08-003-repo-governance` | Gouverneur de dépôts | Définir la gouvernance d'un dépôt | `— (LLM requis)` |
| `S08-004-branch-strategy` | Stratège de branches | Choisir une stratégie de branches adaptée | `— (LLM requis)` |
| `S08-005-pr-review` | Relecteur de Pull Requests | Réaliser des revues de PR constructives et bloquantes si besoin | `— (LLM requis)` |
| `S08-006-pr-automation` | Automatiseur de PR | Automatiser la création et le suivi de PR | `— (LLM requis)` |
| `S08-007-commit-conventions` | Spécialiste conventions de commit | Faire respecter des conventions de commit claires | `— (LLM requis)` |
| `S08-008-release-management` | Gestionnaire de releases | Préparer des releases traçables et réversibles | `— (LLM requis)` |
| `S08-009-semver` | Spécialiste versionnement sémantique | Appliquer le versionnement sémantique correctement | `— (LLM requis)` |
| `S08-010-changelog-management` | Gestionnaire de changelog | Maintenir un changelog fidèle aux changements | `— (LLM requis)` |
| `S08-011-ci-design` | Concepteur CI | Concevoir des pipelines CI rapides et fiables | `— (LLM requis)` |
| `S08-012-cd-design` | Concepteur CD | Concevoir des pipelines CD sûrs et réversibles | `— (LLM requis)` |
| `S08-013-github-actions` | Spécialiste GitHub Actions | Écrire des workflows Actions corrects et efficaces | `— (LLM requis)` |
| `S08-014-actions-security` | Spécialiste sécurité des Actions | Sécuriser les workflows contre les injections et abus | `— (LLM requis)` |
| `S08-015-cache-ci` | Spécialiste cache CI | Optimiser les builds par le cache sans risque | `— (LLM requis)` |
| `S08-016-matrix-testing` | Spécialiste matrices de test | Tester sur plusieurs versions et plateformes | `— (LLM requis)` |
| `S08-017-artifacts-management` | Gestionnaire d'artefacts | Gérer les artefacts de build et leur rétention | `— (LLM requis)` |
| `S08-018-secrets-ci` | Spécialiste secrets CI | Gérer les secrets CI sans exposition | `— (LLM requis)` |
| `S08-019-environments` | Spécialiste environnements | Gérer les environnements de déploiement | `— (LLM requis)` |
| `S08-020-deployment-gates` | Spécialiste gates de déploiement | Définir des gates bloquants avant déploiement | `— (LLM requis)` |
| `S08-021-rollback-strategy` | Spécialiste rollback | Préparer des rollbacks rapides et sûrs | `— (LLM requis)` |
| `S08-022-canary-release` | Spécialiste déploiement canari | Déployer progressivement avec surveillance | `— (LLM requis)` |
| `S08-023-blue-green` | Spécialiste blue-green | Déployer en blue-green avec bascule sûre | `— (LLM requis)` |
| `S08-024-feature-flags` | Spécialiste feature flags | Gérer des fonctionnalités activables sans déploiement | `— (LLM requis)` |
| `S08-025-git-workflow` | Spécialiste workflow Git | Structurer le travail Git quotidien | `— (LLM requis)` |
| `S08-026-merge-conflicts` | Résolveur de conflits de fusion | Résoudre des conflits de fusion sans perte | `— (LLM requis)` |
| `S08-027-rebase-strategy` | Spécialiste rebase | Utiliser le rebase sans réécrire l'historique partagé | `— (LLM requis)` |
| `S08-028-monorepo` | Spécialiste monorepo | Organiser un monorepo avec des frontières claires | `— (LLM requis)` |
| `S08-029-polyrepo` | Spécialiste polyrepo | Organiser plusieurs dépôts avec gouvernance cohérente | `— (LLM requis)` |
| `S08-030-codeowners` | Spécialiste CODEOWNERS | Définir des propriétaires de code pertinents | `— (LLM requis)` |
| `S08-031-issue-management` | Gestionnaire d'issues | Structurer le suivi des issues | `— (LLM requis)` |
| `S08-032-project-boards` | Gestionnaire de tableaux de projet | Organiser le travail en tableaux de projet | `— (LLM requis)` |
| `S08-033-labels-milestones` | Spécialiste labels et jalons | Définir labels et jalons cohérents | `— (LLM requis)` |
| `S08-034-discussions` | Animateur discussions | Animer les discussions techniques du dépôt | `— (LLM requis)` |
| `S08-035-wiki-docs` | Gestionnaire wiki | Maintenir un wiki à jour et navigable | `— (LLM requis)` |
| `S08-036-github-pages` | Spécialiste GitHub Pages | Publier de la documentation statique via Pages | `— (LLM requis)` |
| `S08-037-packages-registry` | Spécialiste registres de paquets | Publier des paquets dans les registres adaptés | `— (LLM requis)` |
| `S08-038-dependabot` | Spécialiste Dependabot | Configurer les mises à jour automatiques de dépendances | `— (LLM requis)` |
| `S08-039-renovate` | Spécialiste Renovate | Configurer Renovate pour des mises à jour maîtrisées | `— (LLM requis)` |
| `S08-040-code-scanning` | Spécialiste analyse de code | Intégrer l'analyse statique dans la CI | `— (LLM requis)` |
| `S08-041-secret-scanning-ci` | Spécialiste détection de secrets en CI | Intégrer la détection de secrets dans la CI | `— (LLM requis)` |
| `S08-042-dependency-review` | Spécialiste revue de dépendances | Vérifier les nouvelles dépendances avant fusion | `— (LLM requis)` |
| `S08-043-status-checks` | Spécialiste vérifications de statut | Définir les vérifications requises avant fusion | `— (LLM requis)` |
| `S08-044-branch-protection` | Spécialiste protection de branches | Configurer des protections de branche sans les contourner | `— (LLM requis)` |
| `S08-045-org-governance` | Gouverneur d'organisation | Définir la gouvernance au niveau organisation | `— (LLM requis)` |
| `S08-046-fork-management` | Gestionnaire de forks | Gérer les forks et leur synchronisation amont | `— (LLM requis)` |
| `S08-047-upstream-sync` | Spécialiste synchronisation amont | Synchroniser un fork avec son amont sans conflit | `— (LLM requis)` |
| `S08-048-license-compliance-devops` | Spécialiste conformité des licences | Vérifier la conformité des licences dans la chaîne logicielle | `— (LLM requis)` |
| `S08-049-repo-templates` | Spécialiste gabarits de dépôt | Créer des gabarits de dépôt réutilisables | `— (LLM requis)` |
| `S08-050-devops-coordinator` | Coordinateur DevOps | Coordonner les spécialistes GitHub et DevOps | `— (LLM requis)` |

## D09 — Architecture logicielle
*Concevoir des architectures modulaires, interopérables, scalables et résilientes sans dépendances circulaires.* · Chef : `M09-architecture-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S09-001-import-graph` | Analyste graphe de dépendances | Détecter les dépendances circulaires entre modules Python | `import_graph` |
| `S09-002-contract-check` | Vérificateur de contrats d'interface | Vérifier la complétude d'un contrat d'interface JSON | `contract_check` |
| `S09-003-system-architecture` | Architecte système | Concevoir l'architecture globale d'un système | `— (LLM requis)` |
| `S09-004-microservices` | Architecte microservices | Concevoir des microservices avec frontières pertinentes | `— (LLM requis)` |
| `S09-005-monolith-design` | Architecte monolithe modulaire | Concevoir un monolithe modulaire évolutif | `— (LLM requis)` |
| `S09-006-modular-design` | Concepteur modularité | Définir des modules à responsabilités uniques | `— (LLM requis)` |
| `S09-007-event-driven` | Architecte événementiel | Concevoir des architectures événementielles fiables | `— (LLM requis)` |
| `S09-008-cqrs` | Spécialiste CQRS | Séparer lectures et écritures quand c'est justifié | `— (LLM requis)` |
| `S09-009-domain-driven-design` | Spécialiste DDD | Modéliser le domaine avec un langage ubiquitaire | `— (LLM requis)` |
| `S09-010-hexagonal-architecture` | Architecte hexagonal | Isoler le domaine des adaptateurs externes | `— (LLM requis)` |
| `S09-011-clean-architecture` | Spécialiste clean architecture | Organiser les couches par dépendances dirigées | `— (LLM requis)` |
| `S09-012-layering` | Spécialiste découpage en couches | Définir des couches aux responsabilités nettes | `— (LLM requis)` |
| `S09-013-api-design` | Concepteur d'API | Concevoir des API cohérentes et évolutives | `— (LLM requis)` |
| `S09-014-data-architecture` | Architecte données | Concevoir l'architecture des données d'un système | `— (LLM requis)` |
| `S09-015-database-design` | Concepteur bases de données | Modéliser des schémas de données corrects | `— (LLM requis)` |
| `S09-016-caching-architecture` | Architecte cache | Placer les caches au bon endroit avec invalidation sûre | `— (LLM requis)` |
| `S09-017-queue-architecture` | Architecte files de messages | Concevoir des files de messages fiables | `— (LLM requis)` |
| `S09-018-scalability-architecture` | Architecte scalabilité | Concevoir pour la montée en charge réelle | `— (LLM requis)` |
| `S09-019-resilience-architecture` | Architecte résilience | Concevoir des systèmes qui survivent aux pannes partielles | `— (LLM requis)` |
| `S09-020-fault-tolerance` | Spécialiste tolérance aux pannes | Ajouter redondance et reprise sans surcoût inutile | `— (LLM requis)` |
| `S09-021-distributed-systems` | Spécialiste systèmes distribués | Traiter les pièges des systèmes distribués | `— (LLM requis)` |
| `S09-022-consistency-models` | Spécialiste modèles de consistance | Choisir un modèle de consistance adapté | `— (LLM requis)` |
| `S09-023-cap-tradeoffs` | Analyste compromis CAP | Expliciter les compromis consistance-disponibilité | `— (LLM requis)` |
| `S09-024-service-mesh` | Spécialiste service mesh | Évaluer la pertinence d'un service mesh | `— (LLM requis)` |
| `S09-025-serverless-architecture` | Architecte serverless | Concevoir des architectures serverless adaptées | `— (LLM requis)` |
| `S09-026-edge-architecture` | Architecte edge | Concevoir du traitement en périphérie quand justifié | `— (LLM requis)` |
| `S09-027-security-architecture` | Architecte sécurité | Intégrer la sécurité dans l'architecture dès la conception | `— (LLM requis)` |
| `S09-028-observability-architecture` | Architecte observabilité | Concevoir logs, métriques et traces corrélés | `— (LLM requis)` |
| `S09-029-deployment-architecture` | Architecte déploiement | Concevoir des topologies de déploiement sûres | `— (LLM requis)` |
| `S09-030-multi-tenant` | Architecte multi-tenant | Concevoir l'isolation multi-tenant | `— (LLM requis)` |
| `S09-031-saas-architecture` | Architecte SaaS | Concevoir une architecture SaaS évolutive | `— (LLM requis)` |
| `S09-032-mobile-architecture` | Architecte mobile | Concevoir l'architecture d'applications mobiles | `— (LLM requis)` |
| `S09-033-web-architecture` | Architecte web | Concevoir l'architecture d'applications web | `— (LLM requis)` |
| `S09-034-realtime-architecture` | Architecte temps réel | Concevoir des systèmes temps réel fiables | `— (LLM requis)` |
| `S09-035-batch-architecture` | Architecte batch | Concevoir des traitements batch efficaces | `— (LLM requis)` |
| `S09-036-streaming-architecture` | Architecte streaming | Concevoir des pipelines de streaming | `— (LLM requis)` |
| `S09-037-storage-architecture` | Architecte stockage | Choisir les stockages adaptés aux accès | `— (LLM requis)` |
| `S09-038-search-architecture` | Architecte recherche | Concevoir des systèmes de recherche pertinents | `— (LLM requis)` |
| `S09-039-ml-architecture` | Architecte ML | Concevoir l'architecture de systèmes ML en production | `— (LLM requis)` |
| `S09-040-integration-architecture` | Architecte intégration | Concevoir des intégrations entre systèmes | `— (LLM requis)` |
| `S09-041-legacy-modernization` | Spécialiste modernisation legacy | Moderniser progressivement du legacy | `— (LLM requis)` |
| `S09-042-migration-architecture` | Architecte migration | Concevoir des migrations d'architecture sûres | `— (LLM requis)` |
| `S09-043-performance-architecture` | Architecte performance | Concevoir pour la performance mesurée | `— (LLM requis)` |
| `S09-044-cost-architecture` | Architecte coût | Concevoir en maîtrisant les coûts réels | `— (LLM requis)` |
| `S09-045-compliance-architecture` | Architecte conformité | Intégrer les exigences de conformité dans l'architecture | `— (LLM requis)` |
| `S09-046-documentation-architecture` | Documentaliste architecture | Documenter l'architecture de façon maintenable | `— (LLM requis)` |
| `S09-047-adr-facilitation` | Facilitateur ADR | Faciliter la prise de décisions d'architecture tracées | `— (LLM requis)` |
| `S09-048-tech-debt-architecture` | Analyste dette technique | Identifier et prioriser la dette technique d'architecture | `— (LLM requis)` |
| `S09-049-architecture-review` | Relecteur d'architecture | Réaliser des revues d'architecture exigeantes | `— (LLM requis)` |
| `S09-050-architecture-coordinator` | Coordinateur architecture | Coordonner les architectes sur une conception complexe | `— (LLM requis)` |

## D10 — Débogage et maintenance
*Diagnostiquer, reproduire, corriger et prévenir les régressions avec des preuves.* · Chef : `M10-debogage-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S10-001-traceback-parse` | Analyste de traces d'erreur | Extraire la structure d'une traceback Python pour diagnostic | `traceback_parse` |
| `S10-002-log-anomaly` | Détecteur d'anomalies de journaux | Repérer les pics d'erreurs dans des journaux | `log_anomaly` |
| `S10-003-bug-reproduction` | Reproducteur de bugs | Reproduire un bug de façon fiable et minimale | `— (LLM requis)` |
| `S10-004-bug-triage` | Trieur de bugs | Prioriser les bugs selon impact et fréquence | `— (LLM requis)` |
| `S10-005-root-cause-debug` | Analyste cause racine technique | Trouver la cause racine technique d'un bug | `— (LLM requis)` |
| `S10-006-regression-detection` | Détecteur de régressions | Détecter les régressions introduites par un changement | `— (LLM requis)` |
| `S10-007-fix-verification` | Vérificateur de correctifs | Vérifier qu'un correctif résout le bug sans effet de bord | `— (LLM requis)` |
| `S10-008-hotfix-management` | Gestionnaire de hotfix | Gérer des correctifs urgents avec traçabilité | `— (LLM requis)` |
| `S10-009-patch-testing` | Testeur de correctifs | Tester un correctif sur les cas limites | `— (LLM requis)` |
| `S10-010-crash-analysis` | Analyste de plantages | Analyser les plantages pour en trouver la cause | `— (LLM requis)` |
| `S10-011-memory-leak-debug` | Détecteur de fuites mémoire | Identifier les fuites mémoire dans une application | `— (LLM requis)` |
| `S10-012-race-condition-debug` | Détecteur de conditions de course | Identifier les conditions de course | `— (LLM requis)` |
| `S10-013-deadlock-debug` | Détecteur d'interblocages | Identifier les interblocages entre ressources | `— (LLM requis)` |
| `S10-014-performance-debug` | Diagnostiqueur performance | Diagnostiquer les lenteurs par la mesure | `— (LLM requis)` |
| `S10-015-network-debug` | Diagnostiqueur réseau | Diagnostiquer les problèmes réseau d'une application | `— (LLM requis)` |
| `S10-016-database-debug` | Diagnostiqueur base de données | Diagnostiquer les problèmes de requêtes et transactions | `— (LLM requis)` |
| `S10-017-api-debug` | Diagnostiqueur API | Diagnostiquer les erreurs d'API | `— (LLM requis)` |
| `S10-018-frontend-debug` | Diagnostiqueur frontend | Diagnostiquer les bugs d'interface | `— (LLM requis)` |
| `S10-019-mobile-debug` | Diagnostiqueur mobile | Diagnostiquer les bugs d'applications mobiles | `— (LLM requis)` |
| `S10-020-build-debug` | Diagnostiqueur build | Diagnostiquer les échecs de build | `— (LLM requis)` |
| `S10-021-dependency-debug` | Diagnostiqueur dépendances | Diagnostiquer les conflits de dépendances | `— (LLM requis)` |
| `S10-022-configuration-debug` | Diagnostiqueur configuration | Diagnostiquer les erreurs de configuration | `— (LLM requis)` |
| `S10-023-environment-debug` | Diagnostiqueur environnements | Diagnostiquer les différences entre environnements | `— (LLM requis)` |
| `S10-024-logging-improvement` | Améliorateur de journalisation | Améliorer les journaux pour faciliter le diagnostic | `— (LLM requis)` |
| `S10-025-error-message-improvement` | Améliorateur de messages d'erreur | Rendre les messages d'erreur actionnables | `— (LLM requis)` |
| `S10-026-defensive-coding` | Spécialiste code défensif | Ajouter des garde-fous sans masquer les erreurs | `— (LLM requis)` |
| `S10-027-invariant-checking` | Spécialiste invariants | Définir et vérifier les invariants d'un système | `— (LLM requis)` |
| `S10-028-assertion-strategy` | Spécialiste stratégie d'assertions | Placer des assertions utiles au bon endroit | `— (LLM requis)` |
| `S10-029-fuzz-testing-defensive` | Testeur fuzzing défensif | Tester la robustesse avec des entrées générées en périmètre autorisé | `— (LLM requis)` |
| `S10-030-property-testing` | Spécialiste tests par propriétés | Définir des propriétés vérifiables du code | `— (LLM requis)` |
| `S10-031-snapshot-testing` | Spécialiste tests snapshot | Utiliser les tests snapshot à bon escient | `— (LLM requis)` |
| `S10-032-golden-testing` | Spécialiste tests golden | Comparer des sorties à des références validées | `— (LLM requis)` |
| `S10-033-diff-debug` | Analyste debug par diff | Identifier le changement responsable d'un bug | `— (LLM requis)` |
| `S10-034-bisect-strategy` | Spécialiste bisect | Localiser une régression par bisect | `— (LLM requis)` |
| `S10-035-instrumentation` | Spécialiste instrumentation | Instrumenter le code pour le diagnostic sans dégradation | `— (LLM requis)` |
| `S10-036-profiling-debug` | Profileur de diagnostic | Profiler pour localiser un goulot | `— (LLM requis)` |
| `S10-037-heap-analysis` | Analyste mémoire heap | Analyser l'occupation mémoire pour trouver les fuites | `— (LLM requis)` |
| `S10-038-thread-analysis` | Analyste threads | Analyser l'état des threads pour diagnostiquer | `— (LLM requis)` |
| `S10-039-io-debug` | Diagnostiqueur entrées/sorties | Diagnostiquer les problèmes d'E/S | `— (LLM requis)` |
| `S10-040-serialization-debug` | Diagnostiqueur sérialisation | Diagnostiquer les erreurs de sérialisation | `— (LLM requis)` |
| `S10-041-timezone-debug` | Diagnostiqueur fuseaux horaires | Diagnostiquer les bugs de fuseaux horaires | `— (LLM requis)` |
| `S10-042-encoding-debug` | Diagnostiqueur encodage | Diagnostiquer les bugs d'encodage de texte | `— (LLM requis)` |
| `S10-043-floating-point-debug` | Diagnostiqueur calcul flottant | Diagnostiquer les erreurs de calcul flottant | `— (LLM requis)` |
| `S10-044-concurrency-debug` | Diagnostiqueur concurrence | Diagnostiquer les bugs de concurrence complexes | `— (LLM requis)` |
| `S10-045-distributed-debug` | Diagnostiqueur distribué | Diagnostiquer les bugs de systèmes distribués | `— (LLM requis)` |
| `S10-046-cache-debug` | Diagnostiqueur cache | Diagnostiquer les incohérences de cache | `— (LLM requis)` |
| `S10-047-state-debug` | Diagnostiqueur état | Diagnostiquer les bugs d'état | `— (LLM requis)` |
| `S10-048-flaky-test-debug` | Détecteur de tests instables | Identifier et stabiliser les tests instables | `— (LLM requis)` |
| `S10-049-maintenance-planning` | Planificateur maintenance | Planifier la maintenance préventive | `— (LLM requis)` |
| `S10-050-debug-coordinator` | Coordinateur débogage | Coordonner les diagnostiqueurs sur un incident complexe | `— (LLM requis)` |

## D11 — Recherche scientifique
*Analyser des publications, méthodes et résultats avec rigueur expérimentale et esprit critique.* · Chef : `M11-science-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S11-001-sample-compare` | Comparateur d'échantillons | Comparer deux échantillons avec des statistiques exactes | `sample_compare` |
| `S11-002-repro-audit` | Auditeur reproductibilité | Évaluer la reproductibilité d'un protocole décrit | `reproducibility_audit` |
| `S11-003-paper-analysis` | Analyste de publications | Analyser une publication scientifique de façon critique | `— (LLM requis)` |
| `S11-004-abstract-screening` | Trieur d'abstracts | Sélectionner des abstracts pertinents pour une revue | `— (LLM requis)` |
| `S11-005-methodology-review` | Relecteur méthodologie | Évaluer la solidité méthodologique d'une étude | `— (LLM requis)` |
| `S11-006-experimental-design` | Concepteur d'expériences | Concevoir des expériences contrôlées et interprétables | `— (LLM requis)` |
| `S11-007-hypothesis-validation` | Validateur d'hypothèses scientifiques | Confronter une hypothèse aux données disponibles | `— (LLM requis)` |
| `S11-008-literature-review` | Réalisateur de revues de littérature | Synthétiser un corpus de publications de façon fidèle | `— (LLM requis)` |
| `S11-009-meta-analysis` | Analyste méta-analyses | Interpréter des méta-analyses avec leurs limites | `— (LLM requis)` |
| `S11-010-statistical-review` | Relecteur statistique | Vérifier l'usage correct des statistiques dans une étude | `— (LLM requis)` |
| `S11-011-peer-review` | Relecteur par les pairs | Réaliser une revue par les pairs constructive | `— (LLM requis)` |
| `S11-012-citation-analysis` | Analyste de citations | Analyser les réseaux de citations d'un domaine | `— (LLM requis)` |
| `S11-013-research-ethics` | Spécialiste éthique de la recherche | Vérifier les aspects éthiques d'un protocole | `— (LLM requis)` |
| `S11-014-data-availability` | Spécialiste disponibilité des données | Vérifier la disponibilité et la qualité des données de recherche | `— (LLM requis)` |
| `S11-015-code-availability` | Spécialiste disponibilité du code | Vérifier la disponibilité du code de recherche | `— (LLM requis)` |
| `S11-016-replication` | Spécialiste réplication | Planifier la réplication d'une expérience | `— (LLM requis)` |
| `S11-017-preprint-analysis` | Analyste de prépublications | Analyser des prépublications avec prudence | `— (LLM requis)` |
| `S11-018-conference-analysis` | Analyste de conférences | Évaluer la qualité et la pertinence de conférences | `— (LLM requis)` |
| `S11-019-journal-selection` | Conseiller choix de journal | Recommander un journal adapté à un travail | `— (LLM requis)` |
| `S11-020-grant-writing` | Conseiller rédaction de demandes de financement | Structurer une demande de financement claire | `— (LLM requis)` |
| `S11-021-research-proposal` | Concepteur propositions de recherche | Concevoir une proposition de recherche solide | `— (LLM requis)` |
| `S11-022-lab-notebook` | Spécialiste cahier de laboratoire | Structurer la traçabilité des expériences | `— (LLM requis)` |
| `S11-023-measurement` | Spécialiste mesure | Évaluer la validité et la fiabilité des mesures | `— (LLM requis)` |
| `S11-024-sampling` | Spécialiste échantillonnage | Concevoir un échantillonnage représentatif | `— (LLM requis)` |
| `S11-025-bias-scientific` | Détecteur de biais scientifiques | Identifier les biais dans une étude | `— (LLM requis)` |
| `S11-026-confounding` | Analyste facteurs de confusion | Identifier les facteurs de confusion d'une relation | `— (LLM requis)` |
| `S11-027-effect-size` | Spécialiste taille d'effet | Interpréter les tailles d'effet au-delà de la significativité | `— (LLM requis)` |
| `S11-028-p-value-interpretation` | Interprète de valeurs p | Interpréter correctement les valeurs p et leurs limites | `— (LLM requis)` |
| `S11-029-confidence-intervals` | Spécialiste intervalles de confiance | Interpréter des intervalles de confiance correctement | `— (LLM requis)` |
| `S11-030-power-analysis` | Analyste puissance statistique | Évaluer la puissance d'une étude | `— (LLM requis)` |
| `S11-031-multiple-testing` | Spécialiste tests multiples | Corriger les tests multiples pour éviter les faux positifs | `— (LLM requis)` |
| `S11-032-bayesian-stats` | Spécialiste statistiques bayésiennes | Interpréter des analyses bayésiennes | `— (LLM requis)` |
| `S11-033-causal-science` | Spécialiste inférence causale scientifique | Évaluer les preuves de causalité d'une étude | `— (LLM requis)` |
| `S11-034-systematic-review` | Spécialiste revue systématique | Concevoir une revue systématique rigoureuse | `— (LLM requis)` |
| `S11-035-scoping-review` | Spécialiste revue exploratoire | Concevoir une revue exploratoire de portée | `— (LLM requis)` |
| `S11-036-evidence-grading` | Évaluateur niveau de preuve | Classer le niveau de preuve d'affirmations | `— (LLM requis)` |
| `S11-037-scientific-writing` | Rédacteur scientifique | Rédiger des textes scientifiques clairs et précis | `— (LLM requis)` |
| `S11-038-figure-review` | Relecteur de figures scientifiques | Vérifier l'exactitude et la lisibilité des figures | `— (LLM requis)` |
| `S11-039-table-review` | Relecteur de tableaux scientifiques | Vérifier l'exactitude et la lisibilité des tableaux | `— (LLM requis)` |
| `S11-040-units-dimensions` | Spécialiste unités et dimensions | Vérifier la cohérence des unités et dimensions | `— (LLM requis)` |
| `S11-041-error-propagation` | Spécialiste propagation d'erreurs | Calculer la propagation des incertitudes | `— (LLM requis)` |
| `S11-042-simulation` | Spécialiste simulation | Concevoir des simulations vérifiables | `— (LLM requis)` |
| `S11-043-model-validation` | Validateur de modèles scientifiques | Valider un modèle scientifique contre des données | `— (LLM requis)` |
| `S11-044-open-science` | Spécialiste science ouverte | Promouvoir des pratiques de science ouverte | `— (LLM requis)` |
| `S11-045-preregistration` | Spécialiste préenregistrement | Concevoir un préenregistrement d'étude | `— (LLM requis)` |
| `S11-046-negative-results` | Analyste résultats négatifs | Valoriser et interpréter les résultats négatifs | `— (LLM requis)` |
| `S11-047-scientific-controversy` | Analyste controverses scientifiques | Analyser une controverse en exposant les preuves | `— (LLM requis)` |
| `S11-048-interdisciplinary` | Spécialiste interdisciplinarité | Faire le lien entre disciplines sur un problème | `— (LLM requis)` |
| `S11-049-research-trends` | Analyste tendances de recherche | Identifier les tendances émergentes d'un domaine | `— (LLM requis)` |
| `S11-050-science-coordinator` | Coordinateur recherche scientifique | Coordonner les spécialistes scientifiques sur une analyse | `— (LLM requis)` |

## D12 — Analyse de données
*Analyser des données structurées, produire des indicateurs fiables et détecter des anomalies.* · Chef : `M12-analyse-donnees-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S12-001-csv-profile` | Profileur de données CSV | Profiler un fichier CSV pour en connaître structure et qualité | `csv_profile` |
| `S12-002-sql-safety` | Auditeur de requêtes SQL | Détecter les requêtes SQL dangereuses ou non optimisées | `sql_safety_check` |
| `S12-003-sql-query` | Analyste requêtes SQL | Écrire des requêtes SQL correctes et lisibles | `— (LLM requis)` |
| `S12-004-data-quality` | Analyste qualité de données | Évaluer la qualité d'un jeu de données | `— (LLM requis)` |
| `S12-005-kpi-design` | Concepteur d'indicateurs | Définir des indicateurs alignés avec les objectifs | `— (LLM requis)` |
| `S12-006-dashboard-design` | Concepteur de tableaux de bord | Concevoir des tableaux de bord lisibles et utiles | `— (LLM requis)` |
| `S12-007-data-viz` | Spécialiste visualisation de données | Choisir des visualisations adaptées aux données | `— (LLM requis)` |
| `S12-008-chart-review` | Relecteur de graphiques | Vérifier l'exactitude et l'honnêteté des graphiques | `— (LLM requis)` |
| `S12-009-anomaly-detection-data` | Détecteur d'anomalies de données | Repérer les anomalies dans des jeux de données | `— (LLM requis)` |
| `S12-010-trend-analysis` | Analyste de tendances | Identifier des tendances dans des séries de données | `— (LLM requis)` |
| `S12-011-cohort-analysis` | Analyste de cohortes | Analyser des cohortes pour comprendre les comportements | `— (LLM requis)` |
| `S12-012-funnel-analysis` | Analyste d'entonnoirs | Analyser des entonnoirs de conversion | `— (LLM requis)` |
| `S12-013-retention-analysis` | Analyste de rétention | Mesurer et interpréter la rétention | `— (LLM requis)` |
| `S12-014-segmentation` | Spécialiste segmentation | Segmenter des données en groupes pertinents | `— (LLM requis)` |
| `S12-015-aggregation` | Spécialiste agrégation | Agréger des données sans introduire de biais | `— (LLM requis)` |
| `S12-016-join-analysis` | Spécialiste jointures | Jointurer des données sans perte ni duplication | `— (LLM requis)` |
| `S12-017-pivot-analysis` | Spécialiste tableaux croisés | Produire des tableaux croisés lisibles | `— (LLM requis)` |
| `S12-018-time-series-data` | Analyste séries temporelles de données | Analyser des séries temporelles métier | `— (LLM requis)` |
| `S12-019-forecast-data` | Spécialiste prévision de données | Produire des prévisions simples avec incertitude | `— (LLM requis)` |
| `S12-020-ab-test-analysis` | Analyste tests A/B | Analyser des tests A/B avec rigueur | `— (LLM requis)` |
| `S12-021-survey-analysis` | Analyste d'enquêtes | Analyser des résultats d'enquête avec leurs biais | `— (LLM requis)` |
| `S12-022-text-data` | Analyste de données textuelles | Extraire des indicateurs de données textuelles | `— (LLM requis)` |
| `S12-023-log-data` | Analyste de données de journaux | Extraire des indicateurs de journaux applicatifs | `— (LLM requis)` |
| `S12-024-metric-definition` | Spécialiste définition de métriques | Définir des métriques sans ambiguïté | `— (LLM requis)` |
| `S12-025-metric-audit` | Auditeur de métriques | Vérifier la cohérence des métriques rapportées | `— (LLM requis)` |
| `S12-026-data-lineage` | Spécialiste lignage de données | Tracer l'origine et les transformations des données | `— (LLM requis)` |
| `S12-027-data-catalog` | Spécialiste catalogue de données | Organiser un catalogue de données exploitable | `— (LLM requis)` |
| `S12-028-metadata-management` | Gestionnaire de métadonnées | Maintenir des métadonnées exactes et à jour | `— (LLM requis)` |
| `S12-029-data-dictionary` | Spécialiste dictionnaire de données | Rédiger un dictionnaire de données clair | `— (LLM requis)` |
| `S12-030-etl-analysis` | Analyste ETL | Analyser et améliorer des pipelines ETL | `— (LLM requis)` |
| `S12-031-data-warehouse` | Spécialiste entrepôt de données | Concevoir des entrepôts de données analytiques | `— (LLM requis)` |
| `S12-032-data-lake` | Spécialiste lac de données | Organiser un lac de données gouverné | `— (LLM requis)` |
| `S12-033-olap` | Spécialiste OLAP | Concevoir des cubes et analyses multidimensionnelles | `— (LLM requis)` |
| `S12-034-reporting` | Spécialiste reporting | Produire des rapports fidèles aux données | `— (LLM requis)` |
| `S12-035-self-service-bi` | Spécialiste BI en libre-service | Permettre l'analyse en libre-service avec garde-fous | `— (LLM requis)` |
| `S12-036-data-storytelling` | Spécialiste data storytelling | Raconter les données de façon fidèle et impactante | `— (LLM requis)` |
| `S12-037-outlier-analysis` | Analyste de valeurs atypiques | Interpréter les valeurs atypiques en contexte | `— (LLM requis)` |
| `S12-038-missing-data-analysis` | Analyste données manquantes | Analyser l'impact des données manquantes | `— (LLM requis)` |
| `S12-039-duplicate-detection` | Détecteur de doublons de données | Détecter et traiter les doublons dans les données | `— (LLM requis)` |
| `S12-040-data-validation` | Spécialiste validation de données | Définir des règles de validation de données | `— (LLM requis)` |
| `S12-041-schema-evolution` | Spécialiste évolution de schémas | Gérer l'évolution des schémas de données | `— (LLM requis)` |
| `S12-042-data-privacy-analysis` | Spécialiste confidentialité des données | Minimiser les données personnelles dans les analyses | `— (LLM requis)` |
| `S12-043-geospatial-analysis` | Analyste données géospatiales | Analyser des données géospatiales avec leurs limites | `— (LLM requis)` |
| `S12-044-graph-data` | Analyste données en graphe | Analyser des données structurées en graphe | `— (LLM requis)` |
| `S12-045-streaming-data` | Analyste données en flux | Analyser des données en flux avec fenêtres | `— (LLM requis)` |
| `S12-046-batch-data` | Analyste données batch | Analyser des traitements batch de données | `— (LLM requis)` |
| `S12-047-data-cost` | Spécialiste coût des données | Maîtriser les coûts de stockage et traitement des données | `— (LLM requis)` |
| `S12-048-data-governance` | Spécialiste gouvernance des données | Définir la gouvernance des données | `— (LLM requis)` |
| `S12-049-data-observability` | Spécialiste observabilité des données | Surveiller la santé des pipelines de données | `— (LLM requis)` |
| `S12-050-data-analysis-coordinator` | Coordinateur analyse de données | Coordonner les analystes sur une étude | `— (LLM requis)` |

## D13 — Applications mobiles
*Concevoir, développer et optimiser des applications Android, iOS et multiplateformes.* · Chef : `M13-mobile-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S13-001-android-manifest` | Auditeur manifestes Android | Vérifier les permissions et composants exposés d'un manifeste Android | `android_manifest_check` |
| `S13-002-ios-plist` | Auditeur fichiers plist iOS | Vérifier la cohérence et la sécurité d'un fichier plist iOS | `plist_check` |
| `S13-003-android-kotlin` | Développeur Android Kotlin | Développer des fonctionnalités Android en Kotlin | `— (LLM requis)` |
| `S13-004-android-compose` | Spécialiste Jetpack Compose | Construire des interfaces Android en Compose | `— (LLM requis)` |
| `S13-005-android-architecture` | Architecte Android | Structurer une application Android maintenable | `— (LLM requis)` |
| `S13-006-ios-swift` | Développeur iOS Swift | Développer des fonctionnalités iOS en Swift | `— (LLM requis)` |
| `S13-007-ios-swiftui` | Spécialiste SwiftUI | Construire des interfaces iOS en SwiftUI | `— (LLM requis)` |
| `S13-008-ios-architecture` | Architecte iOS | Structurer une application iOS maintenable | `— (LLM requis)` |
| `S13-009-flutter-dev` | Développeur Flutter | Développer des applications multiplateformes en Flutter | `— (LLM requis)` |
| `S13-010-react-native-dev` | Développeur React Native | Développer des applications en React Native | `— (LLM requis)` |
| `S13-011-kmp-dev` | Spécialiste Kotlin Multiplatform | Partager du code entre plateformes avec KMP | `— (LLM requis)` |
| `S13-012-mobile-ui` | Concepteur interfaces mobiles | Concevoir des interfaces mobiles ergonomiques | `— (LLM requis)` |
| `S13-013-mobile-ux` | Spécialiste UX mobile | Optimiser l'expérience utilisateur mobile | `— (LLM requis)` |
| `S13-014-mobile-navigation` | Spécialiste navigation mobile | Structurer la navigation d'une application mobile | `— (LLM requis)` |
| `S13-015-mobile-state` | Spécialiste gestion d'état mobile | Gérer l'état d'une application mobile | `— (LLM requis)` |
| `S13-016-mobile-networking` | Spécialiste réseau mobile | Gérer les appels réseau avec conditions mobiles | `— (LLM requis)` |
| `S13-017-mobile-offline` | Spécialiste mode hors ligne | Concevoir le fonctionnement hors ligne | `— (LLM requis)` |
| `S13-018-mobile-storage` | Spécialiste stockage mobile | Stocker les données mobiles de façon sûre | `— (LLM requis)` |
| `S13-019-mobile-permissions` | Spécialiste permissions mobiles | Demander les permissions de façon minimale et expliquée | `— (LLM requis)` |
| `S13-020-mobile-push` | Spécialiste notifications push | Intégrer des notifications push respectueuses | `— (LLM requis)` |
| `S13-021-mobile-deeplinks` | Spécialiste deep links | Gérer les deep links et universal links | `— (LLM requis)` |
| `S13-022-mobile-performance` | Optimiseur performance mobile | Optimiser la performance des applications mobiles | `— (LLM requis)` |
| `S13-023-mobile-battery` | Spécialiste consommation batterie | Réduire la consommation batterie | `— (LLM requis)` |
| `S13-024-mobile-memory` | Spécialiste mémoire mobile | Maîtriser l'usage mémoire sur mobile | `— (LLM requis)` |
| `S13-025-mobile-startup` | Spécialiste démarrage mobile | Optimiser le temps de démarrage | `— (LLM requis)` |
| `S13-026-mobile-rendering` | Spécialiste rendu mobile | Optimiser le rendu des interfaces mobiles | `— (LLM requis)` |
| `S13-027-mobile-accessibility` | Spécialiste accessibilité mobile | Rendre les applications mobiles accessibles | `— (LLM requis)` |
| `S13-028-mobile-localization` | Spécialiste localisation mobile | Localiser les applications correctement | `— (LLM requis)` |
| `S13-029-mobile-testing` | Testeur mobile | Tester les applications mobiles sur appareils cibles | `— (LLM requis)` |
| `S13-030-mobile-ui-testing` | Spécialiste tests UI mobiles | Automatiser les tests d'interface mobile | `— (LLM requis)` |
| `S13-031-mobile-ci` | Spécialiste CI mobile | Intégrer les builds mobiles dans la CI | `— (LLM requis)` |
| `S13-032-mobile-release` | Spécialiste release mobile | Préparer les releases sur les stores | `— (LLM requis)` |
| `S13-033-app-store` | Spécialiste App Store | Optimiser la présence App Store | `— (LLM requis)` |
| `S13-034-play-store` | Spécialiste Play Store | Optimiser la présence Play Store | `— (LLM requis)` |
| `S13-035-mobile-analytics` | Spécialiste analytique mobile | Instrumenter l'analytique mobile avec consentement | `— (LLM requis)` |
| `S13-036-mobile-crash` | Spécialiste crash reporting | Intégrer le reporting de crashs sans données sensibles | `— (LLM requis)` |
| `S13-037-mobile-security` | Spécialiste sécurité mobile | Sécuriser les applications mobiles | `— (LLM requis)` |
| `S13-038-mobile-obfuscation` | Spécialiste obfuscation | Protéger le code mobile contre l'analyse non autorisée | `— (LLM requis)` |
| `S13-039-mobile-webview` | Spécialiste WebView | Intégrer des WebView de façon sûre | `— (LLM requis)` |
| `S13-040-mobile-graphics` | Spécialiste graphismes mobiles | Optimiser les graphismes et animations mobiles | `— (LLM requis)` |
| `S13-041-mobile-camera` | Spécialiste caméra et capteurs | Intégrer caméra et capteurs avec permissions | `— (LLM requis)` |
| `S13-042-mobile-background` | Spécialiste tâches d'arrière-plan | Gérer les tâches d'arrière-plan selon les contraintes OS | `— (LLM requis)` |
| `S13-043-mobile-widgets` | Spécialiste widgets mobiles | Créer des widgets et complications | `— (LLM requis)` |
| `S13-044-mobile-wearables` | Spécialiste objets portables | Adapter les applications aux objets portables | `— (LLM requis)` |
| `S13-045-mobile-tablet` | Spécialiste tablettes et pliables | Adapter les interfaces aux grands écrans | `— (LLM requis)` |
| `S13-046-mobile-migration` | Spécialiste migration mobile | Planifier la migration d'une app mobile | `— (LLM requis)` |
| `S13-047-mobile-legacy` | Spécialiste maintenance mobile legacy | Maintenir des applications mobiles anciennes | `— (LLM requis)` |
| `S13-048-mobile-design-system` | Spécialiste design system mobile | Maintenir un design system mobile cohérent | `— (LLM requis)` |
| `S13-049-mobile-prototype` | Spécialiste prototypage mobile | Prototyper rapidement des idées mobiles | `— (LLM requis)` |
| `S13-050-mobile-coordinator` | Coordinateur mobile | Coordonner les spécialistes mobiles sur une application | `— (LLM requis)` |

## D14 — Développement web et UX
*Construire des interfaces web accessibles, performantes et des backends web fiables.* · Chef : `M14-web-ux-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S14-001-html-a11y` | Auditeur accessibilité HTML | Détecter les problèmes d'accessibilité dans du HTML | `html_accessibility_check` |
| `S14-002-css-sanity` | Auditeur CSS | Détecter les incohérences et risques dans du CSS | `css_sanity_check` |
| `S14-003-frontend-dev` | Développeur frontend | Développer des interfaces web modernes | `— (LLM requis)` |
| `S14-004-backend-web` | Développeur backend web | Développer des backends web fiables | `— (LLM requis)` |
| `S14-005-react-dev` | Développeur React | Développer des applications React | `— (LLM requis)` |
| `S14-006-vue-dev` | Développeur Vue | Développer des applications Vue | `— (LLM requis)` |
| `S14-007-svelte-dev` | Développeur Svelte | Développer des applications Svelte | `— (LLM requis)` |
| `S14-008-angular-dev` | Développeur Angular | Développer des applications Angular | `— (LLM requis)` |
| `S14-009-html-semantics` | Spécialiste HTML sémantique | Utiliser le HTML sémantique correctement | `— (LLM requis)` |
| `S14-010-css-layout` | Spécialiste mise en page CSS | Réaliser des mises en page robustes | `— (LLM requis)` |
| `S14-011-responsive-design` | Spécialiste design responsive | Adapter les interfaces à tous les écrans | `— (LLM requis)` |
| `S14-012-web-accessibility` | Spécialiste accessibilité web | Atteindre les critères d'accessibilité WCAG | `— (LLM requis)` |
| `S14-013-aria` | Spécialiste ARIA | Utiliser ARIA à bon escient | `— (LLM requis)` |
| `S14-014-keyboard-nav` | Spécialiste navigation clavier | Garantir la navigation clavier complète | `— (LLM requis)` |
| `S14-015-screen-reader` | Spécialiste lecteurs d'écran | Optimiser pour les lecteurs d'écran | `— (LLM requis)` |
| `S14-016-color-contrast` | Spécialiste contraste des couleurs | Vérifier les contrastes de couleurs | `— (LLM requis)` |
| `S14-017-web-performance` | Optimiseur performance web | Optimiser la performance web mesurée | `— (LLM requis)` |
| `S14-018-bundle-optimization` | Spécialiste optimisation de bundles | Réduire la taille des bundles JavaScript | `— (LLM requis)` |
| `S14-019-image-optimization` | Spécialiste optimisation d'images | Optimiser les images pour le web | `— (LLM requis)` |
| `S14-020-web-fonts` | Spécialiste polices web | Optimiser le chargement des polices | `— (LLM requis)` |
| `S14-021-critical-css` | Spécialiste CSS critique | Extraire le CSS critique pour le premier rendu | `— (LLM requis)` |
| `S14-022-web-animations` | Spécialiste animations web | Créer des animations performantes et accessibles | `— (LLM requis)` |
| `S14-023-web-forms` | Spécialiste formulaires web | Concevoir des formulaires accessibles et sûrs | `— (LLM requis)` |
| `S14-024-web-state` | Spécialiste gestion d'état web | Gérer l'état des applications web | `— (LLM requis)` |
| `S14-025-web-routing` | Spécialiste routage web | Gérer le routage des applications web | `— (LLM requis)` |
| `S14-026-ssr` | Spécialiste rendu serveur | Intégrer le rendu serveur quand bénéfique | `— (LLM requis)` |
| `S14-027-ssg` | Spécialiste génération statique | Générer des sites statiques performants | `— (LLM requis)` |
| `S14-028-pwa` | Spécialiste applications web progressives | Ajouter les capacités PWA utiles | `— (LLM requis)` |
| `S14-029-service-workers` | Spécialiste service workers | Gérer les service workers sans piège de cache | `— (LLM requis)` |
| `S14-030-web-security-frontend` | Spécialiste sécurité frontend | Sécuriser le frontend contre XSS et fuites | `— (LLM requis)` |
| `S14-031-csp` | Spécialiste Content Security Policy | Configurer une CSP efficace sans casser l'app | `— (LLM requis)` |
| `S14-032-web-api-integration` | Spécialiste intégration API web | Intégrer des API dans le frontend proprement | `— (LLM requis)` |
| `S14-033-websockets` | Spécialiste WebSockets | Intégrer des communications temps réel | `— (LLM requis)` |
| `S14-034-web-testing` | Testeur web | Tester les applications web de bout en bout | `— (LLM requis)` |
| `S14-035-browser-compat` | Spécialiste compatibilité navigateurs | Assurer la compatibilité entre navigateurs | `— (LLM requis)` |
| `S14-036-web-components` | Spécialiste web components | Créer des web components réutilisables | `— (LLM requis)` |
| `S14-037-design-tokens` | Spécialiste design tokens | Gérer des design tokens cohérents | `— (LLM requis)` |
| `S14-038-ui-patterns` | Spécialiste patrons d'interface | Appliquer des patrons d'interface éprouvés | `— (LLM requis)` |
| `S14-039-ux-research` | Chercheur UX | Comprendre les besoins utilisateurs par la recherche | `— (LLM requis)` |
| `S14-040-usability` | Spécialiste utilisabilité | Évaluer et améliorer l'utilisabilité | `— (LLM requis)` |
| `S14-041-information-architecture` | Architecte information | Structurer l'information de façon navigable | `— (LLM requis)` |
| `S14-042-interaction-design` | Concepteur d'interactions | Concevoir des interactions claires et fluides | `— (LLM requis)` |
| `S14-043-visual-design` | Designer visuel | Créer des interfaces visuellement cohérentes | `— (LLM requis)` |
| `S14-044-prototyping-web` | Prototypeur web | Prototyper rapidement des interfaces web | `— (LLM requis)` |
| `S14-045-design-handoff` | Spécialiste passation design-dev | Faciliter la passation entre design et développement | `— (LLM requis)` |
| `S14-046-web-seo` | Spécialiste SEO technique | Optimiser le SEO technique sans manipulation | `— (LLM requis)` |
| `S14-047-web-analytics` | Spécialiste analytique web | Instrumenter l'analytique web avec consentement | `— (LLM requis)` |
| `S14-048-web-i18n` | Spécialiste internationalisation web | Internationaliser les applications web | `— (LLM requis)` |
| `S14-049-web-migration` | Spécialiste migration web | Planifier la migration d'une application web | `— (LLM requis)` |
| `S14-050-web-coordinator` | Coordinateur web et UX | Coordonner les spécialistes web et UX | `— (LLM requis)` |

## D15 — API et intégrations
*Concevoir, sécuriser et intégrer des API, événements et connecteurs de façon fiable.* · Chef : `M15-api-integrations-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S15-001-openapi-check` | Validateur de contrats OpenAPI | Vérifier la structure et la cohérence d'un contrat OpenAPI | `openapi_check` |
| `S15-002-webhook-signature` | Vérificateur de signatures de webhook | Vérifier l'authenticité d'un webhook par signature HMAC | `webhook_signature_check` |
| `S15-003-rest-design` | Concepteur API REST | Concevoir des API REST cohérentes | `— (LLM requis)` |
| `S15-004-graphql-design` | Concepteur GraphQL | Concevoir des schémas GraphQL efficaces | `— (LLM requis)` |
| `S15-005-grpc-design` | Concepteur gRPC | Concevoir des services gRPC typés | `— (LLM requis)` |
| `S15-006-api-versioning` | Spécialiste versionnement d'API | Gérer les versions d'API sans rupture | `— (LLM requis)` |
| `S15-007-api-auth` | Spécialiste authentification API | Sécuriser l'authentification des API | `— (LLM requis)` |
| `S15-008-api-authorization` | Spécialiste autorisation API | Définir des autorisations fines par rôle | `— (LLM requis)` |
| `S15-009-api-rate-limit` | Spécialiste limitation de débit API | Protéger les API par limitation de débit | `— (LLM requis)` |
| `S15-010-api-pagination` | Spécialiste pagination API | Concevoir une pagination efficace et stable | `— (LLM requis)` |
| `S15-011-api-filtering` | Spécialiste filtrage et tri API | Permettre filtrage et tri sûrs | `— (LLM requis)` |
| `S15-012-api-errors` | Spécialiste erreurs API | Définir des erreurs API cohérentes et utiles | `— (LLM requis)` |
| `S15-013-api-docs` | Spécialiste documentation API | Documenter les API de façon exploitable | `— (LLM requis)` |
| `S15-014-api-testing` | Testeur API | Tester les API de façon exhaustive | `— (LLM requis)` |
| `S15-015-api-mocking` | Spécialiste simulation d'API en test | Créer des mocks d'API pour les tests (environnement de test uniquement) | `— (LLM requis)` |
| `S15-016-api-gateway` | Spécialiste passerelle API | Concevoir une passerelle API | `— (LLM requis)` |
| `S15-017-webhooks-design` | Concepteur de webhooks | Concevoir des webhooks fiables et idempotents | `— (LLM requis)` |
| `S15-018-event-schema` | Spécialiste schémas d'événements | Définir des schémas d'événements évolutifs | `— (LLM requis)` |
| `S15-019-event-driven-integration` | Spécialiste intégration événementielle | Intégrer des systèmes par événements | `— (LLM requis)` |
| `S15-020-message-queue` | Spécialiste files de messages | Intégrer des files de messages fiables | `— (LLM requis)` |
| `S15-021-oauth-integration` | Spécialiste intégration OAuth | Intégrer OAuth correctement | `— (LLM requis)` |
| `S15-022-jwt-handling` | Spécialiste gestion JWT | Gérer les JWT de façon sûre | `— (LLM requis)` |
| `S15-023-api-keys-management` | Spécialiste gestion de clés API | Gérer les clés API sans exposition | `— (LLM requis)` |
| `S15-024-connector-design` | Concepteur de connecteurs | Concevoir des connecteurs réutilisables | `— (LLM requis)` |
| `S15-025-sdk-design` | Concepteur de SDK | Concevoir des SDK ergonomiques | `— (LLM requis)` |
| `S15-026-api-client-resilience` | Spécialiste résilience client API | Rendre les clients API résilients | `— (LLM requis)` |
| `S15-027-idempotency-keys` | Spécialiste clés d'idempotence | Garantir l'idempotence des opérations | `— (LLM requis)` |
| `S15-028-api-observability` | Spécialiste observabilité API | Instrumenter les API pour le suivi | `— (LLM requis)` |
| `S15-029-api-performance` | Optimiseur performance API | Optimiser la performance des API | `— (LLM requis)` |
| `S15-030-api-caching` | Spécialiste cache API | Mettre en cache les réponses API correctement | `— (LLM requis)` |
| `S15-031-api-security` | Spécialiste sécurité des API intégrées | Sécuriser les API contre les abus | `— (LLM requis)` |
| `S15-032-api-input-validation` | Spécialiste validation d'entrées API | Valider les entrées API strictement | `— (LLM requis)` |
| `S15-033-api-output-encoding` | Spécialiste encodage de sorties API | Encoder les sorties pour éviter les injections | `— (LLM requis)` |
| `S15-034-cors` | Spécialiste CORS | Configurer CORS de façon sûre | `— (LLM requis)` |
| `S15-035-api-gateway-policy` | Spécialiste politiques de passerelle | Définir les politiques d'une passerelle | `— (LLM requis)` |
| `S15-036-batch-api` | Spécialiste API batch | Concevoir des endpoints batch efficaces | `— (LLM requis)` |
| `S15-037-streaming-api` | Spécialiste API en streaming | Concevoir des API en streaming | `— (LLM requis)` |
| `S15-038-api-migration` | Spécialiste migration d'API | Planifier la migration d'une API | `— (LLM requis)` |
| `S15-039-legacy-integration` | Spécialiste intégration legacy | Intégrer des systèmes legacy proprement | `— (LLM requis)` |
| `S15-040-third-party-integration` | Spécialiste intégrations tierces | Intégrer des services tiers de façon sûre | `— (LLM requis)` |
| `S15-041-etl-integration` | Spécialiste intégration ETL | Intégrer des pipelines ETL entre systèmes | `— (LLM requis)` |
| `S15-042-file-integration` | Spécialiste intégration par fichiers | Intégrer des systèmes par échange de fichiers | `— (LLM requis)` |
| `S15-043-api-contract-testing` | Spécialiste tests de contrat | Vérifier la conformité aux contrats d'API | `— (LLM requis)` |
| `S15-044-api-deprecation` | Spécialiste dépréciation d'API | Gérer la dépréciation proprement | `— (LLM requis)` |
| `S15-045-api-monitoring` | Spécialiste surveillance API | Surveiller la santé des API | `— (LLM requis)` |
| `S15-046-api-cost` | Spécialiste coût des API | Maîtriser les coûts d'appels API | `— (LLM requis)` |
| `S15-047-api-governance` | Spécialiste gouvernance API | Définir la gouvernance du portefeuille d'API | `— (LLM requis)` |
| `S15-048-api-discovery` | Spécialiste découverte d'API | Faciliter la découverte des API disponibles | `— (LLM requis)` |
| `S15-049-api-changelog` | Spécialiste changelog API | Maintenir un changelog API fidèle | `— (LLM requis)` |
| `S15-050-api-coordinator` | Coordinateur API et intégrations | Coordonner les spécialistes API sur une intégration complexe | `— (LLM requis)` |

## D16 — Tests et qualité
*Garantir la qualité par des tests objectifs, indépendants et reproductibles.* · Chef : `M16-tests-qualite-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S16-001-coverage-parse` | Analyste rapports de couverture | Interpréter un rapport de couverture de tests XML | `test_coverage_parse` |
| `S16-002-assertion-density` | Analyste densité d'assertions | Évaluer la densité d'assertions dans des tests | `assertion_density` |
| `S16-003-unit-testing` | Testeur unitaire | Écrire des tests unitaires ciblés et rapides | `— (LLM requis)` |
| `S16-004-integration-testing` | Testeur intégration | Tester les interactions entre composants | `— (LLM requis)` |
| `S16-005-e2e-testing` | Testeur bout en bout | Tester les parcours complets de bout en bout | `— (LLM requis)` |
| `S16-006-regression-testing` | Testeur non-régression | Prévenir les régressions par des tests dédiés | `— (LLM requis)` |
| `S16-007-load-testing` | Testeur de charge | Tester la tenue en charge progressivement | `— (LLM requis)` |
| `S16-008-stress-testing` | Testeur de stress | Identifier le point de rupture d'un système | `— (LLM requis)` |
| `S16-009-performance-testing` | Testeur performance | Mesurer la performance de façon reproductible | `— (LLM requis)` |
| `S16-010-security-testing` | Testeur sécurité défensif | Tester la sécurité dans un périmètre autorisé | `— (LLM requis)` |
| `S16-011-accessibility-testing` | Testeur accessibilité | Tester l'accessibilité avec des critères objectifs | `— (LLM requis)` |
| `S16-012-compatibility-testing` | Testeur compatibilité | Tester la compatibilité entre environnements | `— (LLM requis)` |
| `S16-013-usability-testing` | Testeur utilisabilité | Évaluer l'utilisabilité par des tests structurés | `— (LLM requis)` |
| `S16-014-api-testing-quality` | Testeur API qualité | Tester les API contre leur contrat | `— (LLM requis)` |
| `S16-015-mobile-testing-quality` | Testeur mobile qualité | Tester les applications mobiles objectivement | `— (LLM requis)` |
| `S16-016-test-strategy` | Stratège de tests | Définir une stratégie de tests proportionnée | `— (LLM requis)` |
| `S16-017-test-pyramid` | Spécialiste pyramide de tests | Équilibrer les niveaux de tests | `— (LLM requis)` |
| `S16-018-test-data` | Spécialiste données de test | Préparer des données de test réalistes et sûres | `— (LLM requis)` |
| `S16-019-test-environments` | Spécialiste environnements de test | Gérer des environnements de test fiables | `— (LLM requis)` |
| `S16-020-test-automation-quality` | Spécialiste automatisation des tests | Automatiser les tests de façon maintenable | `— (LLM requis)` |
| `S16-021-test-flakiness` | Stabilisateur de tests instables | Détecter et éliminer les tests instables | `— (LLM requis)` |
| `S16-022-test-coverage` | Spécialiste couverture de tests | Interpréter la couverture sans en faire un fétiche | `— (LLM requis)` |
| `S16-023-mutation-testing` | Spécialiste tests par mutation | Évaluer la qualité des tests par mutation | `— (LLM requis)` |
| `S16-024-property-based-testing` | Spécialiste tests par propriétés qualité | Tester des propriétés avec des entrées générées | `— (LLM requis)` |
| `S16-025-contract-testing` | Spécialiste tests de contrat qualité | Vérifier les contrats entre services | `— (LLM requis)` |
| `S16-026-snapshot-testing-quality` | Spécialiste tests snapshot qualité | Utiliser les snapshots sans bruit | `— (LLM requis)` |
| `S16-027-visual-regression` | Spécialiste régression visuelle | Détecter les régressions visuelles | `— (LLM requis)` |
| `S16-028-test-review` | Relecteur de tests | Relire les tests pour en garantir la qualité | `— (LLM requis)` |
| `S16-029-test-naming` | Spécialiste nommage de tests | Nommer les tests de façon expressive | `— (LLM requis)` |
| `S16-030-test-organization` | Spécialiste organisation des tests | Organiser les tests de façon navigable | `— (LLM requis)` |
| `S16-031-test-speed` | Optimiseur vitesse de tests | Accélérer les suites de tests sans perdre la couverture | `— (LLM requis)` |
| `S16-032-test-isolation` | Spécialiste isolation des tests | Garantir l'indépendance des tests | `— (LLM requis)` |
| `S16-033-test-determinism` | Spécialiste déterminisme des tests | Garantir des tests déterministes | `— (LLM requis)` |
| `S16-034-test-reporting` | Spécialiste rapports de tests | Produire des rapports de tests fidèles | `— (LLM requis)` |
| `S16-035-quality-metrics` | Spécialiste métriques qualité | Définir des métriques qualité mesurables | `— (LLM requis)` |
| `S16-036-quality-gates` | Spécialiste portes qualité | Définir des portes qualité bloquantes | `— (LLM requis)` |
| `S16-037-defect-analysis` | Analyste de défauts | Analyser les défauts pour prévenir leur récidive | `— (LLM requis)` |
| `S16-038-root-cause-quality` | Analyste cause racine qualité | Trouver la cause racine des problèmes qualité | `— (LLM requis)` |
| `S16-039-acceptance-testing` | Spécialiste tests d'acceptation | Vérifier l'acceptation par rapport aux critères | `— (LLM requis)` |
| `S16-040-exploratory-testing` | Testeur exploratoire | Explorer le logiciel pour trouver des défauts | `— (LLM requis)` |
| `S16-041-risk-based-testing` | Spécialiste tests basés risque | Prioriser les tests par le risque | `— (LLM requis)` |
| `S16-042-test-maintenance` | Spécialiste maintenance des tests | Maintenir les tests dans la durée | `— (LLM requis)` |
| `S16-043-test-documentation` | Spécialiste documentation de tests | Documenter la stratégie et les tests | `— (LLM requis)` |
| `S16-044-quality-coaching` | Coach qualité | Diffuser les bonnes pratiques qualité | `— (LLM requis)` |
| `S16-045-release-quality` | Spécialiste qualité release | Vérifier la qualité avant release | `— (LLM requis)` |
| `S16-046-post-release-quality` | Spécialiste qualité post-release | Surveiller la qualité après release | `— (LLM requis)` |
| `S16-047-quality-audit` | Auditeur qualité | Réaliser un audit qualité objectif | `— (LLM requis)` |
| `S16-048-independent-evaluation` | Évaluateur indépendant | Évaluer le travail d'un autre agent sans conflit d'intérêt | `— (LLM requis)` |
| `S16-049-test-oracle` | Spécialiste oracles de test | Définir des oracles de test fiables | `— (LLM requis)` |
| `S16-050-quality-coordinator` | Coordinateur qualité | Coordonner les testeurs sur une campagne | `— (LLM requis)` |

## D17 — Performance et scalabilité
*Mesurer, optimiser et faire monter en charge les systèmes sur la base de données réelles.* · Chef : `M17-performance-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S17-001-latency-stats` | Analyste statistiques de latence | Calculer des percentiles de latence exacts à partir de mesures | `latency_stats` |
| `S17-002-resource-budget` | Vérificateur de budgets de ressources | Vérifier qu'une configuration respecte des budgets de ressources | `resource_budget_check` |
| `S17-003-profiling` | Profileur de systèmes | Profiler un système pour localiser les coûts | `— (LLM requis)` |
| `S17-004-cpu-optimization` | Optimiseur CPU | Réduire la consommation CPU mesurée | `— (LLM requis)` |
| `S17-005-memory-optimization` | Optimiseur mémoire | Réduire l'empreinte mémoire mesurée | `— (LLM requis)` |
| `S17-006-io-optimization` | Optimiseur entrées/sorties | Réduire les coûts d'E/S | `— (LLM requis)` |
| `S17-007-network-optimization` | Optimiseur réseau | Réduire latence et volume réseau | `— (LLM requis)` |
| `S17-008-database-performance` | Optimiseur performance base de données | Optimiser requêtes et index sur la base de mesures | `— (LLM requis)` |
| `S17-009-query-optimization` | Optimiseur de requêtes | Réécrire des requêtes pour la performance | `— (LLM requis)` |
| `S17-010-index-strategy` | Spécialiste stratégie d'index | Choisir les index adaptés aux requêtes réelles | `— (LLM requis)` |
| `S17-011-cache-strategy` | Stratège cache | Concevoir des caches efficaces avec invalidation sûre | `— (LLM requis)` |
| `S17-012-cache-invalidation` | Spécialiste invalidation de cache | Garantir la fraîcheur des données en cache | `— (LLM requis)` |
| `S17-013-cdn-strategy` | Spécialiste CDN | Utiliser un CDN à bon escient | `— (LLM requis)` |
| `S17-014-compression` | Spécialiste compression | Appliquer la compression adaptée aux contenus | `— (LLM requis)` |
| `S17-015-lazy-loading` | Spécialiste chargement paresseux | Différer le chargement non critique | `— (LLM requis)` |
| `S17-016-prefetching` | Spécialiste préchargement | Précharger ce qui sera utile sans gaspiller | `— (LLM requis)` |
| `S17-017-batching` | Spécialiste traitement par lots | Regrouper les opérations pour réduire les coûts | `— (LLM requis)` |
| `S17-018-pooling` | Spécialiste pools de ressources | Dimensionner les pools de connexions et workers | `— (LLM requis)` |
| `S17-019-concurrency-performance` | Spécialiste concurrence performance | Optimiser le degré de concurrence optimal | `— (LLM requis)` |
| `S17-020-parallelization` | Spécialiste parallélisation | Paralléliser les traitements indépendants | `— (LLM requis)` |
| `S17-021-async-performance` | Spécialiste performance asynchrone | Optimiser les pipelines asynchrones | `— (LLM requis)` |
| `S17-022-queue-performance` | Spécialiste performance des files | Optimiser le débit des files de messages | `— (LLM requis)` |
| `S17-023-backpressure` | Spécialiste contre-pression | Éviter la saturation par contre-pression | `— (LLM requis)` |
| `S17-024-rate-limit-performance` | Spécialiste limitation de débit performance | Équilibrer protection et débit | `— (LLM requis)` |
| `S17-025-load-balancing` | Spécialiste répartition de charge | Répartir la charge équitablement | `— (LLM requis)` |
| `S17-026-autoscaling` | Spécialiste autoscaling | Ajuster les ressources à la charge réelle | `— (LLM requis)` |
| `S17-027-horizontal-scaling` | Spécialiste montée en charge horizontale | Ajouter des instances sans état partagé problématique | `— (LLM requis)` |
| `S17-028-vertical-scaling` | Spécialiste montée en charge verticale | Évaluer la montée en charge verticale | `— (LLM requis)` |
| `S17-029-sharding` | Spécialiste partitionnement | Partitionner les données pour la charge | `— (LLM requis)` |
| `S17-030-replication` | Spécialiste réplication orientée performance | Concevoir la réplication pour lecture et résilience | `— (LLM requis)` |
| `S17-031-read-replicas` | Spécialiste réplicas de lecture | Utiliser des réplicas de lecture correctement | `— (LLM requis)` |
| `S17-032-connection-management` | Spécialiste gestion des connexions | Gérer les connexions efficacement | `— (LLM requis)` |
| `S17-033-gc-tuning` | Spécialiste réglage du garbage collector | Régler le GC sur la base de mesures | `— (LLM requis)` |
| `S17-034-jvm-performance` | Spécialiste performance JVM | Optimiser les applications JVM | `— (LLM requis)` |
| `S17-035-python-performance` | Spécialiste performance Python | Optimiser le code Python mesuré | `— (LLM requis)` |
| `S17-036-js-performance` | Spécialiste performance JavaScript | Optimiser le code JavaScript mesuré | `— (LLM requis)` |
| `S17-037-startup-performance` | Spécialiste performance de démarrage | Réduire les temps de démarrage | `— (LLM requis)` |
| `S17-038-cold-start` | Spécialiste démarrages à froid | Réduire les cold starts serverless | `— (LLM requis)` |
| `S17-039-tail-latency` | Spécialiste latence de queue | Réduire les latences extrêmes (p99) | `— (LLM requis)` |
| `S17-040-throughput-optimization` | Optimiseur de débit | Maximiser le débit soutenu | `— (LLM requis)` |
| `S17-041-capacity-planning` | Planificateur de capacité | Planifier la capacité pour la charge future | `— (LLM requis)` |
| `S17-042-performance-regression` | Détecteur de régression performance | Détecter les régressions de performance | `— (LLM requis)` |
| `S17-043-benchmark-design` | Concepteur de benchmarks | Concevoir des benchmarks reproductibles et honnêtes | `— (LLM requis)` |
| `S17-044-performance-budgets` | Spécialiste budgets de performance | Définir des budgets de performance contraignants | `— (LLM requis)` |
| `S17-045-cost-performance` | Spécialiste coût-performance | Optimiser le rapport coût-performance | `— (LLM requis)` |
| `S17-046-energy-efficiency` | Spécialiste efficacité énergétique | Réduire la consommation énergétique des traitements | `— (LLM requis)` |
| `S17-047-mobile-performance` | Spécialiste performance mobile | Optimiser la performance sur mobiles contraints | `— (LLM requis)` |
| `S17-048-web-performance-core` | Spécialiste Core Web Vitals | Optimiser les Core Web Vitals mesurés | `— (LLM requis)` |
| `S17-049-performance-monitoring` | Spécialiste surveillance performance | Surveiller la performance en continu | `— (LLM requis)` |
| `S17-050-performance-coordinator` | Coordinateur performance | Coordonner les optimiseurs sur un chantier | `— (LLM requis)` |

## D18 — Documentation et connaissances
*Documenter, indexer et transmettre les connaissances avec provenance et fraîcheur.* · Chef : `M18-documentation-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S18-001-doc-structure` | Vérificateur de structure documentaire | Vérifier la structure et la complétude d'un document Markdown | `doc_structure_check` |
| `S18-002-link-check` | Vérificateur de liens internes | Détecter les liens internes cassés dans la documentation | `link_check` |
| `S18-003-technical-writing` | Rédacteur technique | Rédiger une documentation technique claire et exacte | `— (LLM requis)` |
| `S18-004-readme-writing` | Rédacteur de README | Rédiger des README utiles et à jour | `— (LLM requis)` |
| `S18-005-api-doc-writing` | Rédacteur documentation API | Documenter les API avec exemples | `— (LLM requis)` |
| `S18-006-architecture-doc` | Documentaliste architecture applicative | Documenter l'architecture avec diagrammes et ADR | `— (LLM requis)` |
| `S18-007-runbook-writing` | Rédacteur de runbooks | Rédiger des runbooks opérationnels actionnables | `— (LLM requis)` |
| `S18-008-troubleshooting-guide` | Rédacteur guide de dépannage | Documenter les problèmes connus et solutions | `— (LLM requis)` |
| `S18-009-onboarding-doc` | Spécialiste documentation d'accueil | Faciliter l'arrivée de nouveaux contributeurs | `— (LLM requis)` |
| `S18-010-contributing-guide` | Rédacteur guide de contribution | Définir des règles de contribution claires | `— (LLM requis)` |
| `S18-011-changelog-writing` | Rédacteur de changelog | Maintenir un changelog fidèle | `— (LLM requis)` |
| `S18-012-release-notes` | Rédacteur notes de version | Rédiger des notes de version utiles | `— (LLM requis)` |
| `S18-013-knowledge-base` | Gestionnaire base de connaissances | Organiser une base de connaissances navigable | `— (LLM requis)` |
| `S18-014-wiki-management` | Gestionnaire de wiki | Maintenir un wiki à jour et structuré | `— (LLM requis)` |
| `S18-015-faq-writing` | Rédacteur FAQ | Rédiger des FAQ à partir de questions réelles | `— (LLM requis)` |
| `S18-016-glossary` | Spécialiste glossaire | Maintenir un glossaire cohérent | `— (LLM requis)` |
| `S18-017-style-guide` | Spécialiste guide de style | Définir un guide de style rédactionnel | `— (LLM requis)` |
| `S18-018-doc-templates` | Spécialiste gabarits documentaires | Créer des gabarits de documents réutilisables | `— (LLM requis)` |
| `S18-019-doc-review` | Relecteur documentaire | Relire la documentation pour exactitude et clarté | `— (LLM requis)` |
| `S18-020-doc-freshness` | Spécialiste fraîcheur documentaire | Détecter la documentation obsolète | `— (LLM requis)` |
| `S18-021-doc-coverage` | Spécialiste couverture documentaire | Identifier les zones non documentées | `— (LLM requis)` |
| `S18-022-doc-versioning` | Spécialiste versionnement documentaire | Versionner la documentation avec le code | `— (LLM requis)` |
| `S18-023-doc-automation` | Spécialiste génération documentaire | Générer la documentation à partir du code réel | `— (LLM requis)` |
| `S18-024-doc-testing` | Spécialiste tests de documentation | Tester les exemples et instructions de la documentation | `— (LLM requis)` |
| `S18-025-diagramming` | Spécialiste diagrammes | Créer des diagrammes clairs et exacts | `— (LLM requis)` |
| `S18-026-mermaid` | Spécialiste diagrammes Mermaid | Créer des diagrammes Mermaid valides | `— (LLM requis)` |
| `S18-027-knowledge-graph-doc` | Spécialiste graphe de connaissances | Structurer les connaissances en graphe | `— (LLM requis)` |
| `S18-028-semantic-indexing` | Spécialiste indexation sémantique | Indexer les connaissances pour la recherche sémantique | `— (LLM requis)` |
| `S18-029-search-optimization-doc` | Spécialiste recherche documentaire | Optimiser la recherche dans la documentation | `— (LLM requis)` |
| `S18-030-metadata-doc` | Spécialiste métadonnées documentaires | Définir des métadonnées utiles | `— (LLM requis)` |
| `S18-031-taxonomy` | Spécialiste taxonomie | Organiser une taxonomie de connaissances | `— (LLM requis)` |
| `S18-032-content-audit` | Auditeur de contenu | Réaliser un audit du contenu existant | `— (LLM requis)` |
| `S18-033-content-migration` | Spécialiste migration de contenu | Migrer du contenu sans perte | `— (LLM requis)` |
| `S18-034-localization-doc` | Spécialiste localisation documentaire | Localiser la documentation fidèlement | `— (LLM requis)` |
| `S18-035-accessibility-doc` | Spécialiste accessibilité documentaire | Rendre la documentation accessible | `— (LLM requis)` |
| `S18-036-doc-security` | Spécialiste confidentialité documentaire | Éviter les données sensibles dans la documentation | `— (LLM requis)` |
| `S18-037-provenance-tracking` | Spécialiste provenance | Tracer la source de chaque connaissance | `— (LLM requis)` |
| `S18-038-knowledge-curation` | Curateur de connaissances | Sélectionner et maintenir les connaissances utiles | `— (LLM requis)` |
| `S18-039-knowledge-retention` | Spécialiste rétention des connaissances | Définir les durées de conservation des connaissances | `— (LLM requis)` |
| `S18-040-lessons-doc` | Documentaliste retours d'expérience | Documenter les enseignements des missions | `— (LLM requis)` |
| `S18-041-decision-doc` | Documentaliste décisions | Documenter les décisions documentaires avec contexte et alternatives | `— (LLM requis)` |
| `S18-042-meeting-notes` | Spécialiste comptes rendus | Produire des comptes rendus fidèles et actionnables | `— (LLM requis)` |
| `S18-043-spec-writing` | Rédacteur de spécifications | Rédiger des spécifications précises et testables | `— (LLM requis)` |
| `S18-044-user-stories` | Rédacteur user stories | Rédiger des user stories claires avec critères | `— (LLM requis)` |
| `S18-045-tutorial-writing` | Rédacteur de tutoriels | Rédiger des tutoriels pas à pas vérifiés | `— (LLM requis)` |
| `S18-046-reference-doc` | Rédacteur documentation de référence | Rédiger une documentation de référence exhaustive | `— (LLM requis)` |
| `S18-047-conceptual-doc` | Rédacteur documentation conceptuelle | Expliquer les concepts clairement | `— (LLM requis)` |
| `S18-048-doc-metrics` | Spécialiste métriques documentaires | Mesurer la qualité et l'usage de la documentation | `— (LLM requis)` |
| `S18-049-doc-governance` | Spécialiste gouvernance documentaire | Définir la gouvernance de la documentation | `— (LLM requis)` |
| `S18-050-doc-coordinator` | Coordinateur documentation | Coordonner les rédacteurs sur un projet documentaire | `— (LLM requis)` |

## D19 — Infrastructure et monitoring
*Surveiller, fiabiliser et opérer les systèmes avec des métriques réelles et des alertes utiles.* · Chef : `M19-infrastructure-chief` · Risque : medium

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S19-001-health-report` | Validateur de rapports de santé | Vérifier la cohérence d'un rapport de santé de service | `health_report_check` |
| `S19-002-alert-rule` | Validateur de règles d'alerte | Vérifier la pertinence et la syntaxe des règles d'alerte | `alert_rule_check` |
| `S19-003-sre` | Ingénieur fiabilité de site | Améliorer la fiabilité mesurée des services | `— (LLM requis)` |
| `S19-004-slo-design` | Concepteur SLO | Définir des objectifs de niveau de service | `— (LLM requis)` |
| `S19-005-error-budget` | Spécialiste budget d'erreur | Gérer le budget d'erreur d'un service | `— (LLM requis)` |
| `S19-006-monitoring-design` | Concepteur monitoring | Concevoir un monitoring utile et complet | `— (LLM requis)` |
| `S19-007-metrics-design` | Concepteur de métriques | Définir des métriques exploitables | `— (LLM requis)` |
| `S19-008-logging-design` | Concepteur journalisation | Concevoir une journalisation structurée et corrélée | `— (LLM requis)` |
| `S19-009-tracing` | Spécialiste traçage distribué | Instrumenter le traçage distribué | `— (LLM requis)` |
| `S19-010-alerting-design` | Concepteur d'alertes | Concevoir des alertes actionnables et peu bruyantes | `— (LLM requis)` |
| `S19-011-on-call` | Spécialiste astreinte | Organiser l'astreinte et la réponse | `— (LLM requis)` |
| `S19-012-incident-management` | Gestionnaire d'incidents | Gérer les incidents de bout en bout | `— (LLM requis)` |
| `S19-013-incident-review` | Analyste post-incident | Réaliser des post-mortems sans blâme | `— (LLM requis)` |
| `S19-014-chaos-engineering` | Spécialiste ingénierie du chaos | Tester la résilience par injection de pannes contrôlée en périmètre autorisé | `— (LLM requis)` |
| `S19-015-disaster-recovery` | Spécialiste reprise après sinistre | Préparer la reprise après sinistre | `— (LLM requis)` |
| `S19-016-backup-ops` | Spécialiste exploitation des sauvegardes | Exploiter et vérifier les sauvegardes | `— (LLM requis)` |
| `S19-017-capacity-ops` | Spécialiste capacité opérationnelle | Surveiller et anticiper la capacité | `— (LLM requis)` |
| `S19-018-availability` | Spécialiste disponibilité | Maximiser la disponibilité mesurée | `— (LLM requis)` |
| `S19-019-latency-monitoring` | Spécialiste surveillance de latence | Surveiller la latence des services | `— (LLM requis)` |
| `S19-020-error-rate-monitoring` | Spécialiste surveillance du taux d'erreur | Surveiller les taux d'erreur | `— (LLM requis)` |
| `S19-021-saturation-monitoring` | Spécialiste surveillance de saturation | Surveiller la saturation des ressources | `— (LLM requis)` |
| `S19-022-traffic-monitoring` | Spécialiste surveillance du trafic | Surveiller les patterns de trafic | `— (LLM requis)` |
| `S19-023-uptime-monitoring` | Spécialiste surveillance de disponibilité | Surveiller la disponibilité externe | `— (LLM requis)` |
| `S19-024-synthetic-monitoring` | Spécialiste monitoring synthétique | Créer des checks synthétiques représentatifs | `— (LLM requis)` |
| `S19-025-real-user-monitoring` | Spécialiste monitoring utilisateur réel | Analyser l'expérience utilisateur réelle | `— (LLM requis)` |
| `S19-026-log-aggregation` | Spécialiste agrégation de journaux | Agréger et indexer les journaux | `— (LLM requis)` |
| `S19-027-log-retention` | Spécialiste rétention des journaux | Définir la rétention des journaux | `— (LLM requis)` |
| `S19-028-log-security` | Spécialiste sécurité des journaux | Protéger les journaux contre les fuites | `— (LLM requis)` |
| `S19-029-cloud-infra` | Spécialiste infrastructure cloud | Concevoir une infrastructure cloud adaptée | `— (LLM requis)` |
| `S19-030-aws-infra` | Spécialiste infrastructure AWS | Concevoir une infrastructure AWS | `— (LLM requis)` |
| `S19-031-azure-infra` | Spécialiste infrastructure Azure | Concevoir une infrastructure Azure | `— (LLM requis)` |
| `S19-032-gcp-infra` | Spécialiste infrastructure GCP | Concevoir une infrastructure GCP | `— (LLM requis)` |
| `S19-033-kubernetes-ops` | Spécialiste exploitation Kubernetes | Opérer des clusters Kubernetes | `— (LLM requis)` |
| `S19-034-docker-ops` | Spécialiste exploitation Docker | Opérer des conteneurs Docker | `— (LLM requis)` |
| `S19-035-serverless-ops` | Spécialiste exploitation serverless | Opérer des fonctions serverless | `— (LLM requis)` |
| `S19-036-network-ops` | Spécialiste exploitation réseau | Opérer et surveiller le réseau | `— (LLM requis)` |
| `S19-037-dns-ops` | Spécialiste exploitation DNS | Gérer et surveiller le DNS | `— (LLM requis)` |
| `S19-038-tls-ops` | Spécialiste exploitation TLS | Gérer les certificats et TLS | `— (LLM requis)` |
| `S19-039-load-balancer-ops` | Spécialiste exploitation des répartiteurs | Opérer les répartiteurs de charge | `— (LLM requis)` |
| `S19-040-cdn-ops` | Spécialiste exploitation CDN | Opérer et surveiller un CDN | `— (LLM requis)` |
| `S19-041-database-ops` | Spécialiste exploitation bases de données | Opérer et surveiller les bases de données | `— (LLM requis)` |
| `S19-042-storage-ops` | Spécialiste exploitation du stockage | Gérer le stockage et sa croissance | `— (LLM requis)` |
| `S19-043-queue-ops` | Spécialiste exploitation des files | Opérer et surveiller les files de messages | `— (LLM requis)` |
| `S19-044-ci-runners` | Spécialiste runners CI | Gérer les runners CI | `— (LLM requis)` |
| `S19-045-infra-as-code` | Spécialiste infrastructure as code | Gérer l'infrastructure par le code | `— (LLM requis)` |
| `S19-046-config-management` | Spécialiste gestion de configuration | Gérer les configurations d'infrastructure | `— (LLM requis)` |
| `S19-047-patch-ops` | Spécialiste application des correctifs | Appliquer les correctifs d'infrastructure | `— (LLM requis)` |
| `S19-048-cost-ops` | Spécialiste coûts d'infrastructure | Surveiller et optimiser les coûts d'infrastructure | `— (LLM requis)` |
| `S19-049-finops` | Spécialiste FinOps | Aligner dépenses cloud et valeur | `— (LLM requis)` |
| `S19-050-infra-coordinator` | Coordinateur infrastructure | Coordonner les spécialistes infrastructure | `— (LLM requis)` |

## D20 — Innovation et expérimentation
*Explorer, prototyper et expérimenter de façon contrôlée, mesurée et réversible.* · Chef : `M20-innovation-chief` · Risque : low

| ID | Nom | Objectif | Outil représentatif |
| --- | --- | --- | --- |
| `S20-001-experiment-design` | Concepteur protocoles d'expérience | Vérifier qu'un protocole d'expérience est complet et contrôlé | `experiment_design_check` |
| `S20-002-hypothesis-matrix` | Vérificateur matrices d'hypothèses | Vérifier la cohérence d'une matrice hypothèses/tests | `hypothesis_matrix_check` |
| `S20-003-prototyping` | Prototypeur rapide | Prototyper une idée pour la tester rapidement | `— (LLM requis)` |
| `S20-004-poc-design` | Concepteur de preuves de concept | Concevoir des POC avec critères de succès | `— (LLM requis)` |
| `S20-005-tech-scouting` | Éclaireur technologique | Identifier les technologies émergentes pertinentes | `— (LLM requis)` |
| `S20-006-tool-comparison` | Comparateur d'outils | Comparer des outils sur critères objectifs | `— (LLM requis)` |
| `S20-007-framework-evaluation` | Évaluateur de frameworks | Évaluer un framework pour un usage donné | `— (LLM requis)` |
| `S20-008-library-evaluation` | Évaluateur de bibliothèques | Évaluer une bibliothèque avant adoption | `— (LLM requis)` |
| `S20-009-innovation-portfolio` | Gestionnaire portefeuille d'innovation | Équilibrer le portefeuille d'expérimentations | `— (LLM requis)` |
| `S20-010-experiment-prioritization` | Priorisateur d'expériences | Prioriser les expériences par valeur d'apprentissage | `— (LLM requis)` |
| `S20-011-mvp-design` | Concepteur MVP | Concevoir des MVP minimaux mais utiles | `— (LLM requis)` |
| `S20-012-pilot-design` | Concepteur de pilotes | Concevoir des pilotes contrôlés | `— (LLM requis)` |
| `S20-013-ab-experiment` | Spécialiste expériences A/B | Concevoir des expériences A/B rigoureuses | `— (LLM requis)` |
| `S20-014-multivariate-testing` | Spécialiste tests multivariés | Concevoir des tests multivariés interprétables | `— (LLM requis)` |
| `S20-015-experiment-analysis` | Analyste résultats d'expérience | Analyser des résultats d'expérience avec rigueur | `— (LLM requis)` |
| `S20-016-learning-extraction` | Extracteur d'enseignements | Extraire les enseignements actionnables des expériences | `— (LLM requis)` |
| `S20-017-failure-analysis` | Analyste d'échecs d'expérience | Analyser les échecs pour en tirer des leçons | `— (LLM requis)` |
| `S20-018-success-criteria` | Spécialiste critères de succès | Définir des critères de succès avant expérience | `— (LLM requis)` |
| `S20-019-reversibility` | Spécialiste réversibilité | Garantir la réversibilité des expérimentations | `— (LLM requis)` |
| `S20-020-sandbox-experimentation` | Spécialiste expérimentation isolée | Expérimenter en environnement isolé | `— (LLM requis)` |
| `S20-021-innovation-metrics` | Spécialiste métriques d'innovation | Mesurer la valeur des expérimentations | `— (LLM requis)` |
| `S20-022-tech-radar` | Spécialiste radar technologique | Maintenir un radar technologique à jour | `— (LLM requis)` |
| `S20-023-adoption-strategy` | Stratège d'adoption | Planifier l'adoption progressive d'une technologie | `— (LLM requis)` |
| `S20-024-deprecation-strategy` | Stratège de retrait | Planifier le retrait d'une technologie | `— (LLM requis)` |
| `S20-025-build-vs-buy` | Analyste build vs buy | Arbitrer entre construire et acheter | `— (LLM requis)` |
| `S20-026-open-source-evaluation` | Évaluateur open source | Évaluer la santé des projets open source | `— (LLM requis)` |
| `S20-027-license-evaluation` | Évaluateur de licences | Évaluer les implications des licences | `— (LLM requis)` |
| `S20-028-emerging-tech-analysis` | Analyste technologies émergentes | Analyser la maturité des technologies émergentes | `— (LLM requis)` |
| `S20-029-ai-experimentation` | Spécialiste expérimentation IA | Expérimenter l'IA de façon contrôlée et mesurée | `— (LLM requis)` |
| `S20-030-agent-experimentation` | Spécialiste expérimentation agents | Expérimenter de nouveaux designs d'agents | `— (LLM requis)` |
| `S20-031-prompt-experimentation` | Spécialiste expérimentation de prompts | Comparer des variantes de prompts rigoureusement | `— (LLM requis)` |
| `S20-032-model-experimentation` | Spécialiste expérimentation de modèles | Comparer des modèles sur des tâches réelles | `— (LLM requis)` |
| `S20-033-workflow-experimentation` | Spécialiste expérimentation de workflows | Comparer des workflows alternatifs | `— (LLM requis)` |
| `S20-034-ux-experimentation` | Spécialiste expérimentation UX | Expérimenter des variantes d'interface | `— (LLM requis)` |
| `S20-035-pricing-experimentation` | Spécialiste expérimentation tarifaire | Expérimenter des hypothèses tarifaires sans engagement | `— (LLM requis)` |
| `S20-036-growth-experimentation` | Spécialiste expérimentation croissance | Concevoir des expériences de croissance éthiques | `— (LLM requis)` |
| `S20-037-automation-experimentation` | Spécialiste expérimentation automatisation | Expérimenter de nouvelles automatisations | `— (LLM requis)` |
| `S20-038-integration-experimentation` | Spécialiste expérimentation intégrations | Expérimenter de nouvelles intégrations | `— (LLM requis)` |
| `S20-039-performance-experimentation` | Spécialiste expérimentation performance | Expérimenter des optimisations de performance | `— (LLM requis)` |
| `S20-040-security-experimentation` | Spécialiste expérimentation sécurité défensive | Expérimenter des défenses en périmètre autorisé | `— (LLM requis)` |
| `S20-041-documentation-experimentation` | Spécialiste expérimentation documentaire | Expérimenter des formats de documentation | `— (LLM requis)` |
| `S20-042-knowledge-experimentation` | Spécialiste expérimentation connaissances | Expérimenter des structures de connaissances | `— (LLM requis)` |
| `S20-043-memory-experimentation` | Spécialiste expérimentation mémoire | Expérimenter des stratégies de mémoire agents | `— (LLM requis)` |
| `S20-044-routing-experimentation` | Spécialiste expérimentation routage | Expérimenter des stratégies de routage | `— (LLM requis)` |
| `S20-045-council-experimentation` | Spécialiste expérimentation conseil | Expérimenter des protocoles de conseil multi-modèles | `— (LLM requis)` |
| `S20-046-evaluation-experimentation` | Spécialiste expérimentation évaluation | Expérimenter des méthodes d'évaluation | `— (LLM requis)` |
| `S20-047-learning-experimentation` | Spécialiste expérimentation apprentissage | Expérimenter des stratégies d'apprentissage continu | `— (LLM requis)` |
| `S20-048-innovation-scouting` | Éclaireur d'opportunités | Identifier des opportunités d'innovation utiles | `— (LLM requis)` |
| `S20-049-innovation-facilitation` | Facilitateur innovation | Faciliter la génération et sélection d'idées | `— (LLM requis)` |
| `S20-050-innovation-coordinator` | Coordinateur innovation | Coordonner les expérimentateurs sur un programme | `— (LLM requis)` |
