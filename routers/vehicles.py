"""
Rotas de veiculos: camioes disponiveis e gestao pela empresa.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
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
from models.models import User, Vehicle
from schemas.schemas import (
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
        company_id=vehicle.company_id,
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
        company_name=vehicle.company.company_name if vehicle.company else None,
        driver_name=vehicle.driver.user.name if vehicle.driver else None,
        driver_rating=float(vehicle.driver.average_rating) if vehicle.driver else None,
        driver_photo=vehicle.driver.user.profile_photo if vehicle.driver and vehicle.driver.user else None,
    )


@router.get("/me", response_model=list[VehicleListItem])
def list_my(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista camioes da empresa ou atribuidos ao motorista autenticado."""
    return [_to_list_item(v) for v in list_my_vehicles(db, current_user)]


@router.post("", response_model=VehicleListItem, status_code=201)
def create(
    plate: str = Form(...),
    driver_id: int | None = Form(None),
    driver_email: str | None = Form(None, description="Email do motorista da empresa"),
    brand: str | None = Form(None),
    model_name: str | None = Form(None),
    vehicle_type: str | None = Form(None),
    tonnage_capacity: float | None = Form(None, gt=0),
    status: str = Form("disponivel"),
    current_lat: float | None = Form(None),
    current_lng: float | None = Form(None),
    photo: Annotated[
        UploadFile | None,
        File(description="Foto do camião (jpg, png)"),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Empresa regista novo camiao com foto opcional."""
    data = VehicleCreateRequest(
        driver_id=driver_id,
        driver_email=driver_email,
        plate=plate,
        brand=brand,
        model_name=model_name,
        vehicle_type=vehicle_type,
        tonnage_capacity=tonnage_capacity,
        status=status,
        current_lat=current_lat,
        current_lng=current_lng,
    )
    vehicle = create_vehicle(db, current_user, data, photo_file=photo)
    return _to_list_item(vehicle)


@router.patch("/{vehicle_id}/location", response_model=VehicleListItem)
def patch_location(
    vehicle_id: int,
    data: LocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motorista atribuido atualiza posicao GPS do camiao no mapa."""
    vehicle = update_vehicle_location(db, current_user, vehicle_id, data)
    return _to_list_item(vehicle)


@router.patch("/{vehicle_id}", response_model=VehicleListItem)
def patch(
    vehicle_id: int,
    plate: str | None = Form(None),
    driver_id: int | None = Form(None),
    driver_email: str | None = Form(None),
    brand: str | None = Form(None),
    model_name: str | None = Form(None),
    vehicle_type: str | None = Form(None),
    tonnage_capacity: float | None = Form(None),
    status: str | None = Form(None),
    photo: Annotated[
        UploadFile | None,
        File(description="Foto do camião (jpg, png)"),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Empresa atualiza o camiao (com foto opcional)."""
    data = VehicleUpdateRequest(
        plate=plate,
        driver_id=driver_id,
        driver_email=driver_email,
        brand=brand,
        model_name=model_name,
        vehicle_type=vehicle_type,
        tonnage_capacity=tonnage_capacity,
        status=status,
    )
    vehicle = update_vehicle(db, current_user, vehicle_id=vehicle_id, data=data, photo_file=photo)
    return _to_list_item(vehicle)


@router.delete("/{vehicle_id}", status_code=204)
def remove(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Empresa desativa camiao."""
    deactivate_vehicle(db, current_user, vehicle_id)


@router.get("", response_model=list[VehicleListItem])
def list_all(
    status: str | None = Query("disponivel", description="Filtrar por status do veiculo"),
    available_only: bool = Query(True, description="So motoristas disponiveis"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista camioes disponiveis."""
    vehicles = list_vehicles(db, status_filter=status, available_only=available_only)
    return [_to_list_item(v) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
def get_by_id(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalhe do camiao."""
    return _to_detail(get_vehicle_by_id(db, vehicle_id))
