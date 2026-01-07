# Yam Fluent API

Yam Fluent is a FastAPI backend that powers user sessions, speech analysis, and coaching workflows. It combines MongoDB persistence, Redis-backed rate limiting, background processing with Celery, and scheduled tasks via APScheduler. Optional OpenAI integrations support speech-to-text, coaching tips, and script generation.

## Features

- JWT authentication with user/admin roles and account status checks
- Session management and speech analysis scoring
- Coaching tips generation and content utilities
- Email workflows for sign-in, invitations, and password resets
- Role-based rate limiting backed by Redis
- Celery worker for async tasks and APScheduler for scheduled jobs
- Health endpoints that verify MongoDB, Redis, scheduler, and Celery

## Project Structure

- `api/` HTTP route handlers and API versioning
- `controller/` speech analysis, scoring, and script generation logic
- `services/` business logic for users, sessions, coaching tips, admin flows
- `repositories/` data access for MongoDB collections
- `schemas/` Pydantic request and response models
- `security/` JWT, hashing, permissions, and account checks
- `core/` database, Redis cache, scheduler, and task registry

## Requirements

- Python 3.8+
- MongoDB
- Redis
- (Optional) OpenAI API key for AI-driven features
- (Optional) SMTP credentials for email workflows

## Configuration

Create a `.env` file in the project root or export variables in your shell.

Required:
- `MONGO_URL`
- `DB_NAME`
- `JWT_SECRET` (signing secret for access/admin JWTs)
- `SECRETID` (ID of JWT key document used for member token secrets)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

Common optional:
- `OPENAI_API_KEY`, `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`
- `OPENAI_MODEL`, `OPENAI_TEXT_MODEL`, `OPENAI_ASR_MODEL`, `OPENAI_TTS_MODEL`
- `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_HOST`, `EMAIL_PORT`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`
- `APP_SCHEME` (mobile deep link scheme, default `yamfluent`)
- `CLOUDFLARE_R2_ENDPOINT`, `CLOUDFLARE_R2_BUCKET`, `CLOUDFLARE_R2_PUBLIC_URL`
- `JWT_SECRET_KEY` or `SECRET_KEY` (alternate names for JWT signing secret)

## Local Development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 7864
```
Set the Celery worker Variable:

```bash
set CELERY_CUSTOM_WORKER_POOL=celery_aio_pool.pool:AsyncIOPool
```

Run the Celery worker:

```bash
celery -A celery_worker worker -l info --pool=custom --concurrency=5
```

## Docker

```bash
docker compose up -d --build
```

The API will be available at `http://localhost:7864`.

## Operations

- Run the API, Celery worker, and scheduler for full functionality.
- Account deletion triggers background cleanup of sessions, coaching tips, and notification device state.
- Session deletion attempts to remove Cloudflare R2 audio URLs tied to the session.
- Celery monitoring is available via Flower if enabled in `docker-compose.yml`.

## API Docs and Health

- Swagger UI: `http://localhost:7864/docs`
- ReDoc: `http://localhost:7864/redoc`
- Health: `GET /health` and `GET /health-detailed`

## Testing

```bash
pytest -q
```
