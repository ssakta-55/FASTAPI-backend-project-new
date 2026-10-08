from pydantic import BaseModel, ConfigDict, Field


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


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    team: str = Field(min_length=1, max_length=50)


class PlayerResponse(BaseModel):
    id: int
    name: str
    team: str
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
