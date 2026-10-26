# Match Score API

A FastAPI backend for matches, scores and a live leaderboard, with JWT authentication, role-based access, owner-only editing, PostgreSQL, Alembic migrations and automated tests.

**Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, WebSockets, Pydantic, JWT (python-jose), bcrypt, pytest

## Run locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then set SECRET_KEY
docker compose up -d db         # starts PostgreSQL on port 5432
alembic upgrade head            # creates the tables
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.

**No Docker?** Set `DATABASE_URL=sqlite:///./test.db` in `.env` (or use a hosted PostgreSQL connection string), skip the `docker compose` line, and run the rest. The migration works on both SQLite and PostgreSQL.

- Generate a secret key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Make a user an admin: `python -m app.make_admin <username>`
- After changing `app/models.py`: `alembic revision --autogenerate -m "describe change"` then `alembic upgrade head`

## Caching and rate limiting

- `GET /leaderboard` is cached for 30 seconds (cache-aside). The response header `X-Cache` shows `HIT` or `MISS`. The cache is cleared whenever a match score changes or a match is deleted.
- Rate limits (fixed window, 60 seconds): `/login` 5 per IP, `/register` 10 per IP, and all write endpoints 30 per user. Over the limit the API returns `429` with a `Retry-After` header.
- Set `REDIS_URL` in `.env` to share cache and counters between server processes. Without it, an in-memory backend is used. If Redis goes down, the API keeps working without a cache and without rate limiting (fail open).

## Background jobs and live updates

- **Celery job:** when a match becomes `finished`, the API queues a job and answers immediately. A separate worker sends a notification to `WEBHOOK_URL` (or just logs it if unset). Failed deliveries are retried 3 times with growing waits (2s, 4s, 8s).
- **Queue (broker):** `CELERY_BROKER_URL`, else `REDIS_URL`, else a local `.celery/` folder (development only), so it runs with nothing to install.
- **WebSockets (public):** `ws://127.0.0.1:8000/ws/matches/{id}` sends the current match, then every score update. `ws://127.0.0.1:8000/ws/leaderboard` says when standings change.

```bash
# terminal 1: the API
uvicorn app.main:app --reload
# terminal 2: the worker (run from the project folder; --pool=solo is the simplest on macOS)
celery -A app.celery_app worker --loglevel=info --pool=solo
# optional terminal 3: a fake webhook that fails twice, so you can watch retries
python scripts/webhook_receiver.py --fail-first 2      # then set WEBHOOK_URL=http://127.0.0.1:9000 in .env
# optional terminal 4: watch a match live (the match must exist)
python scripts/ws_listen.py matches/1
```

Limit: WebSocket connections live inside one server process. Several processes would need Redis Pub/Sub to share messages.

## Tests

```bash
pytest --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite database, so they need neither Docker nor PostgreSQL.

## Endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | /health | public | Health check |
| POST | /register | public | Create account (409 if username taken) |
| POST | /login | public | Get JWT access token |
| GET | /me | logged in | Current user |
| GET | /users | admin | List all users |
| GET | /players | public | List players (`limit`, `offset`) |
| GET | /player/{id} | public | Get one player |
| POST | /player | logged in | Create player (you become the owner) |
| PUT | /player/{id} | owner or admin | Update player |
| DELETE | /player/{id} | owner or admin | Delete player |
| GET | /matches | public | List matches (`status`, `limit`, `offset`) |
| GET | /matches/{id} | public | Get one match |
| POST | /matches | logged in | Create match (you become the owner) |
| PATCH | /matches/{id}/score | owner or admin | Update score and status |
| DELETE | /matches/{id} | owner or admin | Delete match |
| GET | /leaderboard | public | Standings from finished matches (win 3, draw 1, loss 0) |
| WS | /ws/matches/{id} | public | Live score updates for one match |
| WS | /ws/leaderboard | public | Signals when standings change |

List endpoints return `{ "items": [...], "total": N, "limit": L, "offset": O }`.

## Roadmap

- [x] Stage 1: config, response models, error handling, authorization
- [x] Stage 2: PostgreSQL, Alembic migrations, matches and leaderboard, pagination, pytest
- [x] Stage 3: Redis caching, rate limiting
- [x] Stage 4: Celery background jobs, WebSocket live updates
- [ ] Stage 5: Docker, GitHub Actions CI, AWS deployment
- [ ] AI module: RAG question answering with pgvector
