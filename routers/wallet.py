"""
Rotas de carteira: saldo, extrato e depósitos M-Pesa.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.wallet_controller import (
    confirm_deposit,
    create_deposit,
    create_deposit_with_polling,
    get_deposit_status,
    get_wallet_balance,
    list_wallet_transactions,
    process_mpesa_callback,
    sync_deposit_with_mpesa,
)
from controllers.wallet_transport_controller import get_transport_payment_status, pay_accepted_proposal_from_wallet
from database import get_db
from deps import get_current_user
from models.models import User
from schemas.schemas import (
    WalletBalanceResponse,
    WalletDepositRequest,
    WalletDepositResponse,
    WalletDepositStatusResponse,
    WalletTransactionResponse,
)

router = APIRouter()


@router.get("/transactions", response_model=list[WalletTransactionResponse])
def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extrato de movimentos da carteira."""
    rows = list_wallet_transactions(db, current_user, limit=limit, offset=offset)
    return [
        WalletTransactionResponse(
            id=row.id,
            transaction_type=row.transaction_type,
            amount=float(row.amount),
            status=row.status,
            reference=row.reference,
            description=row.description,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/deposits", response_model=WalletDepositResponse, status_code=201)
async def request_deposit(
    data: WalletDepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inicia depósito na carteira via M-Pesa (botão + no app)."""
    return await create_deposit(db, current_user, data)


@router.post("/deposits-with-polling", response_model=WalletDepositResponse, status_code=201)
async def request_deposit_with_polling(
    data: WalletDepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Inicia depósito e aguarda confirmação do usuário via polling automático (até 60s).

    Diferente de /deposits que retorna imediatamente, esta rota:
    1. Inicia o pagamento M-Pesa
    2. Aguarda automaticamente o usuário confirmar no telemóvel
    3. Credita o saldo se confirmado
    4. Retorna erro se rejeitado ou timeout

    Use esta rota para fluxo mais direto sem callbacks de webhook.
    """
    return await create_deposit_with_polling(
        db,
        current_user,
        data,
        max_wait_seconds=30,
    )



@router.post("/deposits/{payment_id}/sync", response_model=WalletDepositStatusResponse)
def sync_deposit_route(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta verificador M-Pesa e actualiza estado (polling do app)."""
    return sync_deposit_with_mpesa(db, current_user, payment_id)


@router.get("/deposits/{payment_id}/status", response_model=WalletDepositStatusResponse)
def deposit_status_route(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta estado do depósito (pending/completed/failed)."""
    return get_deposit_status(db, current_user, payment_id)


@router.post("/deposits/{payment_id}/confirm", response_model=WalletDepositResponse)
def confirm_deposit_route(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirma depósito pendente (callback M-Pesa ou ambiente sem auto-confirmação)."""
    return confirm_deposit(db, current_user, payment_id)


@router.get("/proposal-payments/{proposal_id}")
def proposal_payment_status_route(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_transport_payment_status(db, current_user, proposal_id)


@router.post("/proposal-payments/{proposal_id}")
def pay_proposal_from_wallet_route(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return pay_accepted_proposal_from_wallet(db, current_user, proposal_id)


@router.get("", response_model=WalletBalanceResponse)
def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saldo na carteira (ecrã inicial do cliente)."""
    wallet = get_wallet_balance(db, current_user)
    return WalletBalanceResponse(
        available_balance=float(wallet.available_balance),
        pending_balance=float(wallet.pending_balance),
        blocked_balance=float(wallet.blocked_balance),
    )


@router.post("/mpesa-callback")
def mpesa_callback(payload: dict):
    """
    Webhook para receber callbacks de pagamentos M-Pesa.
    Chamado pelo servidor Mpesa após confirmação/rejeição do pagamento.
    Não requer autenticação (chamado por sistema externo).
    """
    result = process_mpesa_callback(payload)
    return result
