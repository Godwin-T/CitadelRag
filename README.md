# CitadelRAG

Multi-tenant production RAG knowledge platform with ingestion, vector search, citation-backed answers, evaluation, analytics, and memory.

## What This Repo Contains

- `api`: FastAPI API service.
- `worker`: background ingestion, memory, and evaluation worker.
- `ui`: React + TypeScript frontend.
- `docker`: Docker compose and Dockerfiles.
- `docs/TECHNICAL_README.md`: deep technical guide.

## Quickstart (Docker)

1. Copy env template.

```bash
cp env.example .env
```

2. Start services.

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build

To clean up old/orphaned containers if you see warnings:

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build --remove-orphans
```
```

If you are running with manual migrations, run the migrator once before starting the API:

```bash
docker compose -f docker/docker-compose.yml --env-file .env --profile migrations run --rm api-migrate
```

3. Open API:

- `http://localhost:8000/health`

4. Open web app:

- `http://localhost:5173`

## Groq Models

Set these in `.env` to use Groq (OpenAI-compatible):

- `LLM_PROVIDER=groq`
- `GROQ_API_KEY=...`
- `GROQ_BASE_URL=https://api.groq.com/openai/v1`

## Embeddings (OpenAI Default)

Groq does not provide embeddings. Use OpenAI by default:

- `EMBED_PROVIDER=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_BASE_URL=https://api.openai.com/v1`

Optional:

- `EMBED_PROVIDER=huggingface`
- `HF_EMBED_BASE_URL=http://embeddings:80/v1`

## Local Development

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=./
alembic -c alembic.ini upgrade head
uvicorn api.main:app --reload
```

### Worker

```bash
cd worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=./
python -m api.main
```

### Frontend

```bash
cd ui
npm install
npm run dev
```

## Services and Ports

- API: `8000`
- Web: `5173`
- LLM server: `8001`
- Embeddings server: `8002`
- Postgres: `5432`
- Redis: `6379`
- Qdrant: `6333`
- MinIO (S3): `9000` (API), `9001` (console)

## Environment Variables

See `env.example` for the full list.

Key variables:

- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- `JWT_SECRET`
- `LLM_BASE_URL`, `LLM_MODEL`
- `EMBED_BASE_URL`, `EMBED_MODEL`
- `MEMORY_TTL_SECONDS`
- `STORAGE_BACKEND`, `S3_ENDPOINT`, `S3_BUCKET`

## API Overview

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/tenants`
- `POST /api/documents/upload`
- `POST /api/query`
- `POST /api/eval/sets`
- `POST /api/eval/runs`
- `GET /api/analytics/queries`

## Notes

- The ingestion worker pulls jobs from Redis lists: `ingest_queue`, `memory_queue`, `eval_queue`.
- OSS model servers must be running and OpenAI-compatible.
- Default admin credentials are seeded on API startup: `admin` / `admin`.

## Database Migrations (Alembic)

Manual migrations are the default and recommended for production:

```bash
cd api
alembic -c alembic.ini upgrade head
```

Safe autogenerate (creates a migration only if changes exist):

```bash
./scripts/makemigrations.sh
```

Docker (runs inside the API image):

```bash
docker compose -f docker/docker-compose.yml --env-file .env --profile migrations run --rm api-makemigrations
```

Create a new migration:

```bash
cd api
alembic -c alembic.ini revision --autogenerate -m "message"
```

Optional auto-migrate on API startup (use for dev only):

```bash
AUTO_MIGRATE=true
```

If you see `Target database is not up to date` when autogenerating, run:

```bash
docker compose -f docker/docker-compose.yml --env-file .env --profile migrations run --rm api-migrate
```

## Next Steps

- Configure your preferred OSS models in `.env`.
- Add UI improvements and dashboards as needed.
