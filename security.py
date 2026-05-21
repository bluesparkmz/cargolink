"""
Utilitários de segurança: hash de senhas e tokens JWT.
Usa passlib (bcrypt) e python-jose.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

# Contexto de hashing com bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha em texto plano."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Compara senha em texto plano com o hash armazenado."""
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    """
    Cria token JWT com payload (ex.: sub = id do utilizador).
    Inclui data de expiração.
    """
    payload = data.copy()
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload.update({"exp": expires_at})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """
    Decodifica e valida o token JWT.
    Devolve None se inválido ou expirado.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
