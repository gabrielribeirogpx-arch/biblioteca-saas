# Library SaaS

## Run locally

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Backend migration runbook

Run database migrations before starting the API:

```bash
cd backend
pip install -r app/requirements.txt
alembic -c alembic.ini upgrade head
```

For containers, the backend entrypoint runs migrations automatically before Uvicorn startup.
