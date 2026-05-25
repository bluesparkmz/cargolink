"""
Rotas de avaliacoes apos viagem concluida.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.ratings_controller import (
    create_trip_rating,
    list_my_given_ratings,
    list_my_received_ratings,
    list_trip_ratings,
)
from database import get_db
from deps import get_current_user
from models.models import User
from schemas.schemas import RatingCreateRequest, RatingResponse

router = APIRouter()


@router.post("/trips/{trip_id}", response_model=RatingResponse, status_code=201)
def create_rating(
    trip_id: int,
    data: RatingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Avalia um participante da viagem concluida."""
    return create_trip_rating(db, current_user, trip_id, data)


@router.get("/trips/{trip_id}", response_model=list[RatingResponse])
def list_for_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista avaliacoes de uma viagem."""
    return list_trip_ratings(db, current_user, trip_id)


@router.get("/me/received", response_model=list[RatingResponse])
def list_received(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Avaliacoes que recebi."""
    return list_my_received_ratings(db, current_user)


@router.get("/me/given", response_model=list[RatingResponse])
def list_given(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Avaliacoes que fiz."""
    return list_my_given_ratings(db, current_user)
