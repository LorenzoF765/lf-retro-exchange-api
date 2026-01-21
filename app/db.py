# Database configuration and session management for the Retro Exchange application. Coded by Copilot with minor edits by LF made afterwards.
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite connection URL (file DB stored next to the project)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./retro_exchange.db")


# Engine configuration: allow cross-thread access for FastAPI's async worker model.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

# Session factory used by dependency injection to provide DB sessions per request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Base class for declarative models to inherit from.
Base = declarative_base()
