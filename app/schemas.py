from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MatchStatus = Literal["scheduled", "live", "finished"]


# ---- users ----
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class UserResponse(BaseModel):
    # No password field here, so the hash can never leak in a response.
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


# ---- players ----
class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    team: str = Field(min_length=1, max_length=50)


class PlayerResponse(BaseModel):
    id: int
    name: str
    team: str
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


class PlayerPage(BaseModel):
    items: List[PlayerResponse]
    total: int
    limit: int
    offset: int


# ---- matches ----
class MatchCreate(BaseModel):
    home_team: str = Field(min_length=1, max_length=50)
    away_team: str = Field(min_length=1, max_length=50)

    @field_validator("home_team", "away_team")
    @classmethod
    def strip_spaces(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("team name cannot be blank")
        return value

    @model_validator(mode="after")
    def teams_must_differ(self):
        if self.home_team.lower() == self.away_team.lower():
            raise ValueError("home_team and away_team must be different")
        return self


class MatchScoreUpdate(BaseModel):
    home_score: int = Field(ge=0, le=999)
    away_score: int = Field(ge=0, le=999)
    status: Optional[MatchStatus] = None  # leave out to keep the current status


class MatchResponse(BaseModel):
    id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchPage(BaseModel):
    items: List[MatchResponse]
    total: int
    limit: int
    offset: int


class LeaderboardRow(BaseModel):
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
