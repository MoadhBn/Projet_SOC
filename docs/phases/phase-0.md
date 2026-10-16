# Phase 0: lab infrastructure (laptop 2)

Status: laptop 2 side finished on 16 October 2026 (started 13 October). Remaining: step 0.7, the cable link with laptop 1, which needs both laptops in the same place.

This file is the journal of phase 0.

## 1. Objective

Build the ground the SOC stands on, before any security tool is installed:

- the virtual machines of the lab (firewall, two targets, attacker);
- three isolated network zones with a firewall between them;
- the addressing plan;
- the link to laptop 1, where the SOC tools run.

Phase 0 is finished when every allowed path works and every forbidden path is proven blocked.

## 2. Why it is built this way

### Three zones instead of one flat network

| Zone | Network | Role |
|---|---|---|
| SOC link | 10.10.10.0/24 | Where the defenders are: Wazuh, Shuffle, MISP, DFIR-IRIS, the analysis API |
| Targets | 10.10.20.0/24 | The machines being monitored and attacked |
| Attack | 10.10.30.0/24 | The simulated attacker (Kali) |

Putting the attacker, the victims and the SOC in separate networks has three effects:

1. **The firewall becomes a control point.** Traffic between zones must cross OPNsense, so it can be filtered, inspected by Suricata, and cut by an automatic block. On a flat network the attacker would reach the targets directly and a firewall block would do nothing.
2. **The SOC is protected from what it observes.** The attacker zone can never reach the SOC zone. A SOC that can be attacked by the threat it is analysing is not trustworthy.
3. **Least privilege between zones.** The targets may only talk to the SOC on the two Wazuh agent ports. Everything else is denied by default.

### VMware network types used

| Type | Behaviour | Used for |
|---|---|---|
| Bridged | The VM is placed directly on a physical network card of the host | The SOC link over the Ethernet cable to laptop 1 |
| Host-only | A private virtual switch that exists only inside the laptop | The targets and attack zones, which must stay isolated |
| NAT | The VM reaches the internet through the host's connection | Updates for the firewall only |

A host-only network normally gives the Windows host its own adapter on that network. For the targets and attack zones this adapter is removed, so the host is not a member of those zones and the only way out of them is through the firewall.

### Solo mode and cable mode

The team does not work in the same place during the build. With no cable plugged in, the Ethernet adapter of the host has no usable address, so the host could not reach the firewall through the bridged network. A third host-only network (VMnet12) therefore carries the SOC link while working alone. On integration day the firewall's first adapter is moved to the bridged network; nothing changes inside the firewall.

## 3. Steps

### Step 0.0: repository skeleton (done)

- Folder layout from the brief, `.gitignore` excluding secrets, VM files and raw firewall backups.
- Brief copied to `docs/`, network plan written in `infra/laptop2-lab/network-plan.md`.
- Pushed to `github.com/MoadhBn/Projet_SOC`.

### Step 0.1: host pre-checks (done)

| Check | Result |
|---|---|
| CPU | Intel Core i5-12450HX, 8 cores / 12 threads, virtualization enabled in firmware |
| RAM | 15.7 GB total; 6.1 GB free at the time of the check, with other applications open |
| Disk | 132 GB free on C: |
| VMware Workstation | 17.6.4 |
| Ethernet | Realtek PCIe GbE port present, no cable connected |
| Virtualization-based security | Off; no Windows hypervisor, so VMware uses hardware virtualization directly |

Findings:

- The four lab VMs are sized at 8.5 GB in total (estimate). Other applications must be closed when all four run.
- OPNsense is given 3 GB instead of the 2 GB of the brief: the official documentation lists 3 GB as the minimum and as the amount the installer needs.
- VMnet1, VMnet2 and VMnet3 are already used by other labs on this laptop, so the project uses VMnet10, VMnet11 and VMnet12.

### Step 0.2: VMware virtual networks (done)

Target configuration:

| VMnet | Type | Subnet | Host adapter | VMware DHCP | Use |
|---|---|---|---|---|---|
| VMnet0 | Bridged to the Realtek Ethernet card (not automatic) | n/a | n/a | n/a | SOC link, cable mode |
| VMnet8 | NAT (existing) | 192.168.78.0/24 | yes | on | Firewall WAN |
| VMnet10 | Host-only | 10.10.20.0/24 | no | off | Targets zone |
| VMnet11 | Host-only | 10.10.30.0/24 | no | off | Attack zone |
| VMnet12 | Host-only | 10.10.10.0/24 | yes | off | SOC link, solo mode |

VMware's DHCP service is turned off on the three lab networks because every machine has a fixed address from the plan; an address handed out by VMware would bypass the plan.

Before changing VMnet0, every existing VM was checked: none uses the bridged network (the ZTNA lab in EVE-NG uses VMnet2, VMnet3 and NAT), so binding VMnet0 to the Ethernet card affects no other project.

Verification (14 October 2026, from Windows):

| Check | Result |
|---|---|
| VMnet0 bridge target | Only the Realtek `Ethernet` adapter is bound to VMnet0; all other adapters are unassigned |
| VMnet10, VMnet11 | Subnets 10.10.20.0/24 and 10.10.30.0/24 configured; no host adapter exists, so the host is not part of these zones |
| VMnet12 | Subnet 10.10.10.0/24; host adapter present and up, address 10.10.10.1 given by VMware (changed in step 0.3) |
| VMware DHCP | No DHCP scope declared for any 10.10.x.0 network |
| Other labs | VMnet1, VMnet2, VMnet3 and VMnet8 unchanged |

### Step 0.3: host address on the SOC link (done)

VMware gives the host adapter of a host-only network the first address of the subnet (10.10.10.1). In the plan that address belongs to laptop 1's host, so laptop 2's host is moved to 10.10.10.20. No default gateway is set on this adapter: the internet route must stay on Wi-Fi, and nothing beyond 10.10.10.0/24 is reached from the host through it.

Commands (administrator PowerShell):

```powershell
Remove-NetIPAddress -InterfaceAlias "VMware Network Adapter VMnet12" -AddressFamily IPv4 -Confirm:$false
New-NetIPAddress -InterfaceAlias "VMware Network Adapter VMnet12" -IPAddress 10.10.10.20 -PrefixLength 24
```

Verification (14 October 2026):

| Check | Result |
|---|---|
| Address on VMnet12 | 10.10.10.20/24, manual, only IPv4 address on the adapter |
| Default route | Only through Wi-Fi (192.168.100.1); none on VMnet12 |
| Internet from the host | Still working |

Finding: two persistent Windows routes left by the ZTNA lab use the same address ranges as this project: `172.16.0.0/24 via 10.10.10.1` and `10.10.30.10/32 via 192.168.78.20` (the ZTNA lab also uses 10.10.10.0/24 and 10.10.30.10). The virtual machines of the two labs are on separate VMware networks and cannot collide; only the Windows host's routing is ambiguous. The routes are left in place, the host never needs to reach the attack zone, and the two labs are never run at the same time (laptop memory would not allow it anyway).

### Step 0.4: OPNsense installation and interfaces (done)

Adapter order of the VM, which fixes the interface names inside OPNsense:

| VMware adapter | Network | OPNsense interface | Role | Address |
|---|---|---|---|---|
| Network Adapter 1 | VMnet12 (solo) / VMnet0 (cable) | vmx0 | LAN, renamed SOC | 10.10.10.254/24 |
| Network Adapter 2 | NAT (VMnet8) | vmx1 | WAN | DHCP |
| Network Adapter 3 | VMnet10 | vmx2 | OPT1, renamed TARGETS | 10.10.20.1/24 |
| Network Adapter 4 | VMnet11 | vmx3 | OPT2, renamed ATTACK | 10.10.30.1/24 |

The SOC side is the LAN interface on purpose: OPNsense only opens its administration page on LAN by default (anti-lockout rule), and the administrators (host, later the soc VM) are in the SOC zone. The virtual card type is VMXNET3, the type the current OPNsense documentation recommends under VMware.

VM `soc-opnsense`: 2 vCPU, 3 GB RAM, 20 GB disk, BIOS firmware, OPNsense 26.7 dvd image (SHA-256 checked against the official checksum file).

The VMware wizard does not expose the card type and listed the adapters in a different order, so the `.vmx` file was edited with Workstation closed (original kept as `soc-opnsense.vmx.bak-before-edit`):

| Setting | Wizard result | After edit |
|---|---|---|
| Card order | VMnet12, VMnet10, NAT, VMnet11 | VMnet12, NAT, VMnet10, VMnet11 |
| `ethernetN.virtualDev` | `e1000` | `vmxnet3` |
| `guestOS` | `freebsd-64` (FreeBSD 10 or earlier) | `freebsd15-64` (OPNsense 26.7 is based on FreeBSD 15.1) |
| `sound.present` | `TRUE` | `FALSE` |

Installation: from the live ISO with the `installer` account, ZFS on a single disk (stripe). ZFS was kept, as recommended by the documentation, because it tolerates abrupt power loss better, which matters on a laptop.

Interface assignment and addressing from the console (options 1 and 2): WAN `vmx1` by DHCP from VMware NAT; LAN `vmx0` 10.10.10.254/24; OPT1 `vmx2` 10.10.20.1/24; OPT2 `vmx3` 10.10.30.1/24. No upstream gateway on the internal interfaces, no IPv6, no DHCP server (all lab addresses are static), web interface kept on HTTPS.

Verification (15 October 2026, from the laptop 2 host):

| Check | Result |
|---|---|
| Console banner | Four interfaces with the planned addresses |
| `ping 10.10.10.254` | Replies, TTL 64 (FreeBSD); MAC 00:0c:29:8f:7e:04, the VMnet12 card |
| HTTPS 443 | Open; `https://10.10.10.254/` returns the OPNsense login page (HTTP 200) |
| SSH 22 | Closed (SSH is off by default; not needed) |

Note: Windows PowerShell 5.1's `Invoke-WebRequest` fails against the web interface because it defaults to old TLS versions that OPNsense refuses; a browser or `curl` works.

### Step 0.5a: first configuration of OPNsense (done)

| Item | Setting |
|---|---|
| Setup wizard | LAN kept at 10.10.10.254/24, LAN DHCP server off; WAN by DHCP with "Block RFC1918 private networks" and "Block bogon networks" kept; deployment options (multi-WAN, automatic DHCP/DNS registration, IPsec) off since none applies |
| Version | Updated from 26.7 to 26.7.7 through System > Firmware (this also proved the WAN reaches the internet through VMware NAT) |
| Interface names | LAN renamed SOC, OPT1 renamed TARGETS, OPT2 renamed ATTACK, all enabled |
| Hardware offloading | CRC, TSO and LRO offloading disabled (default kept); TSO offloading is documented as incompatible with Suricata in IPS mode |
| IPv6 | Turned off on the firewall: the lab is IPv4 only and the rules are written for IPv4 |
| Plugin | `os-vmware` installed, so VMware can shut the firewall down cleanly |

Verification: Interfaces > Overview shows SOC (vmx0) 10.10.10.254, WAN (vmx1) DHCP address in 192.168.78.0/24, TARGETS (vmx2) 10.10.20.1, ATTACK (vmx3) 10.10.30.1, all up.

### Step 0.5b: baseline firewall rules (done)

Principle: default deny. OPNsense blocks all traffic entering an interface unless a rule allows it, so only the required flows are written. Rules are created in **Firewall > Rules [new]** (the newer rule engine, which has an API); the first matching rule wins and rules on several interfaces (floating) are evaluated before single-interface rules.

Aliases (Firewall > Aliases):

| Alias | Type | Content | Purpose |
|---|---|---|---|
| `SOC_BLOCKLIST` | External (advanced) | empty | Addresses blocked automatically by Shuffle (phase 4) |
| `WAZUH_MANAGER` | Host(s) | 10.10.10.10 | The soc VM |
| `WAZUH_AGENT_PORTS` | Port(s) | 1514, 1515 | Wazuh agent channel and enrolment |
| `PRIVATE_NETS` | Network(s) | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 | "The internet" is defined as "not private" |

`SOC_BLOCKLIST` is of type External because the documentation describes this type for entries pushed by an outside program, the API endpoint `/api/firewall/alias_util/add/<alias>` accepts it, and changes apply immediately. Its entries are not kept across a firewall reboot, which is acceptable for temporary blocks (a reboot lifts them early).

Rules, read back from the configuration backup:

| # | Interface(s) | Action | Protocol | Source | Destination | Enabled |
|---|---|---|---|---|---|---|
| 1 | TARGETS, ATTACK | Block | any | `SOC_BLOCKLIST` | any | yes |
| 2 | TARGETS, ATTACK | Block | any | any | `SOC_BLOCKLIST` | yes |
| 3 | ATTACK | Pass | any | ATTACK net | TARGETS net | yes |
| 4 | ATTACK | Pass | ICMP | ATTACK net | ATTACK address | yes |
| 5 | TARGETS | Pass | TCP | TARGETS net | `WAZUH_MANAGER` port `WAZUH_AGENT_PORTS` | yes |
| 6 | TARGETS | Pass | ICMP | TARGETS net | TARGETS address | yes |
| 7 | TARGETS | Pass | any | TARGETS net | not `PRIVATE_NETS` (internet) | no, maintenance only |
| 8 | ATTACK | Pass | any | ATTACK net | not `PRIVATE_NETS` (internet) | no, maintenance only |
| 9 | SOC | Pass | TCP | SOC net | SOC address port 443 | yes |
| 10 | SOC | Pass | ICMP | SOC net | any | yes |
| - | SOC | Pass | any | SOC net | any | no: default "allow LAN to any" rules (IPv4 and IPv6) disabled |

What is therefore blocked: attack to SOC, attack to internet, targets to SOC except the agent ports, targets to attack (open question, decided when a scenario needs it), targets and attack to internet unless a maintenance rule is enabled, SOC to the targets and attack zones (except ping). The system anti-lockout rule keeps the administration page reachable from the SOC side.

Verification from the host after Apply: ping 10.10.10.254 answers, HTTPS returns the login page, HTTP is redirected to HTTPS.

Finding while reading the backup: the `WAZUH_MANAGER` alias also contained the entry `__lo0_network` (the loopback network, selected by mistake in the alias form), which would have allowed the targets to reach the firewall's own loopback on ports 1514 and 1515. The entry was removed and a new backup confirmed the alias holds only 10.10.10.10 (8 enabled rules out of 12 in total).

Configuration in the repository: `infra/laptop2-lab/opnsense/config-scrubbed.xml`, produced by `scrub_config.py`, which replaces the password hash, private keys and certificates with `REDACTED`. The raw backup stays local and is excluded by `.gitignore`.

### Step 0.6: target and attacker VMs (done)

Internet access for installations goes through the maintenance rules (7 for TARGETS, 8 for ATTACK), enabled only for the duration of an installation and disabled afterwards.

#### Step 0.6a: Linux target (done)

| Item | Value |
|---|---|
| VM | `soc-target-linux`, 1 vCPU, 20 GB disk, VMnet10 |
| Memory | Installed with 2 GB, then lowered to 1.5 GB. Canonical documents 1.5 GB as the minimum for an ISO installation, above the 1 GB estimated in the brief |
| System | Ubuntu Server 26.04.1 LTS, hostname `target-linux`, fully updated after installation |
| Address | 10.10.20.20/24, gateway 10.10.20.1, DNS 1.1.1.1 (static) |
| SSH | OpenSSH server installed; it is the target of scenario T-01 (SSH brute force) |

Problem met: the VMware wizard connected the VM to NAT instead of VMnet10, so the installer could not reach its gateway ("Destination Host Unreachable") and the package mirror failed. The adapter was moved to VMnet10. Since then each new VM's `.vmx` file is checked before first boot.

Note: since Ubuntu 22.10, SSH uses socket activation: `ssh.socket` listens on port 22 and `ssh.service` only starts on a connection, so `systemctl is-active ssh` reports "inactive" while SSH works.

Verification (maintenance rule disabled):

| Test from 10.10.20.20 | Result | Proves |
|---|---|---|
| `ip -4 addr` | 10.10.20.20/24 | Static address |
| ping 10.10.20.1 | replies | Rule 6 |
| ping 10.10.10.254 | no reply | Targets cannot reach the SOC zone outside the agent ports |
| ping 1.1.1.1 | no reply | No internet outside maintenance |
| `systemctl is-active ssh.socket`, `ss -tln` | active, listening on 0.0.0.0:22 and [::]:22 | SSH ready for T-01 |

#### Step 0.6b: Kali attacker (done)

The Kali 2026.1 official VMware image already present on the laptop was reused rather than reinstalled. It ships with a desktop; instead of reinstalling without one, it is set to boot in text mode (`systemctl set-default multi-user.target`), which gives the same memory saving.

| Item | Value |
|---|---|
| VM | `soc-kali`, 2 vCPU, 1.5 GB, VMnet11 |
| Address | 10.10.30.10/24, gateway 10.10.30.1, DNS 1.1.1.1 (NetworkManager, static) |
| Default password | changed |
| Updates | not applied: the 2026.1 tools (nmap, hydra, sqlmap) cover the scenarios; rule 8 is enabled only if a missing tool has to be installed |

Verification:

| Test from 10.10.30.10 | Result | Proves |
|---|---|---|
| `ip -4 addr` | 10.10.30.10/24 | Static address |
| ping 10.10.30.1 | replies | Rule 4 |
| ping 10.10.20.20 | replies, TTL 63 | Rule 3: the attack path works, and the TTL decreased by one shows the packet was routed through the firewall |
| ping 10.10.10.254 | no reply | Attack zone cannot reach the SOC zone |
| ping 1.1.1.1 | no reply | No internet for the attacker |
| `free -h` | 1.4 GiB total, 350 MiB used | Text mode keeps Kali light |

#### Step 0.6c: Windows target (done)

| Item | Value |
|---|---|
| VM | `soc-target-win`, 2 vCPU, 3 GB, 40 GB NVMe disk, UEFI, VMnet10 |
| System | Windows 10 Professionnel version 1903 (French), not activated, not updated |
| Installation | VMware Easy Install (unattended, local account, VMware Tools installed automatically); no internet during installation |
| Address | 10.10.20.10/24, gateway 10.10.20.1, DNS 1.1.1.1, hostname `target-win` |
| Windows firewall | Rule added: `LAB - Allow ICMPv4 echo request` (inbound ICMP type 8, all profiles) |

Origin of the installation image: SHA-1 `DFE4D1C27E2D40D52E7D4312B9B8B506B96FC909`, identical to the French Windows 10 1903 x64 image redistributed by Le Crabe Info; no hash published by Microsoft could be found to confirm it directly. Windows 10 is out of support since 14 October 2025 and version 1903 since December 2020: for a deliberately attacked machine in an isolated lab this is acceptable and realistic.

Problem met: the built-in Windows rule "File and Printer Sharing (Echo Request – ICMPv4-In)" only accepts pings from the local subnet. The Linux target (same subnet) got answers but Kali (attack zone) did not, even though the OPNsense rule allowed it. An explicit rule, accepting ICMP echo requests from any address, replaced it.

Verification:

| Test | Result | Proves |
|---|---|---|
| `ipconfig` | 10.10.20.10/24, gateway 10.10.20.1 | Static address |
| ping 10.10.20.1, ping 10.10.20.20 | replies | Gateway and same-zone link |
| ping 10.10.10.254 | no reply | Targets cannot reach the SOC zone |
| ping 1.1.1.1 | no reply | No internet outside maintenance |
| From Kali: ping 10.10.20.10 | replies | Attack path to the Windows target |
| Edition, VMware Tools | Windows 10 Pro, service running | Reported by the operator |

#### Memory measured with the four VMs running (16 October 2026)

With OPNsense, both targets and Kali running (9 GB allocated to VMs in total) and ordinary applications open on the host (browser, chat applications, about 3 GB together), only **0.9 GB of the 15.7 GB remained free**. The lab fits, but only with other applications closed. This matters for phase 3: the AI engine also runs on this host (Ollama, analysis API), so during AI tests it will probably be necessary to run only the VMs a scenario needs (for example one target instead of two). This is an observation, to be measured again in phase 3.

### Step 0.7: cable link with laptop 1 (not started, needs both laptops)

### Step 0.8: connectivity matrix, snapshots (done, OPNsense snapshot to confirm)

#### SOC zone towards the targets (16 October 2026)

The laptop 2 host has no route to the targets zone. A temporary route was added for the test (`route add 10.10.20.0 mask 255.255.255.0 10.10.10.254`, not persistent), which is the same route the soc VM will need in phase 1 for Wazuh to answer its agents.

| Test from the host (10.10.10.20) | Result | Proves |
|---|---|---|
| `tracert 10.10.20.20` | 10.10.10.254, then 10.10.20.20 | Traffic between zones goes through the firewall |
| ping 10.10.20.20 | replies, TTL 63 | Rule 10 (SOC ping for diagnostics) |
| ping 10.10.20.10 | replies, TTL 127 | Rule 10, and the Windows ICMP rule |
| TCP 10.10.20.20:22 | no connection, timeout | SOC to targets is blocked except ping: SSH is listening on the target (step 0.6a), so the failure comes from the firewall |
| TCP 10.10.20.10:3389 and 445 | no connection, timeout | Same |

The temporary route was removed after the test.

#### Attack zone towards the SOC zone, seen in the firewall log

From Kali, `ping -c 2 10.10.10.254` and `nc -zv -w 3 10.10.10.254 443` both failed. The OPNsense log (Firewall > Log Files) shows both attempts dropped:

| Interface | Direction | Protocol | Source | Destination | Action | Rule |
|---|---|---|---|---|---|---|
| ATTACK | in | ICMP | 10.10.30.10 | 10.10.10.254 | block | Default deny |
| ATTACK | in | TCP | 10.10.30.10 | 10.10.10.254:443 | block | Default deny |

No explicit rule is needed for this: the default deny policy covers it, and the log gives evidence for the report. Practical note: the live log is very busy (the Windows target constantly sends discovery broadcasts), so the evidence is easier to find with Plain View and a search on the source address, or with Live View filter conditions on source and destination.

#### Snapshots

The four VMs were shut down cleanly (OPNsense last) and a snapshot was taken of each, so the lab can be returned to this state if a later phase breaks something. Snapshots of powered-off VMs do not store memory, so they use little disk.

| VM | Snapshot |
|---|---|
| soc-target-linux | taken |
| soc-target-win | taken |
| soc-kali | taken |
| soc-opnsense | to confirm (not found in the VM files at the time of the check) |

#### Connectivity matrix (summary of all tests)

| From | To | Expected | Result | Evidence |
|---|---|---|---|---|
| Host (SOC) | Firewall 10.10.10.254, HTTPS | allowed | allowed | steps 0.4, 0.5b |
| Host (SOC) | Targets, ping | allowed | allowed | step 0.8 |
| Host (SOC) | Targets, TCP (SSH, RDP, SMB) | blocked | blocked | step 0.8 |
| Targets | Own gateway, ping | allowed | allowed | step 0.6 |
| Targets | Each other (same zone) | allowed | allowed | step 0.6c |
| Targets | SOC zone (except agent ports) | blocked | blocked | step 0.6 |
| Targets | Internet (maintenance rule off) | blocked | blocked | step 0.6 |
| Attack | Own gateway, ping | allowed | allowed | step 0.6b |
| Attack | Linux and Windows targets | allowed | allowed | steps 0.6b, 0.6c |
| Attack | SOC zone (ping, HTTPS) | blocked | blocked, logged by "Default deny" | step 0.8 |
| Attack | Internet | blocked | blocked | step 0.6b |
| Targets | Wazuh manager 10.10.10.10, TCP 1514-1515 | allowed | not testable yet | the soc VM does not exist yet (phase 1) |
| Laptop 2 SOC side | Laptop 1 over the cable | allowed | not tested | step 0.7 |

## 4. Problems met and how they were handled

| Problem | Handling |
|---|---|
| OPNsense sized at 2 GB in the design, below the official minimum | Raised to 3 GB; laptop 2 has the margin |
| Team not in the same place during the build | Solo-mode network (VMnet12) for the SOC link |
| Lab zones have no internet but need packages during installation | A "maintenance" firewall rule, disabled by default (step 0.5) |
| The VMware wizard offers no custom network and put VMs on NAT | Network adapter changed afterwards; each `.vmx` checked before first boot |
| The VMware wizard cannot set the VMXNET3 card type or the FreeBSD 15 guest type | `.vmx` edited with Workstation closed |
| Default "allow LAN to any" rules would let the SOC zone reach every zone | Disabled, replaced by two explicit rules (admin HTTPS, ping) |
| Loopback network added by mistake to the `WAZUH_MANAGER` alias | Found by reading the configuration backup, removed |
| The Ubuntu installer could not reach its mirror | VM on NAT instead of VMnet10, gateway and DNS fields empty; corrected |
| Windows answers pings only from its own subnet | Explicit Windows firewall rule for ICMP echo |
| Address ranges shared with an earlier lab (ZTNA) on the same laptop | Only the host's routing is affected; the two labs are never run together |
| Host memory: 0.9 GB free with the four VMs and usual applications | Close other applications; plan to run only the VMs a scenario needs in phase 3 |

## 5. Résumé pour le rapport

### Ce qui a été réalisé

La phase 0 a mis en place l'infrastructure du laboratoire sur le second ordinateur portable (laboratoire et IA), avant l'installation de tout outil de sécurité. Le laboratoire est découpé en trois zones réseau isolées : la zone SOC (10.10.10.0/24), la zone des cibles (10.10.20.0/24) et la zone d'attaque (10.10.30.0/24). Les zones des cibles et d'attaque sont des réseaux virtuels VMware de type « host-only » sans carte côté hôte : la seule sortie possible passe par le pare-feu.

Le pare-feu OPNsense 26.7.7 (machine virtuelle de 3 Go, quatre cartes VMXNET3) relie les trois zones et dispose d'une interface WAN en NAT réservée aux mises à jour. Les machines du laboratoire ont des adresses statiques :

| Machine | Système | Zone | Adresse |
|---|---|---|---|
| soc-opnsense | OPNsense 26.7.7 | toutes | 10.10.10.254, 10.10.20.1, 10.10.30.1 |
| soc-target-linux | Ubuntu Server 26.04.1 LTS avec SSH | cibles | 10.10.20.20 |
| soc-target-win | Windows 10 Professionnel 1903 | cibles | 10.10.20.10 |
| soc-kali | Kali Linux 2026.1 en mode texte | attaque | 10.10.30.10 |

La politique de filtrage suit le principe du refus par défaut : seuls les flux nécessaires sont autorisés. La zone d'attaque peut joindre les cibles (chemin d'attaque des scénarios). Les cibles ne peuvent joindre la zone SOC que sur les ports des agents Wazuh (1514 et 1515 vers 10.10.10.10). La zone SOC peut seulement administrer le pare-feu en HTTPS et effectuer des tests ping. Les zones des cibles et d'attaque n'ont pas accès à Internet ; deux règles de maintenance, désactivées par défaut, l'ouvrent temporairement pour les installations. Une liste de blocage (alias `SOC_BLOCKLIST` de type externe) est placée en tête des règles ; elle sera alimentée automatiquement par Shuffle en phase 4 au moyen de l'API d'OPNsense.

### Ce qui a été vérifié

Chaque flux autorisé et chaque flux interdit a été testé depuis la machine concernée. Les tests ping montrent que le trafic entre zones traverse bien le pare-feu (TTL diminué de un). Les tentatives de la machine Kali vers la zone SOC (ICMP et TCP 443) sont rejetées et apparaissent dans le journal du pare-feu avec la règle « Default deny ». Une connexion SSH de la zone SOC vers la cible Linux échoue alors que le service SSH écoute sur la cible, ce qui montre que le blocage provient du pare-feu. La configuration du pare-feu est versionnée dans le dépôt après suppression des secrets (empreinte du mot de passe, clés privées, certificats), et un instantané de référence des machines virtuelles a été pris.

### Difficultés rencontrées

Les difficultés ont surtout été pratiques. L'assistant de VMware ne permet ni de choisir un réseau personnalisé ni le type de carte réseau, ce qui a conduit à vérifier puis corriger le fichier de configuration de chaque machine. Une cible connectée par erreur au réseau NAT empêchait son installation. Le pare-feu de Windows n'acceptait les pings que depuis son propre sous-réseau. Enfin, la mémoire de l'hôte est presque entièrement occupée lorsque les quatre machines fonctionnent (0,9 Go libre sur 15,7 Go) : il faut fermer les autres applications, et ce point devra être pris en compte lors de l'intégration du moteur d'IA.

### Écarts par rapport à la conception

- Le pare-feu dispose de 3 Go de mémoire au lieu des 2 Go prévus : c'est le minimum indiqué par la documentation officielle d'OPNsense.
- La cible Linux dispose de 1,5 Go au lieu de 1 Go : c'est le minimum indiqué par Canonical pour une installation depuis l'image ISO.
- Les membres de l'équipe ne travaillant pas au même endroit pendant le développement, la zone SOC du second portable passe provisoirement par un réseau virtuel interne (VMnet12). Elle sera basculée sur le câble Ethernet (réseau ponté VMnet0) lors de l'intégration, sans modification du pare-feu.

### Ce qui reste

- Étape 0.7 : liaison par câble avec le premier portable, route statique sur la VM « soc » et règle du pare-feu Windows pour l'API d'analyse. Elle nécessite de réunir les deux portables.
- Le test des ports des agents Wazuh (1514 et 1515) ne pourra être fait qu'une fois la VM « soc » installée (phase 1).
