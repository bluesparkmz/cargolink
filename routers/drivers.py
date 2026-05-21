"""
Rotas de motoristas: perfil, disponibilidade e listagem.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.drivers_controller import (
    get_driver_by_id,
    get_my_driver,
    list_drivers,
    set_availability,
    update_my_driver,
)
from controllers.location_controller import update_driver_location
from deps import get_current_user
from database import get_db
from models import Driver, User
from schemas import (
    AvailabilityUpdateRequest,
    DriverDetailResponse,
    DriverListItem,
    DriverProfileUpdateRequest,
    LocationUpdateRequest,
)

router = APIRouter()


def _to_list_item(driver: Driver) -> DriverListItem:
    """Monta resposta resumida com dados do utilizador."""
    return DriverListItem(
        id=driver.id,
        user_id=driver.user_id,
        company_id=driver.company_id,
        name=driver.user.name,
        average_rating=float(driver.average_rating),
        total_trips=driver.total_trips,
        available=driver.available,
        profile_photo=driver.user.profile_photo,
        verified=driver.user.verified,
        current_lat=float(driver.current_lat) if driver.current_lat is not None else None,
        current_lng=float(driver.current_lng) if driver.current_lng is not None else None,
        location_updated_at=driver.location_updated_at,
    )


@router.get("/me", response_model=DriverDetailResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perfil do motorista autenticado."""
    return get_my_driver(db, current_user)


@router.patch("/me", response_model=DriverDetailResponse)
def update_me(
    data: DriverProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza perfil do motorista autenticado."""
    return update_my_driver(db, current_user, data)


@router.patch("/me/location", response_model=DriverDetailResponse)
def update_location(
    data: LocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista envia posição GPS atual (mapa de disponíveis)."""
    return update_driver_location(db, current_user, data)


@router.patch("/me/availability", response_model=DriverDetailResponse)
def update_availability(
    data: AvailabilityUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Altera disponibilidade do motorista para novas viagens."""
    return set_availability(db, current_user, data.available)


@router.get("", response_model=list[DriverListItem])
def list_all(
    available_only: bool = Query(False, description="Filtrar só motoristas disponíveis"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista motoristas registados."""
    drivers = list_drivers(db, available_only=available_only)
    return [_to_list_item(d) for d in drivers]


@router.get("/{driver_id}", response_model=DriverDetailResponse)
def get_by_id(
    driver_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta motorista por id."""
    return get_driver_by_id(db, driver_id)
