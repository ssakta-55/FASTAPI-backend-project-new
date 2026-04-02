from pydantic import BaseModel, Field

class PlayerCreate(BaseModel):
  # 🔥 Validation added
  name: str = Field(..., min_length=1, max_length=50)
  team: str = Field(..., min_length=1, max_length=50)

#Field(...) → required field
# min_length=1 → empty allowed nahi
# max_length=50 → limit set

# Adding Response Model concept below:
class PlayerResponse(BaseModel):
  id: int
  name: str
  team: str

  class Config:
    from_attributes = True

# Adding concept of JWT below:
class UserCreate(BaseModel):
  username: str
  password: str


class Token(BaseModel):
  access_token: str
  token_type: str
