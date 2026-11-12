# Phase 0: SOC infrastructure (laptop 1)

Status: started 12 November 2026. Steps 0.1 to 0.3 done. Remaining: steps 0.4 to 0.6 alone, then step 0.7 (cable link) with laptop 2.

This file is the journal of phase 0 on laptop 1. Laptop 2's side is in `phase-0-laptop2.md`.

## 1. Objective

Build the machine the SOC tools run on, before any of them is installed:

- one Ubuntu Server VM, "soc" (10.10.10.10), sized for Wazuh, Shuffle, MISP and DFIR-IRIS in Docker;
- its two network links: the SOC link towards laptop 2 (no gateway) and NAT for downloads;
- the static route that lets the SOC answer the agents of the targets zone;
- laptop 1's host on the SOC link (10.10.10.1).

Phase 0 is finished on laptop 1 when the soc VM has its addresses, route, swap and updates, and, after step 0.7, reaches the firewall and the targets zone through the cable.

## 2. Why it is built this way

### One VM, everything in Docker

All four SOC tools run in Docker inside a single VM. One VM costs one operating system instead of four, which matters on a 16 GB laptop, and each tool is described by versioned Compose files (BNF-08 reproducibility).

### No graphical interface

The brief asks for Ubuntu Server: no graphical environment, the VM is administered from the console or over SSH and the web interfaces are opened from the host's browser, so a desktop would only take memory the SOC tools need. The server image could not be downloaded on the available connection, so Ubuntu Desktop 24.04.4 is installed with the minimal option and set to boot in text mode (`multi-user.target`): the graphical session never starts and its memory stays free. This is recorded as a deviation from the brief.

### Two network adapters

| Adapter | Network | Address | Why |
|---|---|---|---|
| 1 | SOC link | 10.10.10.10/24, no gateway | Where the agents, the firewall and the AI API are reached |
| 2 | NAT | DHCP, default route | Downloads only (packages, Docker images, feeds) |

The default route stays on NAT so internet traffic never goes through the lab firewall. The targets zone (10.10.20.0/24) sits behind OPNsense, so a static route `10.10.20.0/24 via 10.10.10.254` is needed; without it the replies of Wazuh to the agents would leave through NAT and be lost. No route to the attack zone is added: the attack zone must never reach the SOC.

### Solo mode and cable mode

The team builds in different places. With no cable, the host's Ethernet card has no link and a bridged VM reaches nobody. As on laptop 2, a host-only network carries the SOC link while working alone; on integration day the VM's first adapter moves to the bridged network VMnet0, bound to the Ethernet card, and nothing changes inside the VM.

## 3. Plan

| Step | Content | Status |
|---|---|---|
| 0.1 | Host pre-checks | done |
| 0.2 | VMware networks: VMnet0 bridged to Ethernet, host-only network for solo mode | done |
| 0.3 | Host address 10.10.10.1 on the SOC link | done |
| 0.4 | soc VM created, `.vmx` checked before first boot | to do |
| 0.5 | Ubuntu Server installed: addresses, route, 4 GB swap, updates | to do |
| 0.6 | Snapshot `phase0-baseline` | to do |
| 0.7 | Cable link with laptop 2 (joint session) | to do |

## 4. Steps

### Step 0.1: host pre-checks (done, 12 November 2026)

| Check | Result |
|---|---|
| CPU | Intel Core i5-13420H, 8 cores / 12 threads, virtualization enabled in firmware |
| RAM | 15.7 GB total; 7.1 GB free at the time of the check, with other applications open |
| Disk | 150 GB free on C: (D: has 2.7 GB free, not usable) |
| Operating system | Windows 11 Pro (build 26200) |
| VMware Workstation | 17.6.1 |
| Virtualization-based security | Off; VMware uses hardware virtualization directly |
| Ethernet | Realtek PCIe GbE present, disconnected (no cable yet); VMware Bridge Protocol enabled on it |
| VMware networks in the Virtual Network Editor | VMnet1 (host-only, 192.168.153.0/24), VMnet2 (host-only, 192.168.10.0/24), VMnet3 (host-only, 192.168.20.0/24), VMnet8 (NAT, 192.168.136.0/24); **no VMnet0** |
| Host adapters in Windows | VMnet1 to VMnet19 exist; those not declared in the editor only have link-local addresses (169.254.x.x) |
| Addresses in 10.10.0.0/16 on the host | None |
| Persistent routes | None |
| Other hypervisor | VirtualBox installed (host-only 192.168.56.0/24); not used by the project |

Findings:

- With the soc VM at 11 GB, about 4.7 GB is left for Windows and VMware. Every other application must be closed while the VM runs.
- VMnet0 must be created and bound explicitly to the Realtek card (step 0.2).
- The leftover host adapters carry only link-local addresses and do not overlap the lab ranges; they are left in place.
- The Ubuntu image on the laptop is the desktop edition (24.04.4). The brief asks for Ubuntu Server; the latest server image is `ubuntu-24.04.5-live-server-amd64.iso` (SHA-256 `97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8`, from releases.ubuntu.com/24.04/SHA256SUMS).

### Step 0.2: VMware virtual networks (done, 12 November 2026)

Configuration (Virtual Network Editor, administrator mode):

| VMnet | Type | Subnet | Host adapter | VMware DHCP | Use | Reason |
|---|---|---|---|---|---|---|
| VMnet0 | Bridged to the Realtek PCIe GbE card (not automatic) | n/a | n/a | n/a | SOC link, cable mode | "Automatic" may bridge to Wi-Fi |
| VMnet12 | Host-only | 10.10.10.0/24 | yes | off | SOC link, solo mode | Same number as on laptop 2; fixed addresses only, so no DHCP |
| VMnet1, 2, 3, 8 | unchanged | | | | Used by other VMs on the laptop | Not touched |

Verification:

| Test | Result | What it proves |
|---|---|---|
| Virtual Network Editor | VMnet0 Bridged, external connection Realtek PCIe GbE; VMnet12 Host-only, 10.10.10.0, no DHCP | Both networks exist with the planned settings |
| Ubuntu image | `ubuntu-24.04.4-desktop-amd64.iso`, SHA-256 `3a4c9877...a99d1e`, identical to the official SHA256SUMS | The image is intact |

### Step 0.3: host address on the SOC link (done, 12 November 2026)

VMware gives the host adapter of a host-only network the first address of the subnet, which is exactly the address of laptop 1's host in the plan (10.10.10.1). No change was needed.

| Test | Result | What it proves |
|---|---|---|
| `Get-NetIPConfiguration` on VMnet12 | 10.10.10.1/24, no IPv4 gateway | The host is on the SOC link and does not route through it |
| `Get-NetRoute -DestinationPrefix 0.0.0.0/0` | One default route, through Wi-Fi (192.168.1.1) | Internet stays on Wi-Fi |

On integration day (step 0.7), 10.10.10.1 moves to the Ethernet card and the VMnet12 host adapter is disabled, so that two adapters never hold the same subnet.

## 5. Problems met and how they were handled

| Problem | Handling |
|---|---|
| No VMnet0 in the Virtual Network Editor | Created in step 0.2 and bound to the Realtek card |
| VMnet0 disappeared once after applying other changes while set to "Automatic" | Re-created and bound directly to the Realtek card before applying |
| Ubuntu Server image could not be downloaded (slow connection) | Ubuntu Desktop 24.04.4 used, graphical interface disabled at boot (deviation from the brief) |

## 6. Résumé pour le rapport

À rédiger à la clôture de la phase.
