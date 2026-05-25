"""
Controller de empresas transportadoras: perfil, motoristas e propostas.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.models import Company, Driver, LoadProposal, Trip, User
from schemas.schemas import CompanyProfileUpdateRequest


def require_company(user: User) -> None:
    """Garante que o utilizador autenticado e uma empresa transportadora."""
    if user.user_type != "empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para empresas transportadoras",
        )


def get_my_company(db: Session, user: User) -> Company:
    """Retorna perfil da empresa autenticada."""
    require_company(user)
    company = (
        db.query(Company)
        .options(joinedload(Company.user))
        .filter(Company.user_id == user.id)
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de empresa nao encontrado",
        )
    return company


def get_company_by_id(db: Session, company_id: int) -> Company:
    """Busca empresa por id com dados do utilizador."""
    company = (
        db.query(Company)
        .options(joinedload(Company.user))
        .filter(Company.id == company_id)
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )
    return company


def list_companies(db: Session) -> list[Company]:
    """Lista empresas transportadoras registadas."""
    return db.query(Company).options(joinedload(Company.user)).all()


def update_my_company(db: Session, user: User, data: CompanyProfileUpdateRequest) -> Company:
    """Atualiza perfil da empresa autenticada."""
    company = get_my_company(db, user)
    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return get_company_by_id(db, company.id)


def list_company_drivers(db: Session, user: User) -> list[Driver]:
    """Lista motoristas associados a empresa autenticada."""
    company = get_my_company(db, user)
    return (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.company_id == company.id)
        .order_by(Driver.created_at.desc())
        .all()
    )


def attach_driver_to_company(db: Session, user: User, driver_id: int) -> Driver:
    """Associa motorista existente a empresa autenticada."""
    company = get_my_company(db, user)
    driver = (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.id == driver_id)
        .first()
    )
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motorista nao encontrado",
        )
    if driver.company_id and driver.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motorista ja pertence a outra empresa",
        )

    driver.company_id = company.id
    db.commit()
    db.refresh(driver)
    return driver


def detach_driver_from_company(db: Session, user: User, driver_id: int) -> None:
    """Remove motorista da empresa autenticada."""
    company = get_my_company(db, user)
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver is None or driver.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motorista nao encontrado nesta empresa",
        )

    driver.company_id = None
    for vehicle in driver.vehicles:
        if vehicle.company_id == company.id:
            vehicle.driver_id = None
    db.commit()


def list_company_proposals(db: Session, user: User) -> list[LoadProposal]:
    """Lista propostas enviadas pela empresa autenticada."""
    company = get_my_company(db, user)
    return (
        db.query(LoadProposal)
        .filter(LoadProposal.company_id == company.id)
        .order_by(LoadProposal.created_at.desc())
        .all()
    )


def list_company_trips(db: Session, user: User) -> list[Trip]:
    """Lista viagens da empresa autenticada."""
    company = get_my_company(db, user)
    return (
        db.query(Trip)
        .filter(Trip.company_id == company.id)
        .order_by(Trip.created_at.desc())
        .all()
    )
