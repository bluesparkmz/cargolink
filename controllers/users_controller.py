"""
Controller de utilizadores: perfil e atualização dos dados base.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models import User
from schemas import UserUpdateRequest


def get_user_profile(db: Session, user: User) -> User:
    """Carrega utilizador com perfil cliente ou motorista."""
    return (
        db.query(User)
        .options(joinedload(User.client), joinedload(User.driver))
        .filter(User.id == user.id)
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User:
    """Busca utilizador por id com perfis relacionados."""
    user = (
        db.query(User)
        .options(joinedload(User.client), joinedload(User.driver))
        .filter(User.id == user_id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado")
    return user


def update_user(db: Session, user: User, data: UserUpdateRequest) -> User:
    """Atualiza nome, email ou foto de perfil."""
    if data.email and data.email != user.email:
        exists = db.query(User).filter(User.email == data.email, User.id != user.id).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registado",
            )
        user.email = data.email

    if data.name is not None:
        user.name = data.name
    if data.profile_photo is not None:
        user.profile_photo = data.profile_photo

    db.commit()
    db.refresh(user)
    return get_user_profile(db, user)
