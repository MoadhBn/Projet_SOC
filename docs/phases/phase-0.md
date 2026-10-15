# Phase 0: lab infrastructure (laptop 2)

Status: in progress. Started 13 October 2026.

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

### Step 0.6: target and attacker VMs (not started)

### Step 0.7: cable link with laptop 1 (not started, needs both laptops)

### Step 0.8: connectivity matrix, snapshots (not started)

## 4. Problems met and how they were handled

| Problem | Handling |
|---|---|
| OPNsense sized at 2 GB in the design, below the official minimum | Raised to 3 GB; laptop 2 has the margin |
| Team not in the same place during the build | Solo-mode network (VMnet12) for the SOC link |
| Lab zones have no internet but need packages during installation | A "maintenance" firewall rule, disabled by default (step 0.5) |

## 5. Résumé pour le rapport

To be written when the phase is closed.
