"""
Controller de carteira: saldo, extrato e depósitos M-Pesa.
"""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from constants import (
    PAYMENT_METHOD_MPESA,
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_PENDING,
    TRANSACTION_TYPE_DEPOSIT,
)
from models import Payment, Transaction, User, Wallet
from schemas import WalletDepositRequest


def get_or_create_wallet(db: Session, user: User) -> Wallet:
    """Garante carteira para o utilizador."""
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if wallet is None:
        wallet = Wallet(user_id=user.id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def get_wallet_balance(db: Session, user: User) -> Wallet:
    """Saldo da carteira."""
    return get_or_create_wallet(db, user)


def list_wallet_transactions(
    db: Session,
    user: User,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    """Extrato de movimentos."""
    wallet = get_or_create_wallet(db, user)
    return (
        db.query(Transaction)
        .filter(Transaction.wallet_id == wallet.id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def _complete_deposit(
    db: Session,
    wallet: Wallet,
    payment: Payment,
    transaction: Transaction,
) -> None:
    """Credita saldo após confirmação M-Pesa."""
    amount = payment.amount
    payment.status = PAYMENT_STATUS_COMPLETED
    transaction.status = TRANSACTION_STATUS_COMPLETED
    wallet.available_balance = (wallet.available_balance or Decimal(0)) + amount
    payment.gateway_response = {
        "provider": PAYMENT_METHOD_MPESA,
        "simulated": settings.AUTO_CONFIRM_MPESA_DEPOSITS,
        "status": PAYMENT_STATUS_COMPLETED,
    }
    db.commit()


def create_deposit(db: Session, user: User, data: WalletDepositRequest) -> dict:
    """
    Inicia depósito M-Pesa: regista pagamento e movimento pendente.
    Em dev (AUTO_CONFIRM_MPESA_DEPOSITS) confirma de imediato.
    """
    wallet = get_or_create_wallet(db, user)
    phone = (data.phone or user.phone).strip()
    amount = Decimal(str(data.amount))
    external_reference = f"MPESA-{uuid.uuid4().hex[:12].upper()}"

    payment = Payment(
        user_id=user.id,
        method=data.method,
        phone=phone,
        amount=amount,
        status=PAYMENT_STATUS_PENDING,
        external_reference=external_reference,
    )
    db.add(payment)
    db.flush()

    transaction = Transaction(
        wallet_id=wallet.id,
        transaction_type=TRANSACTION_TYPE_DEPOSIT,
        amount=amount,
        status=TRANSACTION_STATUS_PENDING,
        reference=external_reference,
        description=f"Depósito {data.method.upper()}",
    )
    db.add(transaction)
    db.flush()

    message = "Depósito registado. Aguarde confirmação M-Pesa no telemóvel."
    final_status = PAYMENT_STATUS_PENDING

    if settings.AUTO_CONFIRM_MPESA_DEPOSITS:
        _complete_deposit(db, wallet, payment, transaction)
        db.refresh(payment)
        db.refresh(transaction)
        db.refresh(wallet)
        message = "Depósito confirmado. Saldo atualizado."
        final_status = PAYMENT_STATUS_COMPLETED
    else:
        db.commit()
        db.refresh(payment)
        db.refresh(transaction)

    return {
        "payment_id": payment.id,
        "transaction_id": transaction.id,
        "amount": float(amount),
        "status": final_status,
        "external_reference": external_reference,
        "phone": phone,
        "message": message,
    }


def confirm_deposit(db: Session, user: User, payment_id: int) -> dict:
    """
    Confirma depósito pendente (callback M-Pesa ou teste manual).
    Só o dono do pagamento pode confirmar.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
    if payment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    if payment.method != PAYMENT_METHOD_MPESA or payment.load_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pagamento inválido para depósito na carteira",
        )
    if payment.status == PAYMENT_STATUS_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Depósito já confirmado",
        )
    if payment.status == PAYMENT_STATUS_FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Depósito falhou; inicie um novo pedido",
        )

    wallet = get_or_create_wallet(db, user)
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.wallet_id == wallet.id,
            Transaction.reference == payment.external_reference,
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimento da carteira não encontrado",
        )

    _complete_deposit(db, wallet, payment, transaction)
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "transaction_id": transaction.id,
        "amount": float(payment.amount),
        "status": payment.status,
        "external_reference": payment.external_reference or "",
        "phone": payment.phone or user.phone,
        "message": "Depósito confirmado. Saldo atualizado.",
    }
