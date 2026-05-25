"""
Controller de propostas: envio, listagens, detalhe e decisão do cliente.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from controllers.loads_controller import accept_proposal, create_proposal, reject_proposal
from models import Client, Company, Driver, Load, LoadProposal, ProposalNegotiation, Trip, User
from schemas import LoadProposalCreateRequest, ProposalNegotiationCreateRequest

PROPOSAL_STATUS_PENDING = "pendente"
PROPOSAL_STATUS_NEGOTIATING = "em_negociacao"
PROPOSAL_STATUS_ACCEPTED = "aceite"
PROPOSAL_STATUS_REJECTED = "recusada"

NEGOTIATION_STATUS_PENDING = "pendente"
NEGOTIATION_STATUS_ACCEPTED = "aceite"
NEGOTIATION_STATUS_REJECTED = "recusada"
NEGOTIATION_STATUS_REPLACED = "substituida"


def _proposal_options():
    return (
        joinedload(LoadProposal.load),
        joinedload(LoadProposal.company),
        joinedload(LoadProposal.driver).joinedload(Driver.user),
        joinedload(LoadProposal.vehicle),
        joinedload(LoadProposal.negotiations).joinedload(ProposalNegotiation.sender),
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


def _user_side_for_proposal(db: Session, user: User, proposal: LoadProposal) -> str:
    if user.user_type == "empresa":
        company = _get_company_for_user(db, user)
        if proposal.company_id == company.id:
            return "empresa"

    if user.user_type == "cliente":
        client = _get_client_for_user(db, user)
        if proposal.load is not None and proposal.load.client_id == client.id:
            return "cliente"

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")


def _latest_pending_negotiation(
    proposal: LoadProposal,
) -> ProposalNegotiation | None:
    pending = [
        item
        for item in proposal.negotiations
        if item.status == NEGOTIATION_STATUS_PENDING
    ]
    pending.sort(key=lambda item: item.created_at, reverse=True)
    return pending[0] if pending else None


def _ensure_open_for_negotiation(proposal: LoadProposal) -> None:
    if proposal.status in (PROPOSAL_STATUS_ACCEPTED, PROPOSAL_STATUS_REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposta ja foi encerrada",
        )


def _close_proposal_as_accepted(db: Session, proposal: LoadProposal) -> None:
    """Fecha proposta como aceite e cria viagem sem depender do papel do utilizador."""
    load = proposal.load or db.query(Load).filter(Load.id == proposal.load_id).first()
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga nao encontrada")
    if load.status != "disponivel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carga ja nao esta disponivel",
        )

    existing_trip = db.query(Trip).filter(Trip.load_id == proposal.load_id).first()
    if existing_trip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta carga ja tem viagem associada",
        )

    proposal.status = PROPOSAL_STATUS_ACCEPTED
    other_proposals = (
        db.query(LoadProposal)
        .filter(
            LoadProposal.load_id == proposal.load_id,
            LoadProposal.id != proposal.id,
            LoadProposal.status.in_([PROPOSAL_STATUS_PENDING, PROPOSAL_STATUS_NEGOTIATING]),
        )
        .all()
    )
    for other in other_proposals:
        other.status = PROPOSAL_STATUS_REJECTED

    load.status = "aceite"
    db.add(
        Trip(
            load_id=proposal.load_id,
            company_id=proposal.company_id,
            driver_id=proposal.driver_id,
            vehicle_id=proposal.vehicle_id,
        )
    )


def _close_proposal_as_rejected(proposal: LoadProposal) -> None:
    """Fecha proposta como recusada sem depender do papel do utilizador."""
    proposal.status = PROPOSAL_STATUS_REJECTED
    if proposal.load is not None and not proposal.load.negotiable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta carga nao aceita negociacao",
        )


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


def list_proposal_negotiations(
    db: Session,
    user: User,
    proposal_id: int,
) -> list[ProposalNegotiation]:
    """Lista historico de negociacao de uma proposta."""
    proposal = get_proposal_detail(db, user, proposal_id)
    return sorted(proposal.negotiations, key=lambda item: item.created_at)


def create_counter_offer(
    db: Session,
    user: User,
    proposal_id: int,
    data: ProposalNegotiationCreateRequest,
) -> ProposalNegotiation:
    """Cria uma contraproposta com novo valor."""
    proposal = _query_proposal(db, proposal_id)
    user_side = _user_side_for_proposal(db, user, proposal)
    _ensure_open_for_negotiation(proposal)

    latest_pending = _latest_pending_negotiation(proposal)
    if latest_pending is None and user_side == "empresa":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aguarde resposta do cliente antes de enviar nova contraproposta",
        )
    if latest_pending is not None and latest_pending.sender_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aguarde resposta da outra parte antes de enviar nova contraproposta",
        )
    if latest_pending is not None:
        latest_pending.status = NEGOTIATION_STATUS_REPLACED

    negotiation = ProposalNegotiation(
        proposal_id=proposal.id,
        sender_id=user.id,
        amount=Decimal(str(data.amount)),
        message=data.message,
    )
    proposal.status = PROPOSAL_STATUS_NEGOTIATING
    db.add(negotiation)
    db.commit()
    db.refresh(negotiation)

    return negotiation


def accept_counter_offer(
    db: Session,
    user: User,
    proposal_id: int,
    negotiation_id: int,
) -> LoadProposal:
    """Aceita uma contraproposta e cria a viagem."""
    proposal = _query_proposal(db, proposal_id)
    _user_side_for_proposal(db, user, proposal)
    _ensure_open_for_negotiation(proposal)

    negotiation = (
        db.query(ProposalNegotiation)
        .filter(
            ProposalNegotiation.id == negotiation_id,
            ProposalNegotiation.proposal_id == proposal_id,
        )
        .first()
    )
    if negotiation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negociacao nao encontrada")
    if negotiation.status != NEGOTIATION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Negociacao ja processada")
    if negotiation.sender_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao pode aceitar a sua propria contraproposta",
        )

    negotiation.status = NEGOTIATION_STATUS_ACCEPTED
    proposal.proposed_value = negotiation.amount
    _close_proposal_as_accepted(db, proposal)
    db.commit()
    return _query_proposal(db, proposal_id)


def reject_counter_offer(
    db: Session,
    user: User,
    proposal_id: int,
    negotiation_id: int,
) -> LoadProposal:
    """Recusa uma contraproposta e encerra a proposta."""
    proposal = _query_proposal(db, proposal_id)
    _user_side_for_proposal(db, user, proposal)
    _ensure_open_for_negotiation(proposal)

    negotiation = (
        db.query(ProposalNegotiation)
        .filter(
            ProposalNegotiation.id == negotiation_id,
            ProposalNegotiation.proposal_id == proposal_id,
        )
        .first()
    )
    if negotiation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negociacao nao encontrada")
    if negotiation.status != NEGOTIATION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Negociacao ja processada")
    if negotiation.sender_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao pode recusar a sua propria contraproposta",
        )

    negotiation.status = NEGOTIATION_STATUS_REJECTED
    _close_proposal_as_rejected(proposal)
    db.commit()
    return _query_proposal(db, proposal_id)
