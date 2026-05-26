"""
Controller de motoristas: perfil, disponibilidade e listagem.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.models import Driver, User
from schemas.schemas import DriverProfileUpdateRequest

from controllers.companies_controller import get_my_company


def require_driver(user: User) -> None:
    """Garante que o utilizador autenticado é motorista."""
    if user.user_type != "motorista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para motoristas",
        )


def get_my_driver(db: Session, user: User) -> Driver:
    """Retorna perfil motorista do utilizador autenticado."""
    require_driver(user)
    driver = (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.user_id == user.id)
        .first()
    )
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil motorista não encontrado",
        )
    return driver


def get_driver_by_id(db: Session, driver_id: int) -> Driver:
    """Busca motorista por id com dados do utilizador."""
    driver = (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.id == driver_id)
        .first()
    )
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motorista não encontrado",
        )
    return driver


def list_drivers(db: Session, available_only: bool = False) -> list[Driver]:
    """Lista todos os motoristas (apenas uso interno/admin)."""
    query = db.query(Driver).options(joinedload(Driver.user))
    if available_only:
        query = query.filter(Driver.available.is_(True))
    return query.all()


def list_drivers_for_user(db: Session, user: User, available_only: bool = False) -> list[Driver]:
    """Listagem com privacidade: empresa ve so os seus; motorista usa /me."""
    if user.user_type == "admin":
        return list_drivers(db, available_only=available_only)
    if user.user_type == "empresa":
        from controllers.companies_controller import list_company_drivers

        drivers = list_company_drivers(db, user)
        if available_only:
            drivers = [d for d in drivers if d.available]
        return drivers
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Listagem de motoristas nao permitida. Empresa: use GET /companies/me/drivers",
    )


def get_driver_for_user(db: Session, user: User, driver_id: int) -> Driver:
    """Consulta motorista com controlo de acesso."""
    driver = get_driver_by_id(db, driver_id)
    if user.user_type == "admin":
        return driver
    if user.user_type == "motorista":
        if driver.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado a este motorista",
            )
        return driver
    if user.user_type == "empresa":
        company = get_my_company(db, user)
        if driver.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Motorista nao pertence a sua empresa",
            )
        return driver
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado",
    )


def update_my_driver(db: Session, user: User, data: DriverProfileUpdateRequest) -> Driver:
    """Atualiza perfil do motorista autenticado."""
    driver = get_my_driver(db, user)
    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(driver, field, value)
    db.commit()
    db.refresh(driver)
    return get_driver_by_id(db, driver.id)


def set_availability(db: Session, user: User, available: bool) -> Driver:
    """Define se o motorista está disponível para viagens."""
    driver = get_my_driver(db, user)
    driver.available = available
    db.commit()
    db.refresh(driver)
    return get_driver_by_id(db, driver.id)
