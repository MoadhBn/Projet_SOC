# Phase 1: detection base (laptop 1)

Status: started 12 November 2026. Laptop 1 side done on 13 November 2026 (steps 1.1 to 1.6). Remaining: enrolment of the agents and first use cases with laptop 2 (joint session).

This file is the journal of phase 1 on laptop 1. Laptop 2's side (Suricata, Sysmon, DVWA, agents) is in `phase-1-laptop2.md`.

## 1. Objective

Run the Wazuh manager, indexer and dashboard 4.14.9 on the soc VM (10.10.10.10), ready to receive the agents already installed on laptop 2:

- the Windows target and the Linux target (agents 4.14.9);
- the OPNsense firewall (agent 4.14.8 from the `os-wazuh-agent` plugin), which also forwards Suricata alerts.

Phase 1 is finished when the three agents are active in the dashboard and the first use cases (UC-01 SSH brute force, UC-02 encoded PowerShell, UC-04 port scan) raise alerts with their ATT&CK technique. This last part needs both laptops.

## 2. Why it is built this way

### Docker and the official single-node deployment

Wazuh publishes a Docker deployment (`wazuh/wazuh-docker`) with one manager, one indexer and one dashboard container. It is the lightest way to run the three components on one VM, and the whole deployment is described by files that can be versioned (BNF-08). Version 4.14.9 is pinned (git tag and image tags): a Wazuh agent must never be newer than its manager, and the targets already run 4.14.9.

### Passwords out of the Compose file

The official procedure writes the new passwords in clear in `docker-compose.yml`. Here the Compose file only names variables (`${INDEXER_PASSWORD}`, `${DASHBOARD_PASSWORD}`, `${API_PASSWORD}`) and Docker Compose reads their values from a `.env` file next to it, which `.gitignore` excludes. Wazuh receives exactly the same values, and the Compose file can be versioned (BNF-02 protected secrets, BNF-08 reproducibility).

### Docker from Docker's own repository

Docker's documentation recommends its `apt` repository over the convenience script (testing only) and over Ubuntu's unofficial `docker.io` package. The repository provides the `docker compose` plugin that `wazuh-docker` uses. The user is not added to the `docker` group, which is equivalent to root access; Docker commands are run with `sudo`.

## 3. Plan

| Step | Content | Status |
|---|---|---|
| 1.1 | Docker Engine and Docker Compose plugin | done |
| 1.2 | `vm.max_map_count` at least 262144, persistent | done (already set by Ubuntu) |
| 1.3 | `wazuh-docker` v4.14.9: certificates, ports | done |
| 1.4 | First start, first login to the dashboard, memory measurement | done |
| 1.5 | Default passwords changed, kept out of the Compose file | done |
| 1.6 | Compose file without secrets in `infra/laptop1-soc/wazuh/` | done |
| Joint | Agents enrolled (targets, OPNsense with Suricata events); use cases UC-01, UC-02, UC-04 | to do |

## 4. Steps

### Step 1.1: Docker Engine (done, 12 November 2026)

Source: Docker's installation page for Ubuntu, read from its source in the `docker/docs` repository (12 November 2026), since docs.docker.com was not reachable from the assistant's network. It lists Ubuntu 24.04 (Noble) as supported.

| Action | Detail | Reason |
|---|---|---|
| Conflicting packages | Official removal command; none were installed | Unofficial packages conflict with Docker's |
| Signing key | `/etc/apt/keyrings/docker.asc` from download.docker.com | apt checks that packages come from Docker |
| Repository | `/etc/apt/sources.list.d/docker.sources`, suite `noble`, `stable`, amd64 | Official repository for this release |
| Packages | `docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin` | Engine and the Compose plugin |

Verification:

| Test | Result | What it proves |
|---|---|---|
| `apt update` | Docker repository read, no signature error | Repository and key are valid |
| `systemctl is-active docker`, `is-enabled docker` | active, enabled | Docker runs and starts at boot (BNF-06) |
| `docker version` | Engine 29.9.3 (API 1.56), containerd 2.4.2, runc 1.5.3 | Wazuh asks for Docker Engine 20.10 or newer |
| `docker compose version` | v5.7.1 | Compose plugin present |
| `docker run hello-world` | "Hello from Docker!" | Images are pulled from Docker Hub through NAT and containers run |
| `free -h` | 769 MiB used, 7.0 GiB available (605 MiB before Docker) | Docker itself costs little memory |

### Step 1.2: `vm.max_map_count` (done, 12 November 2026)

The indexer (OpenSearch) maps its index files in memory and refuses to start if the kernel allows fewer than 262144 memory map areas. The setting belongs to the VM's kernel, which the containers share.

| Test | Result | What it proves |
|---|---|---|
| `sysctl vm.max_map_count` before any change | 1048576, set by Ubuntu in `/etc/sysctl.d/10-map-count.conf` | The requirement (at least 262144) is already met and persistent |

A drop-in file setting 262144 was first added, as the Wazuh documentation suggests, then removed: it lowered Ubuntu's higher value for no benefit. No setting is added for Wazuh.

### Step 1.3: `wazuh-docker` v4.14.9 and certificates (done, 12 November 2026)

| Action | Detail | Reason |
|---|---|---|
| Repository | `git clone https://github.com/wazuh/wazuh-docker.git -b v4.14.9 --depth 1` in the home directory of `soc-admin` | Pinned to the release; images `wazuh/wazuh-manager`, `wazuh-indexer`, `wazuh-dashboard`, all `4.14.9` |
| Indexer heap | `-Xms1g -Xmx1g`, already in the official file | Brief: 1 GB heap |
| Ports (official defaults, kept) | 1514, 1515 (agents), 55000 (Wazuh API), 9200 (indexer), 443 (dashboard) | 443 stays with Wazuh; MISP and DFIR-IRIS get other ports in phase 2. 9200 stays reachable because the analysis API on laptop 2 reads events from the indexer |
| Certificates | `docker compose -f generate-indexer-certs.yml run --rm generator` (image `wazuh/wazuh-certs-generator:0.0.4`, tool 4.14) | TLS between manager, indexer and dashboard, with a certificate authority of the lab |

Verification:

| Test | Result | What it proves |
|---|---|---|
| `git describe --tags` | v4.14.9 | Right release |
| `grep image: docker-compose.yml` | three images tagged 4.14.9 | Manager not newer than the agents (4.14.9 and 4.14.8) |
| `sudo ls -l config/wazuh_indexer_ssl_certs/` | root CA, admin, indexer, manager, dashboard certificates and keys, all mode 400; manager files owned by UID 999, the others by UID 1000 | Every file mounted by the Compose file exists, with the owners the containers expect |
| `openssl x509` on the manager certificate | CN = wazuh.manager, valid until 9 November 2036 | Certificate readable and valid |

Notes:

- The certificate folder is not readable by `soc-admin` without `sudo` (mode 500): it holds private keys. These files never go into the repository (`*.pem` and `*.key` are in `.gitignore`).
- On the VM, UID 1000 is displayed as `soc-admin` and UID 999 as `dnsmasq`: only the numeric IDs matter, they match the users inside the containers.
- The generator printed `find: command not found` (line 641 of `wazuh-certs-tool.sh`, downloaded at run time). Every certificate was created and installed, so the message had no effect on the result; the line itself could not be checked (packages.wazuh.com not reachable from the assistant's network).

### Step 1.4: first start and memory measurement (done, 12 to 13 November 2026)

The three images (compressed sizes from Docker Hub: indexer 1.1 GB, manager 1.0 GB, dashboard 507 MB; 7.5 GB once extracted) were pulled over a slow and unstable connection. The pull was finally run as a transient system service, so that it survived SSH disconnections and retried after network errors:

```bash
sudo systemd-run --unit=wazuh-pull --working-directory=/home/soc-admin/wazuh-docker/single-node /bin/sh -c 'until docker compose pull; do echo "ECHEC, nouvel essai dans 10 s"; sleep 10; done; echo "TELECHARGEMENT TERMINE"'
```

Then `sudo docker compose up -d`. The first start runs with the default passwords on purpose: the official password procedure needs the indexer image and a running stack. The VM is only reachable from laptop 1's host at this point.

| Test | Result | What it proves |
|---|---|---|
| `docker compose ps` | manager, indexer and dashboard `Up`, no restart | The stack runs on Docker 29.9.3 / Compose v5.7.1 |
| `curl -k https://localhost:9200` (authenticated) | `wazuh-cluster`, OpenSearch 2.19.6 underneath | Indexer up |
| Dashboard `https://10.10.10.10` from the host | Overview page, no agent; alerts from the manager itself (agent 000) | Dashboard, indexer and API work together; reachable over the SOC link |

Memory, no agent connected (`docker stats`, `free -h`):

| Container | At 43 s | Stabilised (about 15 min) |
|---|---|---|
| Indexer (heap 1 GB) | 1.36 GiB | 1.42 GiB |
| Manager | 531 MiB (CPU 113 %, first initialisation) | 562 MiB (CPU 14 %) |
| Dashboard | 182 MiB | 197 MiB |
| Total Wazuh | about 2.1 GiB | **about 2.2 GiB** |
| Whole VM (8 GB) | 2.7 GiB used | 2.8 GiB used, 5.0 GiB available, swap unused |

The brief estimated 3.5 GB for Wazuh. This first measurement is lower but has no agent and almost no events; it is repeated with the three agents and the use cases. Disk after the deployment: 18 GB used, 61 GB free.

### Step 1.5: default passwords changed (done, 13 November 2026)

Source: "Changing the default password of Wazuh users", Wazuh documentation 4.14, read from its source (`wazuh/wazuh-documentation`, branch 4.14, 11 November 2026) because documentation.wazuh.com was not reachable from the assistant's network.

| Account | System | Where the password lives |
|---|---|---|
| `admin` | Indexer; dashboard login | `.env` (`INDEXER_PASSWORD`), hash in `internal_users.yml` |
| `kibanaserver` | Indexer; dashboard to indexer | `.env` (`DASHBOARD_PASSWORD`), hash in `internal_users.yml` |
| `wazuh-wui` | Wazuh server API; dashboard to manager | `.env` (`API_PASSWORD`), `config/wazuh_dashboard/wazuh.yml` |

Procedure, following the documentation (one indexer user at a time, so two passes: `admin`, then `kibanaserver` with `wazuh-wui`):

1. Log out of the dashboard; keep copies of the original files (`*.orig`, on the VM only).
2. Replace the three passwords in `docker-compose.yml` by variables (`sed`), values in `.env` (mode 600).
3. `docker compose down`; generate the hash with `hash.sh` from the `wazuh/wazuh-indexer:4.14.9` image; put it in `config/wazuh_indexer/internal_users.yml`; for `wazuh-wui`, set the password in `config/wazuh_dashboard/wazuh.yml`.
4. `docker compose up -d`; once the indexer answers, apply the security configuration with `securityadmin.sh` (admin certificate, `-icl -nhnv`).

Verification (13 November 2026), only HTTP status codes are shown:

| Test | Result | What it proves |
|---|---|---|
| `securityadmin.sh`, both passes | 10 of 10 configuration types updated, cluster GREEN, `Done with success` | New users loaded in the indexer |
| `admin` on port 9200, old / new password | 401 / 200 | Default `admin` password refused |
| `kibanaserver` on port 9200, old / new | 401 / 200 | Default `kibanaserver` password refused |
| `wazuh-wui` on `/security/user/authenticate` (port 55000), old / new | 401 / 200 | Default API password refused |
| `grep -c` of the old API password in `wazuh.yml` | 0 | Dashboard configuration updated |
| `diff` of `internal_users.yml` with the original | 2 lines changed (`admin`, `kibanaserver`) | No other user touched |
| Dashboard login with the new `admin` password | Overview page, no API error | Dashboard reaches the indexer (`kibanaserver`) and the API (`wazuh-wui`) |

### Step 1.6: configuration in the repository (done, 13 November 2026)

`infra/laptop1-soc/wazuh/`:

| File | Content |
|---|---|
| `docker-compose.yml` | Official file of tag v4.14.9 with the passwords replaced by variables; same SHA-256 as the file running on the VM (`8472c14f…9eea41`) |
| `.env.example` | The three variables with placeholders and the password rules |
| `README.md` | Files kept on the VM only, rebuild procedure, published ports |

Kept on the VM only: `.env`, `internal_users.yml` (hashes), `wazuh.yml` (API password), certificates and private keys.

## 5. Problems met and how they were handled

| Problem | Handling |
|---|---|
| docs.docker.com not reachable from the assistant's network | Same page read from the official `docker/docs` source repository |
| `vm.max_map_count` lowered from Ubuntu's 1048576 to 262144 by an unneeded setting | Setting removed; Ubuntu's default already meets the requirement |
| `ls` on the certificate folder refused | Expected: folder restricted to root by the generator; listed with `sudo` |
| Image pull slow (0.35 to 1.8 MB/s) and cut by the registry (`connection reset by peer`) | Pull retried in a loop |
| SSH sessions dropped, which killed the pull running in them | Pull run as a transient systemd service (`systemd-run`), independent of SSH; SSH with `ServerAliveInterval=30` |
| `securityadmin.sh`: "no OpenSearch running on localhost:9200" | Run too early after the start; run again once port 9200 answers 401 |
| Hash generated from the wrong password during pass 2 | Generated again before it was applied; nothing was loaded in between |

## 6. Résumé pour le rapport

À rédiger à la clôture de la phase.
