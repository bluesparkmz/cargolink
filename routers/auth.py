"""
Rotas de autenticação: registo, login e perfil atual.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.auth_controller import (
    authenticate_google_user,
    authenticate_user,
    change_password,
    create_user_token,
    register_user,
)
from deps import get_current_user
from database import get_db
from models.models import User
from schemas.schemas import (
    GoogleLoginRequest,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Regista novo cliente ou motorista e devolve token JWT."""
    user = register_user(db, data)
    token = create_user_token(user)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica por email e senha; devolve token JWT."""
    user = authenticate_user(db, data.email, data.password)
    token = create_user_token(user)
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Autentica com id_token do Google; devolve token JWT local."""
    user = authenticate_google_user(db, data.id_token)
    token = create_user_token(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Devolve dados do utilizador autenticado (requer Bearer token)."""
    return current_user


@router.patch("/password")
def update_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Altera senha (ecrã Segurança do perfil)."""
    change_password(db, current_user, data)
    return {"message": "Senha alterada com sucesso"}
