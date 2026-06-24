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
    try:
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
        logger.info(f"Deposit completed: payment_id={payment.id}, amount={amount}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing deposit: {str(e)}", exc_info=True)
        raise


async def create_deposit(db: Session, user: User, data: WalletDepositRequest) -> dict:
    """
    Inicia depósito M-Pesa sem polling bloqueante.
    
    Fluxo:
    1. Cria registros de pagamento e transação como PENDING
    2. Envia requisição ao M-Pesa (assincronamente)
    3. Se aceito (INS-0), retorna imediatamente com status PENDING
    4. Callback do M-Pesa confirma o depósito automaticamente
    """
    wallet = get_or_create_wallet(db, user)
    phone = (data.phone or user.phone).strip()
    amount = Decimal(str(data.amount))
    
    # Gera referências únicas
    transaction_ref = f"T{uuid.uuid4().hex[:12].upper()}"
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

    # Em desenvolvimento, simula confirmação automática
    if settings.AUTO_CONFIRM_MPESA_DEPOSITS:
        logger.info(f"Auto-confirming M-Pesa deposit for {user.id} (dev mode)")
        _complete_deposit(db, wallet, payment, transaction)
        return {
            "payment_id": payment.id,
            "transaction_id": transaction.id,
            "amount": float(amount),
            "status": "completed",  # Frontend espera inglês
            "external_reference": external_reference,
            "phone": phone,
            "message": "Depósito confirmado (modo desenvolvimento). Saldo atualizado.",
        }

    # ========== PRODUÇÃO: Requisição ao M-Pesa (ASSÍNCRONA) ==========
    try:
        logger.info(f"M-Pesa C2B request: phone={phone}, amount={amount}, ref={transaction_ref}")
        
        mpesa_response = await mpesa_client.initiate_payment_async(
            transaction_reference=transaction_ref,
            customer_msisdn=phone,
            amount=float(amount),
            third_party_reference=external_reference,
        )
        
        payment.gateway_response = mpesa_response
        db.commit()
        
        # Verifica resposta do M-Pesa
        response_code = mpesa_response.get("output_ResponseCode", "").upper()
        response_desc = mpesa_response.get("output_ResponseDesc", "")
        
        logger.info(f"M-Pesa C2B response: code={response_code}, desc={response_desc}")
        
        # Se não foi aceito, marca como falha
        if response_code not in ("INS0", "INS-0"):
            payment.status = PAYMENT_STATUS_FAILED
            transaction.status = "failed"
            db.commit()
            logger.warning(f"M-Pesa rejected payment {payment.id}: {response_desc}")
            return {
                "payment_id": payment.id,
                "transaction_id": transaction.id,
                "amount": float(amount),
                "status": "failed",  # Frontend espera inglês
                "external_reference": external_reference,
                "phone": phone,
                "message": f"M-Pesa rejeitou: {response_desc}",
            }
        
        # ========== INS-0 ACEITO: Retorna PENDING (callback virá depois) ==========
        logger.info(f"M-Pesa accepted (INS-0). Waiting for callback: payment_id={payment.id}")
        
        return {
            "payment_id": payment.id,
            "transaction_id": transaction.id,
            "amount": float(amount),
            "status": "pending",  # Frontend espera inglês
            "external_reference": external_reference,
            "phone": phone,
            "message": (
                "Depósito iniciado. Confirme no seu telemóvel para completar. "
                "Receberá SMS com código de confirmação."
            ),
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in create_deposit: {str(e)}", exc_info=True)
        payment.status = PAYMENT_STATUS_FAILED
        transaction.status = "failed"
        payment.gateway_response = {"error": str(e)}
        db.commit()
        
        # Mensagem mais clara sobre o erro
        error_msg = str(e)
        if "403" in error_msg:
            user_msg = "Erro na configuração de autenticação com M-Pesa. Contacte suporte."
        elif "Connection" in error_msg or "timeout" in error_msg.lower():
            user_msg = "Erro de conexão com M-Pesa. Tente novamente."
        else:
            user_msg = f"Erro ao processar depósito: {error_msg[:100]}"
        
        return {
            "payment_id": payment.id,
            "transaction_id": transaction.id,
            "amount": float(amount),
            "status": "failed",  # Frontend espera inglês
            "external_reference": external_reference,
            "phone": phone,
            "message": user_msg,
        }


def confirm_deposit(db: Session, user: User, payment_id: int) -> dict:
    """
    Confirma depósito pendente manualmente (para testes ou confirmação manual).
    Em produção, o callback do M-Pesa fará isso automaticamente.
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
    
    Este é o ponto onde M-Pesa notifica que o utilizador confirmou o pagamento.
    
    Esperado no payload:
    - output_ConversationID: ID da conversa
    - output_ResponseCode: Código de resposta (INS0 = sucesso)
    - output_ResponseDesc: Descrição da resposta
    - input_ThirdPartyReference: Nossa referência externa (external_reference)
    
    Fluxo:
    1. Localiza o pagamento pela external_reference
    2. Se sucesso (INS0), credita o saldo
    3. Se falha, marca como failed
    """
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        # Extrai info do callback
        conversation_id = payload.get("output_ConversationID", "")
        response_code = payload.get("output_ResponseCode", "").upper()
        response_desc = payload.get("output_ResponseDesc", "")
        third_party_ref = payload.get("input_ThirdPartyReference", "")
        
        logger.info(
            f"M-Pesa callback: conversation={conversation_id}, "
            f"code={response_code}, ref={third_party_ref}"
        )
        
        if not third_party_ref:
            logger.error("M-Pesa callback missing input_ThirdPartyReference")
            return {
                "status": "error",
                "message": "Referência do M-Pesa ausente no callback",
            }
        
        # Localiza o pagamento pela nossa external_reference
        payment = (
            db.query(Payment)
            .filter(Payment.external_reference == third_party_ref)
            .first()
        )
        
        if payment is None:
            logger.warning(f"Payment not found for reference: {third_party_ref}")
            return {
                "status": "error",
                "message": "Pagamento não encontrado com referência fornecida",
            }
        
        # Se pagamento já foi processado, ignora callback duplicado
        if payment.status in (PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_FAILED):
            logger.info(
                f"Payment {payment.id} already processed (status: {payment.status}). "
                "Ignoring duplicate callback."
            )
            return {
                "status": "ignored",
                "message": f"Pagamento já foi processado com status: {payment.status}",
            }
        
        # ========== Sucesso: INS0 ==========
        if response_code == "INS0":
            user_id = payment.user_id
            wallet = get_or_create_wallet(db, user_id)
            
            # Localiza a transação pendente
            transaction = (
                db.query(Transaction)
                .filter(
                    Transaction.wallet_id == wallet.id,
                    Transaction.reference == payment.external_reference,
                )
                .first()
            )
            
            if not transaction:
                logger.error(f"Transaction not found for payment {payment.id}")
                payment.status = PAYMENT_STATUS_FAILED
                payment.gateway_response = payload
                db.commit()
                return {
                    "status": "error",
                    "message": "Movimento não encontrado",
                }
            
            # Credita o saldo
            _complete_deposit(db, wallet, payment, transaction)
            payment_id_val = payment.id
            
            logger.info(f"✅ Deposit confirmed via M-Pesa callback: payment_id={payment_id_val}, amount={payment.amount}")
            return {
                "status": "success",
                "message": "Depósito confirmado",
                "payment_id": payment_id_val,
            }
        
        # ========== Falha: Código diferente de INS0 ==========
        else:
            payment.status = PAYMENT_STATUS_FAILED
            payment.gateway_response = payload
            
            # Marca a transação como falha também
            transaction = (
                db.query(Transaction)
                .filter(Transaction.reference == payment.external_reference)
                .first()
            )
            if transaction:
                transaction.status = "failed"
            
            db.commit()
            logger.warning(
                f"❌ M-Pesa payment rejected: payment_id={payment.id}, "
                f"code={response_code}, desc={response_desc}"
            )
            return {
                "status": "failed",
                "message": f"Pagamento rejeitado: {response_desc}",
                "payment_id": payment.id,
            }
            
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Erro ao processar callback: {str(e)}",
        }
    finally:
        db.close()
