"""Utilitários partilhados para integração M-Pesa (alinhado com Skywallet)."""

import random
import re
import string
import time
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

MPESA_SUCCESS_CODES = {"INS-0", "INS0"}

# Códigos M-Pesa que indicam pagamento falhado/cancelado (não confundir com INS-0 do pedido C2B)
MPESA_FAILED_CODES = {
    "INS-1", "INS-2", "INS-4", "INS-5", "INS-6", "INS-10", "INS-13", "INS-14",
    "INS-15", "INS-17", "INS-18", "INS-19", "INS-20", "INS-21", "INS-22",
    "INS-23", "INS-24", "INS-25", "INS-26", "INS-993", "INS-994", "INS-995",
    "INS-996", "INS-997", "INS-998", "INS-2001", "INS-2002", "INS-2006",
    "INS-2051", "INS-2057",
}

PAYMENT_SUCCESS_KEYWORDS = (
    "success", "sucesso", "completed", "concluido", "concluída", "concluido",
    "approved", "aprovado", "done", "pago",
)
PAYMENT_FAILED_KEYWORDS = (
    "failed", "falhou", "falha", "rejected", "rejeitado", "cancelled", "canceled",
    "cancelado", "declined", "error", "expired", "timeout", "denied", "negado",
)

# Campos que descrevem o estado do pagamento (não a resposta HTTP da query)
PAYMENT_STATUS_FIELDS = (
    "status_da_transacao_resposta",
    "status_da_transação_resposta",
    "output_TransactionStatus",
    "output_TransactionStatusDesc",
    "output_TransactionStatusDescription",
)


def normalize_msisdn(msisdn: str) -> str:
    """Normaliza número moçambicano para formato 258XXXXXXXXX."""
    digits = "".join(ch for ch in (msisdn or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if digits.startswith("258"):
        digits = digits[3:]
    if len(digits) != 9:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Número inválido: use 84xxxxxxx, 085xxxxxxx ou 25884xxxxxxx "
                f"(recebido {len(digits)} dígitos)."
            ),
        )
    if digits[:2] not in {"84", "85"}:
        raise HTTPException(
            status_code=400,
            detail=f"Número inválido: deve começar por 84 ou 85. Recebido: {digits[:2]}",
        )
    return f"258{digits}"


def normalize_mpesa_reference(value: str, *, fallback_prefix: str = "CL") -> str:
    """Referência alfanumérica, máximo 20 caracteres (exigência M-Pesa)."""
    raw = (value or "").strip().upper()
    cleaned = re.sub(r"[^A-Z0-9]", "", raw)
    if not cleaned:
        cleaned = f"{fallback_prefix}{int(time.time())}"
    return cleaned[:20]


def build_mpesa_reference(prefix: str = "CL") -> str:
    """Gera referência única curta para transação M-Pesa."""
    timestamp = datetime.utcnow().strftime("%y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{timestamp}{suffix}"[:20]


def format_mpesa_amount(amount: Decimal | float) -> str:
    """Formata valor sem zeros desnecessários (ex: 10 em vez de 10.0)."""
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def is_mpesa_accepted(response_code: str | None) -> bool:
    """Verifica se M-Pesa aceitou o pedido C2B (INS-0)."""
    if not response_code:
        return False
    return response_code.strip().upper().replace("-", "") == "INS0"


def is_mpesa_success(response_code: str | None) -> bool:
    """Verifica código de sucesso (callback ou query)."""
    if not response_code:
        return False
    normalized = response_code.strip().upper()
    return normalized in MPESA_SUCCESS_CODES or normalized.replace("-", "") == "INS0"


def is_mpesa_failed(response_code: str | None) -> bool:
    """Código M-Pesa que indica falha/cancelamento do pagamento."""
    if not response_code:
        return False
    return response_code.strip().upper() in MPESA_FAILED_CODES


def extract_payment_status(api_response: dict | None) -> str | None:
    """
    Extrai apenas o estado real do pagamento.
    Não usa output_ResponseDesc — esse campo confirma a query, não o pagamento.
    """
    if not api_response:
        return None
    for key in PAYMENT_STATUS_FIELDS:
        value = api_response.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def evaluate_payment_status(
    *,
    response_code: str | None,
    payment_status: str | None,
) -> str | None:
    """
    Avalia estado do pagamento para polling.
    Retorna: 'confirmed', 'rejected' ou None (ainda pendente).
    """
    if is_mpesa_failed(response_code):
        return "rejected"

    if not payment_status:
        return None

    status_lower = payment_status.strip().lower()

    if any(keyword in status_lower for keyword in PAYMENT_FAILED_KEYWORDS):
        return "rejected"

    if any(keyword in status_lower for keyword in PAYMENT_SUCCESS_KEYWORDS):
        return "confirmed"

    return None
