# Phase 1: detection base

Status: in progress. Started 16 October 2026.

This file is the journal of phase 1.

## 1. Objective

Make the lab observable: every attack of the test scenarios must leave a trace that reaches Wazuh and raises an alert. Milestone: séance 4 (first progress evaluation), where the detection base must work.

Phase 1 is finished when:

- the Wazuh agents of both targets and of the firewall report to the Wazuh manager on laptop 1;
- Sysmon events from the Windows target and Suricata network alerts arrive in Wazuh;
- the first use cases raise alerts (at least UC-01 SSH brute force, UC-02 encoded PowerShell, UC-04 port scan).

## 2. Why it is built this way

### Two complementary sources of detection

| Source | Sees | Misses |
|---|---|---|
| Host telemetry (Wazuh agent, Sysmon, system logs) | What happens on the machine: processes, command lines, logins, file changes, web server logs | Traffic that never touches a monitored machine |
| Network detection (Suricata on the firewall) | Traffic crossing the firewall between zones: scans, exploit attempts, known malicious patterns | Traffic inside one zone, content of encrypted connections, what happens after a payload runs |

Neither source is enough alone. A port scan is obvious on the network and almost invisible on the host; an encoded PowerShell command is the opposite. Wazuh brings both into one place, which is the base of the rest of the pipeline.

### Sysmon

Windows' own event log records logins and services but not, by default, each process launched with its command line or each network connection. Sysmon (Microsoft Sysinternals) adds these events. A configuration file decides what is recorded, to keep useful events and drop noise.

### Suricata in detection mode

Suricata runs on OPNsense in IDS mode (PCAP live capture): it raises alerts but never drops traffic. Blocking is decided later in the pipeline by the score (phase 4), not by the IDS itself, which keeps one decision point and avoids an unexplained block.

### Home network and external network

Suricata rules are written in terms of `HOME_NET` (what we protect) and `EXTERNAL_NET` (everything else); many rules only fire for traffic from `EXTERNAL_NET` towards `HOME_NET`. OPNsense's default home network is all private address space, which would make the attacker (10.10.30.10) part of `HOME_NET` and silence those rules. The home network is therefore limited to the SOC and targets zones, so the attack zone counts as external.

## 3. Plan

| Step | Content | Needs laptop 1 |
|---|---|---|
| 1.1 | Suricata on OPNsense with Emerging Threats Open rules | no |
| 1.2 | Sysmon on the Windows target | no |
| 1.3 | Vulnerable web application on the Linux target | no |
| 1.4 | Wazuh agent plugin on OPNsense (installed, not yet enrolled) | no |
| 1.5 | Wazuh agents on both targets, enrolment, Suricata events in Wazuh | yes (manager running, cable or VPN link) |
| 1.6 | First use cases: SSH brute force, encoded PowerShell, port scan | yes |

## 4. Points from the brief verified at the start of the phase

| Point (brief section 12) | Finding | Source |
|---|---|---|
| How Suricata's eve.json leaves OPNsense for Wazuh | Confirmed: the `os-wazuh-agent` plugin exists (community plugin, "as-is" support). Its option "Intrusion detection events" forwards the Suricata eve feed to the manager; Wazuh only accepts RFC 3164 syslog, so the plugin writes a copy to `/var/ossec/logs/opnsense_syslog.log` | OPNsense documentation, Wazuh Agent page |
| Current Wazuh version | 4.14.9 (14 October 2026). The agents must not be newer than the manager, so laptop 1 and laptop 2 must agree on the version | Wazuh release notes |
| Firewall block for the response (phase 4) | New option found: the plugin ships an active response `opnsense-fw` that adds and removes addresses on the firewall. To compare in phase 4 with the planned Shuffle call to the OPNsense API | OPNsense documentation, Wazuh Agent page |

## 5. Steps

### Step 1.1: Suricata on OPNsense (done)

Configuration (Services > Intrusion Detection > Administration):

| Setting | Value | Reason |
|---|---|---|
| Enabled | yes | |
| Capture mode | PCAP live mode (IDS) | Alerts only; blocking is decided by the score later in the pipeline |
| Promiscuous mode | off | Routed traffic is addressed to the firewall's card anyway |
| Interfaces | TARGETS, ATTACK | As decided in the brief |
| Pattern matcher | Hyperscan | Recommended by the documentation where the CPU supports it |
| Home networks | 10.10.10.0/24, 10.10.20.0/24 | The attack zone must count as external for `EXTERNAL_NET -> HOME_NET` rules to fire |
| Rule sets | ET Open categories for the scenarios only (scan, web server, SQL, exploit, attack response, policy) | Full ET Open would cost memory on a 3 GB firewall |

Verification: from Kali, `sudo nmap -sS -p 1433,1521,3306,5432,5900 10.10.20.20` raised Emerging Threats scan alerts (SIDs 2010935, 2010936, 2010937, 2010939: suspicious inbound connections to database ports), source 10.10.30.10, destination 10.10.20.20, action "allowed" (detection only). These rules are written from `EXTERNAL_NET` to `HOME_NET`, so they also confirm that the home network setting places the attacker outside.

Observations:

- A first scan of ports 1 to 1000 raised nothing: the classic ET scan rules watch specific higher ports (databases, VNC). Test commands must target what the rules look for.
- `nmap -sV -p 22` raised no alert. This is expected: a single version probe is not suspicious enough for network rules; SSH attacks (UC-01) will be detected from the target's authentication logs by Wazuh.
- Every alert appears twice, once on ATTACK and once on TARGETS, because the packet crosses both monitored interfaces. Grouping in Shuffle (phase 2) is expected to merge them; watching only TARGETS would halve the work and the duplicates, but changes a decision of the brief and is left to the team.

### Step 1.2: Sysmon on the Windows target (done)

| Item | Value |
|---|---|
| Sysmon | Current Sysinternals release (page dated 10 September 2026), 64-bit build, installed with `Sysmon64.exe -accepteula -i` |
| Configuration | SwiftOnSecurity `sysmon-config` (version 74), stored in the repository as `wazuh/sysmon/sysmonconfig.xml` (licence CC BY 4.0, attribution kept in the file header) |
| Files on the VM | `C:\Tools\Sysmon\`, copied from the host by drag and drop (no internet needed) |
| Event log | `Microsoft-Windows-Sysmon/Operational` |

Support note: Microsoft's Sysmon page now lists "Client: Windows 11 and higher". Windows 10 is no longer listed since its end of support. The current release installed and works on Windows 10 1903, but this is outside Microsoft's stated support.

Verification: the encoded PowerShell command `powershell -NoProfile -EncodedCommand dwBoAG8AYQBtAGkA` (the encoded text is `whoami`) produced a Sysmon **Event ID 1** (Process Create) on `target-win`, whose CommandLine field contains the full `-EncodedCommand` argument. This is the raw event Wazuh will turn into a UC-02 (T1059.001) alert.

### Step 1.3: vulnerable web application on the Linux target (done)

Choice: **DVWA** (Damn Vulnerable Web Application) rather than OWASP Juice Shop. DVWA is a PHP and MySQL application: it is lighter on the 1.5 GB target, and its attacks (SQL injection, XSS) land in Apache's standard access log, which Wazuh already has decoders and rules for. Juice Shop is a heavier Node.js application whose attacks are harder to observe in logs.

| Item | Value |
|---|---|
| Installation | Native (not Docker), following the current DVWA README: Apache 2.4.66, MariaDB, PHP with `php-mysqli` and `php-gd`, DVWA cloned into `/var/www/html/DVWA` |
| Database | Database `dvwa`, local account `dvwa` with DVWA's documented default password (exists only inside the VM) |
| Security level | `low` (`default_security_level` in `config/config.inc.php`) so the scenario attacks work |
| PHP options | README's `allow_url_include` change not applied: only needed for remote file inclusion, which is not part of the scenarios |
| Internet | Maintenance rule 7 enabled only during the installation |
| Database initialisation | From Kali's browser (`/DVWA/setup.php`), Kali's desktop started temporarily and returned to text mode afterwards; the host cannot reach the targets zone by design |

Problem met: the setup page returned "500 Internal Server Error". Apache's error log showed `Access denied for user 'dvwa'@'localhost'`: the database account had not been created as expected. It was recreated with an idempotent command, and a direct connection test (`mariadb -h 127.0.0.1 -u dvwa ...`) confirmed the fix before retrying.

Verification:

| Test | Result |
|---|---|
| Login to DVWA from Kali (10.10.30.10) | Login page, POST login (302), index and security pages served (200) |
| `/var/log/apache2/access.log` on the target | Each request from 10.10.30.10 recorded with method, URL, status and user agent: the input Wazuh will analyse for UC-03 |
| Memory with Apache and MariaDB running | 503 MiB used, 906 MiB available out of 1.4 GiB |

### Step 1.4: Wazuh agent plugin on OPNsense (done, not enrolled)

| Item | Value |
|---|---|
| Plugin | `os-wazuh-agent` 1.3_1, community plugin (support tier 3), hidden until "Show community plugins" is ticked in System > Firmware > Plugins |
| Agent package installed with it | `wazuh-agent` **4.14.8** |
| State | Installed, **disabled**; manager address to be set to 10.10.10.10 when the manager exists |

Why the version matters: Wazuh requires an agent to be no newer than its manager, and the plugin's agent version is fixed by OPNsense's package repository, not chosen by us. With 4.14.8 on the firewall, a manager in 4.14.9 (current stable release) is compatible. Decision shared with laptop 1: **Wazuh 4.14.9** for the manager (official Docker single-node deployment, tag `v4.14.9`) and for the agents on both targets.

Problem met: the plugin installation was refused with "Installation out of date. The update to opnsense-26.7.7 is required": the firewall was still on 26.7 although the earlier update had appeared to finish. A second firmware update brought it to 26.7.7, after which the plugin installed.

### Step 1.5a: Wazuh agents pre-installed on the targets (done, waiting for the manager)

The agents are installed before the manager exists, pointing at 10.10.10.10. They retry until the manager answers, then enrol, which shortens the joint session with laptop 1.

| Target | Version | Installation |
|---|---|---|
| target-linux | 4.14.9 | Wazuh APT repository, version pinned (`wazuh-agent=4.14.9-1`), package put on hold so a system upgrade cannot make it newer than the manager; maintenance rule 7 enabled only during the installation |
| target-win | 4.14.9 | Official MSI downloaded on the host and copied to the VM, installed with `msiexec /q WAZUH_MANAGER="10.10.10.10"` |

Version policy: an agent must never be newer than its manager. Manager and target agents are on 4.14.9; the firewall's agent stays on 4.14.8, the version imposed by the OPNsense plugin, which is compatible.

Verification: `systemctl is-active wazuh-agent` returns `active` on the Linux target, `Get-Service wazuhsvc` returns `Running` on the Windows target.

Additional log sources, kept in the repository (`wazuh/agents/`):

| File | Adds | For |
|---|---|---|
| `target-linux-localfile.xml` | Apache access and error logs (`log_format` `apache`) | UC-03 |
| `target-win-localfile.xml` | Sysmon event channel `Microsoft-Windows-Sysmon/Operational` (`log_format` `eventchannel`) | UC-02, UC-05 |

## 6. Problems met and how they were handled

| Problem | Handling |
|---|---|

## 7. Résumé pour le rapport

To be written when the phase is closed.
