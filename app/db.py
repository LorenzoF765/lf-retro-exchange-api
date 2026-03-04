# Database configuration and session management for the Retro Exchange application. Coded by Copilot with minor edits by LF made afterwards.
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Allow overriding DB via environment (docker-compose provides a PostgreSQL URL).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./retro_exchange.db")

# Only pass sqlite-specific connect_args when using sqlite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()
