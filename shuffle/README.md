# Shuffle playbooks

Playbooks exported from Shuffle 2.3.0 on the soc VM (laptop 1). Setup of Shuffle itself: `infra/laptop1-soc/shuffle/`. Design and tests: `docs/phases/phase-2-laptop1.md`, steps 2.5 to 2.7.

## `wazuh-alerts-workflow.json`

Workflow `Wazuh-Alerts`, exchanges 4, 5 and 7 of the architecture:

```
Wazuh alerts (webhook) -> Change_Me -> MISP_lookup -> Create_IRIS_alert_MISP
```

| Node | App | What it does |
|---|---|---|
| Wazuh alerts | Webhook trigger | Receives each alert sent by Wazuh's built-in `shuffle` integration |
| Change_Me | Shuffle Tools 1.2.0, `repeat_back_to_me` | Returns the alert (`$exec`), so that every execution shows what Wazuh sent |
| MISP_lookup | http 1.4.0, POST | `https://10.10.10.10:9443/attributes/restSearch` with the source address of the alert (`none` when the alert has none) |
| Create_IRIS_alert_MISP | http 1.4.0, POST | `https://10.10.10.10:8443/alerts/add`: IRIS alert with the Wazuh rule, the source address, the MISP attributes found and the full Wazuh alert |

## What was removed from the export

| Item | In this file | Where the real value is |
|---|---|---|
| MISP API key (read-only) | `Authorization: change-me` | MISP, Administration, Auth keys |
| DFIR-IRIS API key | `Authorization: Bearer change-me` | DFIR-IRIS, My settings |
| Webhook identifier | `webhook_webhook-id-removed` | Shuffle trigger; `hook_url` in the Wazuh manager configuration on the VM |
| App icons (base64 images) | empty | Restored by Shuffle on import |

Shuffle's own export also left the `url` field of the two http nodes empty; the two addresses above were put back by hand, since they are lab addresses already in the documentation.

## Import

1. Shuffle, Workflows, Import, choose this file.
2. In `MISP_lookup` and `Create_IRIS_alert_MISP`, replace `change-me` with the keys (do not take screenshots of these fields).
3. Start the webhook trigger. Shuffle gives it a new identifier: put the new URL, with port 5001 and plain HTTP (`http://10.10.10.10:5001/api/v1/hooks/webhook_<id>`), in the `hook_url` of the Wazuh manager configuration, then recreate the manager container (`docker compose up -d --force-recreate wazuh.manager`).
4. Test: restart the Wazuh manager; rule 502 "Wazuh server started" must give one execution with three nodes run and one IRIS alert tagged `misp-checked`.

## Known limits

- The http nodes do not check certificates (`verify` false): MISP and DFIR-IRIS use self-signed certificates on the isolated lab network.
- Values from the alert are inserted as text in the IRIS request body: an alert title containing a double quote would make the request invalid. To check with the real alerts of phase 3.
- Every alert gets severity "Unspecified" in IRIS; severity from the analysis is phase 3.
