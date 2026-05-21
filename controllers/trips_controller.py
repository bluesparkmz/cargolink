"""
Controller de viagens: estados e localização GPS.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants import (
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_STARTED,
    TRIP_STATUS_WAITING,
    TRIP_STATUS_WAITING_CLIENT,
)
from models import Client, Driver, Load, Trip, TripLocation, User, Vehicle
from schemas import TripLocationCreateRequest, TripStartRequest


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
    if user.user_type == "admin":
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a esta viagem")


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

    return db.query(Trip).order_by(Trip.created_at.desc()).all()


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
        if vehicle is None or vehicle.driver_id != driver.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veículo inválido para este motorista",
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

    db.commit()
    db.refresh(trip)
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

    location = TripLocation(
        trip_id=trip_id,
        latitude=Decimal(str(data.latitude)),
        longitude=Decimal(str(data.longitude)),
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
