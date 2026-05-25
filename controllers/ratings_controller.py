"""
Controller de avaliacoes apos viagem concluida.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from constants import TRIP_STATUS_COMPLETED
from controllers.notifications_controller import create_notification, emit_notification
from controllers.realtime_events import emit_to_rooms
from models.models import Client, Company, Driver, Load, Rating, Trip, User
from schemas.schemas import RatingCreateRequest


def _trip_or_404(db: Session, trip_id: int) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viagem nao encontrada")
    return trip


def _participant_user_ids(db: Session, trip: Trip) -> set[int]:
    user_ids: set[int] = set()

    load = db.query(Load).filter(Load.id == trip.load_id).first()
    if load:
        client = db.query(Client).filter(Client.id == load.client_id).first()
        if client:
            user_ids.add(client.user_id)

    if trip.company_id:
        company = db.query(Company).filter(Company.id == trip.company_id).first()
        if company:
            user_ids.add(company.user_id)

    if trip.driver_id:
        driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
        if driver:
            user_ids.add(driver.user_id)

    return user_ids


def _ensure_can_rate(db: Session, user: User, trip: Trip, rated_user_id: int) -> None:
    if trip.status != TRIP_STATUS_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avaliacao apenas apos viagem concluida",
        )

    participants = _participant_user_ids(db, trip)
    if user.user_type != "admin" and user.id not in participants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a esta viagem")
    if rated_user_id not in participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilizador avaliado nao participou nesta viagem",
        )
    if rated_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao pode avaliar a si mesmo",
        )


def _refresh_average_rating(db: Session, rated_user_id: int) -> None:
    avg = (
        db.query(func.avg(Rating.score))
        .filter(Rating.rated_user_id == rated_user_id, Rating.score.isnot(None))
        .scalar()
    )
    average = Decimal(str(round(float(avg or 0), 2)))

    driver = db.query(Driver).filter(Driver.user_id == rated_user_id).first()
    if driver:
        driver.average_rating = average

    company = db.query(Company).filter(Company.user_id == rated_user_id).first()
    if company:
        company.average_rating = average


def create_trip_rating(
    db: Session,
    user: User,
    trip_id: int,
    data: RatingCreateRequest,
) -> Rating:
    """Cria avaliacao unica entre dois participantes da viagem."""
    trip = _trip_or_404(db, trip_id)
    _ensure_can_rate(db, user, trip, data.rated_user_id)

    existing = (
        db.query(Rating)
        .filter(
            Rating.trip_id == trip_id,
            Rating.rater_id == user.id,
            Rating.rated_user_id == data.rated_user_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ja avaliou este utilizador nesta viagem",
        )

    rating = Rating(
        trip_id=trip_id,
        rater_id=user.id,
        rated_user_id=data.rated_user_id,
        score=data.score,
        comment=data.comment,
    )
    db.add(rating)
    db.flush()
    _refresh_average_rating(db, data.rated_user_id)
    notification = create_notification(
        db,
        user_id=data.rated_user_id,
        title="Nova avaliacao recebida",
        body=f"Recebeu uma avaliacao de {data.score} estrela(s).",
        notification_type="rating.created",
        payload={"trip_id": trip_id, "rating_id": rating.id, "score": data.score},
    )
    db.commit()
    db.refresh(rating)
    db.refresh(notification)

    emit_notification(notification)
    emit_to_rooms(
        {f"trip:{trip.id}", f"load:{trip.load_id}", f"user:{data.rated_user_id}", f"user:{user.id}"},
        {
            "type": "rating.created",
            "trip_id": trip.id,
            "load_id": trip.load_id,
            "rating": rating,
        },
    )
    return rating


def list_trip_ratings(db: Session, user: User, trip_id: int) -> list[Rating]:
    """Lista avaliacoes da viagem para participantes."""
    trip = _trip_or_404(db, trip_id)
    participants = _participant_user_ids(db, trip)
    if user.user_type != "admin" and user.id not in participants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a esta viagem")
    return (
        db.query(Rating)
        .filter(Rating.trip_id == trip_id)
        .order_by(Rating.created_at.desc())
        .all()
    )


def list_my_received_ratings(db: Session, user: User) -> list[Rating]:
    """Lista avaliacoes recebidas pelo utilizador autenticado."""
    return (
        db.query(Rating)
        .filter(Rating.rated_user_id == user.id)
        .order_by(Rating.created_at.desc())
        .all()
    )


def list_my_given_ratings(db: Session, user: User) -> list[Rating]:
    """Lista avaliacoes feitas pelo utilizador autenticado."""
    return (
        db.query(Rating)
        .filter(Rating.rater_id == user.id)
        .order_by(Rating.created_at.desc())
        .all()
    )
