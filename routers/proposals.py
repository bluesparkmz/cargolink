"""
Rotas de propostas: minhas propostas, recebidas e decisoes do cliente.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.proposals_controller import (
    accept_proposal_by_id,
    get_proposal_detail,
    list_my_received_proposals,
    list_my_sent_proposals,
    reject_proposal_by_id,
    send_proposal,
)
from database import get_db
from deps import get_current_user
from models import LoadProposal, User
from schemas import (
    LoadProposalCreateRequest,
    LoadProposalDetailResponse,
    ProposalCompanySummary,
    ProposalDriverSummary,
    ProposalLoadSummary,
    ProposalVehicleSummary,
)

router = APIRouter()


def _proposal_to_detail(proposal: LoadProposal) -> LoadProposalDetailResponse:
    load = proposal.load
    company = proposal.company
    driver = proposal.driver
    vehicle = proposal.vehicle

    return LoadProposalDetailResponse(
        id=proposal.id,
        load_id=proposal.load_id,
        company_id=proposal.company_id,
        driver_id=proposal.driver_id,
        vehicle_id=proposal.vehicle_id,
        proposed_value=float(proposal.proposed_value) if proposal.proposed_value else None,
        message=proposal.message,
        status=proposal.status,
        created_at=proposal.created_at,
        load=ProposalLoadSummary(
            id=load.id,
            code=load.code,
            load_type=load.load_type,
            load_name=load.load_name,
            origin=load.origin,
            destination=load.destination,
            value=float(load.value) if load.value is not None else None,
            negotiable=load.negotiable,
            status=load.status,
            departure_date=load.departure_date,
        ),
        company=ProposalCompanySummary(
            id=company.id,
            company_name=company.company_name,
            average_rating=float(company.average_rating),
            total_trips=company.total_trips,
            verified=company.verified,
        )
        if company
        else None,
        driver=ProposalDriverSummary(
            id=driver.id,
            name=driver.user.name,
            average_rating=float(driver.average_rating),
            total_trips=driver.total_trips,
            available=driver.available,
        )
        if driver and driver.user
        else None,
        vehicle=ProposalVehicleSummary(
            id=vehicle.id,
            plate=vehicle.plate,
            brand=vehicle.brand,
            model_name=vehicle.model_name,
            vehicle_type=vehicle.vehicle_type,
            tonnage_capacity=float(vehicle.tonnage_capacity)
            if vehicle.tonnage_capacity is not None
            else None,
            status=vehicle.status,
        )
        if vehicle
        else None,
    )


@router.post("/loads/{load_id}", response_model=LoadProposalDetailResponse, status_code=201)
def create_for_load(
    load_id: int,
    data: LoadProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Empresa envia proposta para uma carga."""
    return _proposal_to_detail(send_proposal(db, current_user, load_id, data))


@router.get("/me", response_model=list[LoadProposalDetailResponse])
def get_my_sent(
    status: str | None = Query(None, description="Filtrar por pendente, aceite ou recusada"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Minhas propostas enviadas pela empresa autenticada."""
    proposals = list_my_sent_proposals(db, current_user, status)
    return [_proposal_to_detail(proposal) for proposal in proposals]


@router.get("/received", response_model=list[LoadProposalDetailResponse])
def get_my_received(
    status: str | None = Query(None, description="Filtrar por pendente, aceite ou recusada"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Propostas recebidas nas cargas do cliente autenticado."""
    proposals = list_my_received_proposals(db, current_user, status)
    return [_proposal_to_detail(proposal) for proposal in proposals]


@router.get("/{proposal_id}", response_model=LoadProposalDetailResponse)
def get_by_id(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalhe de uma proposta."""
    return _proposal_to_detail(get_proposal_detail(db, current_user, proposal_id))


@router.post("/{proposal_id}/accept", response_model=LoadProposalDetailResponse)
def accept_by_id(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cliente aceita proposta e cria a viagem."""
    return _proposal_to_detail(accept_proposal_by_id(db, current_user, proposal_id))


@router.post("/{proposal_id}/reject", response_model=LoadProposalDetailResponse)
def reject_by_id(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cliente recusa proposta."""
    return _proposal_to_detail(reject_proposal_by_id(db, current_user, proposal_id))
