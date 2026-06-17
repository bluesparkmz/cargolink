"""
Controller de carteira: saldo, extrato e depósitos M-Pesa.
"""

import logging
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
from controllers.mpesa_client import mpesa_client
from models.models import Payment, Transaction, User, Wallet
from schemas.schemas import WalletDepositRequest

logger = logging.getLogger(__name__)


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
    Inicia depósito M-Pesa: faz requisição ao Mpesa, regista pagamento e movimento.
    Em prod, aguarda callback do Mpesa. Em dev (AUTO_CONFIRM_MPESA_DEPOSITS), 
    simula confirmação automática.
    """
    wallet = get_or_create_wallet(db, user)
    phone = (data.phone or user.phone).strip()
    amount = Decimal(str(data.amount))
    
    # Gera referências únicas para a transação
    transaction_ref = f"T{uuid.uuid4().hex[:12].upper()}"
    third_party_ref = uuid.uuid4().hex[:6].upper()
    external_reference = f"MPESA-{uuid.uuid4().hex[:12].upper()}"

    # Cria registro de pagamento (será atualizado com resposta do Mpesa)
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

    # Cria movimento da carteira (pendente até confirmação)
    transaction = Transaction(
        wallet_id=wallet.id,
        transaction_type=TRANSACTION_TYPE_DEPOSIT,
        amount=amount,
        status=TRANSACTION_STATUS_PENDING,
        reference=external_reference,
        description=f"Depósito {data.method.upper()} via {phone}",
    )
    db.add(transaction)
    db.flush()

    message = "Depósito registado. Aguarde confirmação M-Pesa no telemóvel."
    final_status = PAYMENT_STATUS_PENDING

    # Em desenvolvimento, simula confirmação automática
    if settings.AUTO_CONFIRM_MPESA_DEPOSITS:
        logger.info(f"Auto-confirming M-Pesa deposit for {user.id} (dev mode)")
        _complete_deposit(db, wallet, payment, transaction)
        db.refresh(payment)
        db.refresh(transaction)
        db.refresh(wallet)
        message = "Depósito confirmado (modo desenvolvimento). Saldo atualizado."
        final_status = PAYMENT_STATUS_COMPLETED
    else:
        # Em produção, faz requisição ao Mpesa
        try:
            logger.info(
                f"Initiating M-Pesa payment for user {user.id}: "
                f"phone={phone}, amount={amount}"
            )
            mpesa_response = mpesa_client.initiate_payment(
                transaction_reference=transaction_ref,
                customer_msisdn=phone,
                amount=float(amount),
                third_party_reference=third_party_ref,
            )
            
            # Armazena resposta do Mpesa no pagamento
            payment.gateway_response = mpesa_response
            db.commit()
            
            # Verifica se a resposta indica sucesso
            # Nota: adaptar conforme estrutura real da resposta do Mpesa
            if mpesa_response.get("output_ResponseCode") == "INS0":
                message = (
                    f"Pagamento iniciado. Confirme no seu telemóvel ({phone}). "
                    "Referência: " + mpesa_response.get("output_ConversationID", "")
                )
            else:
                error_msg = mpesa_response.get("output_ResponseDesc", "Erro desconhecido")
                logger.error(f"M-Pesa returned error: {error_msg}")
                message = f"Erro: {error_msg}"
                
            db.refresh(payment)
            db.refresh(transaction)
        except Exception as e:
            logger.error(f"M-Pesa deposit error: {str(e)}")
            # Marca como falhe caso erro na integração
            payment.status = PAYMENT_STATUS_FAILED
            transaction.status = "failed"
            payment.gateway_response = {"error": str(e)}
            db.commit()
            message = f"Erro ao processar depósito: {str(e)}"

    return {
        "payment_id": payment.id,
        "transaction_id": transaction.id,
        "amount": float(amount),
        "status": payment.status,
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


def process_mpesa_callback(payload: dict) -> dict:
    """
    Processa callback do M-Pesa após pagamento confirmado.
    
    Esperado no payload:
    - output_ConversationID: ID da conversa
    - output_ResponseCode: Código de resposta (INS0 = sucesso)
    - output_ResponseDesc: Descrição da resposta
    - input_ThirdPartyReference: Ref original que usamos para encontrar payment
    
    Returns resultado do processamento.
    """
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        # Extrai info do callback
        conversation_id = payload.get("output_ConversationID", "")
        response_code = payload.get("output_ResponseCode", "")
        response_desc = payload.get("output_ResponseDesc", "")
        third_party_ref = payload.get("input_ThirdPartyReference", "")
        
        logger.info(
            f"M-Pesa callback: conversation={conversation_id}, "
            f"code={response_code}, ref={third_party_ref}"
        )
        
        # Encontra pagamento pela referência do Mpesa
        # Nota: pode ser necessário adaptar conforme como guardamos a referência
        payment = (
            db.query(Payment)
            .filter(Payment.external_reference.like(f"MPESA%"))
            .order_by(Payment.created_at.desc())
            .first()
        )
        
        if payment is None:
            logger.warning(f"Payment not found for callback: {third_party_ref}")
            return {
                "status": "error",
                "message": "Pagamento não encontrado",
            }
        
        # Verifica se é sucesso
        if response_code == "INS0":
            wallet = get_or_create_wallet(db, payment.user)
            transaction = (
                db.query(Transaction)
                .filter(
                    Transaction.wallet_id == wallet.id,
                    Transaction.reference == payment.external_reference,
                )
                .first()
            )
            
            if transaction:
                _complete_deposit(db, wallet, payment, transaction)
                db.refresh(payment)
                logger.info(f"Deposit confirmed for user {payment.user_id}")
                return {
                    "status": "success",
                    "message": "Depósito confirmado",
                    "payment_id": payment.id,
                }
            else:
                logger.error(f"Transaction not found for payment {payment.id}")
                return {
                    "status": "error",
                    "message": "Movimento não encontrado",
                }
        else:
            # Marca como falhe
            payment.status = PAYMENT_STATUS_FAILED
            payment.gateway_response = payload
            db.commit()
            logger.warning(f"M-Pesa payment failed: {response_desc}")
            return {
                "status": "failed",
                "message": f"Pagamento falhou: {response_desc}",
            }
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return {
            "status": "error",
            "message": f"Erro ao processar callback: {str(e)}",
        }
    finally:
        db.close()
