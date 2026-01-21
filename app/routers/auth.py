# Authentication router for user login and JWT token issuance. Coded by Copilot with minor edits by LF
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from jose import JWTError

from .. import models, schemas
from ..deps import get_db
from ..auth import verify_password, create_access_token
from ..errors import http_error

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/token", response_model=schemas.TokenResponse)
def login(req: schemas.TokenRequest, db: Session = Depends(get_db)):
    """Authenticate user with email/password and return a JWT on success."""
    # Normalize email case when looking up the user
    user = db.query(models.User).filter(models.User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise http_error(401, "INVALID_CREDENTIALS", "Email or password is incorrect")

    # Issue a token containing the user's id as the subject
    token = create_access_token(subject=str(user.id))
    return schemas.TokenResponse(access_token=token)
