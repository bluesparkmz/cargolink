"""
Rotas de utilizadores: dados base e perfil geral.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.users_controller import get_user_by_id, get_user_profile, update_user
from deps import get_current_user
from database import get_db
from models import User
from schemas import UserProfileResponse, UserResponse, UserUpdateRequest

router = APIRouter()


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perfil completo do utilizador autenticado (cliente ou motorista)."""
    return get_user_profile(db, current_user)


@router.patch("/me", response_model=UserResponse)
def update_my_user(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza dados base do utilizador autenticado."""
    return update_user(db, current_user, data)


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta utilizador por id (requer autenticação)."""
    return get_user_by_id(db, user_id)
