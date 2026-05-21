"""
Controller de cargas: publicar, listar, imagens e propostas.
"""

import math
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from constants import (
    LOAD_FILL_IDS,
    LOAD_FILL_LABELS,
    LOAD_TYPE_IDS,
    LOAD_TYPE_LABELS,
    MAX_LOAD_IMAGES,
    ROUTE_AVG_SPEED_KMH_MAX,
    ROUTE_AVG_SPEED_KMH_MIN,
    WEIGHT_UNITS,
)
from models import Client, Driver, Load, LoadImage, LoadProposal, Rating, Trip, TripLocation, User
from controllers.trips_controller import _user_can_access_trip
from schemas import (
    LoadCreateRequest,
    LoadDetailResponse,
    LoadImageCreateRequest,
    LoadImageResponse,
    LoadProposalCreateRequest,
    LoadRouteEstimate,
    LoadSenderSummary,
    LoadUpdateRequest,
)


def _generate_load_code() -> str:
    """Gera código único para a carga."""
    return f"CL-{uuid.uuid4().hex[:8].upper()}"


def _validate_load_type(load_type: str) -> None:
    """Valida tipo de carga contra catálogo do app."""
    if load_type not in LOAD_TYPE_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de carga inválido. Use um de: {', '.join(sorted(LOAD_TYPE_IDS))}",
        )


def _validate_weight_unit(weight_unit: str | None) -> None:
    """Valida unidade de peso."""
    if weight_unit and weight_unit not in WEIGHT_UNITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unidade de peso inválida. Use: {', '.join(WEIGHT_UNITS)}",
        )


def _validate_load_fill(load_fill: str | None) -> None:
    """Valida tipo completa / meia carga."""
    if load_fill and load_fill not in LOAD_FILL_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de volume inválido. Use: {', '.join(sorted(LOAD_FILL_IDS))}",
        )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distância em linha recta entre dois pontos (aproximação de rota)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _estimate_route(load: Load, trip: Trip | None) -> LoadRouteEstimate | None:
    """Calcula distância e tempo para a secção Rota do app."""
    distance_km: float | None = None

    if trip and trip.total_distance_km is not None:
        distance_km = float(trip.total_distance_km)
    elif (
        load.origin_lat is not None
        and load.origin_lng is not None
        and load.destination_lat is not None
        and load.destination_lng is not None
    ):
        straight = _haversine_km(
            float(load.origin_lat),
            float(load.origin_lng),
            float(load.destination_lat),
            float(load.destination_lng),
        )
        distance_km = round(straight * 1.15, 1)

    if distance_km is None:
        return None

    if trip and trip.estimated_time:
        return LoadRouteEstimate(
            distance_km=distance_km,
            estimated_time_label=trip.estimated_time,
        )

    hours_min = distance_km / ROUTE_AVG_SPEED_KMH_MAX
    hours_max = distance_km / ROUTE_AVG_SPEED_KMH_MIN
    h_min, m_min = int(hours_min), int((hours_min % 1) * 60)
    h_max, m_max = int(hours_max), int((hours_max % 1) * 60)
    if m_min >= 30:
        h_min += 1
    if m_max >= 30:
        h_max += 1
    label = f"{h_min}h" if h_min == h_max else f"{h_min}h - {h_max}h"
    avg_minutes = int((hours_min + hours_max) / 2 * 60)

    return LoadRouteEstimate(
        distance_km=distance_km,
        estimated_time_min=avg_minutes,
        estimated_time_label=label,
    )


def _client_ratings(db: Session, user_id: int) -> tuple[float | None, int]:
    """Média e total de avaliações recebidas pelo cliente."""
    avg, count = (
        db.query(func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.rated_user_id == user_id, Rating.score.isnot(None))
        .first()
    ) or (None, 0)
    return (round(float(avg), 1) if avg is not None else None, int(count or 0))


def build_load_detail_response(db: Session, load: Load) -> LoadDetailResponse:
    """Monta resposta completa do ecrã Detalhes da Carga."""
    if not load.client or not load.client.user:
        client = (
            db.query(Client)
            .options(joinedload(Client.user))
            .filter(Client.id == load.client_id)
            .first()
        )
        load.client = client

    user = load.client.user
    avg_rating, rating_count = _client_ratings(db, user.id)
    trip = db.query(Trip).filter(Trip.load_id == load.id).first()
    proposals_count = (
        db.query(func.count(LoadProposal.id)).filter(LoadProposal.load_id == load.id).scalar() or 0
    )

    return LoadDetailResponse(
        id=load.id,
        client_id=load.client_id,
        code=load.code,
        load_type=load.load_type,
        load_name=load.load_name,
        description=load.description,
        weight=float(load.weight) if load.weight is not None else None,
        weight_unit=load.weight_unit,
        volume=float(load.volume) if load.volume is not None else None,
        value=float(load.value) if load.value is not None else None,
        negotiable=load.negotiable,
        origin=load.origin,
        destination=load.destination,
        origin_lat=float(load.origin_lat) if load.origin_lat is not None else None,
        origin_lng=float(load.origin_lng) if load.origin_lng is not None else None,
        destination_lat=float(load.destination_lat) if load.destination_lat is not None else None,
        destination_lng=float(load.destination_lng) if load.destination_lng is not None else None,
        departure_date=load.departure_date,
        load_fill=load.load_fill,
        suggested_vehicle_type=load.suggested_vehicle_type,
        instructions=load.instructions,
        status=load.status,
        created_at=load.created_at,
        updated_at=load.updated_at,
        images=[LoadImageResponse.model_validate(img) for img in load.images],
        load_type_label=LOAD_TYPE_LABELS.get(load.load_type, load.load_type),
        load_fill_label=LOAD_FILL_LABELS.get(load.load_fill) if load.load_fill else None,
        sender=LoadSenderSummary(
            client_id=load.client_id,
            user_id=user.id,
            name=user.name,
            phone=user.phone,
            email=user.email,
            profile_photo=user.profile_photo,
            verified=user.verified,
            average_rating=avg_rating,
            rating_count=rating_count,
        ),
        route=_estimate_route(load, trip),
        proposals_count=proposals_count,
    )


def get_load_detail_response(db: Session, load_id: int) -> LoadDetailResponse:
    """Detalhe completo da carga para a API."""
    return build_load_detail_response(db, get_load_detail(db, load_id))


def get_client_or_403(db: Session, user: User) -> Client:
    """Obtém perfil cliente do utilizador autenticado."""
    if user.user_type != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes podem gerir cargas",
        )
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil cliente não encontrado",
        )
    return client


def get_driver_or_403(db: Session, user: User) -> Driver:
    """Obtém perfil motorista do utilizador autenticado."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas motoristas podem enviar propostas",
        )
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil motorista não encontrado",
        )
    return driver


def get_load_detail(db: Session, load_id: int) -> Load:
    """Busca carga com imagens e cliente."""
    load = (
        db.query(Load)
        .options(
            joinedload(Load.images),
            joinedload(Load.client).joinedload(Client.user),
        )
        .filter(Load.id == load_id)
        .first()
    )
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga não encontrada")
    return load


def _attach_images(db: Session, load: Load, images: list[LoadImageCreateRequest]) -> None:
    """Associa imagens à carga (máximo 5)."""
    if len(images) > MAX_LOAD_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo de {MAX_LOAD_IMAGES} imagens por carga",
        )

    has_primary = any(img.is_primary for img in images)
    for index, img_data in enumerate(images):
        is_primary = img_data.is_primary or (index == 0 and not has_primary)
        if is_primary:
            for existing in load.images:
                existing.is_primary = False
        db.add(
            LoadImage(
                load_id=load.id,
                image_url=img_data.image_url,
                is_primary=is_primary,
            )
        )


def create_load(db: Session, user: User, data: LoadCreateRequest) -> LoadDetailResponse:
    """Cliente publica nova carga (com imagens opcionais no mesmo pedido)."""
    client = get_client_or_403(db, user)
    _validate_load_type(data.load_type)
    _validate_weight_unit(data.weight_unit)
    _validate_load_fill(data.load_fill)

    images = data.images or []
    if len(images) > MAX_LOAD_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo de {MAX_LOAD_IMAGES} imagens por carga",
        )

    payload = data.model_dump(exclude={"images"})
    load = Load(
        client_id=client.id,
        code=_generate_load_code(),
        **payload,
    )
    db.add(load)
    db.flush()

    if images:
        _attach_images(db, load, images)

    db.commit()
    return get_load_detail_response(db, load.id)


def list_available_loads(
    db: Session,
    *,
    status_filter: str | None = "disponivel",
    load_type: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    q: str | None = None,
    departure_date_from: date | None = None,
    departure_date_to: date | None = None,
) -> list[Load]:
    """Lista cargas com filtros (marketplace e pesquisa do app)."""
    query = db.query(Load)
    if status_filter:
        query = query.filter(Load.status == status_filter)
    if load_type:
        query = query.filter(Load.load_type == load_type)
    if origin:
        query = query.filter(Load.origin.ilike(f"%{origin}%"))
    if destination:
        query = query.filter(Load.destination.ilike(f"%{destination}%"))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            (Load.origin.ilike(pattern))
            | (Load.destination.ilike(pattern))
            | (Load.load_name.ilike(pattern))
            | (Load.code.ilike(pattern))
        )
    if departure_date_from:
        query = query.filter(Load.departure_date >= departure_date_from)
    if departure_date_to:
        query = query.filter(Load.departure_date <= departure_date_to)
    return query.order_by(Load.created_at.desc()).all()


def get_load_tracking(db: Session, user: User, load_id: int) -> dict:
    """Rastreio GPS da carga via viagem associada."""
    load = get_load_detail(db, load_id)
    trip = db.query(Trip).filter(Trip.load_id == load_id).first()

    if user.user_type == "cliente":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if not client or load.client_id != client.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    elif user.user_type == "motorista":
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if not driver:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
        allowed = trip is not None and trip.driver_id == driver.id
        if not allowed:
            allowed = (
                db.query(LoadProposal)
                .filter(LoadProposal.load_id == load_id, LoadProposal.driver_id == driver.id)
                .first()
                is not None
            )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    elif user.user_type != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    trackable = trip is not None and trip.status in (
        "viagem_iniciada",
        "aguardando_cliente",
    )
    locations: list[TripLocation] = []
    last_location = None

    if trip:
        _user_can_access_trip(db, user, trip)
        locations = (
            db.query(TripLocation)
            .filter(TripLocation.trip_id == trip.id)
            .order_by(TripLocation.created_at.asc())
            .all()
        )
        if locations:
            last_location = locations[-1]

    return {
        "load_id": load.id,
        "load_code": load.code,
        "load_status": load.status,
        "trip_id": trip.id if trip else None,
        "trip_status": trip.status if trip else None,
        "trackable": trackable,
        "locations": locations,
        "last_location": last_location,
    }


def list_my_loads(db: Session, user: User) -> list[Load]:
    """Lista cargas do cliente autenticado."""
    client = get_client_or_403(db, user)
    return (
        db.query(Load)
        .filter(Load.client_id == client.id)
        .order_by(Load.created_at.desc())
        .all()
    )


def update_load(db: Session, user: User, load_id: int, data: LoadUpdateRequest) -> LoadDetailResponse:
    """Cliente atualiza a própria carga."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    fields = data.model_dump(exclude_unset=True)
    if "load_type" in fields:
        _validate_load_type(fields["load_type"])
    if "weight_unit" in fields:
        _validate_weight_unit(fields.get("weight_unit"))
    if "load_fill" in fields:
        _validate_load_fill(fields.get("load_fill"))

    for field, value in fields.items():
        setattr(load, field, value)

    db.commit()
    return get_load_detail_response(db, load_id)


def delete_load(db: Session, user: User, load_id: int) -> None:
    """Cliente cancela carga."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    load.status = "cancelada"
    db.commit()


def add_load_image(
    db: Session, user: User, load_id: int, data: LoadImageCreateRequest
) -> LoadImage:
    """Cliente adiciona imagem à carga (respeita limite de 5)."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    if len(load.images) >= MAX_LOAD_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo de {MAX_LOAD_IMAGES} imagens por carga",
        )

    if data.is_primary:
        for img in load.images:
            img.is_primary = False

    image = LoadImage(load_id=load.id, image_url=data.image_url, is_primary=data.is_primary)
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def create_proposal(
    db: Session, user: User, load_id: int, data: LoadProposalCreateRequest
) -> LoadProposal:
    """Motorista envia proposta para carga disponível."""
    driver = get_driver_or_403(db, user)
    load = get_load_detail(db, load_id)

    if load.status != "disponivel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carga não está disponível para propostas",
        )

    exists = (
        db.query(LoadProposal)
        .filter(LoadProposal.load_id == load_id, LoadProposal.driver_id == driver.id)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já enviou proposta para esta carga",
        )

    proposal = LoadProposal(
        load_id=load_id,
        driver_id=driver.id,
        proposed_value=Decimal(str(data.proposed_value)) if data.proposed_value else None,
        message=data.message,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def list_load_proposals(db: Session, user: User, load_id: int) -> list[LoadProposal]:
    """Cliente vê propostas da sua carga."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    return (
        db.query(LoadProposal)
        .filter(LoadProposal.load_id == load_id)
        .order_by(LoadProposal.created_at.desc())
        .all()
    )


def accept_proposal(db: Session, user: User, load_id: int, proposal_id: int) -> Trip:
    """Cliente aceita proposta e cria viagem."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    if load.status != "disponivel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carga já não está disponível",
        )

    proposal = (
        db.query(LoadProposal)
        .filter(LoadProposal.id == proposal_id, LoadProposal.load_id == load_id)
        .first()
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada")
    if proposal.status != "pendente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposta já foi processada",
        )

    existing_trip = db.query(Trip).filter(Trip.load_id == load_id).first()
    if existing_trip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta carga já tem viagem associada",
        )

    proposal.status = "aceite"
    other_proposals = (
        db.query(LoadProposal)
        .filter(
            LoadProposal.load_id == load_id,
            LoadProposal.id != proposal_id,
            LoadProposal.status == "pendente",
        )
        .all()
    )
    for other in other_proposals:
        other.status = "recusada"

    load.status = "aceite"
    trip = Trip(load_id=load_id, driver_id=proposal.driver_id)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def reject_proposal(db: Session, user: User, load_id: int, proposal_id: int) -> LoadProposal:
    """Cliente recusa proposta."""
    client = get_client_or_403(db, user)
    load = get_load_detail(db, load_id)
    if load.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga de outro cliente")

    proposal = (
        db.query(LoadProposal)
        .filter(LoadProposal.id == proposal_id, LoadProposal.load_id == load_id)
        .first()
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada")
    if proposal.status != "pendente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposta já foi processada",
        )

    proposal.status = "recusada"
    db.commit()
    db.refresh(proposal)
    return proposal
