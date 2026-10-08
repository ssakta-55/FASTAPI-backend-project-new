# Match Score API

A FastAPI backend for managing players and matches, with JWT authentication, role-based access and owner-only editing.

**Stack:** Python, FastAPI, SQLAlchemy, Pydantic, JWT (python-jose), bcrypt, SQLite (PostgreSQL planned)

## Run locally

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then set SECRET_KEY
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.

Generate a secret key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

Make a user an admin: `python -m app.make_admin <username>`

## Endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | /health | public | Health check |
| POST | /register | public | Create account (409 if username taken) |
| POST | /login | public | Get JWT access token |
| GET | /me | logged in | Current user |
| GET | /users | admin | List all users |
| GET | /players | public | List players |
| GET | /player/{id} | public | Get one player |
| POST | /player | logged in | Create player (you become the owner) |
| PUT | /player/{id} | owner or admin | Update player |
| DELETE | /player/{id} | owner or admin | Delete player |

## Roadmap

- [x] Stage 1: config, response models, error handling, authorization
- [ ] Stage 2: PostgreSQL, Alembic migrations, pagination, pytest
- [ ] Stage 3: Redis caching, rate limiting
- [ ] Stage 4: Celery background jobs, WebSocket live updates
- [ ] Stage 5: Docker, GitHub Actions CI, AWS deployment
