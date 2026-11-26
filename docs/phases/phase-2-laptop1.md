# Phase 2: enrichment and orchestration (laptop 1)

Status: started 13 November 2026. Steps 2.0 to 2.5 done: a Wazuh alert becomes an IRIS alert without human action. Step 2.6 done on 26 November: MISP installed and measured, test indicators, read-only API key, and every Wazuh alert is looked up in MISP before reaching IRIS. Remaining: playbook export (2.7).

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

### DFIR-IRIS rather than TheHive

The supervisor suggested TheHive instead of DFIR-IRIS. Comparison made on 13 November 2026 from the official repositories:

| Criterion | DFIR-IRIS 2.4.29 | TheHive 6.0 |
|---|---|---|
| Components | 5 light containers: Python application, worker, PostgreSQL, RabbitMQ, nginx | Cassandra, Elasticsearch and TheHive (three Java programs) plus nginx |
| Memory | Measured on the soc VM: about 1.0 GiB | StrangeBee's own "testing" stack (not for production) limits Cassandra, Elasticsearch and TheHive to 2 GB each: about 4 to 6 GB |
| Licence | LGPL v3, open source | Distributed by StrangeBee since version 5 with a free community licence (not open source, as far as known; not re-checked); the last open source version, 4.1.24, is no longer maintained |
| Brief | Planned | Would need a justified deviation (BNF-09 open source) |

With Wazuh and Shuffle already at about 4.5 GiB in a 10 GB VM, TheHive would leave no room for MISP. DFIR-IRIS is kept; TheHive is the documented fallback (with MISP then started only for the tests that need it). The playbook isolates the incident tool in one node, so a change would only touch that node.

### IRIS alerts first, cases later

IRIS separates alerts (events coming from other tools, grouped by similarity) from cases (incidents handled by the analyst, created by escalating alerts). Every Wazuh alert kept by the playbook becomes an IRIS alert; escalation to a case will follow the score of phase 3 (medium and high only), as in the decision rule of the brief.

### Shuffle's two halves

The backend receives webhooks and stores workflows; Orborus runs them by starting a worker container, which starts one container per app action (here the Shuffle Tools app). Orborus needs access to the Docker socket of the VM for that.

## 3. Plan

| Step | Content | Status |
|---|---|---|
| 2.0 | Memory of the soc VM sized for phase 2 | done (10 GB, see step) |
| 2.1 | Shuffle 2.3.0: configuration and images | done |
| 2.2 | Shuffle started, administrator account, memory measured | done |
| 2.3 | Wazuh to Shuffle integration (open point of the brief) | done |
| 2.4 | DFIR-IRIS | done |
| 2.5 | First playbook: Wazuh alert to DFIR-IRIS alert | done |
| 2.6 | MISP with test indicators, lookup in the playbook | done |
| 2.7 | Playbook exported to `shuffle/` without secrets | to do |

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

### Step 2.4: DFIR-IRIS (done, 13 November 2026)

Source: repository `dfir-iris/iris-web`, tag `v2.4.29` (latest stable), README and `.env.model`.

`git clone https://github.com/dfir-iris/iris-web.git -b v2.4.29 --depth 1 iris` in the home directory, then, before the first start:

| Setting | Value | Reason |
|---|---|---|
| `.env` | Copy of `.env.model`, mode 600 | Configuration of the five services |
| `POSTGRES_PASSWORD`, `POSTGRES_ADMIN_PASSWORD`, `IRIS_SECRET_KEY`, `IRIS_SECURITY_PASSWORD_SALT` | 48 random hexadecimal characters each, generated on the VM, never displayed | Default values are public |
| `INTERFACE_HTTPS_PORT` | 8443 | 443 is the Wazuh dashboard's |
| Certificate | Own self-signed certificate, CN and IP 10.10.10.10, 825 days; key owned by UID 33 (`www-data`, the nginx user of the image), mode 400 | The repository ships a development certificate with its private key |
| `IRIS_ADM_PASSWORD` | Set by the administrator | The generated one is printed only once in the logs |
| RabbitMQ image | `3.13-management-alpine` | Pinned version |

Images pulled with `systemd-run --unit=iris-pull` (11 minutes, no failure): app 558 MB compressed / 2.24 GB on disk, db 106 MB / 381 MB, nginx 109 MB / 417 MB, rabbitmq 88 MB / 277 MB.

| Test | Result | What it proves |
|---|---|---|
| `grep` checks of `.env` | 0 default secret left; 4 random secrets; port 8443; own certificate names; administrator password set | Configuration as intended before the first start |
| `openssl x509` on the certificate | CN = 10.10.10.10, SAN IP 10.10.10.10 | Certificate matches the address used |
| `docker compose config --quiet` | No output | Files valid |
| `docker compose ps` | rabbitmq, db, app, worker `Up`; nginx `Up (healthy)` | nginx reads our certificate; the stack runs |
| `curl https://10.10.10.10:8443/login` | 200 | Web interface reachable |
| Application log | One warning at first start ("Analysts group integrity error ... Updating"), no error | First initialisation completed |
| Login as `administrator` | Dashboard, IRIS v2.4.29 | Administrator password from `.env` works |
| `docker ps` | 12 containers `Up` (Wazuh 3, Shuffle 4, IRIS 5) | The three tools run together |

Memory with the three tools (`docker stats`, `free -h`):

| Tool | Measured | Brief estimate |
|---|---|---|
| DFIR-IRIS (worker 490 MiB, app 258 MiB, RabbitMQ 147 MiB, PostgreSQL 73 MiB, nginx 20 MiB) | about 1.0 GiB | 1.5 GB |
| Shuffle | about 2.0 GiB | 2.5 GB |
| Wazuh | about 1.6 to 1.8 GiB | 3.5 GB |
| Whole VM (10 GB) | 5.3 GiB used, 4.4 GiB available, swap 497 to 717 MiB | |
| Windows host | 338 to 876 MB available depending on the applications open | |

Once the VM has touched its 10 GB, starting more containers inside it costs the host nothing more: the guest gives up part of its cache. The indicator to watch is the swap of the VM; on the host, closing applications is the only lever.

#### Wazuh vulnerability detection disabled

With no agent connected, `docker stats` showed the Wazuh manager at 1.31 GB received and 71 GB read / 89 GB written on disk: the vulnerability detection module downloads its feed every hour (about 1 GB) and rebuilds its database, and it had logged errors since a start where DNS was not ready. It is not used by the use cases. Following the Wazuh 4.14 documentation ("Vulnerability detection, Configuration"), `<enabled>no</enabled>` was set in the `<vulnerability-detection>` block of `wazuh_manager.conf`, applied with `docker compose up -d --force-recreate wazuh.manager`.

| Test | Result |
|---|---|
| `ossec.log` | `Vulnerability scanner module is disabled.` |
| `wazuh-control status` | `wazuh-integratord` and `wazuh-modulesd` running |
| `docker stats` a few minutes later | Manager at 0.9 % CPU, 109 kB received, 194 MB read / 19 MB written; VM swap from 717 to 497 MiB |

### Step 2.5: first playbook, Wazuh alert to IRIS alert (done, 13 November 2026)

API of IRIS 2.4.29 read in its source (`source/app/blueprints/alerts/alerts_routes.py`, `models/alerts.py`): `POST /alerts/add` with header `Authorization: Bearer <API key>`; required fields `alert_title`, `alert_severity_id`, `alert_status_id`, `alert_customer_id`.

The administrator's API key (My settings) was kept in a shell variable (`read -s`), never displayed. Identifiers read from the instance rather than assumed, because they are not in creation order:

| List | Values |
|---|---|
| `/manage/severities/list` | Medium 1, Unspecified 2, Informational 3, Low 4, High 5, Critical 6 |
| `/manage/alert-status/list` | New 2 (and Unspecified 1, Assigned 3, In progress 4, Pending 5, Closed 6, Merged 7, Escalated 8) |
| `/manage/customers/list` | IrisInitialClient 1 |

Manual test with `curl` (alert "Test alert from soc VM", severity 4, status 2, customer 1): `status: success`, `alert_id` 1, visible in IRIS with source Wazuh, tags `wazuh`, `test`.

Workflow `Wazuh-Alerts` in Shuffle: webhook "Wazuh alerts", then "Change Me" (repeat back to me), then a new node "Create IRIS alert" (Http app, action POST):

| Field | Value | Reason |
|---|---|---|
| URL | `https://10.10.10.10:8443/alerts/add` | IRIS API |
| Headers | `Content-Type: application/json`, `Authorization: Bearer <key>` | The key is stored in the workflow: it must be removed from any export |
| Verify | false | Self-signed certificate |
| `alert_title` | `$exec.title` | Rule description |
| `alert_description` | `Wazuh rule $exec.rule_id: $exec.title` | Short description |
| `alert_source` / `alert_source_ref` | `Wazuh` / `$exec.id` | Link back to the Wazuh alert |
| `alert_severity_id` | 2 (Unspecified) | Severity comes from the score of phase 3; none is invented here |
| `alert_status_id` / `alert_customer_id` | 2 (New) / 1 | |
| `alert_tags` | `wazuh,rule-$exec.rule_id` | Filtering by rule |
| `alert_source_content` | `$exec.all_fields` (JSON object, not quoted) | Full Wazuh alert kept in IRIS |

The `text` field sent by Wazuh is not used: it can carry raw log text with quotes, which would break the JSON (logs are untrusted input).

| Test | Result | What it proves |
|---|---|---|
| Manager restarted (alert rule 502), Shuffle execution | "Change Me" success; "Create IRIS alert" HTTP 200, IRIS `status: success`, `success: true` | Shuffle calls the IRIS API |
| IRIS, Alerts | Alert 2 "Wazuh server started.", description "Wazuh rule 502: Wazuh server started.", source Wazuh, reference `1794566655.1457`, severity Unspecified, status New, tags `wazuh`, `rule-502`; raw alert with `rule.level`, `groups`, `pci_dss`, `gdpr` | Exchanges 4 and 7 of the architecture work end to end, with no human action |

Known limit: IRIS shows as "Source Event Time" its own creation time, not the Wazuh timestamp (seconds apart); to set when the playbook is extended.

### Step 2.6: MISP (done, 25 and 26 November 2026)

#### Disk check before the installation

`docker system df`: images 17.7 GB (40, of which 23 are Shuffle app images started at each execution: kept), 62 containers (50 stopped leftovers of Shuffle executions, 54 MB), volumes 11.75 GB. Almost all of the volumes is `single-node_wazuh_queue` (12 GB), and 11 GB of it is `queue/vd`, plus 484 MB in `queue/vd_updater`: the database of the vulnerability detection module disabled in step 2.4. Disk: 40 GB used, 40 GB free, enough for MISP. Removing `vd` is not described in the Wazuh documentation; it is left for a separate maintenance step, not mixed with an installation.

#### 2.6a Configuration

Source: repository `MISP/misp-docker`, commit `88e90bf` (19 November 2026; the repository has no tags), README and `template.env`. Image tags `v2.5.52` (core, nginx) and `v3.1.5` (modules) checked on ghcr.io.

| Setting | Value | Reason |
|---|---|---|
| Running tags | core and nginx `v2.5.52`, modules `v3.1.5` | Default is `latest` |
| Ports | 9080 / 9443, `BASE_URL=https://10.10.10.10:9443` | 443 is the Wazuh dashboard's; `BASE_URL` is mandatory |
| MariaDB `INNODB_BUFFER_POOL_SIZE` | 256M instead of 2048M | Memory budget |
| Secrets | `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `REDIS_PASSWORD` (48 hex characters), `ENCRYPTION_KEY` (32), generated on the VM | Defaults are public (`example`, `password`, `redispassword`) |
| Administrator | `admin@soc.lab`, organisation `SOC-Lab`, generated password | Account created at the first start |
| `DISABLE_PRINTING_PLAINTEXT_CREDENTIALS` | true | No credential in the logs |
| `TZ` | Africa/Tunis | |
| Certificate | Own self-signed certificate in `ssl/`, CN and IP 10.10.10.10; key owned by UID 101 (nginx user), mode 400 | The README states that HTTPS is disabled when the certificates are missing |

Checks: the ten settings present; 3 random passwords; encryption key; administrator password set; `docker compose config --quiet` without error (only "variable is not set" warnings for optional features: LDAP, OIDC, Azure AD, proxy, S3); `docker compose config --images` lists six images, none `latest`. The generated administrator password was shown in a pasted terminal output before the first start; it was replaced by a new one, written straight into `.env`, before MISP ever started.

#### 2.6b Images

Pulled with `systemd-run --unit=misp-pull` in 6 minutes, no failure: misp-core 478 MB compressed / 2.33 GB on disk, misp-modules 451 MB / 1.9 GB, mariadb 105 MB / 456 MB, misp-nginx 75 MB / 276 MB, smtp 59 MB / 244 MB, valkey 43 MB / 162 MB.

#### 2.6c First start and measurement

`docker compose up -d`: redis, db and misp-modules healthy, mail up; `misp-core` was reported unhealthy after 74 seconds and `misp-nginx` was therefore not started ("dependency failed to start"). The `misp-core` log showed a normal first initialisation: database updates, GPG key, organisation SOC-Lab and user admin@soc.lab, base URL, then the component updates (taxonomies, galaxies, warning lists, object templates). The health check only gives 60 seconds before counting failures, which is shorter than this first initialisation. After about 5 minutes the log read "MISP is now live. Users can now log in.", the container turned healthy, and a second `docker compose up -d` started `misp-nginx`.

| Test | Result | What it proves |
|---|---|---|
| `docker compose ps` | db, redis, misp-modules, misp-core, misp-nginx healthy; mail up | MISP stack running |
| `curl https://10.10.10.10:9443/users/login` | 200 | HTTPS with our certificate on 9443 |
| Login as admin@soc.lab | Events page (empty) | Administrator account from `.env` works |
| `docker ps` | 18 containers up (Wazuh 3, Shuffle 4, IRIS 5, MISP 6) | The four tools run together |

Memory with the four tools (`docker stats`, `free -h`):

| Tool | Measured | Brief estimate |
|---|---|---|
| MISP (core 418 MiB, modules 415 MiB, MariaDB 403 MiB, mail 12 MiB, Valkey 10 MiB, nginx 9 MiB) | about 1.25 GiB | 3 GB |
| Shuffle | about 1.97 GiB | 2.5 GB |
| Wazuh | about 1.95 GiB | 3.5 GB |
| DFIR-IRIS | about 0.75 GiB | 1.5 GB |
| **Four tools** | **about 5.9 GiB** | **10.5 GB** |
| Whole VM (10 GB) | 6.7 GiB used, 3.0 GiB available, swap 192 MiB | |
| Windows host | 208 to 313 MB available | |

Decision: MISP stays running. The four tools fit in the 10 GB VM; the swap stays low. The tight resource is the Windows host (VM at its maximum): only one browser tab while working; MISP can be stopped with `docker compose down` in `~/misp` when not needed.

#### 2.6d Test indicators and API key (26 November 2026)

Lab addresses are private and appear in no public feed, so the indicators of the scenarios are added by hand.

| Item | Value | Reason |
|---|---|---|
| Event 1 | "SOC lab - test indicators (T-05, UC-08)", distribution "Your organisation only", threat level High, analysis Completed, not published | Nothing shared outside the instance |
| Attribute 1 | Network activity, `ip-src` 10.10.30.10, for IDS, "Kali - lab attacker (source)" | Attacker of the lab |
| Attribute 2 | Network activity, `ip-dst` 10.10.30.10, for IDS, "Kali - lab attacker (destination, T-05)" | Connection towards a known address (T-05) |
| Attribute 3 | Network activity, `domain` malicious.test.lab, for IDS, "Fictitious malicious domain (UC-08)" | UC-08 |
| API key | "Shuffle playbook (read only)", read-only | Least privilege for the playbook (BNF-02) |

Checks from the VM, the key kept in a shell variable (`read -s`):

| Test | Result | What it proves |
|---|---|---|
| `POST /attributes/restSearch` value 10.10.30.10 | 2 attributes (`ip-src`, `ip-dst`, `to_ids` true, event 1) | Known indicator found |
| Same for 10.10.20.20 | `"Attribute": []` | No false match on a lab target |
| Same for malicious.test.lab | 1 attribute (`domain`) | Domain indicator found |
| `POST /events/add` with the key | 403 | The key cannot write |

The event did not need to be published for `restSearch` to return its attributes. MISP's header is `Authorization: <key>` (no `Bearer` prefix, unlike IRIS).

#### 2.6e MISP lookup in the playbook (26 November 2026)

First design: two branches after "Change Me", with conditions on the Wazuh field `all_fields.data.srcip` ("is empty", negated on the MISP branch), so that alerts without a source address skip MISP. Test with three alerts (two simulated alerts posted to the webhook with `srcip` 10.10.30.10 and 10.10.20.20, and a real alert from a manager restart, rule 502, without `srcip`): the MISP branch behaved as intended, but the branch "srcip is empty" also ran when `srcip` was set (both IRIS nodes created an alert). The condition was correctly configured and the Shuffle SDK code reads correct for "is empty"; the cause in Shuffle 2.3.0 was not found.

Final design, without any condition:

```
Wazuh alerts (webhook) -> Change Me -> MISP lookup -> Create IRIS alert MISP
```

| Node | Setting |
|---|---|
| MISP lookup (Http, POST) | `https://10.10.10.10:9443/attributes/restSearch`, headers `Authorization: <read-only key>`, `Accept` and `Content-Type: application/json`, verify false; body `{"returnFormat":"json","value":"{{ "$exec.all_fields.data.srcip" \| default: "none" }}"}` |
| Create IRIS alert MISP (Http, POST) | `/alerts/add` as in step 2.5, tag `misp-checked`, description mentioning the source address, and `"alert_context":{"src_ip":"$exec.all_fields.data.srcip","misp_attributes":$misp_lookup.body.response.Attribute}` |

A missing field is replaced by an empty value in Shuffle; the Liquid filter `default` turns it into `none`, which matches no indicator, so an alert without a source address can never produce a false MISP match. Every alert now goes through MISP (one more API call per alert).

| Test | MISP lookup | IRIS alert |
|---|---|---|
| Simulated SSH brute force, `srcip` 10.10.30.10 | 200, 2 attributes | 10, tags `wazuh`, `rule-5712`, `misp-checked`, "source 10.10.30.10 checked in MISP" |
| Simulated connection, `srcip` 10.10.20.20 | 200, no attribute | 11, `misp-checked` |
| Real alert rule 502, no `srcip` | 200, no attribute | 12, `misp-checked` |

Each execution ran its three nodes ("3 + 0 = 3"), one IRIS alert per test. Exchanges 4, 5 and 7 of the architecture run end to end with no human action.

Observations:

- For alerts without a source address Shuffle records a notification "shuffle_variable_error: Failed finding exec.all_fields.data.srcip" on the two nodes using that field. The execution still succeeds (the variable is replaced by an empty value): expected for host alerts such as PowerShell.
- Shuffle shows the browser's local time (Tunis, UTC+1); IRIS and Wazuh show UTC. For the rule 502 test the Shuffle execution started at 12:33:44 local time and IRIS created the alert at 11:33:59 UTC (12:33:59 local): about 15 seconds from the webhook to the IRIS alert, through MISP.
- IRIS records its creation time as "Source Event Time"; passing the Wazuh `timestamp` in `alert_source_event_time` is a later improvement.
- The first MISP key was visible on a screenshot of the node settings: it was deleted in MISP and replaced by a new read-only key before the tests above.

## 5. Problems met and how they were handled

| Problem | Handling |
|---|---|
| Host memory exhausted (126 MB available) with the VM at 11 GB | VM reduced to 10 GB; tools measured one by one |
| Shuffle's OpenSearch publishes port 9200, already used by Wazuh | Published on `127.0.0.1:9201` |
| Shuffle runtime "Stopped": Orborus swarm init failed on a VM with several addresses | Swarm mode disabled, Orborus in its default mode |
| Orborus pulled `tenzir/tenzir:main` (pipelines, not in the design) | `SHUFFLE_SKIP_PIPELINES=true` |
| "Test action" refused: no previous execution | First execution created by posting a test JSON to the webhook |
| `docker compose restart` did not apply the new manager configuration | `docker compose up -d --force-recreate wazuh.manager` |
| Wazuh vulnerability detection used disk and network heavily for nothing | Module disabled |
| IRIS severity identifiers not in creation order (Medium is 1) | Read from the API before building the playbook |
| MISP HTTPS disabled without certificates; nginx runs as UID 101 | Own certificate in `ssl/`, key owned by UID 101 |
| MISP generated password shown in a pasted terminal output | Replaced before the first start |
| `misp-core` unhealthy at first start, `misp-nginx` not started | Waited for the first initialisation (about 5 minutes), then `docker compose up -d` again |
| Shuffle branch condition "srcip is empty" did not stop its branch | Workflow rebuilt as a single chain; empty address replaced by `none` with the Liquid `default` filter |
| MISP API key visible on a screenshot | Key deleted and replaced |

## 6. Résumé pour le rapport

À rédiger à la clôture de la phase.
