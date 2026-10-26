from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..realtime import manager

router = APIRouter(tags=["realtime"])


def _snapshot(db: Session, match_id: int):
    match = crud.get_match(db, match_id)
    if match is None:
        return None
    return schemas.MatchResponse.model_validate(match).model_dump(mode="json")


async def _listen(topic: str, websocket: WebSocket, first_message: dict) -> None:
    await manager.connect(topic, websocket)
    try:
        await websocket.send_json(first_message)
        while True:
            await websocket.receive_text()  # we ignore what clients say; this notices a disconnect
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(topic, websocket)


@router.websocket("/ws/matches/{match_id}")
async def match_updates(websocket: WebSocket, match_id: int, db: Session = Depends(get_db)):
    """Public. Sends the current match first, then every score update."""
    snapshot = await run_in_threadpool(_snapshot, db, match_id)
    db.close()  # a socket can stay open for hours: give the DB connection back now
    if snapshot is None:
        await websocket.close(code=4404)
        return
    await _listen(f"match:{match_id}", websocket, {"type": "snapshot", "match": snapshot})


@router.websocket("/ws/leaderboard")
async def leaderboard_updates(websocket: WebSocket):
    """Public. Says 'leaderboard_changed'; the client then calls GET /leaderboard."""
    await _listen("leaderboard", websocket, {"type": "connected"})
