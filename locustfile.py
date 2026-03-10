# Attack simulation using Locust. Coded by LF using copilot inline additions, Copilot added comments afterwards.
#
# Run via docker compose:
#   docker compose up locust
# Or from the Locust web UI at http://localhost:8089
#
# Scenarios:
#   RetroApiUser      - normal user traffic (register, login, browse games)
#   DDoSUser          - high-volume flood targeting all endpoints (no auth)
#   CredentialStuffer - rapid login attempts with wrong passwords
#   SlowRateUser      - low-and-slow requests to stay under obvious thresholds

import random
import string
import threading

from locust import HttpUser, task, between


def random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{suffix}@example.com"


def random_password(length: int = 12) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


# ---------------------------------------------------------------------------
# Normal user traffic — verifies legitimate requests are NOT blocked
# ---------------------------------------------------------------------------
class RetroApiUser(HttpUser):
    """Simulates a normal authenticated user browsing and playing with the API."""

    wait_time = between(1, 3)
    weight = 5

    # Class-level sequential counter so each spawned user gets a unique,
    # deterministic email address.  Using random emails meant all 31 users
    # attempted fresh registrations at startup, immediately hitting the
    # /api/users rate limit — leaving most users without a token and making
    # every subsequent task return 401 instead of exercising real behaviour.
    _lock = threading.Lock()
    _next_id = 0

    def on_start(self) -> None:
        with RetroApiUser._lock:
            RetroApiUser._next_id += 1
            uid = RetroApiUser._next_id

        # Deterministic credentials — the same user can log in across runs
        # without needing to re-register (handles 409 Conflict gracefully).
        self.email = f"locust_{uid:05d}@example.com"
        self.password = "Locust123!"
        self.token = None

        # Register — 201 on first run, 409 on subsequent runs (both are fine).
        reg = self.client.post("/api/users", json={
            "name": f"Locust User {uid}",
            "email": self.email,
            "password": self.password,
            "street_address": "123 Test St",
        })

        # Always attempt login regardless of registration outcome so users that
        # already exist (409) or were rate-limited (429) still get a token.
        if reg.status_code in (201, 409):
            login = self.client.post("/api/auth/token", json={
                "email": self.email,
                "password": self.password,
            })
            if login.status_code == 200:
                self.token = login.json().get("access_token")

    @property
    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(4)
    def list_games(self) -> None:
        self.client.get("/api/games", headers=self.auth_headers)

    @task(2)
    def get_root(self) -> None:
        self.client.get("/api")

    @task(1)
    def get_health(self) -> None:
        self.client.get("/health")


# ---------------------------------------------------------------------------
# DDoS simulation — floods all endpoints at maximum rate
# ---------------------------------------------------------------------------
class DDoSUser(HttpUser):
    """
    Simulates a high-volume DDoS-style flood.

    Requests are intentionally unauthenticated so they fail quickly and
    hammer the rate limiter.  catch_response is NOT used — all 401 and 429
    responses show as failures in Locust stats, making the attack visible.
    """

    wait_time = between(0.01, 0.05)
    weight = 1

    @task(3)
    def flood_games(self) -> None:
        self.client.get("/api/games")

    @task(3)
    def flood_offers(self) -> None:
        self.client.get("/api/offers/incoming")

    @task(2)
    def flood_root(self) -> None:
        self.client.get("/api")

    @task(2)
    def flood_register(self) -> None:
        # Rapid random registrations — will hit the /api/users rate limit
        # and generate 429s that show up in both Locust stats and Grafana.
        self.client.post("/api/users", json={
            "name": "Attacker",
            "email": random_email(),
            "password": random_password(),
            "street_address": "0 Attack Ave",
        })


# ---------------------------------------------------------------------------
# Credential stuffing — rapid login attempts with wrong passwords
# ---------------------------------------------------------------------------
class CredentialStuffer(HttpUser):
    """
    Simulates credential stuffing: repeatedly attempts to log in using
    known email addresses with random (wrong) passwords.

    Uses catch_response with a context manager so Locust can distinguish
    between expected 401s (wrong password, mark success) and rate-limit
    429s (mark failure so they appear in the Failures tab).
    """

    wait_time = between(0.1, 0.5)
    weight = 1

    TARGET_EMAILS = [
        "test@example.com",
        "admin@example.com",
        "user@example.com",
    ]

    @task
    def attempt_login(self) -> None:
        email = random.choice(self.TARGET_EMAILS)
        with self.client.post(
            "/api/auth/token",
            json={"email": email, "password": random_password()},
            catch_response=True,
        ) as response:
            if response.status_code == 401:
                # 401 is the expected outcome for a wrong password — don't
                # count it as a Locust test failure; it's working as intended.
                response.success()
            elif response.status_code == 429:
                # 429 means the rate limiter is doing its job.  Mark it as a
                # Locust failure so it surfaces clearly in the Failures tab.
                response.failure("Rate limited (429)")


# ---------------------------------------------------------------------------
# Slow / low-and-slow attack — avoids obvious rate-limit triggers
# ---------------------------------------------------------------------------
class SlowRateUser(HttpUser):
    """
    Simulates a low-and-slow attack: sends requests just below the rate limit
    threshold to avoid detection while still consuming server resources.
    """

    wait_time = between(6, 10)
    weight = 1

    @task(2)
    def slow_games(self) -> None:
        self.client.get("/api/games?pageSize=100")

    @task(1)
    def slow_register(self) -> None:
        self.client.post("/api/users", json={
            "name": "Slow Attack",
            "email": random_email(),
            "password": random_password(),
            "street_address": "1 Slow Lane",
        })
