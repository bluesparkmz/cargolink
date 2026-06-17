from datetime import datetime, timedelta, timezone
import logging
import os
import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from auth import get_current_user
from controllers.biometric import require_biometric_token
from controllers.connection_manager import notification_connection_manager
from core import WalletService
from database import get_db
from models import Notification, Transaction, User, PaymentMethod
from controllers.mpesa import MpesaProvider
from controllers.webhooks import handle_mpesa_webhook
from controllers.utils import (
    build_balance_response,
    build_transaction_response,
    normalize_msisdn,
    resolve_recipient,
)
from schemas import (
    DepositRequest,
    DepositResponse,
    MpesaOperationResponse,
    MpesaStatusResponse,
    PaymentMethodResponse,
    PaymentMethodUpdateRequest,
    TransferRequest,
    TransferResultResponse,
    TransactionResponse,
    WalletBalanceResponse,
    WithdrawPreviewFullResponse,
    WithdrawPreviewResponse,
    WithdrawRequest,
)
from security import RATE_LIMITS, limiter


router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = logging.getLogger(__name__)
MPESA_QUERY_MIN_INTERVAL_SECONDS = 60
MPESA_QUERY_BACKOFF_STEPS_SECONDS = [120, 300, 900, 1800]
MPESA_STATUS_QUERY_ENABLED = os.getenv("MPESA_STATUS_QUERY_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def _build_mpesa_reference(reference: Optional[str]) -> str:
    if reference:
        cleaned = "".join(ch for ch in reference if ch.isalnum()).upper()
        if cleaned:
            return cleaned[:20]
    timestamp = datetime.utcnow().strftime("%y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SW{timestamp}{suffix}"[:20]


def _extract_mpesa_query_context(tx: Transaction) -> tuple[str, Optional[str]]:
    details = tx.details if isinstance(tx.details, dict) else {}

    mpesa_response = details.get("mpesa_response") if isinstance(details.get("mpesa_response"), dict) else {}
    mpesa_status = details.get("mpesa_status") if isinstance(details.get("mpesa_status"), dict) else {}
    mpesa_callback = details.get("mpesa_callback") if isinstance(details.get("mpesa_callback"), dict) else {}
    mpesa_status_response = mpesa_status.get("api_response") if isinstance(mpesa_status.get("api_response"), dict) else {}

    third_party_ref = (
        details.get("third_party_reference")
        or mpesa_response.get("output_ThirdPartyReference")
        or mpesa_status_response.get("output_ThirdPartyReference")
        or mpesa_callback.get("output_ThirdPartyReference")
    )

    query_reference = (
        details.get("mpesa_query_reference")
        or mpesa_response.get("output_TransactionID")
        or mpesa_response.get("output_ConversationID")
        or mpesa_response.get("output_ThirdPartyReference")
        or mpesa_status_response.get("output_TransactionID")
        or mpesa_status_response.get("output_ConversationID")
        or mpesa_status_response.get("output_ThirdPartyReference")
        or mpesa_callback.get("output_TransactionID")
        or mpesa_callback.get("output_ConversationID")
        or mpesa_callback.get("output_ThirdPartyReference")
        or third_party_ref
        or tx.reference
    )

    return str(query_reference), str(third_party_ref) if third_party_ref else None


def _merge_transaction_details(tx: Transaction, extra: dict) -> dict:
    base = tx.details if isinstance(tx.details, dict) else {}
    merged = dict(base)
    merged.update(extra or {})
    return merged


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _next_backoff_seconds(failure_count: int) -> int:
    index = min(max(failure_count, 1) - 1, len(MPESA_QUERY_BACKOFF_STEPS_SECONDS) - 1)
    return MPESA_QUERY_BACKOFF_STEPS_SECONDS[index]


def _query_allowed_now(tx: Transaction) -> tuple[bool, Optional[datetime], int]:
    details = tx.details if isinstance(tx.details, dict) else {}
    next_allowed_raw = details.get("mpesa_next_query_after")
    next_allowed = _parse_iso_datetime(str(next_allowed_raw) if next_allowed_raw else None)
    failure_count = int(details.get("mpesa_query_403_count") or 0)
    if next_allowed and datetime.utcnow() < next_allowed:
        return False, next_allowed, failure_count
    return True, next_allowed, failure_count


def _record_query_failure(tx: Transaction, *, used_reference: Optional[str], result: Optional[dict]) -> None:
    details = tx.details if isinstance(tx.details, dict) else {}
    http_status = (result or {}).get("http_status")
    message = str((result or {}).get("message") or "")

    is_403 = http_status == 403 or "API error: 403" in message
    previous_403_count = int(details.get("mpesa_query_403_count") or 0)
    current_403_count = previous_403_count + 1 if is_403 else previous_403_count

    cooldown_seconds = _next_backoff_seconds(current_403_count) if is_403 else MPESA_QUERY_MIN_INTERVAL_SECONDS
    next_allowed = datetime.utcnow() + timedelta(seconds=cooldown_seconds)

    tx.details = _merge_transaction_details(
        tx,
        {
            "mpesa_last_query_reference": used_reference,
            "mpesa_last_query_error": message[:280] if message else "query_failed",
            "mpesa_last_query_http_status": http_status,
            "mpesa_last_query_at": datetime.utcnow().isoformat(),
            "mpesa_next_query_after": next_allowed.isoformat(),
            "mpesa_query_403_count": current_403_count,
            "mpesa_query_cooldown_seconds": cooldown_seconds,
        },
    )


def _record_query_success(tx: Transaction, *, used_reference: Optional[str]) -> None:
    details = tx.details if isinstance(tx.details, dict) else {}
    tx.details = _merge_transaction_details(
        tx,
        {
            "mpesa_last_query_reference": used_reference,
            "mpesa_last_query_error": None,
            "mpesa_last_query_http_status": 200,
            "mpesa_last_query_at": datetime.utcnow().isoformat(),
            "mpesa_next_query_after": (datetime.utcnow() + timedelta(seconds=MPESA_QUERY_MIN_INTERVAL_SECONDS)).isoformat(),
            "mpesa_query_403_count": int(details.get("mpesa_query_403_count") or 0),
            "mpesa_query_cooldown_seconds": MPESA_QUERY_MIN_INTERVAL_SECONDS,
        },
    )


def _build_mpesa_query_candidates(tx: Transaction, requested_reference: Optional[str] = None) -> tuple[list[str], Optional[str]]:
    details = tx.details if isinstance(tx.details, dict) else {}
    mpesa_response = details.get("mpesa_response") if isinstance(details.get("mpesa_response"), dict) else {}
    mpesa_status = details.get("mpesa_status") if isinstance(details.get("mpesa_status"), dict) else {}
    mpesa_callback = details.get("mpesa_callback") if isinstance(details.get("mpesa_callback"), dict) else {}
    mpesa_status_response = mpesa_status.get("api_response") if isinstance(mpesa_status.get("api_response"), dict) else {}

    _, third_party_ref = _extract_mpesa_query_context(tx)

    ordered_candidates = [
        details.get("mpesa_query_reference"),
        mpesa_response.get("output_TransactionID"),
        mpesa_response.get("output_ConversationID"),
        mpesa_response.get("output_ThirdPartyReference"),
        mpesa_status_response.get("output_TransactionID"),
        mpesa_status_response.get("output_ConversationID"),
        mpesa_status_response.get("output_ThirdPartyReference"),
        mpesa_callback.get("output_TransactionID"),
        mpesa_callback.get("output_ConversationID"),
        mpesa_callback.get("output_ThirdPartyReference"),
        details.get("third_party_reference"),
        third_party_ref,
        tx.reference,
        requested_reference,
    ]

    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in ordered_candidates:
        if candidate is None:
            continue
        normalized = str(candidate).strip()
        if not normalized:
            continue
        key = normalized.upper()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(normalized)

    if not candidates and requested_reference:
        candidates = [requested_reference.strip()]

    return candidates, third_party_ref


def _sync_pending_deposit_statuses_from_mpesa(
    db: Session,
    service: WalletService,
    *,
    user_id: int,
    transactions: list[Transaction],
) -> None:
    if not MPESA_STATUS_QUERY_ENABLED:
        logger.info("Wallet pending deposit sync skipped: MPESA_STATUS_QUERY_ENABLED=false")
        return

    pending_deposits = [
        tx
        for tx in transactions
        if tx.kind == "deposit" and str(tx.status or "").lower() in {"pending", "processing"}
    ][:5]

    for tx in pending_deposits:
        if not tx.reference:
            continue
        allowed, next_allowed, current_403_count = _query_allowed_now(tx)
        if not allowed:
            logger.info(
                "Wallet pending deposit sync skipped due to cooldown: tx_reference=%s next_query_after=%s consecutive_403=%s",
                tx.reference,
                next_allowed.isoformat() if next_allowed else None,
                current_403_count,
            )
            continue
        query_candidates, third_party_ref = _build_mpesa_query_candidates(tx)
        logger.info(
            "Wallet pending deposit sync: tx_reference=%s query_candidates=%s third_party_reference=%s current_status=%s",
            tx.reference,
            query_candidates,
            third_party_ref,
            tx.status,
        )
        result: Optional[dict] = None
        used_reference: Optional[str] = None
        for candidate in query_candidates:
            used_reference = candidate
            attempt = MpesaProvider.query_status(reference=candidate, third_party_ref=third_party_ref)
            if attempt.get("success"):
                result = attempt
                break
            result = attempt

        if not result or not result.get("success"):
            _record_query_failure(tx, used_reference=used_reference, result=result)
            db.commit()
            logger.warning(
                "Wallet pending deposit sync failed to query status: tx_reference=%s used_reference=%s third_party_reference=%s message=%s",
                tx.reference,
                used_reference,
                third_party_ref,
                result.get("message") if result else None,
            )
            continue

        _record_query_success(tx, used_reference=used_reference)
        db.commit()
        resolved_status = str(result.get("status") or "").lower()
        logger.info(
            "Wallet pending deposit sync result: tx_reference=%s used_reference=%s resolved_status=%s mpesa_code=%s mpesa_tx_status=%s",
            tx.reference,
            used_reference,
            resolved_status,
            result.get("response_code"),
            result.get("transaction_status"),
        )
        if resolved_status == "success":
            service.deposit_with_status(
                user_id=user_id,
                amount=tx.amount,
                reference=tx.reference,
                status="success",
                details=_merge_transaction_details(tx, {"mpesa_status": result}),
            )
        elif resolved_status == "failed":
            service.deposit_with_status(
                user_id=user_id,
                amount=tx.amount,
                reference=tx.reference,
                status="failed",
                details=_merge_transaction_details(tx, {"mpesa_status": result}),
            )


async def _create_and_send_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    data: Optional[dict] = None,
) -> None:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        data=data,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    await notification_connection_manager.send_to_user(
        user_id,
        notification_connection_manager.build_notification(
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type,
            data=notification.data,
        ),
    )


@router.get("/balance", response_model=WalletBalanceResponse)
def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    balance = service.get_balance(current_user.id)
    return build_balance_response(current_user.id, current_user.central_user_id, balance)


@router.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    transactions = service.list_transactions(current_user.id, limit=limit)
    _sync_pending_deposit_statuses_from_mpesa(
        db,
        service,
        user_id=current_user.id,
        transactions=transactions,
    )
    transactions = service.list_transactions(current_user.id, limit=limit)
    return [build_transaction_response(transaction) for transaction in transactions]


@router.post("/deposit", response_model=DepositResponse)
@limiter.limit(RATE_LIMITS["wallet_deposit"])
async def deposit(
    request: Request,
    payload: DepositRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    record = service.validate_idempotency(idempotency_key, "wallet:deposit", current_user.id)
    try:
        if not payload.msisdn:
            raise HTTPException(status_code=400, detail="MSISDN is required for M-Pesa deposits.")
        normalized_msisdn = normalize_msisdn(payload.msisdn)
        reference = _build_mpesa_reference(payload.reference)
        result = MpesaProvider.request_deposit(
            reference=reference,
            msisdn=normalized_msisdn,
            amount=payload.amount,
            wallet_service=service,
            user_id=current_user.id,
        )
        status = str(result.get("status") or "failed").lower()
        if status in {"success", "pending"}:
            service._complete_idempotency(record)
            if status == "success":
                await _create_and_send_notification(
                    db,
                    user_id=current_user.id,
                    title="Deposito confirmado",
                    message=f"Recebeste {payload.amount} MZN na tua carteira.",
                    notification_type="deposit_success",
                    data={"reference": reference, "amount": str(payload.amount)},
                )
            else:
                await _create_and_send_notification(
                    db,
                    user_id=current_user.id,
                    title="Deposito em processamento",
                    message=f"O teu deposito de {payload.amount} MZN foi aceite e aguarda confirmacao.",
                    notification_type="deposit_pending",
                    data={"reference": reference, "amount": str(payload.amount)},
                )
        else:
            service._fail_idempotency(record)
            await _create_and_send_notification(
                db,
                user_id=current_user.id,
                title="Deposito falhou",
                message="Não foi possível processar o depósito M-Pesa neste momento. Por favor tente mais tarde.",
                notification_type="deposit_failed",
                data={"reference": reference, "amount": str(payload.amount)},
            )
        transaction = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.reference == reference,
            Transaction.kind == "deposit",
        ).first()
        balance = service.get_balance(current_user.id)
        return DepositResponse(
            success=status in {"success", "pending"},
            message=result.get("message", "Deposit processed."),
            transaction_reference=reference,
            amount=payload.amount,
            current_balance=balance["main_balance"],
            status=status,
            created_at=transaction.created_at if transaction else datetime.utcnow(),
        )
    except HTTPException:
        service._fail_idempotency(record)
        raise


@router.get("/mpesa/callback")
def mpesa_callback_health():
    return {"status": "ok", "message": "Callback endpoint is reachable"}


@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    db: Session = Depends(get_db),
    x_callback_secret: Optional[str] = Header(None, alias="X-Callback-Secret"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
):
    return await handle_mpesa_webhook(request, db, x_callback_secret, x_signature)


@router.post("/withdraw/preview", response_model=WithdrawPreviewFullResponse)
def withdraw_preview(
    payload: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    preview = service.preview_withdrawal(current_user.id, payload.amount)

    # load payment methods (user-specific first, then system-wide)
    methods = (
        db.query(PaymentMethod)
        .filter((PaymentMethod.user_id == current_user.id) | (PaymentMethod.user_id == None))
        .order_by(PaymentMethod.is_system.asc(), PaymentMethod.id.asc())
        .all()
    )
    payment_methods = []
    default_contact = None
    for m in methods:
        payment_methods.append(
            {
                "id": m.id,
                "name": m.name,
                "label": m.label or m.name,
                "is_enabled": bool(m.is_enabled),
                "is_system": bool(m.is_system),
                "contact": m.contact,
            }
        )
        # pick default contact from enabled M-Pesa system method if not set
        if not default_contact and m.is_enabled and m.contact:
            default_contact = m.contact

    response = dict(preview)
    response["payment_methods"] = payment_methods
    response["default_contact"] = default_contact
    return WithdrawPreviewFullResponse(**response)


@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
def list_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    methods = (
        db.query(PaymentMethod)
        .filter((PaymentMethod.user_id == current_user.id) | (PaymentMethod.user_id == None))
        .order_by(PaymentMethod.is_system.asc(), PaymentMethod.id.asc())
        .all()
    )
    return [
        PaymentMethodResponse(
            id=m.id,
            name=m.name,
            label=m.label or m.name,
            is_enabled=bool(m.is_enabled and m.name == "M-Pesa"),
            is_system=bool(m.is_system),
            contact=m.contact,
        )
        for m in methods
    ]


@router.put("/payment-methods/{method_id}", response_model=PaymentMethodResponse)
def update_payment_method(
    method_id: int,
    payload: PaymentMethodUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    method = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.id == method_id)
        .filter((PaymentMethod.user_id == current_user.id) | (PaymentMethod.user_id == None))
        .first()
    )
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found.")
    if method.name != "M-Pesa":
        raise HTTPException(status_code=403, detail="Only M-Pesa configuration is allowed at this time.")
    if payload.is_enabled is not None:
        method.is_enabled = payload.is_enabled
    if payload.contact is not None:
        method.contact = payload.contact.strip() or None
    if payload.label is not None:
        method.label = payload.label.strip() or method.label
    method.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(method)
    return PaymentMethodResponse(
        id=method.id,
        name=method.name,
        label=method.label or method.name,
        is_enabled=bool(method.is_enabled),
        is_system=bool(method.is_system),
        contact=method.contact,
    )


@router.post("/withdraw", response_model=TransactionResponse)
@limiter.limit(RATE_LIMITS["wallet_withdraw"])
async def withdraw(
    request: Request,
    payload: WithdrawRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    biometric_token: Optional[str] = Header(None, alias="X-Biometric-Token"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    record = service.validate_idempotency(idempotency_key, "wallet:withdraw", current_user.id)
    try:
        require_biometric_token(db, current_user.id, "wallet_withdraw", biometric_token)
        fee_info = WalletService.calculate_withdrawal_fee(payload.amount)
        withdraw_details = dict(payload.metadata or {})
        withdraw_details["withdrawal_fee_rate"] = str(fee_info["fee_rate"])
        withdraw_details["withdrawal_fee_amount"] = str(fee_info["fee_amount"])
        withdraw_details["withdrawal_gross_amount"] = str(fee_info["gross_amount"])
        withdraw_details["withdrawal_net_amount"] = str(fee_info["net_amount"])
        transaction = service.withdraw(
            current_user.id,
            payload.amount,
            reference=payload.reference,
            details=withdraw_details,
        )
        service._complete_idempotency(record)
        await _create_and_send_notification(
            db,
            user_id=current_user.id,
            title="Levantamento concluido",
            message=f"Levantaste {payload.amount} MZN da tua carteira (taxa de {fee_info['fee_amount']} MZN). Recebes {fee_info['net_amount']} MZN.",
            notification_type="withdraw_success",
            data={"reference": transaction.reference, "amount": str(payload.amount), "fee": str(fee_info["fee_amount"]), "net_amount": str(fee_info["net_amount"])},
        )
        return build_transaction_response(transaction)
    except HTTPException:
        service._fail_idempotency(record)
        raise


@router.post("/withdraw/mpesa", response_model=MpesaOperationResponse)
@limiter.limit(RATE_LIMITS["wallet_withdraw"])
async def withdraw_mpesa(
    request: Request,
    payload: WithdrawRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    biometric_token: Optional[str] = Header(None, alias="X-Biometric-Token"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    record = service.validate_idempotency(idempotency_key, "wallet:withdraw:mpesa", current_user.id)
    try:
        require_biometric_token(db, current_user.id, "wallet_withdraw", biometric_token)
        if not payload.msisdn:
            raise HTTPException(status_code=400, detail="MSISDN is required for M-Pesa B2C withdrawals.")
        normalized_msisdn = normalize_msisdn(payload.msisdn)
        reference = _build_mpesa_reference(payload.reference)
        fee_info = WalletService.calculate_withdrawal_fee(payload.amount)
        result = MpesaProvider.request_withdrawal(
            reference=reference,
            msisdn=normalized_msisdn,
            gross_amount=payload.amount,
            mpesa_amount=fee_info["net_amount"],
            wallet_service=service,
            user_id=current_user.id,
        )
        status = str(result.get("status") or "failed").lower()
        if status in {"success", "pending"}:
            service._complete_idempotency(record)
        else:
            service._fail_idempotency(record)

        if status == "success":
            await _create_and_send_notification(
                db,
                user_id=current_user.id,
                title="Levantamento confirmado",
                message=f"Levantaste {payload.amount} MZN (taxa: {fee_info['fee_amount']} MZN). Recebes {fee_info['net_amount']} MZN no M-Pesa.",
                notification_type="withdraw_success",
                data={"reference": reference, "amount": str(payload.amount), "fee": str(fee_info["fee_amount"]), "net_amount": str(fee_info["net_amount"])},
            )
        elif status == "pending":
            await _create_and_send_notification(
                db,
                user_id=current_user.id,
                title="Levantamento em processamento",
                message=f"O levantamento de {payload.amount} MZN (taxa: {fee_info['fee_amount']} MZN) foi aceite. Recebes {fee_info['net_amount']} MZN.",
                notification_type="withdraw_pending",
                data={"reference": reference, "amount": str(payload.amount), "fee": str(fee_info["fee_amount"]), "net_amount": str(fee_info["net_amount"])},
            )
        else:
            await _create_and_send_notification(
                db,
                user_id=current_user.id,
                title="Levantamento falhou",
                message="Não foi possível processar o levantamento M-Pesa neste momento. Por favor tente mais tarde.",
                notification_type="withdraw_failed",
                data={"reference": reference, "amount": str(payload.amount)},
            )

        transaction = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.reference == reference,
            Transaction.kind == "withdrawal",
        ).first()
        # Store fee info in transaction details
        if transaction:
            tx_details = dict(transaction.details or {})
            tx_details["withdrawal_fee_rate"] = str(fee_info["fee_rate"])
            tx_details["withdrawal_fee_amount"] = str(fee_info["fee_amount"])
            tx_details["withdrawal_gross_amount"] = str(fee_info["gross_amount"])
            tx_details["withdrawal_net_amount"] = str(fee_info["net_amount"])
            transaction.details = tx_details
            db.commit()
        balance = service.get_balance(current_user.id)
        return MpesaOperationResponse(
            success=status in {"success", "pending"},
            message=f"Levantamento processado. Taxa: {fee_info['fee_amount']} MZN. Recebes: {fee_info['net_amount']} MZN." if status in {"success", "pending"} else "Withdrawal failed.",
            transaction_reference=reference,
            amount=payload.amount,
            current_balance=balance["main_balance"],
            status=status,
            created_at=transaction.created_at if transaction else datetime.utcnow(),
        )
    except HTTPException:
        service._fail_idempotency(record)
        raise


@router.get("/mpesa/status", response_model=MpesaStatusResponse)
def get_mpesa_status(
    reference: str = Query(..., min_length=1, max_length=40),
    third_party_reference: Optional[str] = Query(None, min_length=1, max_length=40),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WalletService(db)
    normalized_reference = _build_mpesa_reference(reference)
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.reference.in_([reference, normalized_reference]),
        )
        .first()
    )

    if not MPESA_STATUS_QUERY_ENABLED:
        logger.info(
            "Wallet mpesa/status external query disabled by config. requested_reference=%s",
            reference,
        )
        balance = service.get_balance(current_user.id)
        return MpesaStatusResponse(
            success=False,
            reference=reference.strip(),
            response_code=None,
            response_description=(
                "M-Pesa status query disabled in this environment. "
                "Enable MPESA_STATUS_QUERY_ENABLED=true after production approval."
            ),
            transaction_status=None,
            status="pending",
            current_balance=balance["main_balance"],
            updated_transaction_status=None,
        )

    resolved_third_party_ref = third_party_reference
    query_reference = reference.strip()
    query_candidates: list[str] = [query_reference]
    if transaction:
        allowed, next_allowed, current_403_count = _query_allowed_now(transaction)
        if not allowed:
            logger.info(
                "Wallet mpesa/status skipped due to cooldown: tx_reference=%s requested_reference=%s next_query_after=%s consecutive_403=%s",
                transaction.reference,
                reference,
                next_allowed.isoformat() if next_allowed else None,
                current_403_count,
            )
            balance = service.get_balance(current_user.id)
            return MpesaStatusResponse(
                success=False,
                reference=transaction.reference,
                response_code=None,
                response_description="M-Pesa status query is temporarily throttled. Waiting before next retry.",
                transaction_status=None,
                status="pending",
                current_balance=balance["main_balance"],
                updated_transaction_status=None,
            )
        tx_query_candidates, tx_third_party_ref = _build_mpesa_query_candidates(transaction, requested_reference=query_reference)
        query_candidates = tx_query_candidates or query_candidates
        query_reference = query_candidates[0]
        if not resolved_third_party_ref:
            resolved_third_party_ref = tx_third_party_ref
        logger.info(
            "Wallet mpesa/status context: tx_reference=%s requested_reference=%s query_candidates=%s third_party_reference=%s tx_status=%s",
            transaction.reference,
            reference,
            query_candidates,
            resolved_third_party_ref,
            transaction.status,
        )
    else:
        logger.info(
            "Wallet mpesa/status context without local transaction: requested_reference=%s query_candidates=%s third_party_reference=%s",
            reference,
            query_candidates,
            resolved_third_party_ref,
        )

    result: Optional[dict] = None
    used_reference: Optional[str] = None
    for candidate in query_candidates:
        used_reference = candidate
        attempt = MpesaProvider.query_status(reference=candidate, third_party_ref=resolved_third_party_ref)
        if attempt.get("success"):
            result = attempt
            break
        result = attempt

    if not result or not result.get("success"):
        if transaction:
            _record_query_failure(transaction, used_reference=used_reference, result=result)
            db.commit()
        logger.warning(
            "Wallet mpesa/status query failed: requested_reference=%s used_reference=%s third_party_reference=%s message=%s",
            reference,
            used_reference,
            resolved_third_party_ref,
            result.get("message") if result else None,
        )
        balance = service.get_balance(current_user.id)
        return MpesaStatusResponse(
            success=False,
            reference=used_reference or query_reference,
            response_code=result.get("response_code") if result else None,
            response_description=str((result or {}).get("message") or "Could not query M-Pesa status."),
            transaction_status=None,
            status="pending",
            current_balance=balance["main_balance"],
            updated_transaction_status=None,
        )

    mpesa_status = str(result.get("status") or "pending").lower()
    if transaction:
        _record_query_success(transaction, used_reference=used_reference)
        db.commit()
    logger.info(
        "Wallet mpesa/status query success: requested_reference=%s used_reference=%s third_party_reference=%s status=%s code=%s tx_status=%s",
        reference,
        used_reference,
        resolved_third_party_ref,
        mpesa_status,
        result.get("response_code"),
        result.get("transaction_status"),
    )
    updated_transaction_status: Optional[str] = None

    if transaction and transaction.kind == "deposit" and transaction.status in {"pending", "processing"}:
        if mpesa_status == "success":
            updated = service.deposit_with_status(
                user_id=current_user.id,
                amount=transaction.amount,
                reference=transaction.reference,
                status="success",
                details=_merge_transaction_details(transaction, {"mpesa_status": result}),
            )
            updated_transaction_status = updated.status
        elif mpesa_status == "failed":
            updated = service.deposit_with_status(
                user_id=current_user.id,
                amount=transaction.amount,
                reference=transaction.reference,
                status="failed",
                details=_merge_transaction_details(transaction, {"mpesa_status": result}),
            )
            updated_transaction_status = updated.status

    balance = service.get_balance(current_user.id)
    return MpesaStatusResponse(
        success=True,
        reference=used_reference or query_reference,
        response_code=result.get("response_code"),
        response_description=result.get("response_description"),
        transaction_status=result.get("transaction_status"),
        status=mpesa_status,
        current_balance=balance["main_balance"],
        updated_transaction_status=updated_transaction_status,
    )


@router.post("/transfer", response_model=TransferResultResponse)
@limiter.limit(RATE_LIMITS["wallet_transfer"])
async def transfer(
    request: Request,
    payload: TransferRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    biometric_token: Optional[str] = Header(None, alias="X-Biometric-Token"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipient = resolve_recipient(db, payload.recipient_central_user_id, payload.recipient_email)

    service = WalletService(db)
    record = service.validate_idempotency(idempotency_key, "wallet:transfer", current_user.id)
    try:
        require_biometric_token(db, current_user.id, "wallet_transfer", biometric_token)
        outgoing, incoming = service.transfer(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            amount=payload.amount,
            reference=payload.reference,
            details=payload.metadata,
        )
        service._complete_idempotency(record)
        await _create_and_send_notification(
            db,
            user_id=current_user.id,
            title="Transferencia enviada",
            message=f"Enviaste {payload.amount} MZN para {recipient.full_name or recipient.email or recipient.username or 'utilizador'}.",
            notification_type="transfer_out",
            data={"reference": outgoing.reference, "amount": str(payload.amount), "recipient_user_id": recipient.id},
        )
        await _create_and_send_notification(
            db,
            user_id=recipient.id,
            title="Transferencia recebida",
            message=f"Recebeste {payload.amount} MZN de {current_user.full_name or current_user.email or current_user.username or 'utilizador'}.",
            notification_type="transfer_in",
            data={"reference": incoming.reference, "amount": str(payload.amount), "sender_user_id": current_user.id},
        )
        balance = service.get_balance(current_user.id)
        return TransferResultResponse(
            outgoing=build_transaction_response(outgoing),
            incoming=build_transaction_response(incoming),
            sender_balance=build_balance_response(current_user.id, current_user.central_user_id, balance),
        )
    except HTTPException:
        service._fail_idempotency(record)
        raise