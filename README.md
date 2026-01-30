
# Retro Video Game Exchange REST API

A RESTful API built with Python and FastAPI that allows users to register accounts, manage retro video games, and create trade offers with other users.
The system is deployed as a multi-container Docker application with NGINX load balancing and PostgreSQL-backed persistence, and is compliant with Richardson Maturity Model Level 3 (HATEOAS).

This project was developed for CSC380 to demonstrate service-oriented architectures, distributed systems concepts, containerization, and load-balanced deployments.

✨ Features
Core

User self-registration

JWT-based authentication

Authenticated CRUD operations for retro video games

Owner-restricted updates and deletes

Search and pagination

Full HATEOAS support (_links) — RMM Level 3

OpenAPI documentation (Swagger)

Consistent JSON error envelopes

Trade Offers (Distributed Feature)

Browse games owned by other users

Create trade offers (offer one owned game in exchange for another)

View incoming and outgoing offers

Accept or reject offers (owner-only)

Offer state tracking: pending, accepted, rejected

Deployment & Infrastructure

Dockerized API

Two API instances running in parallel

PostgreSQL shared database

NGINX load balancer with round-robin routing

Internal service-to-service routing via Docker network (no localhost forwarding)

🧱 Technology Stack

Python 3.11

FastAPI

SQLAlchemy

Pydantic

PostgreSQL

JWT (python-jose)

Uvicorn

Docker & Docker Compose

NGINX

🚀 Getting Started (Docker – Recommended)
Prerequisites

Docker Desktop (Windows/macOS/Linux)

Docker Compose (included with Docker Desktop)

1. Clone the repository
git clone <your-github-repo-url>
cd lf-retro-exchange-api

2. Build and run the full stack
docker compose up --build


This starts:

db → PostgreSQL

api1 → FastAPI instance

api2 → FastAPI instance

nginx → Load balancer

3. Access the API (via NGINX load balancer)

API Root
👉 http://localhost:8080/api

Swagger UI (OpenAPI)
👉 http://localhost:8080/docs

4. Verifying Load Balancing (Required for Lab)

Every response includes:

X-Instance-Id: api1 | api2


Test:

curl -I http://localhost:8080/api


Repeated requests will alternate between api1 and api2, demonstrating round-robin distribution.

🌐 NGINX Networking Compliance

The NGINX load balancer routes requests only within the Docker network, as required.

Example upstream configuration:

upstream retro_api {
    server api1:8000;
    server api2:8000;
}


NGINX does not forward traffic to localhost. All backend communication uses Docker DNS service names.

🔐 Authentication Flow

Authentication uses JWT Bearer tokens.

Public Endpoints

POST /api/users — Register a user

POST /api/auth/token — Login and receive a JWT

Authenticated Endpoints

All other endpoints require:

Authorization: Bearer <access_token>

👤 User Endpoints
Register

POST /api/users

{
  "name": "Test User",
  "email": "test@example.com",
  "password": "Password123!",
  "street_address": "123 Main St"
}

Login

POST /api/auth/token

{
  "email": "test@example.com",
  "password": "Password123!"
}

Get current user

GET /api/users/me

Update current user (self-only)

PUT /api/users/{userId}

⚠️ Email address cannot be changed.

🎮 Video Game Endpoints
Create a game

POST /api/games

{
  "name": "Chrono Trigger",
  "publisher": "Square",
  "year_published": 1995,
  "system": "SNES",
  "condition": "good",
  "previous_owners": 2
}

List / Search games

GET /api/games

Optional query parameters:

name

publisher

system

condition

year

yearMin

yearMax

ownerId

page

pageSize

Game detail

GET /api/games/{gameId}

Update (owner only)

PUT /api/games/{gameId}

Delete (owner only)

DELETE /api/games/{gameId}

🔁 Trade Offer Endpoints
Create an offer

POST /api/offers

{
  "requested_game_id": 12,
  "offered_game_id": 5
}

View incoming offers

GET /api/offers/incoming

View outgoing offers

GET /api/offers/outgoing

Accept or reject an offer

POST /api/offers/{offerId}/decision

{
  "decision": "accepted"
}

🔗 HATEOAS & Richardson Maturity Model (Level 3)

This API is fully compliant with RMM Level 3.

Demonstrated via:

_links in all responses

Dynamic discovery of allowed actions

Owner-only actions shown conditionally

Collection pagination links

Example:

"_links": {
  "self": { "href": "/api/games/1" },
  "owner": { "href": "/api/users/1" },
  "update": { "href": "/api/games/1", "method": "PUT" },
  "delete": { "href": "/api/games/1", "method": "DELETE" },
  "collection": { "href": "/api/games" }
}

❗ Error Handling

Errors return:

Proper HTTP status codes (400, 401, 403, 404, 409, 422)

Consistent JSON shape:

{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only the owner may update this game",
    "details": {}
  }
}

📂 Project Structure
lf-retro-exchange-api/
│── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── games.py
│   │   └── offers.py
│   ├── auth.py
│   ├── db.py
│   ├── deps.py
│   ├── errors.py
│   ├── hateoas.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── __init__.py
│── nginx/
│   ├── Dockerfile
│   └── nginx.conf
│── Dockerfile
│── docker-compose.yaml
│── requirements.txt
│── README.md

🗄 Database

PostgreSQL (Dockerized)

Shared between both API instances

Schema initialized by a single container (DB_INIT=1) to prevent race conditions
