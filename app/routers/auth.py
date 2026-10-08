from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from ..database import get_db

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    return crud.create_user(db, user.username, hash_password(user.password))


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, form_data.username)
    # Same message for "no such user" and "wrong password" on purpose.
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def read_me(current_user: models.UserDB = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[schemas.UserResponse])
def list_all_users(
    db: Session = Depends(get_db), admin: models.UserDB = Depends(require_admin)
):
    return crud.list_users(db)
