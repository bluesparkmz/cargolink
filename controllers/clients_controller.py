"""
Controller de clientes: perfil e listagem.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models import Client, Company, User
from schemas import ClientProfileUpdateRequest, ConvertClientToCompanyRequest


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


def convert_client_to_company(db: Session, user: User, data: ConvertClientToCompanyRequest) -> Company:
    """
    Converte utilizador cliente para empresa transportadora.
    
    Operações:
    - Valida que é cliente
    - Muda user.user_type para "empresa"
    - Cria novo perfil Company
    - Mantém histórico do perfil Client
    """
    require_client(user)
    
    # Verifica se já tem um perfil de empresa
    existing_company = db.query(Company).filter(Company.user_id == user.id).first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Utilizador já é uma empresa transportadora",
        )
    
    # Muda tipo de utilizador para empresa
    user.user_type = "empresa"
    
    # Cria novo perfil de empresa
    company = Company(
        user_id=user.id,
        company_name=data.company_name,
        tax_id=data.tax_id,
        license_number=data.license_number,
        address=data.address,
        city=data.city,
        state=data.state,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    db.refresh(user)
    
    return company

