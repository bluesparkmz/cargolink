"""
Rotas administrativas (admin).

Objetivo: dar visibilidade básica do sistema para suporte/operacao:
- listar empresas com dados do perfil
- listar cargas relacionadas a uma empresa
- listar camiões de uma empresa
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models.models import Load, LoadProposal, Trip, User, Vehicle
from routers.companies import _to_list_item as _company_to_list_item
from routers.loads import _to_list_item as _load_to_list_item
from routers.vehicles import _to_list_item as _vehicle_to_list_item
from schemas.schemas import CompanyListItem, LoadListItem, VehicleListItem

router = APIRouter()


def _require_admin(user: User) -> None:
    if user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para admin",
        )


@router.get("/companies", response_model=list[CompanyListItem])
def list_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista empresas transportadoras (visão admin)."""
    _require_admin(current_user)
    from controllers.companies_controller import list_companies as _list_companies

    return [_company_to_list_item(c) for c in _list_companies(db)]


@router.get("/companies/{company_id}/vehicles", response_model=list[VehicleListItem])
def list_company_vehicles(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista camiões de uma empresa (visão admin)."""
    _require_admin(current_user)
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.company_id == company_id)
        .order_by(Vehicle.created_at.desc())
        .all()
    )
    return [_vehicle_to_list_item(v) for v in vehicles]


@router.get("/companies/{company_id}/loads", response_model=list[LoadListItem])
def list_company_loads(
    company_id: int,
    include_history: bool = Query(
        True, description="Se false, retorna apenas cargas ainda relevantes (com propostas/viagens ativas)."
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista cargas ligadas a uma empresa.

    Como não existe company_id direto em loads, a relação é via:
    - propostas (load_proposals.company_id)
    - viagens (trips.company_id)
    """
    _require_admin(current_user)

    load_ids_from_proposals = (
        db.query(LoadProposal.load_id).filter(LoadProposal.company_id == company_id).subquery()
    )
    load_ids_from_trips = db.query(Trip.load_id).filter(Trip.company_id == company_id).subquery()

    query = db.query(Load).filter(
        Load.id.in_(load_ids_from_proposals) | Load.id.in_(load_ids_from_trips)
    )

    if not include_history:
        # Regra simples: ignora cargas concluídas/canceladas.
        query = query.filter(Load.status.in_(["disponivel", "em_andamento"]))

    loads = query.order_by(Load.created_at.desc()).all()
    return [_load_to_list_item(l) for l in loads]
