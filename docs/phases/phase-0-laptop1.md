# Phase 0: SOC infrastructure (laptop 1)

Status: laptop 1 side finished on 12 November 2026. Remaining: step 0.7, the cable link with laptop 2, which needs both laptops in the same place.

This file is the journal of phase 0 on laptop 1. Laptop 2's side is in `phase-0-laptop2.md`.

## 1. Objective

Build the machine the SOC tools run on, before any of them is installed:

- one Ubuntu VM without graphical interface, "soc" (10.10.10.10), sized for Wazuh, Shuffle, MISP and DFIR-IRIS in Docker;
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
| 0.4 | soc VM created, `.vmx` checked before first boot | done |
| 0.5 | Ubuntu installed: updates, SSH, address, route, swap, text mode | done |
| 0.6 | Snapshot `phase0-baseline` | done |
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

### Step 0.4: soc VM created (done, 12 November 2026)

Created with the custom wizard and "I will install the operating system later", so that VMware's Easy Install does not install a full desktop with its own choices and does not boot the VM before its hardware is checked.

| Setting | Value | Reason |
|---|---|---|
| Guest OS | Ubuntu 64-bit | |
| vCPU | 1 socket, 4 cores; nested virtualization off | Brief: 4 vCPU; Docker containers do not need VT-x inside the VM |
| Memory | 8192 MB (temporary) | Phase 1 runs only Wazuh (official minimum 4 GB, 6 GB safer); raised for phase 2 from measured use, up to the brief's 11 GB |
| Disk | 85 GB, single file, grows on demand (100 GB was planned) | Wazuh asks 50 GB minimum; MISP, Shuffle and DFIR-IRIS come on top (estimate); can be extended later without reinstalling |
| Adapter 1 | Custom, VMnet12 (solo mode; VMnet0 in cable mode) | SOC link |
| Adapter 2 | NAT | Downloads |
| CD/DVD | Ubuntu Desktop 24.04.4 image | Installation |
| Sound card, printer, 3D acceleration | Removed / off | Unused, costs memory and CPU |

Verification of `soc.vmx` before the first boot (VMware closed):

| Line | Value | What it proves |
|---|---|---|
| `memsize`, `numvcpus`, `cpuid.coresPerSocket` | 8192, 4, 4 | Planned sizing |
| `ethernet0.connectionType`, `ethernet0.vnet` | custom, VMnet12 | First adapter on the SOC link, not on NAT |
| `ethernet1.connectionType` | nat | Second adapter for downloads |
| `ethernetN.virtualDev` | e1000 | Wizard default for Ubuntu, supported by the kernel out of the box; kept |
| `sound.present` | TRUE at first check; removed afterwards | |

### Step 0.5: Ubuntu installation and network (done, 12 November 2026)

#### 0.5a Installation

| Setting | Value | Reason |
|---|---|---|
| Image | Ubuntu Desktop 24.04.4 LTS, interactive installation | Server image not available (see section 2) |
| Applications | Default selection; third-party drivers and media codecs not installed | Fewest packages possible |
| Disk | Erase disk (the VM's virtual disk), no encryption, no ZFS | Simplest layout |
| Computer name / user | `soc` / `soc-admin` | Name from the plan; the password is kept out of the repository |
| Time zone | Africa/Tunis | Correct timestamps in alerts |
| Swap | `/swap.img`, 4 GB, created by the installer | Brief: 4 GB of swap; nothing to add |

#### 0.5b Updates and SSH

`apt full-upgrade` brought the system to Ubuntu 24.04.5 LTS (kernel 7.0.0-43-generic). `openssh-server` installed, so that the VM is administered from the host's terminal. The printing service (`cups`, `cups-browsed`) was disabled: it has no use on the SOC. The upgrade offer to 26.04 is declined: the VM stays on the 24.04 LTS release.

#### 0.5c Address and route on the SOC link

The desktop edition manages the network with NetworkManager, so the SOC link is a dedicated NetworkManager connection, with a higher priority than the automatic one:

```bash
sudo nmcli connection add type ethernet ifname ens33 con-name soc-link \
  ipv4.method manual ipv4.addresses 10.10.10.10/24 \
  ipv4.never-default yes ipv4.ignore-auto-dns yes \
  ipv4.routes "10.10.20.0/24 10.10.10.254" \
  ipv6.method disabled \
  connection.autoconnect yes connection.autoconnect-priority 10
```

| Setting | Value | Reason |
|---|---|---|
| `ens33` (adapter 1, VMnet12) | 10.10.10.10/24, no gateway, never the default route | SOC link; internet must not go through the lab |
| Static route | 10.10.20.0/24 via 10.10.10.254 | Wazuh must answer the agents of the targets zone through the firewall |
| `ens34` (adapter 2, NAT) | DHCP (192.168.136.145), default route | Downloads |
| IPv6 on the SOC link | Disabled | Not used by the plan |

#### 0.5d Text mode

`systemctl set-default multi-user.target`: the graphical session no longer starts at boot. It can still be started by hand with `sudo systemctl start gdm` if ever needed.

#### Verification (12 November 2026)

| Test | Result | What it proves |
|---|---|---|
| `lsb_release`, login banner | Ubuntu 24.04.5 LTS, kernel 7.0.0-43-generic | System up to date |
| `ip -br a` | `ens33` 10.10.10.10/24, `ens34` 192.168.136.145/24 | Addresses as planned |
| `ip route` after reboot | default via 192.168.136.2 dev ens34; 10.10.10.0/24 dev ens33; 10.10.20.0/24 via 10.10.10.254 dev ens33 proto static | Route persistent across reboots; internet stays on NAT |
| `ss -tlnp` | sshd on 0.0.0.0:22 | SSH listening |
| `ssh soc-admin@10.10.10.10` from the host | Login works | The SOC link works end to end between host and VM |
| `ping 10.10.10.1` from the VM | No answer | Expected: the Windows firewall drops inbound ping; SSH proves the link |
| `ping ubuntu.com` from the VM | 3/3 answers | Internet through NAT |
| `systemctl get-default` | multi-user.target | Text mode |
| `free -h` with the graphical session, then in text mode | 1.4 GiB used, then 605 MiB used (7.1 GiB available out of 7.7 GiB) | About 0.8 GiB freed for the SOC tools |
| `swapon --show` | /swap.img, 4 GB | Swap present |
| `lsblk` | sda 85 GB; `/` 84 GB, 70 GB free | Disk space for phase 1 |

The ping to the firewall (10.10.10.254) and to the targets is tested in step 0.7: OPNsense is on laptop 2.

### Step 0.6: snapshot (done, 12 November 2026)

VM shut down cleanly, snapshot `phase0-baseline` taken (powered off, so it holds no memory image). It is the return point if a later installation breaks the VM.

### Step 0.7: cable link with laptop 2 (not started, needs both laptops)

To do on laptop 1 on integration day:

| Action | Check |
|---|---|
| Cable plugged into the Realtek card; host Ethernet card set to 10.10.10.1/24, no gateway; VMnet12 host adapter disabled | `Get-NetIPConfiguration` on Ethernet |
| soc VM adapter 1 moved from VMnet12 to VMnet0 (bridged, Realtek) | Nothing changes inside the VM |
| Pings | Host and soc VM reach 10.10.10.254 and 10.10.10.20; the soc VM reaches 10.10.20.20 through its route |

## 5. Problems met and how they were handled

| Problem | Handling |
|---|---|
| No VMnet0 in the Virtual Network Editor | Created in step 0.2 and bound to the Realtek card |
| VMnet0 disappeared once after applying other changes while set to "Automatic" | Re-created and bound directly to the Realtek card before applying |
| Wizard left the sound card in place | Removed in the VM settings before the first boot |
| Ubuntu Server image could not be downloaded (slow connection) | Ubuntu Desktop 24.04.4 used, graphical interface disabled at boot (deviation from the brief) |
| VMware's Easy Install starts by default when an image is chosen in the wizard | "Install the operating system later", image attached afterwards |
| Disk created at 85 GB instead of 100 GB | Enough for phase 1; to be extended if needed in phase 2 |
| The host does not answer ping from the VM | Windows firewall default; SSH used as the test of the link |

## 6. Résumé pour le rapport

### Ce qui a été réalisé

La phase 0 a préparé, sur le premier ordinateur portable, la machine virtuelle qui héberge les outils du SOC (Wazuh, Shuffle, MISP et DFIR-IRIS, tous déployés avec Docker en phase 1 et 2). Une seule machine virtuelle, nommée « soc », regroupe ces outils : un seul système d'exploitation consomme moins de mémoire que quatre machines séparées, ce qui est déterminant sur un portable de 16 Go.

| Élément | Valeur |
|---|---|
| Hôte | Windows 11 Professionnel, Intel Core i5-13420H, 15,7 Go de mémoire, VMware Workstation 17.6.1 |
| Machine virtuelle | Ubuntu 24.04.5 LTS sans interface graphique, 4 processeurs virtuels, 8 Go de mémoire (provisoire), 4 Go d'espace d'échange, disque de 85 Go |
| Carte 1 : liaison SOC | 10.10.10.10/24, sans passerelle, route statique 10.10.20.0/24 via le pare-feu 10.10.10.254 |
| Carte 2 : NAT | adresse dynamique, route par défaut, réservée aux téléchargements |
| Hôte sur la liaison SOC | 10.10.10.1/24, sans passerelle |

La route statique vers la zone des cibles est indispensable : sans elle, les réponses du serveur Wazuh aux agents des cibles partiraient par la carte NAT et seraient perdues. Aucune route n'est créée vers la zone d'attaque, qui ne doit jamais atteindre le SOC. Le réseau ponté VMnet0 est lié explicitement à la carte Ethernet de l'hôte pour l'intégration par câble ; en attendant, la liaison SOC passe par un réseau virtuel interne (VMnet12), comme sur le second portable.

### Ce qui a été vérifié

L'adresse et la route statique sont présentes et persistent après redémarrage, la route par défaut reste sur la carte NAT, et la machine accède à Internet pour ses mises à jour. L'administration se fait en SSH depuis l'hôte à travers la liaison SOC, ce qui valide cette liaison de bout en bout. Le passage en mode texte a réduit la mémoire utilisée au repos de 1,4 Gio à 605 Mio. Un instantané de référence (`phase0-baseline`) a été pris.

### Difficultés rencontrées

Le réseau ponté VMnet0 était absent de la configuration de VMware et a dû être recréé puis lié explicitement à la carte Ethernet. L'assistant de création de VMware lance par défaut une installation automatique (Easy Install) qui impose ses propres choix ; l'installation a donc été faite manuellement. La mémoire disponible sur l'hôte est limitée : les autres applications doivent être fermées lorsque la machine virtuelle fonctionne.

### Écarts par rapport à la conception

- Ubuntu Desktop au lieu d'Ubuntu Server, faute de pouvoir télécharger l'image serveur : installation minimale, interface graphique désactivée au démarrage, service d'impression désactivé. Le résultat est équivalent à un serveur pour l'usage du SOC.
- 8 Go de mémoire au lieu de 11 Go pendant la phase 1, où seul Wazuh fonctionne ; la valeur définitive sera fixée en phase 2 à partir des mesures réelles.
- Disque de 85 Go au lieu des 100 Go prévus, suffisant pour la phase 1.
- Liaison SOC provisoire par un réseau virtuel interne (VMnet12) tant que l'équipe travaille à distance.

### Ce qui reste

- Étape 0.7 : liaison par câble avec le second portable et tests vers le pare-feu et la zone des cibles.
