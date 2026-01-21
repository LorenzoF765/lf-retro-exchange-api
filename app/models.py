# Models class. Code written by me, Lorenzo Franco, with copilot in charge of adding these comments afterwards to improve readability and documentation.

from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from .db import Base


class User(Base):
    # Map this class to the "users" table and enforce unique email addresses.
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    # Primary key and commonly queried fields are indexed for performance.
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # user's full name
    email = Column(String, nullable=False, index=True)  # unique contact email
    password_hash = Column(String, nullable=False)  # hashed password (never store plaintext)
    street_address = Column(String, nullable=False)  # mailing address

    # One-to-many relationship: a user can own multiple games.
    # Cascade ensures games are deleted when the owning user is removed.
    games = relationship("Game", back_populates="owner", cascade="all, delete-orphan")


class Game(Base):
    # Map to the "games" table and enforce domain constraints on fields.
    __tablename__ = "games"
    __table_args__ = (
        # Ensure the published year is within a reasonable range.
        CheckConstraint("year_published >= 1970 AND year_published <= 2100", name="ck_games_year_range"),
        # previous_owners must be non-negative if provided.
        CheckConstraint("previous_owners IS NULL OR previous_owners >= 0", name="ck_games_prev_owners_nonneg"),
    )

    # Primary key and a foreign key that references the owning user.
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic metadata about the game; many fields are indexed to support searches.
    name = Column(String, nullable=False, index=True)
    publisher = Column(String, nullable=False, index=True)
    year_published = Column(Integer, nullable=False, index=True)
    system = Column(String, nullable=False, index=True)  # platform/console
    condition = Column(String, nullable=False, index=True)  # e.g., "new", "used", "mint"
    previous_owners = Column(Integer, nullable=True)  # optional number of prior owners

    # Back-reference to the owning User object.
    owner = relationship("User", back_populates="games")
