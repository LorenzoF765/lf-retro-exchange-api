from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
import os

from .db import Base, engine
from .routers import auth as auth_router
from .routers import users as users_router
from .routers import games as games_router
from .routers import offers as offers_router  # make sure this exists
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import socket

app = FastAPI(
    title="Retro Video Game Exchange API",
    version="1.0.0",
    description="A REST API for registering users and trading retro video games (RMM Level 3 / HATEOAS).",
)

# Application entry and routing configuration. Coded by LF using copilot inline additions, Copilot added comments afterwards.

# Defer DB initialization until startup so the container can wait for Postgres to be ready.
import time
from sqlalchemy.exc import OperationalError


@app.on_event("startup")
def startup_db():
    """Wait for the database to become available, then create tables."""
    retries = 12
    delay = 2
    for attempt in range(retries):
        try:
            # Quick connectivity check
            with engine.connect() as conn:
                # SQLAlchemy 2.0: use exec_driver_sql or text() for plain SQL
                conn.exec_driver_sql("SELECT 1")
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:
            # If last attempt, re-raise so failures are visible in logs
            if attempt == retries - 1:
                raise
            time.sleep(delay)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(games_router.router)
app.include_router(offers_router.router)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "retro_api_requests_total", "Total HTTP requests", ["method", "endpoint", "http_status"]
)
REQUEST_LATENCY = Histogram("retro_api_request_latency_seconds", "Request latency seconds", ["endpoint"])


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    resp_time = time.time() - start
    endpoint = request.url.path
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(resp_time)
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=str(response.status_code)).inc()
    return response


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    """Health endpoint that checks database connectivity and Kafka broker reachability.

    Returns 200 when all components are reachable, 503 otherwise.
    """
    components = {}
    overall_ok = True

    # DB health
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        components["database"] = {"status": "up"}
    except Exception as exc:
        components["database"] = {"status": "down", "error": str(exc)}
        overall_ok = False

    # Kafka health (TCP connect to bootstrap servers)
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    brokers = []
    kafka_ok = False
    for ep in kafka_bootstrap.split(","):
        host, sep, port = ep.partition(":")
        try:
            port_num = int(port) if port else 9092
            sock = socket.create_connection((host, port_num), timeout=2)
            sock.close()
            brokers.append({"endpoint": ep, "status": "up"})
            kafka_ok = True
        except Exception as exc:
            brokers.append({"endpoint": ep, "status": "down", "error": str(exc)})
    components["kafka"] = {"status": "up" if kafka_ok else "down", "brokers": brokers}
    if not kafka_ok:
        overall_ok = False

    status_code = 200 if overall_ok else 503
    return JSONResponse(status_code=status_code, content={"status": "ok" if overall_ok else "degraded", "components": components})

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )

@app.get("/api", tags=["root"])
def api_root():
    return {
        "name": "Retro Video Game Exchange API",
        "_links": {
            "register": {"href": "/api/users", "method": "POST"},
            "login": {"href": "/api/auth/token", "method": "POST"},
            "me": {"href": "/api/users/me", "method": "GET"},
            "games": {"href": "/api/games", "method": "GET"},
            "offers": {"href": "/api/offers", "method": "POST"},
            "incoming_offers": {"href": "/api/offers/incoming", "method": "GET"},
            "outgoing_offers": {"href": "/api/offers/outgoing", "method": "GET"},
        },
    }
