"""
Rotas de clientes: perfil e consulta.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.activities_controller import list_client_activities
from controllers.client_stats_controller import get_client_stats
from controllers.clients_controller import (
    get_client_by_id,
    get_my_client,
    list_clients,
    update_my_client,
    convert_client_to_company,
)
from deps import get_current_user
from database import get_db
from models.models import Client, User
from schemas.schemas import (
    ActivityItem,
    ClientDetailResponse,
    ClientListItem,
    ClientProfileUpdateRequest,
    ClientStatsResponse,
    ConvertClientToCompanyRequest,
    CompanyDetailResponse,
)

router = APIRouter()


def _to_list_item(client: Client) -> ClientListItem:
    """Monta resposta resumida com dados do utilizador."""
    return ClientListItem(
        id=client.id,
        user_id=client.user_id,
        name=client.user.name,
        client_type=client.client_type,
        city=client.city,
        company_name=client.company_name,
        verified=client.user.verified,
    )


@router.get("/me/stats", response_model=ClientStatsResponse)
def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cards Minhas atividades no perfil (publicadas, em andamento, concluídas, avaliação)."""
    return get_client_stats(db, current_user)


@router.get("/me/activities", response_model=list[ActivityItem])
def get_my_activities(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Feed Atividades recentes do cliente."""
    return list_client_activities(db, current_user, limit=limit)


@router.get("/me", response_model=ClientDetailResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perfil do cliente autenticado."""
    return get_my_client(db, current_user)


@router.patch("/me", response_model=ClientDetailResponse)
def update_me(
    data: ClientProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza perfil do cliente autenticado."""
    return update_my_client(db, current_user, data)


@router.get("", response_model=list[ClientListItem])
def list_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista clientes registados."""
    clients = list_clients(db)
    return [_to_list_item(c) for c in clients]


@router.get("/{client_id}", response_model=ClientDetailResponse)
def get_by_id(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta cliente por id."""
    return get_client_by_id(db, client_id)


@router.post("/convert-to-company", response_model=CompanyDetailResponse, status_code=201)
def convert_to_company(
    data: ConvertClientToCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Converte perfil cliente do utilizador para empresa transportadora.
    
    Requer:
    - Utilizador autenticado com tipo = cliente
    - Dados obrigatórios: company_name
    
    Resultado:
    - Muda user_type para "empresa"
    - Cria novo perfil Company
    - Retorna dados da empresa criada
    """
    return convert_client_to_company(db, current_user, data)
