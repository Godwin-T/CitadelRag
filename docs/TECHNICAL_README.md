# CitadelRAG Technical Guide

This guide explains the system architecture, data flow, and implementation details so a junior engineer can extend the platform confidently.

## 1. Architecture Overview

```
Frontend (React/TS)
  -> API (FastAPI)
     -> Postgres (metadata, auth, analytics, memory)
     -> Qdrant (vectors)
     -> Redis (queues, short-term memory)
     -> OSS LLM/Embedding servers (OpenAI-compatible)
  -> Worker (ingestion, memory summarization, evaluation)
```

### Key Concepts

- **Multi-tenancy**: Every record includes `tenant_id`. Queries and vectors are filtered by tenant.
- **RAG pipeline**: Embedding + retrieval + LLM response with citations.
- **Memory**: Short-term session memory in Redis, long-term summaries and keypoints in Postgres.
- **Evaluation**: Retrieval metrics and faithfulness scoring stored per run.

## 2. Data Flow

### Ingestion

1. Upload document via API.
2. API writes file to S3 (MinIO) or local storage and enqueues ingestion job to Redis.
3. Worker extracts text, chunks, embeds, and stores:
   - chunks + embeddings in Postgres
   - vectors in Qdrant
4. Document status is updated to `ready`.

### Query

1. API embeds query.
2. Qdrant search with `tenant_id`, `embedding_version_id`, `chunk_strategy_id` filter.
3. API composes prompt:
   - Short-term memory (Redis)
   - Long-term memory (Postgres summaries + keypoints)
   - Retrieved chunks
4. LLM generates answer with citations.
5. API stores `queries` and `answers` plus analytics events.

### Memory

- **Short-term**: Stored as a list of turns in Redis (TTL 24h).
- **Long-term**: A worker job summarizes conversations and extracts keypoints, stored in Postgres.

### Evaluation

- Eval sets are uploaded in CSV with `question`, `ground_truth`, and `doc_ids`.
- Worker runs retrieval for each question and computes Recall@K, MRR, nDCG.

## 3. Database Tables (What They Do)

- `tenants`, `users`, `memberships`: multi-tenant auth.
- `documents`, `document_files`: uploaded files.
- `chunks`, `embeddings`: chunked document data and vector references.
- `chunk_strategies`, `embedding_versions`: versioned strategies for comparison.
- `queries`, `answers`: user questions and model responses.
- `eval_sets`, `eval_items`, `eval_runs`: evaluation datasets and metrics.
- `events`: analytics stream.
- `memory_sessions`, `memory_summaries`, `user_keypoints`: memory system.

## 4. RAG Pipeline Details

1. **Chunking**: strategy-based chunking with multiple algorithms in `worker/app/services/chunking.py`.
2. **Embedding**: calls OpenAI-compatible embedding endpoint.
3. **Retrieval**: Qdrant search with tenant and strategy filters.
4. **Answer**: LLM prompt with memory + sources, citations returned in JSON.

## 5. Chunking Options

The worker supports these strategies (default is `fixed`):

- `fixed`: char window with overlap.
- `recursive`: separator-aware recursive splitting.
- `sentence`: sentence packing with max length.
- `paragraph`: paragraph packing with max length.
- `header`: heading-based section splits.
- `semantic`: similarity-based sentence grouping.
- `llm`: LLM-generated chunk boundaries.

Each strategy uses `chunk_strategies.name` and `chunk_strategies.params_json` to configure behavior.

### Default Params by Strategy

- `fixed`: `max_chars=1000`, `overlap=100`
- `recursive`: `max_chars=1000`, `overlap=100`, `separators=["\\n\\n", "\\n", ". ", " "]`
- `sentence`: `max_chars=1000`, `overlap=100`, `min_sentence_chars=20`
- `paragraph`: `max_chars=1200`, `overlap=100`
- `header`: `max_chars=1500`, `overlap=100`, `header_regex="^#{1,6}\\s+.+$"`
- `semantic`: `max_chars=1200`, `overlap=100`, `similarity_threshold=0.75`, `max_sentences=10`
- `llm`: `max_chars=1200`, `overlap=100`, `llm_format="json_list"`

### 5.1 Adding a New Chunk Strategy

1. Implement a new function in `worker/app/services/chunking.py`.
2. Add a record in `chunk_strategies` with `active=false`.
3. Update ingestion to switch strategy based on config or user input.

## 6. Adding a New Embedding Model

1. Add a record in `embedding_versions`.
2. Update `.env` with `EMBED_MODEL` and restart services.
3. Re-run ingestion to generate vectors for that version.

## 7. Testing

- **Unit**: chunking, no-answer logic, memory summarization.
- **Integration**: ingestion pipeline, query pipeline with mocked LLM.
- **E2E**: upload → query → answer → analytics.

## 8. Common Pitfalls

- Missing model servers: ensure OSS LLM and embeddings endpoints are running.
- Large files: increase memory or implement streaming extraction.
- Vector mismatch: ensure embedding dimension matches Qdrant collection.
- Missing MinIO bucket: ensure `citadel-docs` exists (minio-init does this in docker-compose).

## 12. Storage Backend

Uploads are stored in S3-compatible storage (MinIO in dev) with a local fallback.

- S3 URIs are stored as `s3://bucket/key`.
- Local fallbacks are stored as `file:///abs/path`.
- Worker resolves the URI before extraction.

## 13. Model Providers

LLM and embedding calls are provider-driven via env vars:

- `LLM_PROVIDER` / `EMBED_PROVIDER`: `groq`, `custom`, or `local`.
- `GROQ_API_KEY` + `GROQ_BASE_URL` for Groq OpenAI-compatible API.
- `CUSTOM_LLM_BASE_URL` / `CUSTOM_EMBED_BASE_URL` for your own hosted models.

Embeddings default to OpenAI:

- `EMBED_PROVIDER=openai`
- `OPENAI_API_KEY` + `OPENAI_BASE_URL`
- Optional: `EMBED_PROVIDER=huggingface` + `HF_EMBED_BASE_URL`

## 9. API Contracts

See `api/routes/routes_*.py` for request and response shapes.

Key chunking endpoints (optional but available):

- `GET /api/chunk-strategies`
- `POST /api/chunk-strategies`
- `POST /api/chunk-strategies/{id}/activate`

## 10. Extension Ideas

- Add OAuth/SSO
- Add streaming responses
- Add UI-based prompt templates

## 11. Prompt Source of Truth

All system and user prompts live in `api/prompts/prompts.py`.

- API and worker LLM calls import message templates from this module.
- To add or modify prompts, change the constants/builders in that file only.
- Local dev: run worker with `PYTHONPATH=./worker:.` so it can import `api.prompts`.

## 14. Database Migrations

Use Alembic for schema migrations. Manual migrations are default and safest for production.

Run migrations:

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

Optional auto-migrate on API startup (dev only) via `AUTO_MIGRATE=true`.
