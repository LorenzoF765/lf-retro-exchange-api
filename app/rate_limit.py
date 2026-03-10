# Distributed rate limiting middleware using Redis as shared state.
# Coded by LF using copilot inline additions, Copilot added comments afterwards.

import logging
import os
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# --- Prometheus metrics for rate limiting ---
RATE_LIMIT_REJECTED = Counter(
    "rate_limit_requests_rejected_total",
    "Total requests rejected by rate limiter",
    ["endpoint", "client_ip"],
)
RATE_LIMIT_CHECK_LATENCY = Histogram(
    "rate_limit_check_duration_seconds",
    "Time spent checking rate limit in Redis",
)

# --- Configuration from environment ---
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Global limit: requests per window per client (IP or user)
GLOBAL_RATE_LIMIT = int(os.getenv("RATE_LIMIT_GLOBAL", "100"))
GLOBAL_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Endpoint-specific overrides: path_prefix -> (limit, window_seconds)
ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
    "/api/games":       (30, 60),   # expensive search endpoint
    "/api/offers":      (20, 60),   # offer creation / listing
    "/api/auth/token":  (10, 60),   # login — protect against credential stuffing
    "/api/users":       (10, 60),   # registration
}

# Burst multiplier: clients may burst up to this multiple of the limit
BURST_MULTIPLIER = float(os.getenv("RATE_LIMIT_BURST_MULTIPLIER", "1.5"))

# Paths that are never rate-limited (metrics, health, docs)
EXEMPT_PATHS = {"/metrics", "/health", "/docs", "/openapi.json", "/redoc"}

# Lazy Redis client — initialized on first request and re-attempted after
# each failed connection attempt (so rate limiting recovers when Redis restarts).
_redis_client = None
_redis_last_failed_at: float = 0.0
# Wait at least this many seconds before retrying a failed Redis connection.
_REDIS_RETRY_INTERVAL = 30.0


def _get_redis():
    """Return a Redis client, retrying the connection after a cooldown period.

    On first call (or after a failed attempt) this tries to connect to Redis.
    If the connection fails, ``None`` is returned and the caller falls back to
    fail-open behaviour.  The next call after ``_REDIS_RETRY_INTERVAL`` seconds
    will attempt to reconnect, allowing the middleware to recover automatically
    when Redis comes back online.
    """
    global _redis_client, _redis_last_failed_at

    if _redis_client is not None:
        return _redis_client

    # Honour the retry cooldown — don't hammer Redis on every request.
    if time.time() - _redis_last_failed_at < _REDIS_RETRY_INTERVAL:
        return None

    try:
        import redis
        client = redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        _redis_client = client
        logger.info("Rate limiter connected to Redis at %s", REDIS_URL)
    except Exception as exc:
        _redis_last_failed_at = time.time()
        logger.warning("Redis unavailable, rate limiting disabled (will retry in %ds): %s", int(_REDIS_RETRY_INTERVAL), exc)
        _redis_client = None
    return _redis_client


def _client_id(request: Request) -> str:
    """Derive a stable client identifier (authenticated user id or IP address)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    return ip


def _resolve_limit(path: str) -> tuple[int, int]:
    """Return (limit, window_seconds) for the given request path."""
    for prefix, (limit, window) in ENDPOINT_LIMITS.items():
        if path.startswith(prefix):
            return limit, window
    return GLOBAL_RATE_LIMIT, GLOBAL_WINDOW_SECONDS


def _check_sliding_window(redis_client, key: str, limit: int, window: int) -> tuple[bool, int]:
    """
    Sliding-window rate limit check using a Redis sorted set.

    Returns (allowed: bool, current_count: int).
    Uses an atomic Lua script so all operations happen in a single Redis round-trip.
    """
    now = time.time()
    window_start = now - window

    lua_script = """
    local key        = KEYS[1]
    local now        = tonumber(ARGV[1])
    local window_start = tonumber(ARGV[2])
    local limit      = tonumber(ARGV[3])
    local window     = tonumber(ARGV[4])

    -- Remove entries outside the current window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

    -- Count remaining entries
    local count = redis.call('ZCARD', key)

    if count < limit then
        -- Allow: add this request with timestamp as both score and member
        redis.call('ZADD', key, now, now)
        redis.call('EXPIRE', key, window)
        return {1, count + 1}
    else
        return {0, count}
    end
    """

    try:
        result = redis_client.eval(lua_script, 1, key, now, window_start, limit, window)
        allowed = bool(result[0])
        count = int(result[1])
        return allowed, count
    except Exception as exc:
        # Redis call failed mid-request — reset client so the next request
        # triggers a fresh connection attempt via _get_redis().
        global _redis_client, _redis_last_failed_at
        _redis_client = None
        _redis_last_failed_at = time.time()
        logger.warning("Rate limit Redis eval failed, allowing request: %s", exc)
        return True, 0


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware that enforces distributed rate limits via Redis.

    - Exempt paths (/health, /metrics, /docs) are always allowed.
    - On Redis failure, requests are allowed (fail open).
    - Returns 429 with Retry-After header when limit exceeded.
    """
    path = request.url.path

    # Skip rate limiting for exempt paths
    if path in EXEMPT_PATHS or path.startswith("/static"):
        return await call_next(request)

    redis_client = _get_redis()

    # If Redis is unavailable, allow request and log
    if redis_client is None:
        logger.warning("Rate limiting skipped (Redis unavailable) for %s", path)
        return await call_next(request)

    client_id = _client_id(request)
    limit, window = _resolve_limit(path)

    # Apply burst allowance
    effective_limit = int(limit * BURST_MULTIPLIER)

    # Build a Redis key scoped to client + endpoint bucket
    endpoint_bucket = path.split("/")[2] if path.count("/") >= 2 else "root"
    redis_key = f"rl:{client_id}:{endpoint_bucket}"

    start = time.time()
    try:
        allowed, count = _check_sliding_window(redis_client, redis_key, effective_limit, window)
    except Exception as exc:
        logger.warning("Rate limit check error, allowing request: %s", exc)
        allowed, count = True, 0
    finally:
        RATE_LIMIT_CHECK_LATENCY.observe(time.time() - start)

    if not allowed:
        RATE_LIMIT_REJECTED.labels(endpoint=path, client_ip=client_id).inc()
        logger.warning("Rate limit exceeded: client=%s path=%s count=%d limit=%d", client_id, path, count, effective_limit)
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(window)},
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Limit is {limit} per {window}s. Retry after {window} seconds.",
                }
            },
        )

    return await call_next(request)
