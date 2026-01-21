# lf-retro-exchange-api

Retro Video Game Exchange REST API

A RESTful API built with Python and FastAPI that allows users to register accounts and manage retro video games they wish to trade with others. The API supports authenticated access, owner-restricted updates, search functionality, and is fully compliant with Richardson Maturity Model Level 3 (HATEOAS).

📌 Features

User self-registration

JWT-based authentication

Authenticated CRUD operations for retro video games

Search and pagination for games

Owner-only update and delete permissions

Full HATEOAS (_links) support (RMM Level 3)

OpenAPI documentation (Swagger)

JSON-based request and response bodies

Persistent storage using SQLite (easily swappable with other databases)

Consistent error handling with HTTP status codes and JSON error envelopes

🧱 Technology Stack

Python 3.11

FastAPI

SQLAlchemy

Pydantic

JWT (python-jose)

SQLite

Uvicorn

🚀 Getting Started
1. Clone the repository
git clone <your-github-repo-url>
cd lf-retro-exchange-api

2. Create and activate a virtual environment
python -m venv .venv


Windows:

.\.venv\Scripts\Activate.ps1


macOS/Linux:

source .venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Run the API
python -m uvicorn app.main:app --reload


The API will be available at:

http://127.0.0.1:8000

📘 API Documentation (OpenAPI)

FastAPI automatically generates OpenAPI documentation:

Swagger UI:
👉 http://127.0.0.1:8000/docs

OpenAPI JSON:
👉 http://127.0.0.1:8000/openapi.json

These endpoints satisfy the OpenAPI technical requirement.

🔐 Authentication Flow

Authentication uses JWT Bearer tokens.

Public Endpoints

POST /api/users — Register a new user

POST /api/auth/token — Login and receive a JWT

Authenticated Endpoints

All other endpoints require a valid Bearer token in the Authorization header.

Example:

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
Create a game (authenticated)

POST /api/games

{
  "name": "Chrono Trigger",
  "publisher": "Square",
  "year_published": 1995,
  "system": "SNES",
  "condition": "good",
  "previous_owners": 2
}

List / Search games (authenticated)

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

Get a specific game

GET /api/games/{gameId}

Update a game (owner only)

PUT /api/games/{gameId}

Delete a game (owner only)

DELETE /api/games/{gameId}

🔗 HATEOAS & Richardson Maturity Model (Level 3)

This API is compliant with Richardson Maturity Model Level 3.

How this is demonstrated:

All responses include _links

Clients discover allowed actions dynamically

Owner-specific actions (update, delete) appear only when authorized

Collection resources provide paging and creation links

Example response snippet:
"_links": {
  "self": { "href": "/api/games/1" },
  "owner": { "href": "/api/users/1" },
  "update": { "href": "/api/games/1", "method": "PUT" },
  "delete": { "href": "/api/games/1", "method": "DELETE" },
  "collection": { "href": "/api/games" }
}


If the requester is not the owner, update and delete links are omitted.

❗ Error Handling

Errors are returned using:

Correct HTTP status codes (400, 401, 403, 404, 409, 422)

A consistent JSON structure:

{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only the owner may update this game",
    "details": {}
  }
}

📂 Project Structure
lf-retro-exchange-api/
│── .venv/
│── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── games.py
│   ├── auth.py
│   ├── db.py
│   ├── deps.py
│   ├── errors.py
│   ├── hateoas.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── __init__.py
│── requirements.txt
│── README.md

📦 Database

Uses SQLite by default (retro_exchange.db)

Automatically created on first run

Can be replaced with PostgreSQL or another database by changing the SQLAlchemy connection string