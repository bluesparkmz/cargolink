"""
Rotas de veículos (camiões disponíveis e gestão pelo motorista).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.location_controller import resolve_vehicle_coordinates, update_vehicle_location
from controllers.vehicles_controller import (
    create_vehicle,
    deactivate_vehicle,
    get_vehicle_by_id,
    list_my_vehicles,
    list_vehicles,
    update_vehicle,
)
from database import get_db
from deps import get_current_user
from models import User, Vehicle
from schemas import (
    LocationUpdateRequest,
    VehicleCreateRequest,
    VehicleDetailResponse,
    VehicleListItem,
    VehicleUpdateRequest,
)

router = APIRouter()


def _to_list_item(vehicle: Vehicle) -> VehicleListItem:
    lat, lng = resolve_vehicle_coordinates(vehicle)
    updated = vehicle.location_updated_at or (
        vehicle.driver.location_updated_at if vehicle.driver else None
    )
    return VehicleListItem(
        id=vehicle.id,
        driver_id=vehicle.driver_id,
        plate=vehicle.plate,
        brand=vehicle.brand,
        model_name=vehicle.model_name,
        vehicle_type=vehicle.vehicle_type,
        tonnage_capacity=float(vehicle.tonnage_capacity)
        if vehicle.tonnage_capacity is not None
        else None,
        photo=vehicle.photo,
        status=vehicle.status,
        current_lat=lat,
        current_lng=lng,
        location_updated_at=updated,
    )


def _to_detail(vehicle: Vehicle) -> VehicleDetailResponse:
    item = _to_list_item(vehicle)
    return VehicleDetailResponse(
        **item.model_dump(),
        driver_name=vehicle.driver.user.name,
        driver_rating=float(vehicle.driver.average_rating),
    )


@router.get("/me", response_model=list[VehicleListItem])
def list_my(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista camiões do motorista autenticado."""
    return [_to_list_item(v) for v in list_my_vehicles(db, current_user)]


@router.post("", response_model=VehicleListItem, status_code=201)
def create(
    data: VehicleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista regista novo camião."""
    vehicle = create_vehicle(db, current_user, data)
    return _to_list_item(vehicle)


@router.patch("/{vehicle_id}/location", response_model=VehicleListItem)
def patch_location(
    vehicle_id: int,
    data: LocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista atualiza posição GPS do camião no mapa."""
    vehicle = update_vehicle_location(db, current_user, vehicle_id, data)
    return _to_list_item(vehicle)


@router.patch("/{vehicle_id}", response_model=VehicleListItem)
def patch(
    vehicle_id: int,
    data: VehicleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista atualiza o próprio camião."""
    vehicle = update_vehicle(db, current_user, vehicle_id, data)
    return _to_list_item(vehicle)


@router.delete("/{vehicle_id}", status_code=204)
def remove(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista desativa camião (não aparece nas listagens)."""
    deactivate_vehicle(db, current_user, vehicle_id)


@router.get("", response_model=list[VehicleListItem])
def list_all(
    status: str | None = Query("disponivel", description="Filtrar por status do veículo"),
    available_only: bool = Query(True, description="Só motoristas disponíveis"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista camiões (carrossel Camiões disponíveis)."""
    vehicles = list_vehicles(db, status_filter=status, available_only=available_only)
    return [_to_list_item(v) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
def get_by_id(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalhe do camião."""
    return _to_detail(get_vehicle_by_id(db, vehicle_id))
