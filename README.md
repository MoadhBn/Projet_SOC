# Projet_SOC

SOC de nouvelle génération basé sur l'intelligence artificielle pour la détection et la gestion des incidents de sécurité.

Projet académique, Tek-Up University, 2026-2027.
Équipe : Mohamed Nadhir Abidi, Mohamed Amine Rhimi, Moadh Ben Naceur. Encadrant : M. Tarek Hdiji.

A lab SOC on two laptops where the whole chain is automatic: collection, detection, enrichment, scoring, response, AI explanation and incident creation. Everything is open source and the AI runs locally.

The full design is in [docs/SOC_IA_PROJECT_BRIEF.md](docs/SOC_IA_PROJECT_BRIEF.md).

## Layout

| Folder | Content |
|---|---|
| `docs/` | Project brief, report sources, diagrams |
| `infra/laptop1-soc/` | Docker Compose files for Wazuh, Shuffle, MISP, DFIR-IRIS |
| `infra/laptop2-lab/` | Network plan, VMware and OPNsense settings, VM notes |
| `wazuh/` | Custom rules, agent configuration, Sysmon configuration |
| `suricata/` | Rule selection and local rules |
| `shuffle/` | Exported playbooks |
| `ai-engine/` | FastAPI service: scoring, anomaly detection, LLM and RAG |
| `tests/` | Attack scripts for T-01 to T-06 and measurement notes |

## Build progress

| Phase | Content | Status |
|---|---|---|
| 0 | VMs, three network zones, OPNsense, cable link | Laptop 2 done; cable link (step 0.7) pending |
| 1 | Detection base (Wazuh, agents, Sysmon, Suricata) | Not started |
| 2 | Enrichment and orchestration (MISP, Shuffle, DFIR-IRIS) | Not started |
| 3 | AI engine | Not started |
| 4 | Response and supervision | Not started |
| 5 | Validation and report | Not started |

## Secrets

API keys, passwords and raw firewall backups are never committed. See `.gitignore`.
