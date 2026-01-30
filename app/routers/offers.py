# Router for /api/offers endpoints managing offers resources. Coded by Lorenzo Franco, as well as Copilot for adding these comments afterwards.
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from .. import models, schemas
from ..errors import http_error
from ..hateoas import link

router = APIRouter(prefix="/api/offers", tags=["offers"])


def offer_links(offer_id: int, can_decide: bool) -> dict:
    links = {
        "self": link(f"/api/offers/{offer_id}"),
        "incoming": link("/api/offers/incoming"),
        "outgoing": link("/api/offers/outgoing"),
        "create": link("/api/offers", "POST"),
    }
    if can_decide:
        links["decide"] = link(f"/api/offers/{offer_id}/decision", "POST")
    return links


def to_offer_out(offer: models.TradeOffer, can_decide: bool) -> schemas.OfferOut:
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

    return to_offer_out(offer, can_decide=False)


@router.get("/incoming", response_model=schemas.PagedOffers)
def incoming_offers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
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


@router.post("/{offer_id}/decision", response_model=schemas.OfferOut)
def decide_offer(
    offer_id: int,
    payload: schemas.OfferDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    offer = db.query(models.TradeOffer).filter_by(id=offer_id).first()
    if not offer:
        raise http_error(404, "NOT_FOUND", "Offer not found")

    requested_game = db.query(models.Game).filter_by(id=offer.requested_game_id).first()
    if requested_game.owner_id != current_user.id:
        raise http_error(403, "FORBIDDEN", "Only the owner can decide this offer")

    offer.status = payload.decision.value
    db.commit()
    db.refresh(offer)

    return to_offer_out(offer, can_decide=True)
