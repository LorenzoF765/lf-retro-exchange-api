# Router for /api/offers endpoints managing TradeOffer resources.
# Coded by LF using copilot inline additions, Copilot added comments afterwards.
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from .. import models, schemas
from ..errors import http_error
from ..hateoas import link
from ..notifications import publish_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/offers", tags=["offers"])


def offer_links(offer_id: int, can_decide: bool) -> dict:
    """Build HATEOAS links for a single trade offer resource."""
    links = {
        "self": link(f"/api/offers/{offer_id}"),
        "incoming": link("/api/offers/incoming"),
        "outgoing": link("/api/offers/outgoing"),
        "create": link("/api/offers", "POST"),
    }
    if can_decide:
        # Only the owner of the requested game may accept or reject.
        links["decide"] = link(f"/api/offers/{offer_id}/decision", "POST")
    return links


def to_offer_out(offer: models.TradeOffer, can_decide: bool) -> schemas.OfferOut:
    """Convert a TradeOffer ORM instance to the public OfferOut schema."""
    return schemas.OfferOut(
        id=offer.id,
        requested_game_id=offer.requested_game_id,
        offered_game_id=offer.offered_game_id,
        offerer_user_id=offer.offerer_user_id,
        status=schemas.OfferStatus(offer.status),
        _links=offer_links(offer.id, can_decide),
    )


@router.post("", response_model=schemas.OfferOut, status_code=201)
def create_offer(
    payload: schemas.OfferCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new trade offer.

    The authenticated user offers one of their own games (*offered_game_id*) in
    exchange for a game owned by someone else (*requested_game_id*).  Both games
    must exist; the offerer must own the offered game and must not own the
    requested game.
    """
    requested = db.query(models.Game).filter_by(id=payload.requested_game_id).first()
    offered = db.query(models.Game).filter_by(id=payload.offered_game_id).first()

    if not requested or not offered:
        raise http_error(404, "NOT_FOUND", "Requested or offered game not found")
    if requested.owner_id == current_user.id:
        raise http_error(400, "INVALID_OFFER", "You cannot request your own game")
    if offered.owner_id != current_user.id:
        raise http_error(403, "FORBIDDEN", "You may only offer a game you own")

    offer = models.TradeOffer(
        requested_game_id=requested.id,
        offered_game_id=offered.id,
        offerer_user_id=current_user.id,
        status="pending",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    # Notify the owner of the requested game — non-critical, log on failure.
    try:
        owner = db.query(models.User).filter(models.User.id == requested.owner_id).first()
        publish_event(
            "offer.created",
            {
                "offer_id": offer.id,
                "to_email": owner.email if owner else None,
                "from_name": current_user.name,
                "requested_game": requested.name,
            },
        )
    except Exception:
        logger.exception("Failed to publish offer.created event for offer_id=%s", offer.id)

    return to_offer_out(offer, can_decide=False)


@router.get("/incoming", response_model=schemas.PagedOffers)
def incoming_offers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return all pending trade offers targeting games owned by the current user."""
    offers = (
        db.query(models.TradeOffer)
        .join(models.Game, models.TradeOffer.requested_game_id == models.Game.id)
        .filter(models.Game.owner_id == current_user.id)
        .all()
    )
    return schemas.PagedOffers(
        items=[to_offer_out(o, can_decide=True) for o in offers],
        page=1,
        pageSize=len(offers),
        total=len(offers),
        _links={
            "self": link("/api/offers/incoming"),
            "outgoing": link("/api/offers/outgoing"),
        },
    )


@router.get("/outgoing", response_model=schemas.PagedOffers)
def outgoing_offers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return all trade offers created by the current user."""
    offers = (
        db.query(models.TradeOffer)
        .filter(models.TradeOffer.offerer_user_id == current_user.id)
        .all()
    )
    return schemas.PagedOffers(
        items=[to_offer_out(o, can_decide=False) for o in offers],
        page=1,
        pageSize=len(offers),
        total=len(offers),
        _links={
            "self": link("/api/offers/outgoing"),
            "incoming": link("/api/offers/incoming"),
        },
    )


@router.post("/{offer_id}/decision", response_model=schemas.OfferOut)
def decide_offer(
    offer_id: int,
    payload: schemas.OfferDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Accept or reject an incoming trade offer.

    Only the owner of the requested game may decide.  The offer status is
    updated to 'accepted' or 'rejected' and the offerer is notified via Kafka.
    """
    offer = db.query(models.TradeOffer).filter_by(id=offer_id).first()
    if not offer:
        raise http_error(404, "NOT_FOUND", "Offer not found")

    requested_game = db.query(models.Game).filter_by(id=offer.requested_game_id).first()
    if not requested_game or requested_game.owner_id != current_user.id:
        raise http_error(403, "FORBIDDEN", "Only the owner of the requested game can decide this offer")

    offer.status = payload.decision.value
    db.commit()
    db.refresh(offer)

    # Notify the offerer of the decision — non-critical, log on failure.
    try:
        offerer = db.query(models.User).filter(models.User.id == offer.offerer_user_id).first()
        publish_event(
            "offer.decided",
            {
                "offer_id": offer.id,
                "offerer_email": offerer.email if offerer else None,
                "status": offer.status,
            },
        )
    except Exception:
        logger.exception("Failed to publish offer.decided event for offer_id=%s", offer.id)

    return to_offer_out(offer, can_decide=True)
