# DFIR-IRIS 2.4.29 on the soc VM

Incident response platform, from the official repository `dfir-iris/iris-web`, tag `v2.4.29` (licence LGPL v3). Journal: `docs/phases/phase-2-laptop1.md`.

## Files in this folder

| File | Content |
|---|---|
| `docker-compose.yml` | Official file of tag v2.4.29, unchanged (SHA-256 `dc80b581048982c9344b5ba0e25bb3211c76785ae5a2f5ba902932bfb368eb8e`) |
| `docker-compose.base.yml` | Official file of tag v2.4.29 with RabbitMQ pinned to `3.13-management-alpine` (SHA-256 `49b825035a78e1232e01f98d11d492d3e0574091b9ce6fd155b8f5a0b8bd111d`) |
| `.env.example` | `.env.model` of tag v2.4.29 with our port and certificate names, and `change-me` placeholders for the secrets |

## Changes from the official files

| Change | Reason |
|---|---|
| `INTERFACE_HTTPS_PORT=8443` | Port 443 belongs to the Wazuh dashboard |
| Own certificate `iris_soc_cert.pem` / `iris_soc_key.pem` (self-signed, CN and IP 10.10.10.10, 825 days) instead of `iris_dev_*` | The repository ships the development certificate with its private key, so that key is public |
| Key owned by UID 33, mode 400 | nginx runs as `www-data` (UID 33) in the IRIS image |
| Random `POSTGRES_PASSWORD`, `POSTGRES_ADMIN_PASSWORD`, `IRIS_SECRET_KEY`, `IRIS_SECURITY_PASSWORD_SALT` | Default values are public |
| `IRIS_ADM_PASSWORD` set | Otherwise the generated password is printed only once in the logs |
| RabbitMQ `3.13-management-alpine` instead of `3-management-alpine` | Pinned version |

## Rebuild

On the soc VM, in the home directory:

1. `git clone https://github.com/dfir-iris/iris-web.git -b v2.4.29 --depth 1 iris`, then `cd iris`.
2. Replace `docker-compose.base.yml` with the one in this folder; create `.env` from `.env.example` with real values, `chmod 600 .env`.
3. Certificate:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 825 -keyout certificates/web_certificates/iris_soc_key.pem -out certificates/web_certificates/iris_soc_cert.pem -subj "/CN=10.10.10.10" -addext "subjectAltName=IP:10.10.10.10"
sudo chown 33:33 certificates/web_certificates/iris_soc_key.pem
sudo chmod 400 certificates/web_certificates/iris_soc_key.pem
```

4. `sudo docker compose up -d`; log in on `https://10.10.10.10:8443` as `administrator`.

## API used by the playbook

- Authentication: header `Authorization: Bearer <API key>` (key of the user, in "My settings"). The key stays on the VM and in Shuffle, never in the repository.
- `POST /alerts/add` creates an alert. Required: `alert_title`, `alert_severity_id`, `alert_status_id`, `alert_customer_id`.
- Identifiers read from this instance (`/manage/severities/list`, `/manage/alert-status/list`, `/manage/customers/list`): severities Medium 1, Unspecified 2, Informational 3, Low 4, High 5, Critical 6; alert status New 2; customer IrisInitialClient 1. They are not in creation order: read them again on a rebuilt instance.

## Ports published by the VM

| Port | Service | Used by |
|---|---|---|
| 8443/tcp | IRIS web interface and API (nginx) | Analysts' browser; Shuffle (`https://10.10.10.10:8443`) |

## Kept on the VM only

`.env`, the private key of the certificate, the administrator password, the API key.
