# MISP 2.5.52 on the soc VM

Threat intelligence platform, from the official repository `MISP/misp-docker`. The repository has no version tags: the deployment uses commit `88e90bf` (19 November 2026) with images pinned through the running tags below. Journal: `docs/phases/phase-2-laptop1.md`.

## Files in this folder

| File | Content |
|---|---|
| `.env.example` | `template.env` of commit 88e90bf with our settings and `change-me` placeholders for the secrets |

`docker-compose.yml` is the official file of commit 88e90bf, unchanged: every setting goes through `.env`.

## Changes from the official template

| Setting | Official default | Value | Reason |
|---|---|---|---|
| `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG` | `latest` | `v2.5.52`, `v3.1.5` | Pinned versions (tags published on ghcr.io) |
| `NGINX_HTTP_PORT`, `NGINX_HTTPS_PORT` | 80, 443 | 9080, 9443 | Port 443 belongs to the Wazuh dashboard |
| `BASE_URL` | `http://localhost` | `https://10.10.10.10:9443` | Mandatory; address used by browsers and Shuffle |
| `INNODB_BUFFER_POOL_SIZE` | 2048M | 256M | Memory budget of the VM; enough for test indicators |
| `TZ` | UTC | Africa/Tunis | Timestamps |
| `DISABLE_PRINTING_PLAINTEXT_CREDENTIALS` | off | true | Administrator password and key never written to the logs |
| `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `REDIS_PASSWORD`, `ENCRYPTION_KEY` | public defaults or empty | random | Default values are public |
| `ADMIN_EMAIL`, `ADMIN_ORG`, `ADMIN_PASSWORD` | empty | `admin@soc.lab`, `SOC-Lab`, set by the administrator | Administrator account created at the first start |

## Rebuild

On the soc VM, in the home directory:

1. `git clone https://github.com/MISP/misp-docker.git misp`, then `cd misp` and `git checkout 88e90bf`.
2. Create `.env` from `.env.example` with real values, `chmod 600 .env`.
3. Certificate (HTTPS is disabled when `ssl/cert.pem` and `ssl/key.pem` are missing; nginx runs as UID 101):

```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:2048 -nodes -days 825 -keyout ssl/key.pem -out ssl/cert.pem -subj "/CN=10.10.10.10" -addext "subjectAltName=IP:10.10.10.10"
sudo chown 101:101 ssl/key.pem
sudo chmod 400 ssl/key.pem
```

4. `sudo docker compose up -d`. On the first start `misp-core` needs about 5 minutes (database schema, GPG key, administrator, taxonomies and galaxies) and is reported unhealthy after its 60-second start period, so `misp-nginx` is not started. Once `docker inspect --format '{{.State.Health.Status}}' misp-misp-core-1` says `healthy`, run `sudo docker compose up -d` again.
5. Log in on `https://10.10.10.10:9443` as `admin@soc.lab`.

`docker compose` prints many `variable is not set` warnings: they are optional features (LDAP, OIDC, Azure AD, proxy, S3). Add `2>/dev/null` to hide them.

## Ports published by the VM

| Port | Service | Used by |
|---|---|---|
| 9443/tcp (9080/tcp HTTP) | MISP web interface and API (nginx) | Analysts' browser; Shuffle (`https://10.10.10.10:9443`) |

## API used by the playbook

`POST /attributes/restSearch` with header `Authorization: <key>` (the key itself, no `Bearer` prefix) and `{"returnFormat":"json","value":"<IP>"}`. The playbook uses a read-only key. Keys stay on the VM and in Shuffle, never in the repository.

## Kept on the VM only

`.env`, `ssl/key.pem`, the administrator password, the API keys, `configs/` (generated configuration) and the database volume.
