# Main application entry point for the Retro Video Game Exchange API.
# Coded by Lorenzo Franco using copilot for inline assistance, as well as for adding these comments afterwards.

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .db import Base, engine
from .routers import auth as auth_router
from .routers import users as users_router
from .routers import games as games_router
from .routers import offers as offers_router  # NEW

# FastAPI application metadata (used by OpenAPI docs)
app = FastAPI(
    title="Retro Video Game Exchange API",
    version="1.0.0",
    description="A REST API for registering users and trading retro video games (RMM Level 3 / HATEOAS).",
)

# Used to prove load balancing (api1/api2) behind NGINX.
# In local dev this will just be "local" unless you set it.
INSTANCE_ID = os.getenv("INSTANCE_ID", "local")


@app.middleware("http")
async def add_instance_header(request: Request, call_next):
    """Attach an instance identifier to every response (useful for verifying round-robin load balancing)."""
    response = await call_next(request)
    response.headers["X-Instance-Id"] = INSTANCE_ID
    return response


# Ensure DB tables exist at startup (using SQLAlchemy metadata)
Base.metadata.create_all(bind=engine)

# Register API routers (auth, users, games, offers)
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(games_router.router)
app.include_router(offers_router.router)  # NEW


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert FastAPI validation errors into a consistent JSON error shape."""
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
    """Root resource that exposes top-level HATEOAS links for the API."""
    return {
        "name": "Retro Video Game Exchange API",
        "_links": {
            "register": {"href": "/api/users", "method": "POST"},
            "login": {"href": "/api/auth/token", "method": "POST"},
            "me": {"href": "/api/users/me", "method": "GET"},
            "games": {"href": "/api/games", "method": "GET"},
            "offers": {"href": "/api/offers", "method": "POST"},          # NEW
            "incoming_offers": {"href": "/api/offers/incoming", "method": "GET"},  # NEW
            "outgoing_offers": {"href": "/api/offers/outgoing", "method": "GET"},  # NEW
        }
    }
