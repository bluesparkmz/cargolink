"""
Controller de clientes: perfil e listagem.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models import Client, User
from schemas import ClientProfileUpdateRequest


def require_client(user: User) -> None:
    """Garante que o utilizador autenticado é cliente."""
    if user.user_type != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para clientes",
        )


def get_my_client(db: Session, user: User) -> Client:
    """Retorna perfil cliente do utilizador autenticado."""
    require_client(user)
    client = (
        db.query(Client)
        .options(joinedload(Client.user))
        .filter(Client.user_id == user.id)
        .first()
    )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil cliente não encontrado",
        )
    return client


def get_client_by_id(db: Session, client_id: int) -> Client:
    """Busca cliente por id com dados do utilizador."""
    client = (
        db.query(Client)
        .options(joinedload(Client.user))
        .filter(Client.id == client_id)
        .first()
    )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return client


def list_clients(db: Session) -> list[Client]:
    """Lista todos os clientes com utilizador associado."""
    return db.query(Client).options(joinedload(Client.user)).all()


def update_my_client(db: Session, user: User, data: ClientProfileUpdateRequest) -> Client:
    """Atualiza perfil do cliente autenticado."""
    client = get_my_client(db, user)
    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return get_client_by_id(db, client.id)
