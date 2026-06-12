"""
Controller de viagens: estados e localização GPS.
"""

from datetime import datetime, timezone
from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants import (
    TRIP_LOCATION_HEARTBEAT_SECONDS,
    TRIP_LOCATION_MIN_DISTANCE_METERS,
    TRIP_LOCATION_MIN_INTERVAL_SECONDS,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_STARTED,
    TRIP_STATUS_WAITING,
    TRIP_STATUS_WAITING_CLIENT,
)
from controllers.notifications_controller import create_notification, emit_notification
from controllers.realtime_events import emit_to_rooms
from models.models import Client, Company, Driver, Load, Trip, TripLocation, User, Vehicle
from schemas.schemas import TripLocationCreateRequest, TripStartRequest


def get_trip_detail(db: Session, trip_id: int) -> Trip:
    """Busca viagem por id."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viagem não encontrada")
    return trip


def _user_can_access_trip(db: Session, user: User, trip: Trip) -> None:
    """Verifica se utilizador é o motorista ou o cliente da carga."""
    if user.user_type == "motorista":
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if driver and trip.driver_id == driver.id:
            return
    if user.user_type == "cliente":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        load = db.query(Load).filter(Load.id == trip.load_id).first()
        if client and load and load.client_id == client.id:
            return
    if user.user_type == "empresa":
        company = db.query(Company).filter(Company.user_id == user.id).first()
        if company and trip.company_id == company.id:
            return
    if user.user_type == "admin":
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a esta viagem")


def _sync_live_location(
    trip: Trip,
    driver: Driver,
    latitude: Decimal,
    longitude: Decimal,
) -> None:
    """Mantem motorista e camiao da viagem na ultima posicao GPS recebida."""
    now = datetime.now(timezone.utc)
    driver.current_lat = latitude
    driver.current_lng = longitude
    driver.location_updated_at = now

    if trip.vehicle is not None:
        trip.vehicle.current_lat = latitude
        trip.vehicle.current_lng = longitude
        trip.vehicle.location_updated_at = now


def _distance_meters(
    lat1: Decimal,
    lng1: Decimal,
    lat2: Decimal,
    lng2: Decimal,
) -> float:
    """Calcula distancia aproximada entre dois pontos GPS."""
    earth_radius_m = 6371000
    phi1 = radians(float(lat1))
    phi2 = radians(float(lat2))
    delta_phi = radians(float(lat2 - lat1))
    delta_lambda = radians(float(lng2 - lng1))
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return earth_radius_m * 2 * atan2(sqrt(a), sqrt(1 - a))


def _seconds_since(created_at: datetime | None) -> float | None:
    if created_at is None:
        return None
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        return (now.replace(tzinfo=None) - created_at).total_seconds()
    return (now - created_at).total_seconds()


def _latest_trip_location(db: Session, trip_id: int) -> TripLocation | None:
    return (
        db.query(TripLocation)
        .filter(TripLocation.trip_id == trip_id)
        .order_by(TripLocation.created_at.desc())
        .first()
    )


def _should_store_trip_location(
    last_location: TripLocation | None,
    latitude: Decimal,
    longitude: Decimal,
) -> bool:
    if last_location is None:
        return True

    elapsed_seconds = _seconds_since(last_location.created_at)
    if elapsed_seconds is not None and elapsed_seconds >= TRIP_LOCATION_HEARTBEAT_SECONDS:
        return True

    if elapsed_seconds is not None and elapsed_seconds < TRIP_LOCATION_MIN_INTERVAL_SECONDS:
        return False

    distance = _distance_meters(
        last_location.latitude,
        last_location.longitude,
        latitude,
        longitude,
    )
    return distance >= TRIP_LOCATION_MIN_DISTANCE_METERS


def _trip_event_rooms(trip: Trip) -> set[str]:
    rooms = {f"trip:{trip.id}", f"load:{trip.load_id}"}
    if trip.company_id:
        rooms.add(f"company:{trip.company_id}")
    if trip.driver_id:
        rooms.add(f"driver:{trip.driver_id}")
    return rooms


def _trip_user_ids(db: Session, trip: Trip) -> set[int]:
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


def _trip_status_event_payload(db: Session, trip: Trip) -> dict:
    """Monta payload realtime com contexto de motorista/veiculo para cliente e empresa."""
    driver = db.query(Driver).options(joinedload(Driver.user)).filter(Driver.id == trip.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first() if trip.vehicle_id else None
    load = db.query(Load).filter(Load.id == trip.load_id).first()
    client_id = load.client_id if load else None

    return {
        "type": "trip.status_changed",
        "trip_id": trip.id,
        "load_id": trip.load_id,
        "client_id": client_id,
        "company_id": trip.company_id,
        "status": trip.status,
        "started_at": trip.started_at,
        "arrived_at": trip.arrived_at,
        "completed_at": trip.completed_at,
        "driver": {
            "id": driver.id,
            "name": driver.user.name if driver and driver.user else None,
            "phone": driver.user.phone if driver and driver.user else None,
            "current_lat": driver.current_lat if driver else None,
            "current_lng": driver.current_lng if driver else None,
        }
        if driver
        else None,
        "vehicle": {
            "id": vehicle.id,
            "plate": vehicle.plate,
            "brand": vehicle.brand,
            "model_name": vehicle.model_name,
            "vehicle_type": vehicle.vehicle_type,
            "current_lat": vehicle.current_lat,
            "current_lng": vehicle.current_lng,
        }
        if vehicle
        else None,
    }


def _emit_trip_status_changed(
    db: Session,
    trip: Trip,
    *,
    title: str,
    body: str,
    notification_type: str,
) -> None:
    notifications = [
        create_notification(
            db,
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            payload={"trip_id": trip.id, "load_id": trip.load_id, "status": trip.status},
        )
        for user_id in _trip_user_ids(db, trip)
    ]
    db.commit()
    for notification in notifications:
        db.refresh(notification)
        emit_notification(notification)
    emit_to_rooms(_trip_event_rooms(trip), _trip_status_event_payload(db, trip))


def list_my_trips(db: Session, user: User) -> list[Trip]:
    """Lista viagens do motorista ou do cliente."""
    if user.user_type == "motorista":
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if driver is None:
            return []
        return (
            db.query(Trip)
            .filter(Trip.driver_id == driver.id)
            .order_by(Trip.created_at.desc())
            .all()
        )

    if user.user_type == "cliente":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if client is None:
            return []
        return (
            db.query(Trip)
            .join(Load, Trip.load_id == Load.id)
            .filter(Load.client_id == client.id)
            .order_by(Trip.created_at.desc())
            .all()
        )

    if user.user_type == "empresa":
        company = db.query(Company).filter(Company.user_id == user.id).first()
        if company is None:
            return []
        return (
            db.query(Trip)
            .filter(Trip.company_id == company.id)
            .order_by(Trip.created_at.desc())
            .all()
        )

    return []


def start_trip(db: Session, user: User, trip_id: int, data: TripStartRequest) -> Trip:
    """Motorista inicia a viagem."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas motoristas podem iniciar viagem",
        )

    trip = get_trip_detail(db, trip_id)
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if driver is None or trip.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viagem de outro motorista")

    if trip.status != TRIP_STATUS_WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Viagem não pode ser iniciada neste estado",
        )

    if data.vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
        if vehicle is None or vehicle.company_id != trip.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veículo inválido para este motorista",
            )
        if vehicle.driver_id is not None and vehicle.driver_id != driver.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veiculo atribuido a outro motorista",
            )
        trip.vehicle_id = data.vehicle_id

    trip.status = TRIP_STATUS_STARTED
    trip.started_at = datetime.now(timezone.utc)
    if data.total_distance_km is not None:
        trip.total_distance_km = Decimal(str(data.total_distance_km))
    if data.estimated_time:
        trip.estimated_time = data.estimated_time

    load = db.query(Load).filter(Load.id == trip.load_id).first()
    if load:
        load.status = "em_viagem"

    db.commit()
    db.refresh(trip)
    _emit_trip_status_changed(
        db,
        trip,
        title="Viagem iniciada",
        body="O motorista iniciou a viagem.",
        notification_type="trip.started",
    )
    return trip


def arrive_trip(db: Session, user: User, trip_id: int) -> Trip:
    """Motorista confirma chegada ao destino."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas motoristas podem confirmar chegada",
        )

    trip = get_trip_detail(db, trip_id)
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if driver is None or trip.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viagem de outro motorista")

    if trip.status != TRIP_STATUS_STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Viagem deve estar em curso para confirmar chegada",
        )

    trip.status = TRIP_STATUS_WAITING_CLIENT
    trip.arrived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trip)
    _emit_trip_status_changed(
        db,
        trip,
        title="Motorista chegou ao destino",
        body="A carga chegou ao destino. Aguarda confirmacao do cliente.",
        notification_type="trip.arrived",
    )
    return trip


def confirm_delivery(db: Session, user: User, trip_id: int) -> Trip:
    """Cliente confirma entrega concluída."""
    if user.user_type != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes podem confirmar entrega",
        )

    trip = get_trip_detail(db, trip_id)
    client = db.query(Client).filter(Client.user_id == user.id).first()
    load = db.query(Load).filter(Load.id == trip.load_id).first()
    if client is None or load is None or load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viagem de outro cliente")

    if trip.status != TRIP_STATUS_WAITING_CLIENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aguarde confirmação de chegada do motorista",
        )

    now = datetime.now(timezone.utc)
    trip.status = TRIP_STATUS_COMPLETED
    trip.client_confirmed_at = now
    trip.completed_at = now
    load.status = "concluida"

    if trip.driver_id:
        driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
        if driver:
            driver.total_trips += 1
    if trip.company_id:
        company = db.query(Company).filter(Company.id == trip.company_id).first()
        if company:
            company.total_trips += 1

    db.commit()
    db.refresh(trip)
    _emit_trip_status_changed(
        db,
        trip,
        title="Entrega confirmada",
        body="A entrega foi confirmada pelo cliente.",
        notification_type="trip.completed",
    )
    return trip


def add_trip_location(
    db: Session, user: User, trip_id: int, data: TripLocationCreateRequest
) -> TripLocation:
    """Regista ponto GPS durante a viagem."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas motoristas enviam localização",
        )

    trip = get_trip_detail(db, trip_id)
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if driver is None or trip.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viagem de outro motorista")

    if trip.status != TRIP_STATUS_STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Localização só durante viagem em curso",
        )

    if data.traveled_distance_km is not None:
        trip.traveled_distance_km = Decimal(str(data.traveled_distance_km))

    latitude = Decimal(str(data.latitude))
    longitude = Decimal(str(data.longitude))
    _sync_live_location(trip, driver, latitude, longitude)
    last_location = _latest_trip_location(db, trip_id)
    if not _should_store_trip_location(last_location, latitude, longitude):
        db.commit()
        return last_location

    location = TripLocation(
        trip_id=trip_id,
        latitude=latitude,
        longitude=longitude,
        speed=Decimal(str(data.speed)) if data.speed is not None else None,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def list_trip_locations(db: Session, user: User, trip_id: int) -> list[TripLocation]:
    """Lista pontos GPS da viagem."""
    trip = get_trip_detail(db, trip_id)
    _user_can_access_trip(db, user, trip)
    return (
        db.query(TripLocation)
        .filter(TripLocation.trip_id == trip_id)
        .order_by(TripLocation.created_at.asc())
        .all()
    )
