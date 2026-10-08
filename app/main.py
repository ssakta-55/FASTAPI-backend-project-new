from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, player

Base.metadata.create_all(bind=engine)  # replaced by Alembic migrations in Stage 2

app = FastAPI(title="Match Score API")
app.include_router(auth.router)
app.include_router(player.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
