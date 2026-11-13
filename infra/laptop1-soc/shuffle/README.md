# Shuffle 2.3.0 on the soc VM

Shuffle (SOAR) runs on the soc VM next to Wazuh, from the official repository `Shuffle/Shuffle`, tag `v2.3.0`. Journal: `docs/phases/phase-2-laptop1.md`.

## Files in this folder

| File | Content |
|---|---|
| `docker-compose.yml` | The official file of tag v2.3.0 with the changes below (SHA-256 `0c31bd0e11a71798c7c355963f70285fd17c2479382d9d26566038a6ab541e26`) |
| `.env.example` | The official `.env` of tag v2.3.0 with the time zone set and the secrets replaced by `change-me` placeholders |

## Changes from the official files

| Change | Reason |
|---|---|
| OpenSearch port published as `127.0.0.1:9201` instead of `9200` | Port 9200 belongs to the Wazuh indexer; Shuffle's database only needs to be reachable from the VM |
| OpenSearch heap `-Xms1g -Xmx1g` instead of 3 GB | Memory budget of the VM (brief: about 1 GB) |
| Images pinned to `2.3.0` (frontend, backend, orborus, worker) instead of `latest` | Pinned versions |
| `shuffle-security` service removed | Not in the installation guide, only published as `latest`; the interface is the `frontend` service |
| `SHUFFLE_SWARM_CONFIG=run` replaced by `SHUFFLE_SKIP_PIPELINES=true` | Swarm mode failed (`swarm init`: the VM has several addresses) and left the runtime "Stopped"; Orborus has a default mode without Swarm for a single server. Without the skip flag, Orborus downloads `tenzir/tenzir:main` (pipelines, not used by the design) |
| `.env`: `TZ=Africa/Tunis`, random `SHUFFLE_ENCRYPTION_MODIFIER`, new OpenSearch password | Correct timestamps; encryption of the credentials stored by Shuffle; default password is public |

Swap is kept on the VM (the guide suggests `swapoff -a`): the official file locks OpenSearch memory (`bootstrap.memory_lock=true`) so its heap is not swapped.

## Rebuild

On the soc VM, in the home directory:

1. `git clone https://github.com/Shuffle/Shuffle.git -b v2.3.0 --depth 1 shuffle`, then `cd shuffle`.
2. Replace `docker-compose.yml` with the one in this folder; create `.env` from `.env.example`, set the passwords and the encryption modifier, `chmod 600 .env`.
3. `sudo chown -R 1000:1000 shuffle-database`
4. `sudo docker compose up -d`, then create the administrator account at once on `https://10.10.10.10:3443` (Shuffle has no default account: the first visitor creates it).

## Ports published by the VM

| Port | Service | Used by |
|---|---|---|
| 3443/tcp (3001/tcp HTTP) | Interface | Analysts' browser |
| 5001/tcp | Backend API and webhooks | Wazuh integration (`http://10.10.10.10:5001/api/v1/hooks/webhook_<id>`) |
| 127.0.0.1:9201 | Shuffle's OpenSearch | The VM only |

## Kept on the VM only

`.env` (OpenSearch password, encryption modifier), `shuffle-database/` (data), the Shuffle administrator password, and the webhook URLs (anyone who knows one can start the workflow).
