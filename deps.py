"""
Dependências FastAPI reutilizáveis (autenticação, sessão DB).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import decode_token

# Esquema OAuth2: token enviado no header Authorization: Bearer ...
# Nota: Sem tokenUrl, o Swagger não tenta gerar um formulário de login automático
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extrai o utilizador autenticado a partir do token JWT.
    Lança 401 se o token for inválido ou o utilizador não existir.
    """
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise invalid_credentials

    user_id = payload.get("sub")
    if user_id is None:
        raise invalid_credentials

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise invalid_credentials

    if user.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa ou suspensa",
        )

    return user
