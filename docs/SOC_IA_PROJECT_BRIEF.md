# AI-based next-generation SOC: project brief

This file is the single source of truth for building the project. It records what has been decided, what is only estimated, and what still has to be verified. Read it fully before doing anything.

Status as of 13 October 2026: the design phase is finished (cahier des charges and first report chapter written). Nothing is installed yet. The next step is the build.

## 1. Context

| Item | Value |
|---|---|
| Project title | Conception et développement d'un SOC de nouvelle génération basé sur l'intelligence artificielle pour la détection et la gestion des incidents de sécurité |
| School | Tek-Up University, academic year 2026-2027 |
| Subjects | Art de protection du secret (design, 21 h) and Cyber Ops (build and end-to-end tests) |
| Team | Mohamed Nadhir Abidi, Mohamed Amine Rhimi, Moadh Ben Naceur |
| Supervisor | M. Tarek Hdiji |
| Report language | French (LaTeX, compiled on Overleaf) |

Milestones:

1. Architecture validation, based on the cahier des charges (done or imminent).
2. Séance 4: first progress evaluation. Target: the detection base works (Wazuh, agents, Suricata, first use cases).
3. Report handed in at least 3 days before séance 7.
4. Séance 7: defence and final validation, with a live demo.

## 2. The idea in one paragraph

A SOC drowns in alerts and reacts slowly because humans triage everything. This project builds a small lab SOC where the whole chain is automatic: logs are collected, attacks are detected, alerts are enriched and scored, a response is executed, a local AI explains the alert, and an incident file is opened. The analyst does not approve actions beforehand; they are notified, can undo any action, and focus on investigation. Everything is open source and the AI runs locally.

## 3. Decisions already made (do not reopen without a reason)

- **Full automation with guardrails.** No human approval before an action. Safety comes from the guardrails in section 8.
- **A fixed formula decides, not the LLM.** The priority score is computed deterministically. The LLM only summarises, labels and justifies. Its label can raise the score, never lower it.
- **The response does not wait for the LLM.** If the base score is already high, the response fires immediately.
- **The response depends on the attack type** (section 7).
- **The anomaly model works on raw activity**, not only on alerts that rules already raised, so it can catch what rules miss.
- **Repeated alerts are grouped** before processing.
- **Two laptops**, linked by an Ethernet cable (section 5).
- **A firewall VM (OPNsense) sits between the zones** and hosts Suricata.
- **A 3B language model**, running on the laptop's graphics card.
- **All tools from the cahier des charges are kept**: Wazuh, Suricata, Sysmon, Shuffle, DFIR-IRIS, MISP, Ollama, ChromaDB, scikit-learn, FastAPI, Docker.
- **Keep it simple.** The team explicitly wants the simplest design that is fully automated.

## 4. Tools and their roles

| Tool | Role |
|---|---|
| Wazuh (Manager, Indexer, Dashboard) | SIEM/XDR: collects logs through agents, applies rules, raises alerts, stores and displays them, can run an active response on a machine |
| Sysmon | Detailed Windows telemetry (processes, command lines, network connections) |
| Suricata | Network intrusion detection, running on the firewall |
| OPNsense | Firewall between the zones; applies the automatic blocks through its API |
| Shuffle | SOAR orchestrator: runs the playbook for every alert |
| MISP | Threat intelligence: known malicious IPs, domains, hashes |
| DFIR-IRIS | Incident case management |
| Analysis API (FastAPI, built by the team) | Single entry point of the AI engine: anomaly detection, score, call to the LLM |
| Isolation Forest (scikit-learn) | Unsupervised anomaly detection on machine activity |
| Ollama | Runs the local language model |
| ChromaDB | Knowledge base for RAG (MITRE ATT&CK, response procedures) |
| Docker and Docker Compose | Deployment of the SOC tools |
| VMware Workstation | Hosts the virtual machines |
| Kali Linux | Attack machine for the simulated attacks |

Not decided yet:

- The vulnerable web application on the Linux target (DVWA or OWASP Juice Shop are the usual candidates).
- The notification channel (Telegram, Discord or email). The report keeps it generic ("canal de messagerie").

## 5. Hardware and deployment

Two identical laptops: 16 GB RAM, NVIDIA RTX 2050 with 4 GB of video memory, Windows 11, VMware Workstation. About 12 GB is usable per laptop once Windows runs.

All RAM figures below are estimates, not measurements. Confirm them during deployment.

### Laptop 1: the SOC

One Ubuntu Server VM ("soc", 11 GB, 4 vCPU) running everything in Docker.

| Tool | Estimated RAM | Note |
|---|---|---|
| Wazuh single node | 3.5 GB | limit the indexer heap to 1 GB |
| Shuffle | 2.5 GB | limit its OpenSearch heap to about 1 GB |
| MISP | 3 GB | enable few feeds |
| DFIR-IRIS | 1.5 GB | |

Laptop 1 is at its limit. Add 4 GB of swap in the VM and keep nothing else open on the host. Wazuh, MISP and DFIR-IRIS all default to web port 443, so each needs its own port.

### Laptop 2: the lab and the AI

| Item | Estimated RAM | Zone |
|---|---|---|
| VM OPNsense with Suricata | 2 GB | all three zones |
| VM Windows 10 target (Wazuh agent, Sysmon) | 3 GB | targets |
| VM Ubuntu Server target (Wazuh agent, vulnerable web app) | 1 GB | targets |
| VM Kali, no desktop | 1.5 GB | attack |
| Host: Ollama (model on the graphics card), analysis API, ChromaDB embedded | about 1 GB | SOC link |

The AI runs directly on the Windows host because VMware Workstation cannot give the graphics card to a VM.

### Network plan (proposed, can be changed)

| Zone | Network | Machines |
|---|---|---|
| SOC link (the Ethernet cable) | 10.10.10.0/24 | soc VM 10.10.10.10, laptop 2 host (AI API) 10.10.10.20, OPNsense 10.10.10.254, laptop 1 host 10.10.10.1 |
| Targets | 10.10.20.0/24 | Windows 10.10.20.10, Linux 10.10.20.20, OPNsense 10.10.20.1 |
| Attack | 10.10.30.0/24 | Kali 10.10.30.10, OPNsense 10.10.30.1 |

Setup notes:

- One Ethernet cable directly between the laptops, or a small switch. USB-Ethernet adapters if a laptop has no port. Wi-Fi stays on for internet during installation only.
- On both laptops, bind VMware's bridged network (VMnet0) explicitly to the Ethernet adapter, otherwise it may bridge to Wi-Fi.
- The soc VM has one bridged adapter (10.10.10.10) and one NAT adapter for downloads.
- OPNsense has four adapters: bridged (SOC side), two private VMware networks (targets, attack), and NAT for updates.
- The soc VM needs a static route to 10.10.20.0/24 through 10.10.10.254, otherwise Wazuh cannot answer the agents.
- The Windows firewall on laptop 2 must allow the soc VM to reach the analysis API port.

### Firewall rules

- Attack zone to targets zone: allowed (this is the attack path).
- Attack zone to SOC: blocked, always.
- Targets zone to SOC: only the Wazuh agent ports (1514 and 1515 by default) towards 10.10.10.10.
- soc VM to the OPNsense API: allowed.
- A rule at the top blocks every address in a list (alias) that Shuffle fills and empties.
- Targets and attack zones have no internet access.

Suricata runs on OPNsense in detection mode on the targets and attack interfaces, with the free Emerging Threats rules.

## 6. The pipeline: seven steps

1. **Collect.** Agents and the network sensor send logs to Wazuh.
2. **Detect.** Wazuh rules raise alerts. In parallel, the anomaly model watches machine activity and raises an anomaly alert when it becomes very unusual, even if no rule fired.
3. **Group and enrich.** Shuffle groups repeated alerts (same rule, same origin) into one case, then looks up the indicators in MISP.
4. **Score and decide.** A fixed formula computes the score; two thresholds split it into low, medium, high.
5. **Respond.** If the score is high, the response fires immediately.
6. **Explain.** The LLM writes a summary and a justification and gives a label.
7. **Incident and notification.** A case is created in DFIR-IRIS and the analyst is notified.

### The nine numbered exchanges (as drawn in the architecture image)

| No. | From | To | Means | Data |
|---|---|---|---|---|
| 1 | Kali | Targets | Network traffic | Simulated attacks |
| 2 | Wazuh agents | Wazuh Manager | Agents' encrypted channel | Sysmon and Windows events, auth.log, web server logs |
| 3 | Suricata | Wazuh Manager | Agent on the firewall, or log forwarding | Network alerts (eve.json) |
| 4 | Wazuh Manager | Shuffle | HTTPS webhook | Alerts in JSON |
| 5 | Shuffle | MISP | REST API | Indicator lookup |
| 6 | Shuffle | Analysis API | REST API | Enriched alert out; score and explanation back |
| 7 | Shuffle | DFIR-IRIS | REST API | Case creation and updates |
| 8 | Shuffle | Messaging channel | HTTPS | Notification with a cancel link |
| 9 | Shuffle | OPNsense | REST API | Temporary block of an address |

Not drawn: Shuffle to the Wazuh API (active response on a machine), analysis API to the Wazuh Indexer (reading events), analysis API to Ollama (local HTTP).

## 7. Score, decision and response

### Score components (starting weights, to be tuned during tests)

| Component | Source | Maximum weight |
|---|---|---|
| Severity level of the rule that fired | Wazuh | 50 |
| Match with a known indicator | MISP | 25 |
| Anomaly score of the machine concerned | Isolation Forest | 15 |
| Label given by the language model | Ollama | 10 |

How it runs:

- The first three components give a base score within moments.
- If the base score already passes the high threshold, the response fires without waiting for the LLM.
- The LLM then labels the alert as malicious, suspicious or benign. "Malicious" adds points and can push the alert to the next level. "Benign" removes nothing.
- The two thresholds are not fixed yet. Calibrate them on the test scenarios so that, for example, an SSH brute force ends up high and a harmless unusual activity ends up low.

### Decision

- **Low:** archived as a probable false positive; the explanation is kept.
- **Medium:** normal-priority incident, analyst notified, no action.
- **High:** automatic response, priority incident, immediate notification.

### Response by attack type

| Attack type | Examples | Automatic response |
|---|---|---|
| Network attack from another zone | Brute force, port scan, web exploitation | Temporary block of the attacker's address on the firewall |
| Connection to a malicious address | A machine contacts a known bad domain | Temporary block of the destination address on the firewall |
| Attack on the machine itself | Suspicious PowerShell, persistence, privilege escalation, modified files | Wazuh active response on the machine, for example temporarily disabling the account used |

It is always the address outside the protected zone that gets blocked. A monitored machine is never blocked just because it appears as the source of an alert.

### What the LLM does and does not do

- It receives a trimmed alert (useful fields only) plus RAG passages.
- It returns a fixed JSON structure: summary, label, justification.
- It does not compute the score, does not choose the ATT&CK technique (that comes from the Wazuh rule that fired), and cannot trigger any action.
- Candidate models: Llama 3.2 3B or Qwen2.5 3B. Fallback if quality is poor: a 4B-class model (Phi-3.5 mini or Gemma 3 4B). Choose after testing two or three models on the same 20 to 30 lab alerts, comparing explanation quality and response time. Check French output quality early.

### What the anomaly model does

- At regular intervals, the analysis API reads recent events from the Wazuh Indexer and builds features per machine: number of connections, hours of activity, processes launched, network volume.
- Isolation Forest is trained on a period of normal lab activity, which the team has to generate and record first.
- A strong deviation creates an anomaly alert that enters the same pipeline.
- For rule-based alerts, the same model provides the anomaly score of the machine concerned.

## 8. Guardrails

- **Reversible and time-limited actions.** A block is temporary; Shuffle schedules its removal after a configurable duration.
- **Protected list.** SOC machines and essential equipment can never be blocked automatically.
- **AI separated from action.** See above.
- **Traceability and cancel.** Every decision is recorded in the incident file. The notification contains a cancel link that calls Shuffle, which removes the block.
- **Logs are untrusted input.** They contain attacker-written text. Manipulating the LLM must not be able to prevent a block.
- **Notifications carry only a short summary**, never raw logs.

## 9. Requirements

### Functional

| Ref. | Requirement | Priority |
|---|---|---|
| BF-01 | Collect and centralise logs from workstations, servers, applications and the network | Must |
| BF-02 | Detect threats with rules mapped to MITRE ATT&CK | Must |
| BF-03 | Detect abnormal behaviour with a machine learning model, even when no rule fires | Must |
| BF-04 | Group repeated alerts before processing | Must |
| BF-05 | Enrich alerts automatically with indicators of compromise | Must |
| BF-06 | Compute a priority score with a fixed formula | Must |
| BF-07 | Explain each alert with AI: summary, label, justification | Must |
| BF-08 | Decide automatically how to handle the alert from its score | Must |
| BF-09 | Launch a temporary automatic response adapted to the attack type | Must |
| BF-10 | Create an incident file automatically for retained alerts | Must |
| BF-11 | Notify the analyst in real time of each incident and action | Must |
| BF-12 | Let the analyst cancel an automatic action through a link | Must |
| BF-13 | Dashboards and indicators (MTTD, MTTR, volume, false positives) | Should |
| BF-14 | Keep a trace of each decision: inputs, score, label, model version | Should |
| BF-15 | Generate an incident report automatically | Could |

### Non-functional

| Ref. | Category | Requirement |
|---|---|---|
| BNF-01 | Speed | Response to a high-score alert targets under one minute after detection, without waiting for the LLM |
| BNF-02 | Security | TLS, authentication, distinct roles, protected secrets, one API key per integration with minimal rights |
| BNF-03 | Confidentiality | The AI runs locally; logs and alerts are sent to no external AI service |
| BNF-04 | Safety | Automatic actions are reversible, time-limited and never touch protected addresses |
| BNF-05 | Explainability | Every decision can be justified: score detail and readable explanation |
| BNF-06 | Reliability | Services restart automatically; configuration and rules are backed up |
| BNF-07 | Extensibility | A log source or a playbook can be added without redesign |
| BNF-08 | Reproducibility | Deployment described by versioned configuration files |
| BNF-09 | Cost | Open source components only |
| BNF-10 | Resources | The whole solution runs on two 16 GB laptops |

### Detection use cases

| Ref. | Scenario | ATT&CK |
|---|---|---|
| UC-01 | Brute force on SSH or RDP | T1110 |
| UC-02 | Suspicious or encoded PowerShell commands | T1059.001 |
| UC-03 | Exploitation of the web application (SQL injection, XSS) | T1190 |
| UC-04 | Port scan and network reconnaissance | T1046 |
| UC-05 | Persistence (scheduled task, service) | T1053, T1543 |
| UC-06 | Privilege escalation on Linux | T1548 |
| UC-07 | Modification of critical files | T1565 |
| UC-08 | Connection to a known malicious address or domain | T1071 |

## 10. Validation

### Test scenarios

| Ref. | Attack | Expected detection | Expected handling |
|---|---|---|---|
| T-01 | SSH brute force from Kali | Wazuh alert correlating repeated failures | High score, attacker IP blocked on the firewall, incident and notification |
| T-02 | SQL injection on the web app | Suricata alert or web rule | Incident with a justified explanation; block if the score is high |
| T-03 | Port scan | Network alert | Grouped into one case; incident or archive depending on the score |
| T-04 | Encoded PowerShell on the Windows target | Sysmon-based rule, mapped to T1059.001 | Incident, notification, host-level response if high |
| T-05 | Connection to an indicator present in MISP | Alert matched with threat intelligence | High score, destination blocked, immediate notification |
| T-06 | Harmless but unusual activity | Low-severity alert | Archived with its explanation (false positive handled) |

Also test: the cancel link removes a block, a block expires by itself, a protected address is never blocked, and a prompt-injection attempt in a log field does not prevent a block.

### Indicators to measure

- MTTD: average time from attack to alert.
- MTTR: average time from alert to response or closure.
- Coverage: share of UC-01 to UC-08 actually detected.
- False positive rate.
- Triage gain compared with manual handling.
- AI relevance: agreement between LLM labels and a hand-labelled set of alerts.

## 11. Build order

| Phase | Content | Milestone |
|---|---|---|
| 0 | Both laptops: VMs, the three networks, OPNsense, addressing, cable link, connectivity tests | |
| 1 | Detection base: Wazuh on laptop 1, agents on both targets, Sysmon, Suricata alerts reaching Wazuh, first use cases firing | Séance 4 |
| 2 | Enrichment and orchestration: MISP (with test indicators), Shuffle, DFIR-IRIS, a basic playbook from alert to incident | |
| 3 | AI engine: analysis API, score formula, Isolation Forest, Ollama with RAG, model comparison | |
| 4 | Response and supervision: firewall block, Wazuh active response, cancel link, automatic unblock, dashboards | |
| 5 | Validation and report: the six scenarios, indicator measurements, remaining report chapters, defence | Report 3 days before séance 7 |

Suggested work split: laptop 2 is the heavier half. Two people on it (one on network, firewall and attacks; one on the AI engine) and one person on laptop 1 with the Shuffle playbook. Everyone must be able to explain the AI and the decision rule.

## 12. Things to verify during the build (not confirmed)

- How Suricata's eve.json leaves OPNsense for Wazuh: a Wazuh agent plugin on OPNsense is believed to exist; otherwise forward logs by syslog.
- Whether OPNsense can expire a blocked address by itself. The design assumes it cannot and has Shuffle schedule the unblock.
- The exact OPNsense API calls for adding and removing an address in a block list.
- Wazuh's built-in integration for sending alerts to a Shuffle webhook, and the alert level threshold to use.
- Whether VMware bridging behaves on the laptops' Ethernet adapters.
- Real memory use on laptop 1.
- French output quality of the 3B models.
- Always check commands and configuration against the current official documentation of each tool; versions change.

## 13. Known limits (already stated in the report)

- Suricata only sees traffic crossing the firewall: nothing between two machines of the same zone, and not the content of encrypted connections. Host logs cover that gap. For the SQL injection scenario, use plain HTTP or rely on the web server logs.
- Lab addresses are private and appear in no public feed, so MISP needs hand-added test indicators (needed for T-05 and UC-08).
- The language model is small, so explanations are less refined; this is one more reason it does not decide.
- Internet is used only for updates: Suricata rules, MISP indicators, model download.

## 14. Differences from the validated cahier des charges (tell the supervisor)

- Sensitive actions no longer wait for human approval; guardrails replace it.
- The lab runs on two laptops instead of one machine.
- A firewall VM (OPNsense) was added.
- The model is 3B instead of 7 to 8B.
- The optional chatbot assistant was dropped.

## 15. Existing deliverables

- `rapport_soc_ia.tex`: the French LaTeX report with cover page, tables of contents, general introduction, chapter 1 ("État de l'art et conception de la solution") and a bibliography. On Overleaf it expects two images: `download.png` (the architecture) and `tek_up_logo.jpg`.
- `architecture_soc.png` and `architecture_soc.svg`: the architecture diagram with tool logos, two laptops and the nine numbered exchanges.
- The original cahier des charges (PDF, version 1.0) and its simplified rewrite.

Remaining report chapters to write as the build progresses: implementation, tests and results, general conclusion.

## 16. Suggested repository layout

```
soc-ia/
  README.md
  docs/                 brief, report sources, diagrams
  infra/
    laptop1-soc/        docker-compose files for Wazuh, Shuffle, MISP, DFIR-IRIS
    laptop2-lab/        notes and exports for OPNsense, VM settings, network plan
  wazuh/                custom rules, agent configuration, Sysmon configuration
  suricata/             rule selection and local rules
  shuffle/              exported playbooks
  ai-engine/            FastAPI service: scoring, anomaly detection, LLM and RAG
    data/               normal-activity dataset, labelled test alerts
    knowledge/          ATT&CK extracts and response procedures for the RAG
  tests/                attack scripts for T-01 to T-06 and measurement notes
```

Keep secrets (API keys, passwords) out of the repository.
