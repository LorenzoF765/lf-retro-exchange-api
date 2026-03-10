"""
Pydantic request/response schemas for the Retro Exchange API.

Design notes:
- HATEOAS links are serialized as the JSON key ``_links``.  Because Pydantic
  treats fields starting with ``_`` as private (and excludes them from output),
  the field is declared as ``links`` in Python and aliased to ``_links`` via
  ``Field(..., alias="_links")``.
- bcrypt silently truncates passwords at 72 bytes, so we enforce
  ``max_length=72`` on password fields to prevent two distinct passwords from
  hashing identically.

Coded by LF using copilot inline additions, Copilot added comments afterwards.
"""

from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# Domain enum describing acceptable condition values for games.
class GameCondition(str, Enum):
    mint = "mint"
    good = "good"
    fair = "fair"
    poor = "poor"


# User registration payload (validated)
class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit (72 bytes)
    street_address: str = Field(min_length=1, max_length=400)


# Partial user update payload (fields are optional)
class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    street_address: Optional[str] = Field(default=None, min_length=1, max_length=400)


# Public representation of a user returned by the API.
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    street_address: str

    # Serialized as "_links" in JSON (HATEOAS)
    links: Dict[str, Any] = Field(..., alias="_links")

    model_config = ConfigDict(populate_by_name=True)


# Token request/response shapes used by authentication endpoints
class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Payload to create a new game
class GameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=200)
    year_published: int = Field(ge=1970, le=2100)
    system: str = Field(min_length=1, max_length=100)
    condition: GameCondition
    previous_owners: Optional[int] = Field(default=None, ge=0)


# Partial update payload for games (all fields optional)
class GameUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    publisher: Optional[str] = Field(default=None, min_length=1, max_length=200)
    year_published: Optional[int] = Field(default=None, ge=1970, le=2100)
    system: Optional[str] = Field(default=None, min_length=1, max_length=100)
    condition: Optional[GameCondition] = None
    previous_owners: Optional[int] = Field(default=None, ge=0)


# Public representation of a game returned by the API.
class GameOut(BaseModel):
    id: int
    owner_id: int
    name: str
    publisher: str
    year_published: int
    system: str
    condition: GameCondition
    previous_owners: Optional[int]

    # Serialized as "_links" in JSON (HATEOAS)
    links: Dict[str, Any] = Field(..., alias="_links")

    model_config = ConfigDict(populate_by_name=True)


# Standard paginated response for listing games.
class PagedGames(BaseModel):
    items: List[GameOut]
    page: int
    pageSize: int
    total: int

    # Serialized as "_links" in JSON (HATEOAS)
    links: Dict[str, Any] = Field(..., alias="_links")

    model_config = ConfigDict(populate_by_name=True)


class OfferStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class OfferCreate(BaseModel):
    requested_game_id: int
    offered_game_id: int


class OfferDecision(BaseModel):
    """Payload for accepting or rejecting a trade offer.

    Only ``accepted`` and ``rejected`` are valid decisions; ``pending`` is
    rejected at the schema level so the router never receives an invalid status.
    """
    decision: OfferStatus

    @field_validator("decision")
    @classmethod
    def decision_must_be_final(cls, v: OfferStatus) -> OfferStatus:
        if v == OfferStatus.pending:
            raise ValueError("Decision must be 'accepted' or 'rejected', not 'pending'")
        return v


class OfferOut(BaseModel):
    id: int
    requested_game_id: int
    offered_game_id: int
    offerer_user_id: int
    status: OfferStatus

    # Serialized as "_links" in JSON (HATEOAS)
    links: Dict[str, Any] = Field(..., alias="_links")

    model_config = ConfigDict(populate_by_name=True)


class PagedOffers(BaseModel):
    items: List[OfferOut]
    page: int
    pageSize: int
    total: int

    # Serialized as "_links" in JSON (HATEOAS)
    links: Dict[str, Any] = Field(..., alias="_links")

    model_config = ConfigDict(populate_by_name=True)
