"""Database operations only. HTTP errors are handled in the routers."""
from typing import Optional

from sqlalchemy import case, func, select, union_all
from sqlalchemy.orm import Session

from .models import MatchDB, PlayerDB, UserDB


# ---- users ----
def get_user_by_username(db: Session, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()


def list_users(db: Session):
    return db.query(UserDB).all()


def create_user(db: Session, username: str, hashed_password: str):
    user = UserDB(username=username, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---- players ----
def get_players(db: Session, limit: int, offset: int):
    return db.query(PlayerDB).order_by(PlayerDB.id).limit(limit).offset(offset).all()


def count_players(db: Session) -> int:
    return db.query(func.count(PlayerDB.id)).scalar()


def get_player(db: Session, player_id: int):
    return db.query(PlayerDB).filter(PlayerDB.id == player_id).first()


def create_player(db: Session, name: str, team: str, owner_id: int):
    player = PlayerDB(name=name, team=team, owner_id=owner_id)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def update_player(db: Session, player: PlayerDB, name: str, team: str):
    player.name = name
    player.team = team
    db.commit()
    db.refresh(player)
    return player


def delete_player(db: Session, player: PlayerDB):
    db.delete(player)
    db.commit()


# ---- matches ----
def _match_query(db: Session, status: Optional[str]):
    query = db.query(MatchDB)
    if status:
        query = query.filter(MatchDB.status == status)
    return query


def get_matches(db: Session, limit: int, offset: int, status: Optional[str] = None):
    return (
        _match_query(db, status)
        .order_by(MatchDB.id.desc())  # newest first
        .limit(limit)
        .offset(offset)
        .all()
    )


def count_matches(db: Session, status: Optional[str] = None) -> int:
    return _match_query(db, status).count()


def get_match(db: Session, match_id: int):
    return db.query(MatchDB).filter(MatchDB.id == match_id).first()


def create_match(db: Session, home_team: str, away_team: str, created_by: int):
    match = MatchDB(home_team=home_team, away_team=away_team, created_by=created_by)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def update_match_score(
    db: Session, match: MatchDB, home_score: int, away_score: int, status: Optional[str]
):
    match.home_score = home_score
    match.away_score = away_score
    if status is not None:
        match.status = status
    db.commit()
    db.refresh(match)
    return match


def delete_match(db: Session, match: MatchDB):
    db.delete(match)
    db.commit()


def get_leaderboard(db: Session):
    """Standings from finished matches: win = 3 points, draw = 1, loss = 0.

    Every match counts twice, once from the home team's view and once from the
    away team's view. We stack both views with UNION ALL, then GROUP BY team.
    """
    m = MatchDB

    def team_view(team, goals_for, goals_against):
        return select(
            team.label("team"),
            goals_for.label("gf"),
            goals_against.label("ga"),
            case((goals_for > goals_against, 1), else_=0).label("won"),
            case((goals_for == goals_against, 1), else_=0).label("drawn"),
            case((goals_for < goals_against, 1), else_=0).label("lost"),
        ).where(m.status == "finished")

    views = union_all(
        team_view(m.home_team, m.home_score, m.away_score),
        team_view(m.away_team, m.away_score, m.home_score),
    ).subquery()

    stmt = select(
        views.c.team,
        func.count().label("played"),
        func.sum(views.c.won).label("won"),
        func.sum(views.c.drawn).label("drawn"),
        func.sum(views.c.lost).label("lost"),
        func.sum(views.c.gf).label("goals_for"),
        func.sum(views.c.ga).label("goals_against"),
    ).group_by(views.c.team)

    table = []
    for row in db.execute(stmt).all():
        won, drawn = int(row.won), int(row.drawn)
        table.append(
            {
                "team": row.team,
                "played": int(row.played),
                "won": won,
                "drawn": drawn,
                "lost": int(row.lost),
                "goals_for": int(row.goals_for),
                "goals_against": int(row.goals_against),
                "goal_difference": int(row.goals_for) - int(row.goals_against),
                "points": 3 * won + drawn,
            }
        )
    table.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    return table
