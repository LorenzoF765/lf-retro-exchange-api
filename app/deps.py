# Dependency utilities for FastAPI routes, including DB session and user resolution. Coded by LF, comments provided by Copilot
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import SessionLocal
from . import models
from .auth import decode_token
from .errors import http_error

# HTTPBearer security dependency (won't raise automatically so we can return structured errors)
bearer = HTTPBearer(auto_error=False)

def get_db():
    """Request-scoped DB session. Yields a session and ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    """Resolve the current user from a Bearer JWT token.

    Validates the token, extracts the subject (user id), and fetches the
    corresponding User record. Raises structured http_error on failures.
    """
    if creds is None or not creds.credentials:
        raise http_error(401, "AUTH_REQUIRED", "Missing Bearer token")

    try:
        payload = decode_token(creds.credentials)
        subject = payload.get("sub")
        if not subject:
            raise http_error(401, "INVALID_TOKEN", "Token missing subject")
        user_id = int(subject)
    except Exception:
        raise http_error(401, "INVALID_TOKEN", "Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise http_error(401, "INVALID_TOKEN", "User not found for token")
    return user
