# ---- Base image ----
FROM python:3.11-slim

# ---- Environment defaults ----
# Prevents Python from writing .pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- App working directory ----
WORKDIR /app

# ---- System dependencies (optional but common) ----
# curl is useful for healthchecks/debug, build-essential for some pip wheels if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# ---- Install Python dependencies first (better Docker layer caching) ----
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy application code ----
COPY . /app

# ---- Database environment variables ----
# Your app should read DATABASE_URL if present.
# If not set, it will default to SQLite (see note below).
#
# PostgreSQL-style env vars (meets assignment requirement for DB connection parameters):
ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_USER=retro_user
ENV DB_PASSWORD=retro_pass
ENV DB_NAME=retro_exchange

# Optional: direct SQLAlchemy URL override (recommended pattern)
# Example for Postgres:
#   postgresql+psycopg2://retro_user:retro_pass@db:5432/retro_exchange
ENV DATABASE_URL="sqlite:///./retro_exchange.db"

# ---- Expose port ----
EXPOSE 8000

# ---- Run the API ----
# Using python -m ensures we use the correct module and environment
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
