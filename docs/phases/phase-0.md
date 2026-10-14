# Phase 0: lab infrastructure (laptop 2)

Status: in progress. Started 13 October 2026.

This file is the journal of phase 0. It is filled in step by step and closed with a French summary for the implementation chapter of the report.

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

### Step 0.3: host address on the SOC link (in progress)

VMware gives the host adapter of a host-only network the first address of the subnet (10.10.10.1). In the plan that address belongs to laptop 1's host, so laptop 2's host is moved to 10.10.10.20. No default gateway is set on this adapter: the internet route must stay on Wi-Fi, and nothing beyond 10.10.10.0/24 is reached from the host through it.

### Step 0.4: OPNsense installation and interfaces (not started)

### Step 0.5: baseline firewall rules (not started)

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
