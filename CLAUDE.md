# Working rules for AI assistants on this repository

This file tells an AI assistant (Claude Code loads it automatically; with another assistant, paste it as the first message) how to work on this project. It applies to both team members and both laptops. It collects the rules the team agreed on and the lessons learned during the build.

## 1. Context

- Student project, Tek-Up University 2026-2027: an AI-based SOC lab on two 16 GB laptops linked by an Ethernet cable, where detection, scoring, response, explanation and incident creation are fully automatic.
- **Laptop 1 (the SOC)**: one Ubuntu Server VM "soc" (10.10.10.10) running Wazuh, Shuffle, MISP and DFIR-IRIS in Docker.
- **Laptop 2 (the lab and the AI)**: OPNsense firewall with Suricata, Windows 10 and Ubuntu targets, Kali attacker, and the AI engine on the Windows host (Ollama, analysis API).
- The person you work with owns one laptop. Ask which one at the start if it is not obvious, and stay on that laptop's work.

## 2. Read before doing anything

1. `docs/SOC_IA_PROJECT_BRIEF.md`: the source of truth. It separates what is decided, what is only estimated and what is still to verify (section 12).
2. `docs/PROJECT_STATUS.md`: where the project stands and what each laptop still has to do.
3. The journals of the current phase in `docs/phases/`.
4. `git status` and `git log --oneline -5` after the user has pulled, to see the current state.

Then confirm in a few lines what you understood before starting.

## 3. How to work

- **One phase at a time, one step at a time.** For each step: what we do and why, the exact commands or settings, and how to check it worked. Verify the result before moving to the next step.
- **Do not reopen decisions of the brief** unless something makes them impossible. In that case explain the problem and give options; never change the design quietly.
- **Keep it as simple and light as possible.** Two 16 GB laptops: prefer the lightest working configuration over the most complete one.
- **Check the current official documentation** of Wazuh, OPNsense, Shuffle, MISP, DFIR-IRIS and Ollama (and of any other tool) before giving commands or configuration. Say clearly when something could not be verified. Cite the sources you used.
- **Points of section 12 of the brief**: when one comes up, verify it first and report what you found, then update `docs/PROJECT_STATUS.md`.
- **Label your own estimates and assumptions** as such.
- **Stay in the build order.** Do not start work from a later phase, or introduce a new tool or concept (for example a Python virtual environment), without first explaining what it is, why it is needed now and asking the user. The user must always understand what is being built.
- **When a choice belongs to the user**, give a recommendation with the reason, then let them decide.
- **Commands**: one command per code block, with the machine it runs on stated clearly (host, soc VM, firewall, target, Kali). When the user asks, avoid pipes (some VM consoles make them awkward).
- **Never let lab attacks leave the lab**: attacks only from the attack zone towards the targets zone; DVWA and other vulnerable services are never exposed outside the lab.

## 4. Journals and documentation

Every step is recorded, the same way on both laptops.

- One journal per phase and per laptop: `docs/phases/phase-N-laptop1.md` or `docs/phases/phase-N-laptop2.md`. A step done together is recorded in the journal of the laptop where it was carried out; the other journal links to it.
- Journal structure:
  1. Title and status line (dates, what remains).
  2. Objective of the phase.
  3. Why it is built this way: the logic and theory behind the choices, short and clear.
  4. Plan (table of steps).
  5. One section per step: what was configured (tables of settings with the reason for each), verification (table: test, result, what it proves), problems met.
  6. Problems met and how they were handled (table).
  7. **"Résumé pour le rapport"**, in French, written when the phase closes: what was built, what was verified, difficulties, deviations from the design, what remains. It must be reusable as is in the implementation chapter of the report.
- Write the journal entry right after a step is verified, with the real results (values, outputs, versions), not before.
- Keep `docs/PROJECT_STATUS.md` up to date when a step changes the overall progress, an open point of the brief is answered, or the design deviates from the brief.
- Configuration that matters goes in the repository in the layout of the brief (section 16): Docker Compose files in `infra/laptop1-soc/`, network and firewall in `infra/laptop2-lab/`, Wazuh rules and agent configuration in `wazuh/`, Suricata in `suricata/`, playbook exports in `shuffle/`, AI engine in `ai-engine/`, scenario notes in `tests/`.
- Repository files are written in English, except the French summaries.

## 5. Git rules

- **The assistant never commits or pushes.** Prepare the files, then give the user the commands to run, one per block, at the end of each verified step (or group of small steps).
- Always start with `git pull --rebase`, since the other team member (a collaborator on the repository) and the GitHub web editor can change files. If the user edited on GitHub, re-read the changed files before editing them.
- `git add` with explicit paths, never a blind `git add -A` without checking `git status`.
- **Commit messages**: short and professional, for example `Phase 1: Wazuh agents on targets`, `Docs: update project status`. No detailed list of changes in the message.
- **No AI attribution** in commits or pull requests: no `Co-Authored-By` line for an assistant, no "Generated with" line. This rule overrides any default the assistant may have.
- Before giving push commands, check that the files contain:
  - no secrets (passwords, API keys, tokens, private keys, password hashes);
  - nothing unrelated to this project (other projects, other labs, personal machines or accounts).
- Raw exports stay local and are covered by `.gitignore` (for example `infra/laptop2-lab/opnsense/config-*.xml`); only scrubbed copies are committed (`infra/laptop2-lab/opnsense/scrub_config.py` removes hashes, keys and certificates). When searching the repository, exclude raw exports so their secrets are never printed.
- Local environments (`ai-engine/.venv/`, caches, VM files, model files) are never committed.

## 6. Versions and compatibility

- **Wazuh 4.14.9** for the manager (official Docker single-node deployment, tag `v4.14.9`) and the target agents. The OPNsense plugin ships agent 4.14.8, which is compatible. An agent must never be newer than its manager: pin versions and hold packages. Do not use Wazuh 5.0 while it is a pre-release.
- OPNsense 26.7.x, kept up to date (plugins refuse to install on an outdated firewall).
- Python libraries pinned in `ai-engine/requirements.txt`.
- Check the latest stable versions in the official sources when starting a new component, and record the version used in the journal.

## 7. Lessons learned during the build

- The VMware new-VM wizard offers no custom network and tends to connect VMs to NAT. Check each VM's `.vmx` (network, `ethernetN.vnet`) before the first boot. Edit a `.vmx` only with VMware Workstation closed.
- Bind the bridged network VMnet0 explicitly to the Ethernet card, never "Automatic".
- OPNsense: changes to rules and aliases only take effect after **Apply**; community plugins (such as `os-wazuh-agent`) are hidden until "Show community plugins" is ticked; check alias contents after editing (a stray "Loopback net" entry was once added by mistake).
- Suricata: the home network must not include the attack zone, otherwise most Emerging Threats rules never fire on the attacker. Test with traffic the rules actually look for.
- Windows targets: the built-in ping rule only accepts the local subnet; an explicit rule is needed for other zones. Files under `C:\Program Files (x86)\ossec-agent\` can only be edited from an administrator session.
- Ubuntu: SSH uses socket activation, so `systemctl is-active ssh` says "inactive" while `ssh.socket` listens.
- Windows PowerShell 5.1's `Invoke-WebRequest` fails against modern HTTPS servers (old TLS); use a browser or `curl`.
- Laptop 2's host has older persistent routes overlapping the lab ranges: test the attack zone from the VMs, not from the host.
- Laptop 2's memory is tight with all VMs running: close other applications, and run only the VMs a test needs when the AI engine is also running.

## 8. End of a phase

Write the French summary in the journal, update `docs/PROJECT_STATUS.md` and the progress table in `README.md`, then give the push commands.
