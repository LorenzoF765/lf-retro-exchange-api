# Attack simulation using Locust. Coded by LF using copilot inline additions, Copilot added comments afterwards.
#
# Run from inside the locust container:
#   locust -f /locustfile.py --host http://nginx:80
# Or from the Locust web UI at http://localhost:8089
#
# Scenarios:
#   RetroApiUser      - normal user traffic (register, login, browse games, create offers)
#   DDoSUser          - high-volume flood targeting all endpoints
#   CredentialStuffer - rapid login attempts with wrong passwords (credential stuffing)
#   SlowRateUser      - slow "low-and-slow" requests to avoid detection

import random
import string
from locust import HttpUser, task, between, constant_pacing


def random_email():
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{suffix}@example.com"


def random_password(length=12):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


# ---------------------------------------------------------------------------
# Normal user traffic — used to verify legitimate requests are NOT blocked
# ---------------------------------------------------------------------------
class RetroApiUser(HttpUser):
    """Simulates a normal user registering, logging in, and browsing the API."""
    wait_time = between(1, 3)
    weight = 5

    def on_start(self):
        self.email = random_email()
        self.password = random_password()
        self.token = None

        # Register (ignore errors — email may already exist)
        try:
            self.client.post("/api/users", json={
                "name": "Locust User",
                "email": self.email,
                "password": self.password,
                "street_address": "123 Test St",
            })
        except Exception:
            pass

        # Login
        try:
            login = self.client.post("/api/auth/token", json={
                "email": self.email,
                "password": self.password,
            })
            if login.status_code == 200:
                self.token = login.json().get("access_token")
        except Exception:
            pass

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(4)
    def list_games(self):
        self.client.get("/api/games", headers=self.auth_headers)

    @task(2)
    def get_root(self):
        self.client.get("/api")

    @task(1)
    def get_health(self):
        self.client.get("/health")


# ---------------------------------------------------------------------------
# DDoS simulation — floods all endpoints at maximum rate
# ---------------------------------------------------------------------------
class DDoSUser(HttpUser):
    """
    Simulates a high-volume DDoS-style flood.
    Targets search and auth endpoints to maximize server load.
    """
    wait_time = between(0.01, 0.05)   # very short wait — many requests per second
    weight = 1

    @task(3)
    def flood_games(self):
        self.client.get("/api/games", catch_response=True)

    @task(3)
    def flood_offers(self):
        self.client.get("/api/offers/incoming", catch_response=True)

    @task(2)
    def flood_root(self):
        self.client.get("/api", catch_response=True)

    @task(2)
    def flood_register(self):
        self.client.post("/api/users", json={
            "name": "Attacker",
            "email": random_email(),
            "password": random_password(),
            "street_address": "0 Attack Ave",
        }, catch_response=True)


# ---------------------------------------------------------------------------
# Credential stuffing — rapid login attempts with wrong passwords
# ---------------------------------------------------------------------------
class CredentialStuffer(HttpUser):
    """
    Simulates credential stuffing: repeatedly attempts to log in using
    known email addresses with random (wrong) passwords.
    """
    wait_time = between(0.1, 0.5)
    weight = 1

    # A short list of known email addresses to target
    TARGET_EMAILS = [
        "test@example.com",
        "admin@example.com",
        "user@example.com",
    ]

    @task
    def attempt_login(self):
        email = random.choice(self.TARGET_EMAILS)
        self.client.post("/api/auth/token", json={
            "email": email,
            "password": random_password(),
        }, catch_response=True)


# ---------------------------------------------------------------------------
# Slow / low-and-slow attack — avoids obvious rate limit triggers
# ---------------------------------------------------------------------------
class SlowRateUser(HttpUser):
    """
    Simulates a low-and-slow attack: sends requests just below the rate limit
    threshold to avoid detection while still consuming server resources.
    """
    wait_time = between(6, 10)   # slow enough to stay under most per-minute limits
    weight = 1

    @task(2)
    def slow_games(self):
        self.client.get("/api/games?pageSize=100", catch_response=True)

    @task(1)
    def slow_register(self):
        self.client.post("/api/users", json={
            "name": "Slow Attack",
            "email": random_email(),
            "password": random_password(),
            "street_address": "1 Slow Lane",
        }, catch_response=True)
