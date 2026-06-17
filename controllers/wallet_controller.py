import logging
import uuid
import time
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
        # Em produção, faz requisição ao Mpesa com polling
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
            
            # Verifica se a resposta do M-Pesa foi aceita (INS0 ou INS-0)
            response_code = mpesa_response.get("output_ResponseCode", "")
            if response_code not in ("INS0", "INS-0"):
                # M-Pesa rejeitou a requisição
                error_msg = mpesa_response.get("output_ResponseDesc", "Erro desconhecido")
                logger.error(f"M-Pesa rejected payment: {error_msg}")
                payment.status = PAYMENT_STATUS_FAILED
                transaction.status = "failed"
                db.commit()
                message = f"Erro: {error_msg}"
            else:
                # M-Pesa aceitou. Agora faz polling para verificar PIN
                logger.info(
                    f"M-Pesa accepted payment (INS0). Starting polling... "
                    f"(payment_id={payment.id})"
                )
                
                # Extrai ConversationID ou TransactionID para queries
                query_ref = (
                    mpesa_response.get("output_TransactionID")
                    or mpesa_response.get("output_ConversationID")
                    or transaction_ref
                )
                
                # Polling: 10 tentativas, 6 segundos de intervalo (até 60 segundos)
                max_retries = 10
                poll_interval = 6
                failed_queries = 0
                payment_confirmed = False
                
                for attempt in range(max_retries):
                    time.sleep(poll_interval)
                    logger.debug(f"Poll attempt {attempt + 1}/{max_retries}")
                    
                    # Consulta status no M-Pesa
                    status_result = mpesa_client.query_payment_status(
                        transaction_id=query_ref,
                        third_party_reference=third_party_ref,
                    )
                    
                    if status_result["success"]:
                        status_desc = (status_result.get("transaction_status") or "").lower()
                        resp_code = status_result.get("response_code", "")
                        
                        logger.info(
                            f"Poll result: code={resp_code}, status={status_desc}"
                        )
                        
                        # Verifica se foi confirmado (procura palavras-chave)
                        if resp_code == "INS-0" and any(
                            kw in status_desc
                            for kw in ["success", "completed", "done", "pago", 
                                      "sucesso", "concluido", "concluído"]
                        ):
                            # ✅ PIN foi confirmado! Credita saldo
                            logger.info(
                                f"M-Pesa confirmed payment {payment.id}. Crediting..."
                            )
                            _complete_deposit(db, wallet, payment, transaction)
                            payment_confirmed = True
                            message = "Depósito confirmado. Saldo atualizado."
                            break
                        
                        # Verifica se foi rejeitado
                        if any(
                            kw in status_desc
                            for kw in ["fail", "cancel", "reject", "error", "expired",
                                      "falha", "cancelado", "rejeitado"]
                        ):
                            # ❌ M-Pesa rejeitou
                            logger.warning(
                                f"M-Pesa rejected payment {payment.id}: {status_desc}"
                            )
                            payment.status = PAYMENT_STATUS_FAILED
                            transaction.status = "failed"
                            payment.gateway_response = {
                                **payment.gateway_response,
                                "mpesa_status": status_result,
                            }
                            db.commit()
                            message = f"Pagamento rejeitado: {status_desc}"
                            break
                    else:
                        # Query falhou
                        failed_queries += 1
                        logger.warning(
                            f"Poll query failed ({failed_queries}/3): "
                            f"{status_result.get('message')}"
                        )
                        if failed_queries >= 3:
                            # Muitas falhas de query, sair do loop
                            logger.error("Too many failed queries, stopping polling")
                            break
                
                # Se não foi confirmado, fica como pendente
                if not payment_confirmed and payment.status == PAYMENT_STATUS_PENDING:
                    message = (
                        "Depósito aguardando confirmação. "
                        "Você receberá um SMS com um código para confirmar."
                    )
                    logger.info(
                        f"Polling completed without confirmation for payment {payment.id}. "
                        "Waiting for callback..."
                    )
                
                db.refresh(payment)
                db.refresh(transaction)
                
        except Exception as e:
            logger.error(f"M-Pesa deposit error: {str(e)}", exc_info=True)
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
    
    # Evita lazy loading - extrai valores antes de trabalhar com refresh
    payment_id_val = payment.id
    amount_val = float(payment.amount)
    status_val = payment.status
    ext_ref_val = payment.external_reference or ""
    phone_val = payment.phone or user.phone
    transaction_id_val = transaction.id

    return {
        "payment_id": payment_id_val,
        "transaction_id": transaction_id_val,
        "amount": amount_val,
        "status": status_val,
        "external_reference": ext_ref_val,
        "phone": phone_val,
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
        
        # Encontra pagamento pela referência externa (que armazenamos)
        # O callback do M-Pesa deve incluir nossa external_reference para localizar o pagamento
        if not third_party_ref:
            logger.error("M-Pesa callback missing input_ThirdPartyReference")
            return {
                "status": "error",
                "message": "Referência do M-Pesa ausente no callback",
            }
        
        # Tenta buscar por external_reference (nossa referência única armazenada)
        # Assumindo que o M-Pesa ecoa nossa external_reference no callback
        payment = (
            db.query(Payment)
            .filter(Payment.external_reference == third_party_ref)
            .first()
        )
        
        # Se não encontrar, tenta procurar por qualquer pagamento pendente recente
        # com o método M-Pesa e o telefone do callback
        if payment is None:
            logger.warning(
                f"Payment not found for reference: {third_party_ref}. "
                "Searching by phone and recent status..."
            )
            # Esta é uma fallback - idealmente o callback teria a referência correta
            return {
                "status": "error",
                "message": "Pagamento não encontrado com referência fornecida",
            }
        
        # Verifica se é sucesso
        if response_code == "INS0":
            # Validação: pagamento deve estar pendente
            if payment.status != PAYMENT_STATUS_PENDING:
                logger.warning(
                    f"Payment {payment.id} is not pending (status: {payment.status}). "
                    "Ignoring callback."
                )
                return {
                    "status": "error",
                    "message": f"Pagamento não está pendente (status: {payment.status})",
                }
            
            # Busca user_id primeiro para evitar lazy load
            user_id = payment.user_id
            wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
            if wallet is None:
                wallet = Wallet(user_id=user_id)
                db.add(wallet)
                db.flush()
            
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
                # Extrai valores antes de fechar a sessão
                payment_id_val = payment.id
                logger.info(f"Deposit confirmed for user {user_id}: {payment_id_val}")
                return {
                    "status": "success",
                    "message": "Depósito confirmado",
                    "payment_id": payment_id_val,
                }
            else:
                logger.error(f"Transaction not found for payment {payment.id}")
                return {
                    "status": "error",
                    "message": "Movimento não encontrado",
                }
        else:
            # M-Pesa rejeitou o pagamento
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
                f"M-Pesa payment rejected for payment {payment.id}: {response_desc}"
            )
            return {
                "status": "failed",
                "message": f"Pagamento rejeitado: {response_desc}",
                "payment_id": payment.id,
            }
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return {
            "status": "error",
            "message": f"Erro ao processar callback: {str(e)}",
        }
    finally:
        db.close()
