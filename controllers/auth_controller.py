"""
Controller de autenticação: registo, login e perfil.
Sem lógica de carteira ou pagamentos.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from security import create_access_token, hash_password, verify_password
from models.models import Client, Company, Driver, User, Wallet
from schemas.schemas import PasswordChangeRequest, RegisterRequest


def register_user(db: Session, data: RegisterRequest) -> User:
    """
    Cria utilizador e perfil (cliente, empresa ou motorista).
    Valida email único.
    """
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registado",
        )

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone or "",
        password_hash=hash_password(data.password),
        user_type=data.user_type,
    )
    db.add(user)
    db.flush()
    db.add(Wallet(user_id=user.id))

    if data.user_type == "cliente":
        profile = Client(
            user_id=user.id,
            client_type=data.client_type or "individual",
            company_name=data.company_name,
            city=data.city,
            state=data.state,
        )
        db.add(profile)
    elif data.user_type == "motorista":
        profile = Driver(user_id=user.id)
        db.add(profile)
    elif data.user_type == "empresa":
        profile = Company(
            user_id=user.id,
            company_name=data.company_name or data.name,
            city=data.city,
            state=data.state,
        )
        db.add(profile)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Valida credenciais por email e senha.
    Devolve o utilizador ou lança 401.
    """
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    if user.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa ou suspensa",
        )

    return user


def create_user_token(user: User) -> str:
    """Gera JWT com o id do utilizador no campo sub."""
    return create_access_token({"sub": str(user.id)})


def change_password(db: Session, user: User, data: PasswordChangeRequest) -> None:
    """Altera senha após validar a atual."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ser diferente da atual",
        )

    user.password_hash = hash_password(data.new_password)
    db.commit()
