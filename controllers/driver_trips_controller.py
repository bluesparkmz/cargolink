"""
Controller do app motorista: viagens, GPS e paragens.
Sem negociação, pagamentos ou carteira.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants import (
    STOP_TYPE_IDS,
    TRIP_GROUP_COMPLETED,
    TRIP_GROUP_IN_PROGRESS,
    TRIP_GROUP_STATUSES,
    TRIP_STATUS_STARTED,
)
from models.models import Client, Driver, Load, Trip, TripLocation, TripStop, User
from schemas.schemas import TripLocationCreateRequest, TripStartRequest, TripStopCreateRequest


def require_driver(db: Session, user: User) -> Driver:
    """Garante utilizador motorista com perfil."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso apenas para motoristas",
        )
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil motorista não encontrado",
        )
    return driver


def get_driver_trip(db: Session, driver: Driver, trip_id: int) -> Trip:
    """Busca viagem do motorista com carga, cliente e paragens."""
    trip = (
        db.query(Trip)
        .options(
            joinedload(Trip.load).joinedload(Load.client).joinedload(Client.user),
            joinedload(Trip.vehicle),
            joinedload(Trip.stops),
        )
        .filter(Trip.id == trip_id, Trip.driver_id == driver.id)
        .first()
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viagem não encontrada")
    return trip


def _calc_progress(trip: Trip) -> float | None:
    """Calcula percentagem percorrida com base na distância."""
    if trip.total_distance_km and trip.traveled_distance_km:
        total = float(trip.total_distance_km)
        traveled = float(trip.traveled_distance_km)
        if total > 0:
            return min(round((traveled / total) * 100, 1), 100.0)
    return None


def _sync_live_location(
    trip: Trip,
    driver: Driver,
    latitude: Decimal,
    longitude: Decimal,
) -> None:
    """Mantem a posicao atual sincronizada com o ultimo ponto GPS da viagem."""
    now = datetime.now(timezone.utc)
    driver.current_lat = latitude
    driver.current_lng = longitude
    driver.location_updated_at = now

    if trip.vehicle is not None:
        trip.vehicle.current_lat = latitude
        trip.vehicle.current_lng = longitude
        trip.vehicle.location_updated_at = now


def build_trip_list_item(trip: Trip) -> dict:
    """Monta item para lista Minhas Viagens."""
    load = trip.load
    client_user = load.client.user if load and load.client else None
    return {
        "id": trip.id,
        "load_code": load.code if load else "",
        "origin": load.origin if load else "",
        "destination": load.destination if load else "",
        "client_name": client_user.name if client_user else "",
        "status": trip.status,
        "started_at": trip.started_at,
        "estimated_time": trip.estimated_time,
        "departure_date": load.departure_date if load else None,
        "created_at": trip.created_at,
    }


def build_trip_detail(trip: Trip) -> dict:
    """Monta detalhe completo para o ecrã do motorista."""
    load = trip.load
    client_user = load.client.user if load and load.client else None
    data = {
        "id": trip.id,
        "load_id": trip.load_id,
        "company_id": trip.company_id,
        "driver_id": trip.driver_id,
        "vehicle_id": trip.vehicle_id,
        "status": trip.status,
        "started_at": trip.started_at,
        "arrived_at": trip.arrived_at,
        "client_confirmed_at": trip.client_confirmed_at,
        "completed_at": trip.completed_at,
        "total_distance_km": float(trip.total_distance_km) if trip.total_distance_km else None,
        "traveled_distance_km": float(trip.traveled_distance_km)
        if trip.traveled_distance_km
        else None,
        "estimated_time": trip.estimated_time,
        "created_at": trip.created_at,
        "load_code": load.code if load else "",
        "load_type": load.load_type if load else "",
        "origin": load.origin if load else "",
        "destination": load.destination if load else "",
        "client_name": client_user.name if client_user else "",
        "client_phone": client_user.phone if client_user else None,
        "progress_percent": _calc_progress(trip),
        "stops": trip.stops,
    }
    return data


def list_driver_trips(db: Session, user: User, group: str | None = None) -> list[dict]:
    """Lista viagens do motorista (em_andamento ou concluidas)."""
    driver = require_driver(db, user)
    query = (
        db.query(Trip)
        .join(Load, Trip.load_id == Load.id)
        .options(joinedload(Trip.load).joinedload(Load.client).joinedload(Client.user))
        .filter(Trip.driver_id == driver.id)
    )

    if group:
        if group not in TRIP_GROUP_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Grupo inválido. Use: {TRIP_GROUP_IN_PROGRESS}, {TRIP_GROUP_COMPLETED}",
            )
        query = query.filter(Trip.status.in_(TRIP_GROUP_STATUSES[group]))

    trips = query.order_by(Trip.created_at.desc()).all()
    return [build_trip_list_item(t) for t in trips]


def get_driver_trip_detail(db: Session, user: User, trip_id: int) -> dict:
    """Detalhe da viagem para o motorista."""
    driver = require_driver(db, user)
    trip = get_driver_trip(db, driver, trip_id)
    return build_trip_detail(trip)


def start_driver_trip(db: Session, user: User, trip_id: int, data: TripStartRequest) -> dict:
    """Motorista inicia viagem."""
    from controllers.trips_controller import start_trip

    trip = start_trip(db, user, trip_id, data)
    driver = require_driver(db, user)
    return build_trip_detail(get_driver_trip(db, driver, trip.id))


def end_driver_trip(db: Session, user: User, trip_id: int) -> dict:
    """Motorista encerra viagem / confirma chegada ao destino."""
    from controllers.trips_controller import arrive_trip

    trip = arrive_trip(db, user, trip_id)
    driver = require_driver(db, user)
    return build_trip_detail(get_driver_trip(db, driver, trip.id))


def add_driver_location(
    db: Session, user: User, trip_id: int, data: TripLocationCreateRequest
) -> TripLocation:
    """Envia GPS e opcionalmente atualiza distância percorrida."""
    driver = require_driver(db, user)
    trip = get_driver_trip(db, driver, trip_id)

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


def list_driver_locations(db: Session, user: User, trip_id: int) -> list[TripLocation]:
    """Histórico GPS da viagem."""
    driver = require_driver(db, user)
    get_driver_trip(db, driver, trip_id)
    return (
        db.query(TripLocation)
        .filter(TripLocation.trip_id == trip_id)
        .order_by(TripLocation.created_at.asc())
        .all()
    )


def add_trip_stop(db: Session, user: User, trip_id: int, data: TripStopCreateRequest) -> TripStop:
    """Regista paragem (abastecimento, descanso, etc.)."""
    if data.stop_type not in STOP_TYPE_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de paragem inválido. Use: {', '.join(sorted(STOP_TYPE_IDS))}",
        )

    driver = require_driver(db, user)
    trip = get_driver_trip(db, driver, trip_id)

    if trip.status not in (TRIP_STATUS_STARTED,):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paragens só durante viagem em curso",
        )

    stopped_at = data.stopped_at or datetime.now(timezone.utc)
    stop = TripStop(
        trip_id=trip_id,
        stop_type=data.stop_type,
        location_name=data.location_name,
        address=data.address,
        notes=data.notes,
        stopped_at=stopped_at,
    )
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


def list_trip_stops(db: Session, user: User, trip_id: int) -> list[TripStop]:
    """Lista paragens da viagem."""
    driver = require_driver(db, user)
    get_driver_trip(db, driver, trip_id)
    return (
        db.query(TripStop)
        .filter(TripStop.trip_id == trip_id)
        .order_by(TripStop.stopped_at.asc())
        .all()
    )
