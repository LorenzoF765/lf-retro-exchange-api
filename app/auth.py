# Authentication utilities for password hashing and JWT handling. Coded by LF using copilot inline additions, Copilot added comments afterwards.
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import logging
import bcrypt

# Development secret - replace in production
SECRET_KEY = "dev-only-change-me-please-very-long-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

logger = logging.getLogger(__name__)


def _truncate_bytes_to_72_bytes(s: str) -> bytes:
    b = s.encode("utf-8")
    if len(b) <= 72:
        return b
    return b[:72]


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the provided password using the bcrypt library.

    This avoids passlib backend detection issues at runtime. Truncates the
    password to 72 bytes (bcrypt limit) at the byte level.
    """
    pw = _truncate_bytes_to_72_bytes(password)
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    pw = _truncate_bytes_to_72_bytes(password)
    try:
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except Exception:
        return False

def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create a signed JWT with a subject and expiry timestamp."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT, returning its payload (raises on invalid/expired)."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
