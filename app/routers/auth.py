# This file created at the time of JWT first initial implementation.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, crud
from ..database import get_db
from ..auth import create_access_token

router = APIRouter()

# REGISTER
@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
  return crud.create_user(db, user)


# LOGIN But need to comment this to support Protected route using JWT.
#@router.post("/login", response_model=schemas.Token)
#def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
#  db_user = crud.authenticate_user(db, user.username, user.password)

#  if not db_user:
#    raise HTTPException(status_code=401, detail="Invalid credentials")

#  token = create_access_token({"sub": db_user.username})

#  return {"access_token": token, "token_type": "bearer"}

# Now ading this below line for login:

from fastapi.security import OAuth2PasswordRequestForm  # For supporting the authorization(lock) which shows in UI.
 
@router.post("/login", response_model=schemas.Token)
def login(
  form_data: OAuth2PasswordRequestForm = Depends(),
  db: Session = Depends(get_db)
):
  db_user = crud.authenticate_user(
    db,
    form_data.username,
    form_data.password
  )

  if not db_user:
    raise HTTPException(status_code=401, detail="Invalid credentials")

  token = create_access_token({"sub": db_user.username})

  return {
    "access_token": token,
    "token_type": "bearer"
  }
