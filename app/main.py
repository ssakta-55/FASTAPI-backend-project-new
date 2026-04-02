from fastapi import FastAPI
from .database import engine, Base
from .routers import player

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(player.router)

# Now below implementation used for JWT implementation.

from .routers import auth

app.include_router(auth.router)
