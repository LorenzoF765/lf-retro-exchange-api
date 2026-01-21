# Schemas class. Defines Pydantic models for request and response payloads. Coded by Lorenzo Franco using copilot for inline assistance, as well as for adding these comments afterwards.
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

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
    password: str = Field(min_length=8, max_length=200)
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
    links: Dict[str, Any]

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
    links: Dict[str, Any]

# Standard paginated response for listing games.
class PagedGames(BaseModel):
    items: List[GameOut]
    page: int
    pageSize: int
    total: int
    _links: Dict[str, Any]
