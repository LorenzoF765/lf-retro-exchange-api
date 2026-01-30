# User management API routes for registration, profile retrieval, and updates. Coded by LF, comments provided by Copilot
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..deps import get_db, get_current_user
from ..auth import hash_password
from ..errors import http_error
from ..hateoas import user_links

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("", response_model=schemas.UserOut, status_code=201)
def register_user(payload: schemas.UserRegister, response: Response, db: Session = Depends(get_db)):
    """Register a new user, hashing the password and returning the created resource."""
    user = models.User(
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        street_address=payload.street_address,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Unique constraint on email violated
        db.rollback()
        raise http_error(409, "EMAIL_IN_USE", "That email address is already registered")

    db.refresh(user)
    response.headers["Location"] = f"/api/users/{user.id}"

    return schemas.UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        street_address=user.street_address,
        links=user_links(user.id, is_self=True),
    )

@router.get("/me", response_model=schemas.UserOut)
def get_me(current: models.User = Depends(get_current_user)):
    """Return the currently-authenticated user's public profile."""
    return schemas.UserOut(
        id=current.id,
        name=current.name,
        email=current.email,
        street_address=current.street_address,
        links=user_links(current.id, is_self=True),
    )

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Return a user's public profile by id, showing different links if it's the requester."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise http_error(404, "NOT_FOUND", "User not found")

    is_self = (current.id == user.id)
    return schemas.UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        street_address=user.street_address,
        links=user_links(user.id, is_self=is_self),
    )

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Allow users to update their own profile fields (name, street_address)."""
    if current.id != user_id:
        raise http_error(403, "FORBIDDEN", "You may only update your own user details")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise http_error(404, "NOT_FOUND", "User not found")

    if payload.name is not None:
        user.name = payload.name
    if payload.street_address is not None:
        user.street_address = payload.street_address

    db.commit()
    db.refresh(user)

    return schemas.UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        street_address=user.street_address,
        links=user_links(user.id, is_self=True),
    )
