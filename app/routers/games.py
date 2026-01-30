# Router for /api/games endpoints managing Game resources. Coded by Lorenzo Franco using copilot for inline assistance, as well as for adding these comments afterwards.

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user
from ..errors import http_error
from ..hateoas import game_links, games_collection_links

# Create a router scoped under /api/games
router = APIRouter(prefix="/api/games", tags=["games"])

def to_game_out(game: models.Game, requester_id: int) -> schemas.GameOut:
    """Convert a Game ORM instance to the public `GameOut` schema.

    Adds HATEOAS links and marks whether the requester can modify the game AKA whether or not the requester is the owner.
    """
    # Determine whether the requester is the owner and can modify/delete.
    can_modify = (game.owner_id == requester_id)
    return schemas.GameOut(
        id=game.id,
        owner_id=game.owner_id,
        name=game.name,
        publisher=game.publisher,
        year_published=game.year_published,
        system=game.system,
        # Store enum value in the response using the schema enum
        condition=schemas.GameCondition(game.condition),
        previous_owners=game.previous_owners,
        # Attach resource links tailored to the current user permissions.
        _links=game_links(game.id, game.owner_id, can_modify=can_modify),
    )

@router.post("", response_model=schemas.GameOut, status_code=201)
def create_game(payload: schemas.GameCreate, response: Response, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Create a new game owned by the authenticated user.

    Validates via the Pydantic `GameCreate` schema and persists the new
    Game row. Returns the created resource and sets the Location header.
    """
    # Build the ORM object from the validated payload
    game = models.Game(
        owner_id=current.id,
        name=payload.name,
        publisher=payload.publisher,
        year_published=payload.year_published,
        system=payload.system,
        # Persist enum as string in the DB
        condition=payload.condition.value,
        previous_owners=payload.previous_owners,
    )
    db.add(game)
    db.commit()      # Save the new game
    db.refresh(game) # Refresh ORM instance with DB-assigned fields (e.g., id)

    # Set Location header for the created resource and return its representation
    response.headers["Location"] = f"/api/games/{game.id}"
    return to_game_out(game, requester_id=current.id)

@router.get("", response_model=schemas.PagedGames)
def list_games(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
    name: str | None = None,
    publisher: str | None = None,
    system: str | None = None,
    condition: schemas.GameCondition | None = None,
    year: int | None = None,
    yearMin: int | None = None,
    yearMax: int | None = None,
    ownerId: int | None = None,
    page: int = 1,
    pageSize: int = 20,
):
    """List games with optional filtering and pagination.

    Supports partial matches for text fields, exact/equality for years,
    range filtering for yearMin/yearMax, and owner filtering. Returns a
    paginated PagedGames response with HATEOAS collection links.
    """
    # Validate paging parameters
    if page < 1 or pageSize < 1 or pageSize > 100:
        raise http_error(400, "BAD_PAGING", "page must be >= 1 and pageSize must be 1..100")

    # Base query
    q = db.query(models.Game)

    # Apply optional filters
    if name:
        q = q.filter(models.Game.name.ilike(f"%{name}%"))
    if publisher:
        q = q.filter(models.Game.publisher.ilike(f"%{publisher}%"))
    if system:
        q = q.filter(models.Game.system.ilike(f"%{system}%"))
    if condition:
        q = q.filter(models.Game.condition == condition.value)
    if year is not None:
        q = q.filter(models.Game.year_published == year)
    if yearMin is not None:
        q = q.filter(models.Game.year_published >= yearMin)
    if yearMax is not None:
        q = q.filter(models.Game.year_published <= yearMax)
    if ownerId is not None:
        q = q.filter(models.Game.owner_id == ownerId)

    # Total count for pagination metadata
    total = q.count()

    # Fetch the requested page of items, most recent first by id
    items = (
        q.order_by(models.Game.id.desc())
         .offset((page - 1) * pageSize)
         .limit(pageSize)
         .all()
    )

    # Reconstruct query params for pagination links (exclude None values)
    query_params = {}
    if name: query_params["name"] = name
    if publisher: query_params["publisher"] = publisher
    if system: query_params["system"] = system
    if condition: query_params["condition"] = condition.value
    if year is not None: query_params["year"] = year
    if yearMin is not None: query_params["yearMin"] = yearMin
    if yearMax is not None: query_params["yearMax"] = yearMax
    if ownerId is not None: query_params["ownerId"] = ownerId

    # Build and return the paginated response using schema conversion helper
    return schemas.PagedGames(
        items=[to_game_out(g, requester_id=current.id) for g in items],
        page=page,
        pageSize=pageSize,
        total=total,
        _links=games_collection_links(page, pageSize, total, query_params, can_create=True),
    )

@router.get("/{game_id}", response_model=schemas.GameOut)
def get_game(game_id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Retrieve a single game by id. Returns 404 if not found."""
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise http_error(404, "NOT_FOUND", "Game not found")
    return to_game_out(game, requester_id=current.id)

@router.put("/{game_id}", response_model=schemas.GameOut)
def update_game(game_id: int, payload: schemas.GameUpdate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Update mutable fields of a game. Only the owner may update."""
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise http_error(404, "NOT_FOUND", "Game not found")
    if game.owner_id != current.id:
        raise http_error(403, "FORBIDDEN", "Only the owner may update this game")

    # Apply only the provided fields (partial update semantics)
    if payload.name is not None:
        game.name = payload.name
    if payload.publisher is not None:
        game.publisher = payload.publisher
    if payload.year_published is not None:
        game.year_published = payload.year_published
    if payload.system is not None:
        game.system = payload.system
    if payload.condition is not None:
        game.condition = payload.condition.value
    if payload.previous_owners is not None:
        game.previous_owners = payload.previous_owners

    db.commit()
    db.refresh(game)
    return to_game_out(game, requester_id=current.id)

@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    """Delete a game. Only the owner may delete; returns HTTP 204 on success."""
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise http_error(404, "NOT_FOUND", "Game not found")
    if game.owner_id != current.id:
        raise http_error(403, "FORBIDDEN", "Only the owner may delete this game")

    db.delete(game)
    db.commit()
    # Explicitly return a 204 No Content response
    return Response(status_code=204)
