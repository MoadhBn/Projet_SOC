# Wazuh 4.14.9 on the soc VM

Official single-node Docker deployment (`wazuh/wazuh-docker`, tag `v4.14.9`), running on the soc VM (10.10.10.10). Journal: `docs/phases/phase-1-laptop1.md`.

## Files in this folder

| File | Content |
|---|---|
| `docker-compose.yml` | The official `single-node/docker-compose.yml` of tag v4.14.9, with the three passwords replaced by `${INDEXER_PASSWORD}`, `${DASHBOARD_PASSWORD}` and `${API_PASSWORD}`. Nothing else changed (SHA-256 `8472c14f090787b15fdc6c4b3687c39ec396af413366d5795b49219f3b9eea41`). |
| `.env.example` | The three variables with placeholder values. |

## Files that stay on the VM only

| File (in `~/wazuh-docker/single-node/`) | Why it is not committed |
|---|---|
| `.env` | The three passwords |
| `config/wazuh_indexer/internal_users.yml` | Password hashes of `admin` and `kibanaserver` |
| `config/wazuh_dashboard/wazuh.yml` | Password of `wazuh-wui` |
| `config/wazuh_indexer_ssl_certs/` | Private keys of the lab certificate authority and of each component |

## Rebuild from scratch

On the soc VM (Docker Engine and the Compose plugin installed, `vm.max_map_count` at least 262144; Ubuntu 24.04 sets 1048576):

1. `git clone https://github.com/wazuh/wazuh-docker.git -b v4.14.9 --depth 1`, then work in `wazuh-docker/single-node`.
2. Replace `docker-compose.yml` with the one in this folder; create `.env` from `.env.example` with real passwords, `chmod 600 .env`.
3. Certificates: `sudo docker compose -f generate-indexer-certs.yml run --rm generator`.
4. Put the `wazuh-wui` password in `config/wazuh_dashboard/wazuh.yml`, and the hashes of the `admin` and `kibanaserver` passwords in `config/wazuh_indexer/internal_users.yml` (hash tool: `sudo docker run --rm -ti wazuh/wazuh-indexer:4.14.9 bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh`).
5. `sudo docker compose up -d`; once `https://localhost:9200` answers 401, apply the security configuration:

```bash
sudo docker exec single-node-wazuh.indexer-1 bash -c 'export JAVA_HOME=/usr/share/wazuh-indexer/jdk; C=/usr/share/wazuh-indexer/config; bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh -cd $C/opensearch-security/ -nhnv -cacert $C/certs/root-ca.pem -cert $C/certs/admin.pem -key $C/certs/admin-key.pem -p 9200 -icl'
```

Source of the password procedure: "Changing the default password of Wazuh users", Wazuh documentation 4.14 (`wazuh/wazuh-documentation`, `source/deployment-options/docker/changing-default-password.rst`).

## Integration with Shuffle

The manager sends alerts to a Shuffle webhook with Wazuh's built-in `shuffle` integration (Integrator module). The block below is in `config/wazuh_cluster/wazuh_manager.conf` on the VM, right after the first `<ossec_config>` line. The real webhook ID stays on the VM: anyone who knows it can start the workflow.

```xml
  <integration>
    <name>shuffle</name>
    <hook_url>http://10.10.10.10:5001/api/v1/hooks/webhook_<ID></hook_url>
    <level>3</level>
    <alert_format>json</alert_format>
  </integration>
```

- Level 3 is provisional (test with the manager's own alerts); the final threshold is set with the use cases.
- HTTP to the Shuffle backend (port 5001): the traffic stays inside the VM; HTTPS on 3443 uses a self-signed certificate.
- **Apply a change of `wazuh_manager.conf` with `sudo docker compose up -d --force-recreate wazuh.manager`.** A plain `docker compose restart` did not copy the mounted file into `/var/ossec/etc/ossec.conf`; a recreated container does (the data stays in the volumes).
- Shuffle receives the alert reformatted by `/var/ossec/integrations/shuffle.py`: `severity` (1 to 3), `title`, `text`, `rule_id`, `timestamp`, `id`, and the complete alert under `all_fields`.

## Ports published by the VM

| Port | Service | Used by |
|---|---|---|
| 443/tcp | Dashboard | Analysts' browser |
| 1514/tcp, 1515/tcp | Manager: agent events, enrolment | Agents of the targets and of OPNsense (allowed by the firewall towards 10.10.10.10) |
| 55000/tcp | Wazuh server API | Dashboard; Shuffle in phase 4 (active response) |
| 9200/tcp | Indexer | Analysis API on laptop 2 (reads events, phase 3) |
| 514/udp | Syslog | Official default, not used by the design |

Port 443 belongs to Wazuh; MISP and DFIR-IRIS get other ports in phase 2.
