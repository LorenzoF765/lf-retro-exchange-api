# Database engine, session factory, and declarative base for the Retro Exchange API.
# Coded by LF using copilot inline additions, Copilot added comments afterwards.
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Allow overriding the database via environment variable.
# docker-compose injects a PostgreSQL URL; the SQLite default is for local dev.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./retro_exchange.db")

# SQLite requires check_same_thread=False to allow use across threads.
# PostgreSQL does not need (or support) this flag.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Pool settings keep a small number of connections warm while avoiding
# exhaustion under load.  SQLite uses StaticPool so these kwargs are ignored,
# but they must not be passed to SQLite's NullPool — guard them here.
pool_kwargs: dict = {}
if not DATABASE_URL.startswith("sqlite"):
    pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,  # validate connections before handing them to a request
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
    **pool_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()
