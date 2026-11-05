# Carte du réseau de dépôts blassana280-ux

> Règle réseau d'OmniBrain : *compétence manquante → chercher d'abord dans
> les collections du compte avant de réinventer.* Cette carte transforme les
> 40 forks du compte en un index actionnable. Dérivée de l'inventaire GitHub
> du 2026-10-27 (41 dépôts : 40 forks + 1 original `omni-agents-framework`).

## 1. Socle et formatage

| Dépôt | Rôle | Quand consulter |
|---|---|---|
| `agentskills` (ce dépôt) | Spécification Agent Skills + librairie de référence `skills-ref` (parseur/validateur de `SKILL.md`) | Vérifier la conformité d'un skill, comprendre la divulgation progressive |
| `omni-agents-framework` | Maison canonique d'OmniBrain (moteur + 12 agents + gates) | Toute demande passe par lui d'abord |
| `skills` / `skills-` | Collections publiques de skills et MCP | Patterns officiels, grounding de SDK |

## 2. Collections de skills (recherche de compétences)

| Dépôt | Spécialité |
|---|---|
| `agent-skills-index` | Index catégorisé et dédupliqué de 115 repos — **point d'entrée de toute recherche** |
| `awesome-agent-skills` | 1000+ skills, multi-clients (Claude Code, Codex, Gemini CLI, Cursor) |
| `ai-agent-skills-collection` | 2611 skills, prompts système et personas |
| `antigravity-skills` | 500+ skills haute performance, dont skills officiels Anthropic/Vercel |
| `agent-skills` / `agent-skills-3` | Collections cross-platform ; `agent-skills-3` = 90 agents + hub-spoke Nexus, 49 recettes |
| `awesome-claude-code-toolkit` | 135 agents, 35 skills, 42 commandes, hooks, plugins, templates MCP |
| `skills-collection` | Skills pour Claude Code, Copilot et autres harness |
| `designer-skills` | Recherche, design system, UI, interaction, delivery design |
| `awesome-gamedev-agent-skills` | Godot, Unity, Unreal, Phaser, Bevy, pygame, Roblox (74 skills, router inclus) |
| `cc-skills-golang` | Skills agentiques Go |
| `ResumeSkills` | CV, ATS, candidatures, entretien, carrière |

## 3. Orchestration multi-agents (voisins d'OmniBrain)

| Dépôt | Apport |
|---|---|
| `agency-agents` | Agence complète d'agents spécialisés (source du format de fiche frontmatter et des protocoles universels) |
| `xquads-squads` | 12 escouades / 96+ agents en `squad.yaml` — patron d'escouade et de niveaux (tier 0-2) |
| `Open-Agents` | Orchestrateur multi-agents parallèles pour Claude Code |

## 4. Ingénierie de contexte, mémoire et performance

| Dépôt | Apport |
|---|---|
| `Context-Engineering` | Handbook de design/orchestration/optimisation de contexte |
| `Awesome-Context-Engineering` | Survey académique : papiers, frameworks, guides d'implémentation |
| `how-claude-code-works` | Architecture interne, agent loop, système d'outils |
| `mem0` / `cognee` / `hindsight` | Couches de mémoire persistante pour agents |
| `LLMLingua` | Compression de prompts/KV-cache (jusqu'à 20x) |
| `LMCache` | Cache KV pour accélérer les inférences |
| `GPTCache` | Cache sémantique pour LLM (intégrations LangChain/llama_index) |

## 5. Accès aux modèles et routage LLM

| Dépôt | Apport |
|---|---|
| `OmniRoute` | Gateway MIT : 339 providers, 1200+ modèles, fallback quota-aware, compression RTK/Caveman |
| `9router` | Routes gratuites Claude/GPT/Gemini via 40+ providers, auto-fallback |
| `kilocode` | Plateforme agentique open source |

## 6. RAG, applications et formation

| Dépôt | Apport |
|---|---|
| `awesome-llm-apps` | 100+ agents, skills et apps RAG open source |
| `ai-engineering-hub` | Tutoriels LLM, RAG, applications agents réelles |
| `builder` | Générateur open source de sites/apps (alternative Lovable/Replit) |
| `video-use` | Montage vidéo piloté par agents |
| `Prompt-Engineering-Guide` | Guides, papiers et leçons de prompt/context engineering |
| `Qwen3.8` / `minimind` | Séries de modèles ; entraînement d'un LLM 64M from scratch |

## 7. Hors périmètre agent

`Red-DiscordBot` (bot Discord), `vpn-decryptor` (outils d'inspection Android VPN/proxy).

## Procédure de réutilisation

1. Identifier la compétence manquante dans un brief d'escouade.
2. Chercher d'abord dans `agent-skills-index`, puis la collection spécialisée ci-dessus.
3. Porter le skill dans `skills/` et l'enregistrer dans `matrix.toml` (`[[agents]]` ou mots-clés).
4. `python3 -m omnibrain validate` doit rester vert ; ajouter un test si le routage change.
