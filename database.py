"""
Ligação à base de dados PostgreSQL via SQLAlchemy.
Fornece sessão por pedido HTTP (dependency injection).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

# Motor de ligação à base de dados
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Fábrica de sessões (uma sessão por pedido)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""

    pass


def get_db():
    """
    Gera uma sessão de base de dados e fecha-a no fim do pedido.
    Usado como dependência FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
