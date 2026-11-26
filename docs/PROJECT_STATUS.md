# Project status

AI-based next-generation SOC, Tek-Up University 2026-2027.
Team: Mohamed Nadhir Abidi, Mohamed Amine Rhimi, Moadh Ben Naceur. Supervisor: M. Tarek Hdiji.

This file is the entry point for anyone joining the work: what the project is, where it stands, what each laptop still has to do, and the rules the team follows. Details live in the phase journals (`docs/phases/`) and in the brief (`docs/SOC_IA_PROJECT_BRIEF.md`), which remains the source of truth for every design decision.

Last updated: 27 November 2026, from the journals of both laptops.

## 1. The project in short

- A lab SOC on two 16 GB laptops linked by an Ethernet cable, where the whole chain is automatic: collect, detect, group and enrich, score, respond, explain with a local AI, open an incident, notify.
- Laptop 1 (the SOC) runs one Ubuntu VM without graphical session, "soc" (10 GB), with Wazuh, Shuffle, MISP and DFIR-IRIS in Docker.
- Laptop 2 (the lab and the AI) runs the OPNsense firewall (with Suricata), a Windows 10 target, an Ubuntu target and a Kali attacker, plus the AI engine directly on Windows (Ollama and the analysis API).
- A fixed formula decides the priority score; the language model only summarises, labels and justifies, and its label can only raise the score.
- No human approval before a response: guardrails instead (temporary and reversible actions, protected list, cancel link, logs treated as untrusted input).

## 2. Network

| Zone | Network | Machines |
|---|---|---|
| SOC link (the cable) | 10.10.10.0/24 | laptop 1 host 10.10.10.1, soc VM 10.10.10.10, laptop 2 host 10.10.10.20, OPNsense 10.10.10.254 |
| Targets | 10.10.20.0/24 | OPNsense 10.10.20.1, Windows target 10.10.20.10, Linux target 10.10.20.20 |
| Attack | 10.10.30.0/24 | OPNsense 10.10.30.1, Kali 10.10.30.10 |

Firewall policy (default deny), as applied on OPNsense:

| From | To | Allowed |
|---|---|---|
| Attack | Targets | everything (the attack path) |
| Attack | SOC zone, internet | nothing |
| Targets | 10.10.10.10, TCP 1514 and 1515 (Wazuh agents) | yes, nothing else towards the SOC zone |
| Targets, attack | Internet | only through two "MAINTENANCE" rules, disabled by default, enabled during installations |
| SOC zone | Firewall web interface and API (HTTPS) | yes |
| SOC zone | Any zone, ping | yes (diagnostics) |
| Any lab zone | Addresses in alias `SOC_BLOCKLIST` | blocked (first rules; the list is filled by the automatic response) |

Full detail: `infra/laptop2-lab/network-plan.md` and `docs/phases/phase-0-laptop2.md`.

Temporary arrangement while the team works apart: on laptop 2 the SOC link runs on a VMware host-only network (VMnet12) instead of the cable. On integration day the firewall's first adapter moves to the bridged network VMnet0 and 10.10.10.20 moves to laptop 2's Ethernet card. Nothing changes inside the firewall.

## 3. Progress

| Phase | Content | Laptop 1 | Laptop 2 | Milestone |
|---|---|---|---|---|
| 0 | VMs, zones, firewall, cable link | **done** except step 0.7 (cable) | **done** except step 0.7 (cable) | |
| 1 | Detection base | **done** on its side: Wazuh 4.14.9 running; enrolment and use cases need the joint session | **done** on its side; enrolment and use cases wait for the manager | Séance 4 |
| 2 | MISP, Shuffle, DFIR-IRIS, first playbook | **done** on its side: Shuffle 2.3.0, DFIR-IRIS 2.4.29 and MISP 2.5.52 running; Wazuh alerts of the use cases are looked up in MISP and become IRIS alerts automatically; playbook in `shuffle/`. Tests with real attacks need the joint session | nothing to do yet | |
| 3 | AI engine | n/a | **started early**: models compared, API skeleton with the score formula | |
| 4 | Response, cancel link, unblock, dashboards | not started | not started | |
| 5 | Six scenarios, measurements, report | not started | not started | Report 3 days before séance 7 |

### Done on laptop 2

- **Phase 0** (`docs/phases/phase-0-laptop2.md`): three VMware networks, OPNsense 26.7.7 with four interfaces and the rules above, Linux target (Ubuntu 26.04.1, SSH), Windows target (Windows 10 Pro 1903), Kali (text mode). Every allowed and blocked path tested, blocks visible in the firewall log, snapshots taken, scrubbed firewall configuration in the repository.
- **Phase 1** (`docs/phases/phase-1-laptop2.md`): Suricata in detection mode on the TARGETS and ATTACK interfaces with selected Emerging Threats Open rules (alerts confirmed); Sysmon on the Windows target (encoded PowerShell recorded); DVWA on the Linux target (requests visible in Apache's log); Wazuh agents 4.14.9 installed on both targets, reading Sysmon and Apache logs, waiting for the manager; Wazuh agent plugin on OPNsense (agent 4.14.8), installed and disabled.
- **Phase 3, early** (`docs/phases/phase-3-laptop2.md`): Ollama on the host; first comparison of Llama 3.2 3B, Qwen2.5 3B and Gemma 3 4B (Gemma provisional favourite for French quality); analysis API skeleton (`ai-engine/`) with the score formula and 11 passing tests.

### Done on laptop 1

- **Phase 0** (`docs/phases/phase-0-laptop1.md`): VMware networks (VMnet0 bridged to the Realtek Ethernet card, VMnet12 host-only for solo mode, host 10.10.10.1); soc VM (4 vCPU, 8 GB in phase 1 and 10 GB from phase 2, 4 GB swap, 85 GB disk) with Ubuntu 24.04.5 LTS in text mode, `ens33` 10.10.10.10/24 without gateway, persistent route 10.10.20.0/24 via 10.10.10.254, NAT for downloads, SSH from the host; snapshot `phase0-baseline`.
- **Phase 1** (`docs/phases/phase-1-laptop1.md`): Docker Engine 29.9.3 and Compose v5.7.1 from Docker's repository; Wazuh 4.14.9 official single-node deployment (manager, indexer with 1 GB heap, dashboard on https://10.10.10.10); default passwords of `admin`, `kibanaserver` and `wazuh-wui` changed following the official procedure, passwords kept in a `.env` outside the repository; Compose file without secrets in `infra/laptop1-soc/wazuh/`. Ready for the agents: ports 1514 and 1515 published on 10.10.10.10.
- **Phase 2, done on laptop 1** (`docs/phases/phase-2-laptop1.md`): VM at 10 GB after measurement; Shuffle 2.3.0 (images pinned, OpenSearch heap 1 GB on 127.0.0.1:9201, Orborus without Swarm and without Tenzir pipelines) next to Wazuh; Wazuh's built-in `shuffle` integration sends alerts to the workflow `Wazuh-Alerts` (level 7 or more, plus Suricata alerts, rule 86601). Wazuh and Shuffle together: about 4.5 GiB in the VM. DFIR-IRIS 2.4.29 on https://10.10.10.10:8443 (own certificate, secrets changed, about 1.0 GiB). First playbook: Wazuh alert, Shuffle, IRIS alert (`POST /alerts/add`), tested with a real Wazuh alert. Wazuh vulnerability detection disabled (heavy disk and network use, not in the use cases). MISP 2.5.52 on https://10.10.10.10:9443 (MariaDB buffer 256 MB, about 1.25 GiB) with test indicators for Kali (10.10.30.10) and malicious.test.lab, read-only API key; the playbook is now Wazuh alert, Shuffle, MISP lookup of the source address, IRIS alert with the MISP result (about 15 seconds end to end). The four tools together: about 5.9 GiB, 18 containers. Maintenance on 26 November: 11 GB freed in `queue/vd`; playbook exported to `shuffle/` without keys or webhook identifier; IRIS test data closed; snapshot `phase2-soc-stack`.

### Points of the brief's section 12 (to verify during the build)

| Point | Status |
|---|---|
| How Suricata's eve.json reaches Wazuh | **Answered**: OPNsense plugin `os-wazuh-agent`, option "Intrusion detection events" |
| Whether OPNsense expires a block by itself | **Answered as far as the docs go**: nothing documented; Shuffle schedules the unblock as designed. Entries of an External alias are lost when the firewall reboots |
| OPNsense API calls to add and remove a blocked address | **Half answered**: add is `POST /api/firewall/alias_util/add/SOC_BLOCKLIST`; delete to confirm in the API reference (phase 4). Also found: the plugin's active response `opnsense-fw` can block addresses, to compare in phase 4 |
| Wazuh's integration towards a Shuffle webhook, alert level threshold | **Answered for the integration**: built-in `shuffle` integration of the Integrator module, alerts posted to `http://10.10.10.10:5001/api/v1/hooks/webhook_<id>` (inside the VM), full alert under `all_fields`. **Threshold answered**: level 7 or more, plus rule 86601 (Suricata alerts are level 3), from the rule levels of the use cases; two `shuffle` blocks, both loaded |
| VMware bridging on the laptops' Ethernet cards | **Open** (step 0.7) |
| Real memory use on laptop 1 | **Answered without agents**: the four tools fit together in a 10 GB VM, about 5.9 GiB in all (Wazuh 1.95, Shuffle 1.97, MISP 1.25 with MariaDB buffer at 256 MB, DFIR-IRIS 0.75), against 10.5 GB estimated; VM swap about 0.2 GiB. A VM of 11 GB left the Windows host with 126 MB available, so the VM runs at 10 GB; the host keeps 0.2 to 0.3 GB available with the VM at its maximum. To measure again with agents and scenarios |
| French quality of the 3B models | **First answer**: usable but imperfect; Gemma 3 4B clearly better; confirm with the real prompt on 20 to 30 lab alerts |

### Deviations from the brief so far

| Brief | Now | Reason |
|---|---|---|
| OPNsense 2 GB | 3 GB | Official minimum, needed by the installer |
| Linux target 1 GB | 1.5 GB | Canonical's minimum for an ISO installation |
| SOC link on the cable | VMnet12 while working apart, cable on integration day | The team builds in different places |
| Vulnerable web app not chosen | DVWA | Lighter than Juice Shop, attacks visible in Apache logs |
| Model: Llama 3.2 3B or Qwen2.5 3B | Gemma 3 4B provisional favourite (the brief's 4B fallback) | Much better French in the first test; to confirm |
| soc VM on Ubuntu Server | Ubuntu Desktop 24.04 installed minimal, graphical session disabled at boot, printing disabled | Server image could not be downloaded; equivalent result (605 MiB used at rest) |
| soc VM disk (not fixed; 100 GB planned) | 85 GB | 36 GB used with the four tools, 44 GB free (after freeing 11 GB left by the disabled Wazuh vulnerability detection); can be extended |
| SOC link on the cable (laptop 1) | VMnet12 while working apart, cable on integration day | Same arrangement as laptop 2 |
| soc VM 11 GB | 10 GB | Measured: at 11 GB the host had 126 MB available once the VM cache was full |
| Build order MISP, Shuffle, DFIR-IRIS | Shuffle, DFIR-IRIS, MISP | Riskiest and central tool first; testable alone with the manager's own alerts |
| Wazuh to Shuffle over HTTPS (exchange 4) | HTTP to the Shuffle backend, port 5001, inside the VM | Self-signed certificate on 3443; to revisit |
| DFIR-IRIS kept although the supervisor suggested TheHive | DFIR-IRIS 2.4.29 | TheHive 6 needs Cassandra and Elasticsearch (about 4 to 6 GB) and is no longer open source; TheHive is the documented fallback |
| Incident created for retained alerts | Every alert sent to Shuffle becomes an IRIS alert; escalation to a case comes with the score (phase 3) | IRIS separates alerts and cases |
| Wazuh defaults | Vulnerability detection disabled | Heavy disk and network use, not in the use cases |
| Playbook with branches on conditions | Single chain; every alert looked up in MISP, a missing source address replaced by `none` | A Shuffle 2.3.0 branch condition did not stop its branch; the single chain cannot produce a false MISP match |
| Shuffle official compose | Swarm mode and Tenzir pipelines disabled, `shuffle-security` removed, OpenSearch on 127.0.0.1:9201 with 1 GB heap | Swarm failed on the VM; lighter; port 9200 used by Wazuh |

### Decisions still open

- Suricata on both TARGETS and ATTACK (as in the brief) produces each alert twice; watching only TARGETS would halve the load. Team decision.
- Targets to attack zone traffic: blocked for now; open only if a scenario needs it.
- Cable sessions or a VPN (Tailscale was studied) for integration while apart.
- Notification channel (Telegram, Discord or email). Note: it needs permanent outbound internet from the soc VM, and the cancel link only works from a machine on the SOC network.

## 4. Work required on laptop 1

### Before the joint session

1. **soc VM**: done (phase 0 journal). Ubuntu 24.04.5 in text mode, 4 vCPU, 10 GB (see phase 2), 4 GB swap.
2. **Network of the soc VM**: done in solo mode (VMnet12); VMnet0 already bound to Ethernet for the cable.
   - one **bridged** adapter on VMnet0, with VMnet0 bound explicitly to laptop 1's **Ethernet** card in the Virtual Network Editor (not "Automatic", which may pick Wi-Fi): address **10.10.10.10/24, no gateway** on that adapter;
   - one **NAT** adapter for downloads (default route);
   - a **persistent static route**: `10.10.20.0/24 via 10.10.10.254`; without it Wazuh cannot answer the agents on the targets.
3. **Laptop 1 host**: 10.10.10.1/24 on VMnet12 for now; moves to the Ethernet card (no gateway) on integration day.
4. **Wazuh 4.14.9**: done (phase 1 journal). Original instructions kept for reference: official Docker single-node deployment, pinned version: `git clone https://github.com/wazuh/wazuh-docker.git -b v4.14.9`. Agents must never be newer than the manager: the targets run 4.14.9 and the firewall 4.14.8, so the manager must be 4.14.9. Do not use Wazuh 5.0 (pre-release).
   - `vm.max_map_count`: already 1048576 in Ubuntu 24.04 (at least 262144 required);
   - indexer Java heap 1 GB (official file); memory measured (see the open points above);
   - default passwords of `admin`, `kibanaserver` and `wazuh-wui` changed with the official procedure;
   - one port per tool: Wazuh 443, Shuffle 3443 (webhooks on 5001), DFIR-IRIS 8443, MISP 9443.
5. **Record it**: done (`docs/phases/phase-0-laptop1.md`, `docs/phases/phase-1-laptop1.md`, `infra/laptop1-soc/wazuh/`).

### Joint session (both laptops and the cable, or the VPN)

| Step | Action | Check |
|---|---|---|
| 0.7 | Cable between the laptops. Laptop 1: soc VM adapter 1 from VMnet12 to VMnet0 (bridged, bound to Ethernet), 10.10.10.1 moved from the VMnet12 host adapter to the Ethernet card (no gateway), VMnet12 host adapter disabled. Laptop 2: firewall adapter 1 to VMnet0, VMnet12 host adapter disabled, 10.10.10.20 moved to the Ethernet card | Laptop 2 host and OPNsense ping 10.10.10.1 and 10.10.10.10; the soc VM pings 10.10.10.254 and, through its route, 10.10.20.20 |
| 1.5 | Agents enrol: targets automatically (already pointed at 10.10.10.10); OPNsense plugin enabled with manager 10.10.10.10 and "Intrusion detection events" ticked | Three agents active in the Wazuh dashboard; Suricata alerts visible in Wazuh |
| 1.6 | First use cases: SSH brute force (UC-01), encoded PowerShell (UC-02), port scan (UC-04), from Kali or on the Windows target | An alert for each in Wazuh, with its ATT&CK technique |
| 2 | Same attacks through the playbook | One IRIS alert each (rules 5712/5763, 92057, 86601), MISP match for Kali 10.10.30.10; note the number of Suricata alerts |
| - | Windows firewall on laptop 2 allows the soc VM to reach the analysis API port (needed for phase 3) | Shuffle can call `http://10.10.10.20:8000/health` |

### Phase 2 (laptop 1): done on 26 November 2026

Done: Shuffle, Wazuh integration, DFIR-IRIS, first playbook (Wazuh alert to IRIS alert), MISP installed and measured. Next:

1. Done (26 November): MISP test indicators (event 1: `ip-src` and `ip-dst` 10.10.30.10, `domain` malicious.test.lab), read-only API key, `restSearch` checked.
2. Done (26 November): every Wazuh alert is looked up in MISP (source address, `none` when missing) and reaches IRIS with the result; about 15 seconds from webhook to IRIS alert.
3. Done (26 November): workflow exported to `shuffle/` without the IRIS key, the MISP key or the webhook identifier.
4. Done (26 November): maintenance, 11 GB of `queue/vd` freed, chain tested again.
5. Done (26 November): alerts sent to Shuffle filtered (level 7 or more, plus Suricata rule 86601), IRIS test data closed, snapshot `phase2-soc-stack`, French summary in the phase journal.

Details in `docs/phases/phase-2-laptop1.md`; configuration in `infra/laptop1-soc/` (wazuh, shuffle, iris, misp).

## 5. Loose ends on laptop 2

- New firewall backup to take (the scrubbed copy in the repository predates Suricata and the agent plugin).
- OPNsense snapshot not confirmed; the other three VMs have one ("Snapshot 1", to rename `phase0-baseline`).
- Sound cards still present on the Windows, Linux and Kali VMs (cosmetic).
- Host memory is tight: 0.9 GB free with the four VMs and usual applications; Gemma 3 4B uses part of system memory too. Measure again in phase 3.

## 6. Repository layout

| Path | Content |
|---|---|
| `docs/SOC_IA_PROJECT_BRIEF.md` | Source of truth: decisions, estimates, open points |
| `docs/PROJECT_STATUS.md` | This file |
| `docs/phases/phase-N-laptopX.md` | One journal per phase and per laptop |
| `infra/laptop1-soc/` | Docker Compose files and notes for the soc VM |
| `infra/laptop2-lab/` | Network plan, OPNsense scrubbed configuration and scrub script |
| `wazuh/` | Agent log sources, Sysmon configuration, custom rules |
| `suricata/` | Rule selection and local rules |
| `shuffle/` | Exported playbooks |
| `ai-engine/` | Analysis API (FastAPI), tests, RAG knowledge, datasets |
| `tests/` | Scenario descriptions and measurement notes |

## 7. Rules the team follows

The detailed rules file was removed from the repository on 13 November 2026; the rules below still apply.

- **The brief is the source of truth.** Decisions in it are not reopened unless something makes them impossible; then the problem and options are written down for the team.
- **One phase at a time, one step at a time.** Each step says what is done and why, gives the exact commands, and is verified before moving on.
- **Check current official documentation** (Wazuh, OPNsense, Shuffle, MISP, DFIR-IRIS, Ollama) before configuring anything, and write down what could not be verified. Estimates and assumptions are labelled as such.
- **Lightest working configuration**: two 16 GB laptops, nothing optional.
- **Every step is recorded** in the phase journal of the laptop that did it, and each journal ends with a French summary for the report.
- **Git**: each person commits and pushes their own work; AI assistants never commit or push, they give the commands. Short professional commit messages, no AI attribution lines. Always `git pull --rebase` first.
- **No secrets in the repository**: passwords, API keys, raw configuration backups and local environments stay out (see `.gitignore`); exported configurations are scrubbed first.
- **Nothing unrelated to the project** in repository files (other projects, personal machines).
- **Versions are pinned** (Wazuh 4.14.9, Python libraries in `requirements.txt`); a Wazuh agent is never newer than the manager.
