# Authentication utilities for password hashing and JWT token creation/verification.
# Coded by LF using copilot inline additions, Copilot added comments afterwards.
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import logging
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# Load the signing secret from the environment.  In production this MUST be a
# long, unpredictable value set via the SECRET_KEY env var.  The fallback
# default is intentionally weak and is for local development only.
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-change-me-please-very-long-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def _truncate_to_72_bytes(s: str) -> bytes:
    """Truncate a UTF-8 string to at most 72 bytes.

    bcrypt silently ignores bytes beyond the 72-byte limit, which can cause
    two different passwords to produce the same hash.  We truncate explicitly
    at the byte level (not character level) to ensure consistent, safe behaviour.
    """
    b = s.encode("utf-8")
    return b[:72] if len(b) > 72 else b


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*.

    Uses the bcrypt library directly to avoid passlib backend-detection issues.
    The password is truncated to 72 bytes before hashing (see _truncate_to_72_bytes).
    """
    pw = _truncate_to_72_bytes(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if *password* matches the stored bcrypt *password_hash*."""
    pw = _truncate_to_72_bytes(password)
    try:
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create a signed HS256 JWT.

    Args:
        subject: The token subject — typically the user's id as a string.
        expires_minutes: Token lifetime in minutes (default: ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        A compact, URL-safe JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT, returning its payload.

    Raises:
        jose.JWTError: If the token is malformed, expired, or has an invalid signature.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
