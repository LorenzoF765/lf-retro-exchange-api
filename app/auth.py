# Authentication utilities for password hashing and JWT handling. Coded by LF using copilot inline additions, Copilot added comments afterwards.
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

# Development secret - replace in production
SECRET_KEY = "dev-only-change-me-please-very-long-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Return a bcrypt hash of the provided password."""
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(password, password_hash)

def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create a signed JWT with a subject and expiry timestamp."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT, returning its payload (raises on invalid/expired)."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
