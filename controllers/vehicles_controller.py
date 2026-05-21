"""
Controller de veículos (camiões).
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants import VEHICLE_STATUSES, VEHICLE_STATUS_INACTIVE
from controllers.drivers_controller import get_my_driver
from models import Driver, User, Vehicle
from schemas import VehicleCreateRequest, VehicleUpdateRequest


def list_vehicles(
    db: Session,
    *,
    status_filter: str | None = "disponivel",
    available_only: bool = True,
) -> list[Vehicle]:
    """Lista camiões para o carrossel do app."""
    query = db.query(Vehicle).options(
        joinedload(Vehicle.driver).joinedload(Driver.user)
    )
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    else:
        query = query.filter(Vehicle.status != VEHICLE_STATUS_INACTIVE)
    if available_only:
        query = query.join(Driver).filter(Driver.available.is_(True))
    return query.order_by(Vehicle.created_at.desc()).all()


def list_my_vehicles(db: Session, user: User) -> list[Vehicle]:
    """Lista veículos do motorista autenticado."""
    driver = get_my_driver(db, user)
    return (
        db.query(Vehicle)
        .options(joinedload(Vehicle.driver).joinedload(Driver.user))
        .filter(Vehicle.driver_id == driver.id, Vehicle.status != VEHICLE_STATUS_INACTIVE)
        .order_by(Vehicle.created_at.desc())
        .all()
    )


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Vehicle:
    """Detalhe do veículo com motorista."""
    vehicle = (
        db.query(Vehicle)
        .options(joinedload(Vehicle.driver).joinedload(Driver.user))
        .filter(Vehicle.id == vehicle_id)
        .first()
    )
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado",
        )
    return vehicle


def _get_own_vehicle(db: Session, user: User, vehicle_id: int) -> Vehicle:
    """Veículo que pertence ao motorista autenticado."""
    driver = get_my_driver(db, user)
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if vehicle.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veículo de outro motorista",
        )
    return vehicle


def _validate_vehicle_status(status: str) -> None:
    if status not in VEHICLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status inválido. Use: {', '.join(sorted(VEHICLE_STATUSES))}",
        )


def create_vehicle(db: Session, user: User, data: VehicleCreateRequest) -> Vehicle:
    """Motorista regista novo camião."""
    driver = get_my_driver(db, user)
    _validate_vehicle_status(data.status)

    existing = db.query(Vehicle).filter(Vehicle.plate == data.plate.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula já registada",
        )

    payload = data.model_dump()
    payload["plate"] = data.plate.strip().upper()
    if payload.get("tonnage_capacity") is not None:
        payload["tonnage_capacity"] = Decimal(str(payload["tonnage_capacity"]))
    if payload.get("current_lat") is not None:
        payload["current_lat"] = Decimal(str(payload["current_lat"]))
    if payload.get("current_lng") is not None:
        payload["current_lng"] = Decimal(str(payload["current_lng"]))
    if payload.get("current_lat") is not None and payload.get("current_lng") is not None:
        from controllers.location_controller import _now

        payload["location_updated_at"] = _now()

    vehicle = Vehicle(driver_id=driver.id, **payload)
    db.add(vehicle)
    db.commit()
    return get_vehicle_by_id(db, vehicle.id)


def update_vehicle(
    db: Session, user: User, vehicle_id: int, data: VehicleUpdateRequest
) -> Vehicle:
    """Motorista atualiza o próprio veículo."""
    vehicle = _get_own_vehicle(db, user, vehicle_id)
    fields = data.model_dump(exclude_unset=True)

    if "status" in fields:
        _validate_vehicle_status(fields["status"])
    if "plate" in fields and fields["plate"]:
        plate = fields["plate"].strip().upper()
        taken = (
            db.query(Vehicle)
            .filter(Vehicle.plate == plate, Vehicle.id != vehicle_id)
            .first()
        )
        if taken:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Matrícula já registada",
            )
        fields["plate"] = plate
    if "tonnage_capacity" in fields and fields["tonnage_capacity"] is not None:
        fields["tonnage_capacity"] = Decimal(str(fields["tonnage_capacity"]))
    if "current_lat" in fields and fields["current_lat"] is not None:
        fields["current_lat"] = Decimal(str(fields["current_lat"]))
    if "current_lng" in fields and fields["current_lng"] is not None:
        fields["current_lng"] = Decimal(str(fields["current_lng"]))
    if "current_lat" in fields or "current_lng" in fields:
        from controllers.location_controller import _now

        fields["location_updated_at"] = _now()

    for field, value in fields.items():
        setattr(vehicle, field, value)

    db.commit()
    return get_vehicle_by_id(db, vehicle_id)


def deactivate_vehicle(db: Session, user: User, vehicle_id: int) -> None:
    """Remove veículo da listagem (soft delete)."""
    vehicle = _get_own_vehicle(db, user, vehicle_id)
    vehicle.status = VEHICLE_STATUS_INACTIVE
    db.commit()
