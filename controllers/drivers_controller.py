"""
Controller de motoristas: perfil, disponibilidade e listagem.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models import Driver, User
from schemas import DriverProfileUpdateRequest


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
    """Lista motoristas; filtro opcional por disponibilidade."""
    query = db.query(Driver).options(joinedload(Driver.user))
    if available_only:
        query = query.filter(Driver.available.is_(True))
    return query.all()


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
