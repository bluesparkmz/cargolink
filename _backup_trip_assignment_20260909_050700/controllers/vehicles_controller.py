"""
Controller de veiculos (camioes).
"""

import shutil
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from config import settings
from constants import VEHICLE_STATUSES, VEHICLE_STATUS_INACTIVE
from controllers.companies_controller import get_company_driver_by_email
from controllers.drivers_controller import get_my_driver
from controllers.realtime_events import emit_to_user
from models.models import Company, Driver, User, Vehicle
from schemas.schemas import VehicleCreateRequest, VehicleUpdateRequest

ALLOWED_VEHICLE_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}
VEHICLE_UPLOAD_DIR = "uploads/vehicles"


def get_my_company(db: Session, user: User) -> Company:
    """Obtem a empresa transportadora do utilizador autenticado."""
    if user.user_type != "empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas transportadoras podem gerir frota",
        )
    company = db.query(Company).filter(Company.user_id == user.id).first()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de empresa nao encontrado",
        )
    return company


def _vehicle_options():
    return (
        joinedload(Vehicle.company).joinedload(Company.user),
        joinedload(Vehicle.driver).joinedload(Driver.user),
    )


def list_vehicles(
    db: Session,
    *,
    status_filter: str | None = "disponivel",
    available_only: bool = True,
) -> list[Vehicle]:
    """Lista camioes para o carrossel do app."""
    query = db.query(Vehicle).options(*_vehicle_options())
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    else:
        query = query.filter(Vehicle.status != VEHICLE_STATUS_INACTIVE)
    if available_only:
        query = query.outerjoin(Driver).filter(
            or_(Vehicle.driver_id.is_(None), Driver.available.is_(True))
        )
    return query.order_by(Vehicle.created_at.desc()).all()


def list_my_vehicles(db: Session, user: User) -> list[Vehicle]:
    """Lista veiculos da empresa ou atribuidos ao motorista autenticado."""
    query = db.query(Vehicle).options(*_vehicle_options())
    if user.user_type == "empresa":
        company = get_my_company(db, user)
        query = query.filter(Vehicle.company_id == company.id)
    elif user.user_type == "motorista":
        driver = get_my_driver(db, user)
        query = query.filter(Vehicle.driver_id == driver.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para empresas transportadoras ou motoristas",
        )
    return (
        query.filter(Vehicle.status != VEHICLE_STATUS_INACTIVE)
        .order_by(Vehicle.created_at.desc())
        .all()
    )


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Vehicle:
    """Detalhe do veiculo com empresa e motorista atribuido."""
    vehicle = (
        db.query(Vehicle)
        .options(*_vehicle_options())
        .filter(Vehicle.id == vehicle_id)
        .first()
    )
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )
    return vehicle


def _get_own_vehicle(db: Session, user: User, vehicle_id: int) -> Vehicle:
    """Veiculo gerido pela empresa ou atribuido ao motorista autenticado."""
    vehicle = get_vehicle_by_id(db, vehicle_id)
    allowed = False
    if user.user_type == "empresa":
        company = get_my_company(db, user)
        allowed = vehicle.company_id == company.id
    elif user.user_type == "motorista":
        driver = get_my_driver(db, user)
        allowed = vehicle.driver_id == driver.id

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veiculo de outra conta",
        )
    return vehicle


def _validate_vehicle_status(vehicle_status: str) -> None:
    if vehicle_status not in VEHICLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status invalido. Use: {', '.join(sorted(VEHICLE_STATUSES))}",
        )


def _validate_company_driver(db: Session, company: Company, driver_id: int | None) -> None:
    if driver_id is None:
        return
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver is None or driver.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motorista invalido para esta empresa",
        )


def _normalize_vehicle_payload(payload: dict) -> dict:
    if payload.get("tonnage_capacity") is not None:
        payload["tonnage_capacity"] = Decimal(str(payload["tonnage_capacity"]))
    if payload.get("current_lat") is not None:
        payload["current_lat"] = Decimal(str(payload["current_lat"]))
    if payload.get("current_lng") is not None:
        payload["current_lng"] = Decimal(str(payload["current_lng"]))
    if payload.get("current_lat") is not None and payload.get("current_lng") is not None:
        from controllers.location_controller import _now

        payload["location_updated_at"] = _now()
    return payload


def save_vehicle_photo(file: UploadFile | None) -> str | None:
    """Guarda foto do camiao no volume persistente e devolve URL pública."""
    if file is None:
        return None

    extension = ALLOWED_VEHICLE_IMAGE_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foto invalida. Envie apenas ficheiros JPG ou PNG.",
        )

    upload_dir = Path(settings.STORAGE_DIR) / VEHICLE_UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = upload_dir / filename

    file.file.seek(0)
    with file_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    return f"/{VEHICLE_UPLOAD_DIR}/{filename}"


def create_vehicle(
    db: Session,
    user: User,
    data: VehicleCreateRequest,
    photo_file: UploadFile | None = None,
) -> Vehicle:
    """Empresa regista novo camiao e pode atribuir motorista."""
    company = get_my_company(db, user)
    _validate_vehicle_status(data.status)

    driver_id = data.driver_id
    if data.driver_email:
        if driver_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe driver_id ou driver_email, nao ambos",
            )
        driver = get_company_driver_by_email(db, company, str(data.driver_email))
        driver_id = driver.id
    _validate_company_driver(db, company, driver_id)

    existing = db.query(Vehicle).filter(Vehicle.plate == data.plate.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matricula ja registada",
        )

    payload = _normalize_vehicle_payload(
        data.model_dump(exclude={"driver_id", "driver_email"})
    )
    payload["driver_id"] = driver_id
    payload["plate"] = data.plate.strip().upper()
    if photo_file is not None:
        payload["photo"] = save_vehicle_photo(photo_file)

    vehicle = Vehicle(company_id=company.id, **payload)
    db.add(vehicle)
    db.commit()
    created = get_vehicle_by_id(db, vehicle.id)
    emit_to_user(user.id, {'type':'vehicle.created','vehicle_id':created.id,'company_id':company.id})
    return created


def update_vehicle(
    db: Session, user: User, vehicle_id: int, data: VehicleUpdateRequest, photo_file: UploadFile | None = None
) -> Vehicle:
    """Empresa atualiza o proprio veiculo (com upload opcional de foto)."""
    if user.user_type != "empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas podem editar dados do camiao",
        )
    company = get_my_company(db, user)
    vehicle = _get_own_vehicle(db, user, vehicle_id)
    fields = data.model_dump(exclude_unset=True)

    if fields.get("driver_email"):
        if fields.get("driver_id") is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe driver_id ou driver_email, nao ambos",
            )
        driver = get_company_driver_by_email(db, company, str(fields.pop("driver_email")))
        fields["driver_id"] = driver.id

    if "status" in fields:
        _validate_vehicle_status(fields["status"])
    if "driver_id" in fields:
        _validate_company_driver(db, company, fields["driver_id"])
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
                detail="Matricula ja registada",
            )
        fields["plate"] = plate

    # Processa upload de foto se fornecido
    if photo_file is not None:
        photo_url = save_vehicle_photo(photo_file)
        if photo_url:
            fields["photo"] = photo_url

    fields = _normalize_vehicle_payload(fields)
    for field, value in fields.items():
        setattr(vehicle, field, value)

    db.commit()
    updated = get_vehicle_by_id(db, vehicle_id)
    emit_to_user(user.id, {'type':'vehicle.updated','vehicle_id':updated.id,'company_id':company.id,'driver_id':updated.driver_id})
    return updated


def deactivate_vehicle(db: Session, user: User, vehicle_id: int) -> None:
    """Remove veiculo da listagem (soft delete)."""
    if user.user_type != "empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas podem desativar camioes",
        )
    vehicle = _get_own_vehicle(db, user, vehicle_id)
    vehicle.status = VEHICLE_STATUS_INACTIVE
    db.commit()
    emit_to_user(user.id, {'type':'vehicle.deactivated','vehicle_id':vehicle.id,'company_id':vehicle.company_id})
