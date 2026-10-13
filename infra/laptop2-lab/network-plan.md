# Laptop 2: network plan and VM sizing

Working document for phase 0. Values marked "to confirm" are not applied or tested yet.

## Host (measured on 13 October 2026)

| Item | Value |
|---|---|
| CPU | Intel Core i5-12450HX, 8 cores / 12 threads, virtualization enabled in firmware |
| RAM | 15.7 GB total |
| Free disk on C: | about 132 GB |
| VMware Workstation | 17.6.4 |
| Ethernet adapter | Realtek PCIe GbE Family Controller (Windows name: `Ethernet`) |
| Virtualization-based security | off, no Windows hypervisor present (VMware runs natively) |

## Zones and addresses

| Zone | Network | Machines |
|---|---|---|
| SOC link | 10.10.10.0/24 | soc VM 10.10.10.10, laptop 2 host 10.10.10.20, OPNsense 10.10.10.254, laptop 1 host 10.10.10.1 |
| Targets | 10.10.20.0/24 | Windows 10.10.20.10, Linux 10.10.20.20, OPNsense 10.10.20.1 |
| Attack | 10.10.30.0/24 | Kali 10.10.30.10, OPNsense 10.10.30.1 |

## VMware virtual networks (to confirm at step 0.2)

| VMnet | Type | Use | Host adapter | VMware DHCP |
|---|---|---|---|---|
| VMnet0 | Bridged to `Ethernet` (Realtek), not automatic | SOC link when the cable is plugged in | n/a | n/a |
| VMnet1 | Host-only | SOC link in solo mode (cable unplugged) | yes, 10.10.10.20 | off |
| VMnet8 | NAT | Internet for OPNsense updates (WAN) | yes | on |
| VMnet10 | Host-only | Targets zone | no | off |
| VMnet11 | Host-only | Attack zone | no | off |

Solo mode and cable mode: the Windows Ethernet adapter loses its address when no cable is plugged in, so the host cannot reach OPNsense through the bridge while working alone. During solo work the first OPNsense adapter sits on VMnet1. For integration with laptop 1 it is switched to VMnet0 and 10.10.10.20 moves from the VMnet1 host adapter to `Ethernet`. Nothing changes inside OPNsense.

## OPNsense adapters (to confirm at step 0.4)

| Order | VMware network | OPNsense role | Address |
|---|---|---|---|
| 1 | VMnet1 (solo) or VMnet0 (cable) | SOC | 10.10.10.254/24 |
| 2 | VMnet8 | WAN | DHCP from VMware NAT |
| 3 | VMnet10 | TARGETS | 10.10.20.1/24 |
| 4 | VMnet11 | ATTACK | 10.10.30.1/24 |

## VM sizing (estimates, to measure)

| VM | RAM | vCPU | Disk | Note |
|---|---|---|---|---|
| OPNsense 26.7 | 3 GB | 2 | 20 GB | Brief said 2 GB; official minimum is 3 GB and the installer needs 3 GB |
| Windows 10 target | 3 GB | 2 | 40 GB | |
| Ubuntu Server target | 1 GB | 1 | 20 GB | |
| Kali, no desktop | 1.5 GB | 2 | 25 GB | |
| Total | 8.5 GB | | 105 GB thin-provisioned | Host keeps about 7 GB for Windows, Ollama and the analysis API |

## Firewall rules (from the brief, to apply at step 0.5)

| Interface | Rule | Action |
|---|---|---|
| All lab interfaces, first | Source or destination in alias `SOC_BLOCKLIST` (filled by Shuffle) | Block |
| ATTACK | To TARGETS net | Pass |
| ATTACK | To SOC net | Block |
| TARGETS | To 10.10.10.10, TCP 1514 and 1515 | Pass |
| TARGETS | Anything else to SOC net | Block |
| SOC | 10.10.10.10 to the firewall, HTTPS (API) | Pass |
| TARGETS, ATTACK | Maintenance: to the internet. Disabled by default, enabled only during installations | Pass |
| TARGETS, ATTACK | Everything else, including internet | Block (default deny) |

Not decided: TARGETS to ATTACK (reverse shells, T-05 with Kali as the "malicious address"). Blocked until a scenario needs it.
