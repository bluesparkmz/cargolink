"""
Controller de propostas: envio, listagens, detalhe e decisão do cliente.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from controllers.loads_controller import accept_proposal, create_proposal, reject_proposal
from models import Client, Company, Driver, Load, LoadProposal, User, Vehicle
from schemas import LoadProposalCreateRequest


def _proposal_options():
    return (
        joinedload(LoadProposal.load),
        joinedload(LoadProposal.company),
        joinedload(LoadProposal.driver).joinedload(Driver.user),
        joinedload(LoadProposal.vehicle),
    )


def _get_company_for_user(db: Session, user: User) -> Company:
    if user.user_type != "empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas podem gerir propostas enviadas",
        )
    company = db.query(Company).filter(Company.user_id == user.id).first()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de empresa nao encontrado",
        )
    return company


def _get_client_for_user(db: Session, user: User) -> Client:
    if user.user_type != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes podem gerir propostas recebidas",
        )
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil cliente nao encontrado",
        )
    return client


def _query_proposal(db: Session, proposal_id: int) -> LoadProposal:
    proposal = (
        db.query(LoadProposal)
        .options(*_proposal_options())
        .filter(LoadProposal.id == proposal_id)
        .first()
    )
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposta nao encontrada",
        )
    return proposal


def _user_can_access_proposal(db: Session, user: User, proposal: LoadProposal) -> bool:
    if user.user_type == "admin":
        return True

    if user.user_type == "empresa":
        company = db.query(Company).filter(Company.user_id == user.id).first()
        return company is not None and proposal.company_id == company.id

    if user.user_type == "cliente":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        return client is not None and proposal.load is not None and proposal.load.client_id == client.id

    if user.user_type == "motorista":
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        return driver is not None and proposal.driver_id == driver.id

    return False


def send_proposal(
    db: Session,
    user: User,
    load_id: int,
    data: LoadProposalCreateRequest,
) -> LoadProposal:
    """Empresa envia uma proposta para carga disponivel."""
    proposal = create_proposal(db, user, load_id, data)
    return _query_proposal(db, proposal.id)


def list_my_sent_proposals(
    db: Session,
    user: User,
    status_filter: str | None = None,
) -> list[LoadProposal]:
    """Lista propostas enviadas pela empresa autenticada."""
    company = _get_company_for_user(db, user)
    query = (
        db.query(LoadProposal)
        .options(*_proposal_options())
        .filter(LoadProposal.company_id == company.id)
    )
    if status_filter:
        query = query.filter(LoadProposal.status == status_filter)
    return query.order_by(LoadProposal.created_at.desc()).all()


def list_my_received_proposals(
    db: Session,
    user: User,
    status_filter: str | None = None,
) -> list[LoadProposal]:
    """Lista propostas recebidas nas cargas do cliente autenticado."""
    client = _get_client_for_user(db, user)
    query = (
        db.query(LoadProposal)
        .options(*_proposal_options())
        .join(Load, Load.id == LoadProposal.load_id)
        .filter(Load.client_id == client.id)
    )
    if status_filter:
        query = query.filter(LoadProposal.status == status_filter)
    return query.order_by(LoadProposal.created_at.desc()).all()


def get_proposal_detail(db: Session, user: User, proposal_id: int) -> LoadProposal:
    """Detalhe de uma proposta para empresa, cliente, motorista ou admin."""
    proposal = _query_proposal(db, proposal_id)
    if not _user_can_access_proposal(db, user, proposal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    return proposal


def accept_proposal_by_id(db: Session, user: User, proposal_id: int) -> LoadProposal:
    """Cliente aceita proposta pelo id da proposta."""
    proposal = _query_proposal(db, proposal_id)
    if proposal.load_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proposta sem carga")
    accept_proposal(db, user, proposal.load_id, proposal_id)
    return _query_proposal(db, proposal_id)


def reject_proposal_by_id(db: Session, user: User, proposal_id: int) -> LoadProposal:
    """Cliente recusa proposta pelo id da proposta."""
    proposal = _query_proposal(db, proposal_id)
    if proposal.load_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proposta sem carga")
    reject_proposal(db, user, proposal.load_id, proposal_id)
    return _query_proposal(db, proposal_id)
