# Combined application runtime

Place this `runtime_host/` directory beside the existing `vulnforge_8/` directory:

```text
benchmark_vul_v1/
├── vulnforge_8/
└── runtime_host/
```

No file under `vulnforge_8/` needs to be modified.

## Start

```sh
cd runtime_host
./run-single-docker.sh
```

or:

```sh
docker compose up --build
```

Open:

- Application hub: `http://localhost:8080`
- CompanyEmail local mail inbox (Mailpit): `http://localhost:8025`
- Applications: `http://localhost:8101` through `http://localhost:8108`

ParcelPad keeps the original Compose behavior of using generated secrets. The login user defaults to `operator`; a fresh password is printed once in the container log unless `PARCELPAD_PASSWORD` is supplied in `runtime_host/.env`.

## Integrated prerequisites

The combined runtime preserves the prerequisites from the original per-application Docker definitions:

| Application | Integrated prerequisite |
|---|---|
| CompanyEmail | Mailpit v1.30.7, SMTP on loopback `:1025`, Mailpit UI `:8025`, database path and port environment |
| Mailbox | Nginx static hosting |
| MingleFeed | Jinja2 environment, writable SQLite state, application/internal service ports |
| Parcel Room | FastAPI/Uvicorn stack and required `PARCEL_TMP_ENCRYPTION_KEY` |
| ParcelPad | PostgreSQL, generated secret files, receiver service on internal `:9000`, Gunicorn web process, original login/internal URL environment |
| Pulseboard | FastAPI/Uvicorn/HTTPX; its own internal probe remains on loopback `:9101` |
| QuickCart | Flask/Gunicorn/Flask-WTF/Requests plus original `AMK`, app secret and HMAC-key defaults; internal log URL adjusted only to the combined web port |
| ShellNest | `curl`, CA certificates, `APP_ENV=testing`, workspace and loopback command server |

Python dependencies are installed in separate virtual environments so applications with different Flask/Gunicorn requirements do not overwrite each other.

The single combined image uses Python 3.13 as its common interpreter. The original isolated Dockerfiles used a mix of Python 3.12 and 3.13. Package versions, environment requirements and supporting services are preserved; exact per-app interpreter isolation would require separate containers or bundling multiple Python runtimes.

## Internal-only supporting ports

The following are intentionally **not** published by the helper script or Compose file:

- `1025` CompanyEmail SMTP
- `5432` ParcelPad PostgreSQL
- `9000` ParcelPad receiver
- `9001` MingleFeed internal service
- `9101` Pulseboard probe
- `8765` ShellNest command server

They remain reachable by processes inside the single container because all eight applications share one network namespace.
