"""
Atualização de localização GPS — motorista e camiões.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from constants import VEHICLE_STATUS_AVAILABLE
from controllers.drivers_controller import get_my_driver
from controllers.vehicles_controller import _get_own_vehicle, get_vehicle_by_id
from models import Driver, User, Vehicle
from schemas import LocationUpdateRequest


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _apply_coords(entity: Driver | Vehicle, data: LocationUpdateRequest) -> None:
    entity.current_lat = Decimal(str(data.latitude))
    entity.current_lng = Decimal(str(data.longitude))
    entity.location_updated_at = _now()


def update_driver_location(db: Session, user: User, data: LocationUpdateRequest) -> Driver:
    """Motorista atualiza a própria posição no mapa."""
    driver = get_my_driver(db, user)
    _apply_coords(driver, data)

    if data.sync_vehicles:
        for vehicle in driver.vehicles:
            if vehicle.status == VEHICLE_STATUS_AVAILABLE:
                _apply_coords(vehicle, data)

    db.commit()
    db.refresh(driver)
    return driver


def update_vehicle_location(
    db: Session, user: User, vehicle_id: int, data: LocationUpdateRequest
) -> Vehicle:
    """Motorista atualiza posição de um camião específico."""
    vehicle = _get_own_vehicle(db, user, vehicle_id)
    _apply_coords(vehicle, data)
    db.commit()
    return get_vehicle_by_id(db, vehicle_id)


def resolve_vehicle_coordinates(vehicle: Vehicle) -> tuple[float | None, float | None]:
    """Coordenadas do camião ou, em fallback, do motorista."""
    if vehicle.current_lat is not None and vehicle.current_lng is not None:
        return float(vehicle.current_lat), float(vehicle.current_lng)
    driver = vehicle.driver
    if driver and driver.current_lat is not None and driver.current_lng is not None:
        return float(driver.current_lat), float(driver.current_lng)
    return None, None
