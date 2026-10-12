from fastapi import FastAPI

from .routers import auth, matches, player

# The database schema is now created by Alembic migrations: run `alembic upgrade head`.
app = FastAPI(title="Match Score API")
app.include_router(auth.router)
app.include_router(player.router)
app.include_router(matches.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
