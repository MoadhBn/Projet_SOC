# Phase 2: enrichment and orchestration (laptop 1)

Status: started 13 November 2026. Steps 2.0 to 2.3 done. Remaining: DFIR-IRIS (2.4), first playbook from alert to incident (2.5), MISP with test indicators (2.6).

This file is the journal of phase 2 on laptop 1.

## 1. Objective

Add to the soc VM the tools that turn a Wazuh alert into a handled incident:

- Shuffle (SOAR), which runs the playbook for every alert (exchange 4 of the architecture: Wazuh to Shuffle);
- DFIR-IRIS, where incidents are created (exchange 7);
- MISP, where indicators are looked up (exchange 5), with hand-added test indicators because lab addresses appear in no public feed.

Phase 2 is finished when an alert raised by Wazuh reaches Shuffle, is enriched with MISP and becomes a case in DFIR-IRIS without any human action.

## 2. Why it is built this way

### Order of the tools

The brief lists MISP, Shuffle, DFIR-IRIS. Shuffle is installed first (team decision, 13 November 2026): it is the centre of the pipeline, the riskiest part (open point of the brief on the Wazuh integration, its own OpenSearch database), and it can be tested without laptop 2 because the Wazuh manager raises alerts about itself. Shuffle then DFIR-IRIS gives the first visible result (alert to incident); MISP comes last because it only enriches and is the heaviest download.

### One VM, measured tool by tool

All tools share the soc VM. Each tool is started on its own and its memory is measured before the next one is added, so that the memory limit of laptop 1 is known from measurements and not from the brief's estimates.

### Shuffle's two halves

The backend receives webhooks and stores workflows; Orborus runs them by starting a worker container, which starts one container per app action (here the Shuffle Tools app). Orborus needs access to the Docker socket of the VM for that.

## 3. Plan

| Step | Content | Status |
|---|---|---|
| 2.0 | Memory of the soc VM sized for phase 2 | done (10 GB, see step) |
| 2.1 | Shuffle 2.3.0: configuration and images | done |
| 2.2 | Shuffle started, administrator account, memory measured | done |
| 2.3 | Wazuh to Shuffle integration (open point of the brief) | done |
| 2.4 | DFIR-IRIS | to do |
| 2.5 | First playbook: Wazuh alert to DFIR-IRIS case | to do |
| 2.6 | MISP with test indicators, lookup in the playbook | to do |

## 4. Steps

### Step 2.0: memory of the soc VM (done, 13 November 2026)

The VM went from 8 GB (phase 1) to the brief's 11 GB, then down to 10 GB after measurement.

| Situation (Windows host, `AvailableMBytes`) | Available on the host |
|---|---|
| VM powered off | 11 289 MB (Windows and usual applications use about 4.4 GB) |
| VM at 11 GB, after the Shuffle images were pulled and extracted | **126 MB** |
| VM at 10 GB, just started with Wazuh | 5 982 MB |
| VM at 10 GB, Wazuh and Shuffle running | 2 622 MB |

Explanation: Linux uses all free memory of the VM as disk cache (5.7 GiB of cache after the image extraction, for 2.8 GiB really used), and VMware has to back every page the guest has touched with host memory. At 11 GB the host had no margin left. At 10 GB the expected margin, once the guest cache is full again, is about 0.8 to 1 GB (estimate: 15.7 GB minus 4.4 GB for Windows, 10 GB for the VM and VMware's own overhead). VMware's setting "Allow some virtual machine memory to be swapped" (default) is kept: Windows can page out the least used guest pages, mostly cache.

Deviation from the brief: 10 GB instead of 11 GB, from measurements. Whether MISP and DFIR-IRIS also fit is measured in steps 2.4 and 2.6.

### Step 2.1: Shuffle configuration and images (done, 13 November 2026)

Source: repository `Shuffle/Shuffle`, tag `v2.3.0` (latest stable; 2.3.1 is a release candidate), its `.github/install-guide.md`, and the source of Orborus (`Shuffle/orborus`, tag `v2.3.0`). Images `2.3.0` checked on ghcr.io.

`git clone https://github.com/Shuffle/Shuffle.git -b v2.3.0 --depth 1 shuffle` in the home directory of `soc-admin`, then:

| Change | Reason |
|---|---|
| OpenSearch port `127.0.0.1:9201` instead of `9200` | Port 9200 is the Wazuh indexer's |
| OpenSearch heap 1 GB instead of 3 GB | Memory budget |
| Images pinned to `2.3.0` | Pinned versions |
| `shuffle-security` service removed | Undocumented, `latest` only, not needed for the interface |
| `.env`: `TZ=Africa/Tunis`, random `SHUFFLE_ENCRYPTION_MODIFIER` (generated on the VM, never displayed), new OpenSearch password, file mode 600 | Correct timestamps, encryption of stored credentials, default password is public |
| `sudo chown -R 1000:1000 shuffle-database` | Required by the installation guide |
| Swap kept | The guide suggests `swapoff -a`; the brief requires swap and the official file locks OpenSearch memory |

Images pulled as a transient systemd service with retries (`systemd-run --unit=shuffle-pull`, same method as for Wazuh), including the worker image that Orborus starts at the first execution. Pull time: 14 minutes, no failure.

| Image | Compressed | On disk |
|---|---|---|
| shuffle-backend 2.3.0 | 57 MB | 198 MB |
| shuffle-frontend 2.3.0 | 83 MB | 286 MB |
| shuffle-orborus 2.3.0 | 48 MB | 169 MB |
| shuffle-worker 2.3.0 | 49 MB | 173 MB |
| opensearch 3.2.0 | 1.01 GB | 2.48 GB |

### Step 2.2: Shuffle started (done, 13 November 2026)

`sudo docker compose up -d`, then the administrator account `soc-admin` created at once on `https://10.10.10.10:3443` (Shuffle has no default account; the first visitor creates it).

Problem met: the runtime location showed "Stopped" and no action could run. Orborus logs: `Swarm init failed ... could not be uniquely identified` (the VM has several addresses) and a pull of `tenzir/tenzir:main` had started. The source of Orborus shows a default run mode without Swarm (header `X-Orborus-Runmode: Default`) and that pipelines (Tenzir) are enabled unless `SHUFFLE_SKIP_PIPELINES=true`. Fix: in `docker-compose.yml`, `SHUFFLE_SWARM_CONFIG=run` replaced by `SHUFFLE_SKIP_PIPELINES=true`, then `docker compose up -d` (only Orborus recreated). No Tenzir image was left on disk.

| Test | Result | What it proves |
|---|---|---|
| `docker compose ps` | frontend, backend, orborus, opensearch `Up` | Shuffle runs next to Wazuh, no port conflict |
| Backend log | One `connection refused` while OpenSearch started, then `Initialized Shuffle database connection`, organisation `default` created | Backend and database work; the backend retries by itself |
| Orborus log after the fix | `Setting swarm config to ""`, no swarm error, no Tenzir pull | Default mode |
| Runtime location in the interface | Running | Orborus connected to the backend |
| `curl` POST of a test JSON to `http://10.10.10.10:5001/api/v1/hooks/webhook_<id>` | Execution created; node "Change Me" (Shuffle Tools, repeat back to me, `$exec`) returned the JSON sent | Webhook, backend, Orborus, worker and app all work |

Memory with Wazuh and Shuffle (`docker stats`, `free -h`):

| Container | Memory |
|---|---|
| shuffle-opensearch | 1.88 GiB |
| shuffle-backend | 211 MiB |
| shuffle-orborus | 89 MiB |
| shuffle-frontend | 18 MiB |
| **Shuffle total** | **about 2.2 GiB** (brief estimate: 2.5 GB) |
| Wazuh (indexer 1.49 GiB, manager 509 MiB, dashboard 280 MiB) | about 2.3 GiB |
| Whole VM (10 GB) | 4.7 GiB used, 5.0 GiB available, swap unused |

### Step 2.3: Wazuh to Shuffle integration (done, 13 November 2026)

Source: "External API integration", section Shuffle, Wazuh documentation 4.14 (`wazuh/wazuh-documentation`, branch 4.14). This answers the open point of the brief: Wazuh has a built-in `shuffle` integration (Integrator module) that posts each alert, in JSON, to a Shuffle webhook.

Workflow `Wazuh-Alerts` in Shuffle: webhook trigger "Wazuh alerts" (started), then "Change Me" (Shuffle Tools, repeat back to me, `$exec`), as in the documentation.

Block added after the first `<ossec_config>` line of `config/wazuh_cluster/wazuh_manager.conf` (original kept as `.orig` on the VM; the webhook ID is not recorded here):

| Setting | Value | Reason |
|---|---|---|
| `name` | shuffle | Built-in integration |
| `hook_url` | `http://10.10.10.10:5001/api/v1/hooks/webhook_<id>` | Shuffle backend; traffic stays inside the VM. The interface shows the URL on 3443 (HTTPS with a self-signed certificate) |
| `level` | 3 | Provisional, the documentation's example: the manager's own alerts are enough to test. Final threshold set with the use cases |
| `alert_format` | json | Required for Shuffle |

Problem met: after `docker compose restart wazuh.manager`, `wazuh-integratord` was not running and logged `Remote integrations not configured. Clean exit.` The mounted file contained the block, but `/var/ossec/etc/ossec.conf` in the container did not. After `sudo docker compose up -d --force-recreate wazuh.manager`, the start log shows `'/wazuh-config-mount/etc/ossec.conf' -> '/var/ossec/etc/ossec.conf'`. Rule kept: apply manager configuration changes by recreating the container (data stays in the volumes).

| Test | Result | What it proves |
|---|---|---|
| `grep -c "<name>shuffle</name>" /var/ossec/etc/ossec.conf` in the container | 1 | Configuration applied |
| `wazuh-control status` | `wazuh-integratord is running` | Integrator started |
| `ossec.log` | `Enabling integration for: 'shuffle'` | Integration loaded |
| Shuffle execution 13/11/2026 10:12:52 | Alert rule 502 "Wazuh server started.", level 3, from the manager | A real Wazuh alert reached Shuffle and ran the workflow |

Format received by Shuffle (built by `/var/ossec/integrations/shuffle.py`): `severity` (1 to 3), `pretext`, `title`, `text`, `rule_id`, `timestamp`, `id`, and the full alert under `all_fields` (`rule.level`, `rule.mitre`, `agent`, `data`...). The playbook reads `$exec.all_fields...`.

Note: `wazuh-modulesd:vulnerability-scanner` and `content-updater` log errors since a start where the container could not resolve Wazuh's content server (DNS not ready). Vulnerability detection is not part of the use cases; to check later.

## 5. Problems met and how they were handled

| Problem | Handling |
|---|---|
| Host memory exhausted (126 MB available) with the VM at 11 GB | VM reduced to 10 GB; tools measured one by one |
| Shuffle's OpenSearch publishes port 9200, already used by Wazuh | Published on `127.0.0.1:9201` |
| Shuffle runtime "Stopped": Orborus swarm init failed on a VM with several addresses | Swarm mode disabled, Orborus in its default mode |
| Orborus pulled `tenzir/tenzir:main` (pipelines, not in the design) | `SHUFFLE_SKIP_PIPELINES=true` |
| "Test action" refused: no previous execution | First execution created by posting a test JSON to the webhook |
| `docker compose restart` did not apply the new manager configuration | `docker compose up -d --force-recreate wazuh.manager` |

## 6. Résumé pour le rapport

À rédiger à la clôture de la phase.
