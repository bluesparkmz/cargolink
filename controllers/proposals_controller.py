"""
Controller de propostas: envio, listagens, detalhe e decisão do cliente.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants import (
    LOAD_STATUS_ACCEPTED,
    LOAD_STATUS_AVAILABLE,
    NEGOTIATION_STATUS_ACCEPTED,
    NEGOTIATION_STATUS_PENDING,
    NEGOTIATION_STATUS_REJECTED,
    NEGOTIATION_STATUS_REPLACED,
    PROPOSAL_OPEN_STATUSES,
    PROPOSAL_STATUS_ACCEPTED,
    PROPOSAL_STATUS_NEGOTIATING,
    PROPOSAL_STATUS_REJECTED,
)
from controllers.notifications_controller import create_notification, emit_notification
from controllers.realtime_events import emit_to_rooms
from controllers.loads_controller import accept_proposal, create_proposal, reject_proposal
from models.models import Client, Company, Driver, Load, LoadProposal, ProposalNegotiation, Trip, User
from schemas.schemas import LoadProposalCreateRequest, ProposalNegotiationCreateRequest


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


def _standing_amount(proposal: LoadProposal) -> Decimal:
    """Valor em vigor na mesa: ultima contraproposta pendente ou proposta inicial."""
    latest_pending = _latest_pending_negotiation(proposal)
    if latest_pending is not None:
        return latest_pending.amount
    if proposal.proposed_value is not None:
        return proposal.proposed_value
    return Decimal("0")


def _validate_counter_offer_amount(
    proposal: LoadProposal,
    user_side: str,
    amount: Decimal,
) -> None:
    """
    Regras de negociacao:
    - Cliente so pode baixar o valor em vigor.
    - Empresa so pode subir em relacao a oferta do cliente, sem passar a proposta inicial.
    """
    standing = _standing_amount(proposal)

    if user_side == "cliente":
        if standing <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao ha valor em vigor para contrapropor.",
            )
        if amount >= standing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"O cliente so pode sugerir um valor inferior ao actual "
                    f"({standing:.2f} MT)."
                ),
            )
        return

    latest_pending = _latest_pending_negotiation(proposal)
    if latest_pending is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A empresa so responde a uma contraproposta do cliente.",
        )

    client_offer = latest_pending.amount
    empresa_ceiling = proposal.proposed_value or standing
    if amount <= client_offer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A empresa deve sugerir um valor superior a {client_offer:.2f} MT "
                f"(oferta do cliente)."
            ),
        )
    if amount > empresa_ceiling:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A empresa nao pode ultrapassar a proposta inicial ({empresa_ceiling:.2f} MT)."
            ),
        )


def _ensure_open_for_negotiation(proposal: LoadProposal) -> None:
    if proposal.status in (PROPOSAL_STATUS_ACCEPTED, PROPOSAL_STATUS_REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposta ja foi encerrada",
        )


def _ensure_load_allows_negotiation(proposal: LoadProposal) -> None:
    if proposal.load is not None and not proposal.load.negotiable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta carga nao aceita negociacao",
        )


def _reject_pending_negotiations(proposal: LoadProposal) -> None:
    for negotiation in proposal.negotiations:
        if negotiation.status == NEGOTIATION_STATUS_PENDING:
            negotiation.status = NEGOTIATION_STATUS_REJECTED


def _proposal_user_ids(db: Session, proposal: LoadProposal) -> set[int]:
    user_ids: set[int] = set()
    load = proposal.load or db.query(Load).filter(Load.id == proposal.load_id).first()
    if load:
        client = db.query(Client).filter(Client.id == load.client_id).first()
        if client:
            user_ids.add(client.user_id)
    if proposal.company_id:
        company = db.query(Company).filter(Company.id == proposal.company_id).first()
        if company:
            user_ids.add(company.user_id)
    if proposal.driver_id:
        driver = db.query(Driver).filter(Driver.id == proposal.driver_id).first()
        if driver:
            user_ids.add(driver.user_id)
    return user_ids


def _proposal_acceptance_user_ids(db: Session, proposal: LoadProposal) -> set[int]:
    # Cliente + empresa. Motorista só participa após trip.assigned.
    user_ids: set[int] = set()
    load = proposal.load or db.query(Load).filter(Load.id == proposal.load_id).first()
    if load:
        client = db.query(Client).filter(Client.id == load.client_id).first()
        if client:
            user_ids.add(client.user_id)
    if proposal.company_id:
        company = db.query(Company).filter(Company.id == proposal.company_id).first()
        if company:
            user_ids.add(company.user_id)
    return user_ids


def _proposal_acceptance_rooms(proposal: LoadProposal) -> set[str]:
    rooms = {f"load:{proposal.load_id}", f"proposal:{proposal.id}"}
    if proposal.company_id:
        rooms.add(f"company:{proposal.company_id}")
    return rooms


def _proposal_rooms(proposal: LoadProposal) -> set[str]:
    rooms = {f"load:{proposal.load_id}", f"proposal:{proposal.id}"}
    if proposal.company_id:
        rooms.add(f"company:{proposal.company_id}")
    if proposal.driver_id:
        rooms.add(f"driver:{proposal.driver_id}")
    return rooms


def _close_proposal_as_accepted(db: Session, proposal: LoadProposal) -> None:
    """Fecha proposta como aceite e cria viagem sem depender do papel do utilizador."""
    load = proposal.load or db.query(Load).filter(Load.id == proposal.load_id).first()
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga nao encontrada")
    if load.status != LOAD_STATUS_AVAILABLE:
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
    _reject_pending_negotiations(proposal)
    other_proposals = (
        db.query(LoadProposal)
        .filter(
            LoadProposal.load_id == proposal.load_id,
            LoadProposal.id != proposal.id,
            LoadProposal.status.in_(PROPOSAL_OPEN_STATUSES),
        )
        .all()
    )
    for other in other_proposals:
        other.status = PROPOSAL_STATUS_REJECTED

    load.status = LOAD_STATUS_ACCEPTED
    db.add(
        Trip(
            load_id=proposal.load_id,
            company_id=proposal.company_id,
            driver_id=None,
            vehicle_id=None,
        )
    )


def _close_proposal_as_rejected(proposal: LoadProposal) -> None:
    """Fecha proposta como recusada sem depender do papel do utilizador."""
    proposal.status = PROPOSAL_STATUS_REJECTED
    _reject_pending_negotiations(proposal)


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
    _ensure_load_allows_negotiation(proposal)
    _validate_counter_offer_amount(proposal, user_side, Decimal(str(data.amount)))

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
    target_user_ids = _proposal_user_ids(db, proposal) - {user.id}
    notifications = [
        create_notification(
            db,
            user_id=user_id,
            title="Nova contraproposta",
            body="Recebeu uma nova contraproposta.",
            notification_type="negotiation.created",
            payload={"proposal_id": proposal.id, "load_id": proposal.load_id},
        )
        for user_id in target_user_ids
    ]
    db.commit()
    db.refresh(negotiation)
    for notification in notifications:
        db.refresh(notification)
        emit_notification(notification)
    emit_to_rooms(
        _proposal_rooms(proposal),
        {
            "type": "negotiation.created",
            "proposal_id": proposal.id,
            "negotiation_id": negotiation.id,
            "load_id": proposal.load_id,
            "sender_id": user.id,
            "status": proposal.status,
        },
    )

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
    trip = db.query(Trip).filter(Trip.load_id == proposal.load_id).first()
    notifications = [
        create_notification(
            db,
            user_id=user_id,
            title="Contraproposta aceite",
            body="A contraproposta foi aceite. A empresa deve atribuir um camião para iniciar o transporte.",
            notification_type="negotiation.accepted",
            payload={
                "proposal_id": proposal.id,
                "negotiation_id": negotiation.id,
                "load_id": proposal.load_id,
                "trip_id": trip.id if trip else None,
            },
        )
        for user_id in (_proposal_acceptance_user_ids(db, proposal) - {user.id})
    ]
    db.commit()
    for notification in notifications:
        db.refresh(notification)
        emit_notification(notification)
    emit_to_rooms(
        _proposal_acceptance_rooms(proposal) | ({f"trip:{trip.id}"} if trip else set()),
        {
            "type": "negotiation.accepted",
            "proposal_id": proposal.id,
            "negotiation_id": negotiation.id,
            "load_id": proposal.load_id,
            "trip_id": trip.id if trip else None,
            "status": proposal.status,
        },
    )
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
    notifications = [
        create_notification(
            db,
            user_id=user_id,
            title="Contraproposta recusada",
            body="A contraproposta foi recusada.",
            notification_type="negotiation.rejected",
            payload={
                "proposal_id": proposal.id,
                "negotiation_id": negotiation.id,
                "load_id": proposal.load_id,
            },
        )
        for user_id in (_proposal_user_ids(db, proposal) - {user.id})
    ]
    db.commit()
    for notification in notifications:
        db.refresh(notification)
        emit_notification(notification)
    emit_to_rooms(
        _proposal_rooms(proposal),
        {
            "type": "negotiation.rejected",
            "proposal_id": proposal.id,
            "negotiation_id": negotiation.id,
            "load_id": proposal.load_id,
            "status": proposal.status,
        },
    )
    return _query_proposal(db, proposal_id)
