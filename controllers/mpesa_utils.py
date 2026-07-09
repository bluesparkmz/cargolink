"""Utilitários M-Pesa — lógica alinhada com Skywallet."""

import random
import re
import string
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

MPESA_SUCCESS_CODE = "INS-0"

MPESA_PENDING_CODES = {"INS-9", "INS-16"}

MPESA_FAILED_CODES = {
    "INS-1", "INS-2", "INS-4", "INS-5", "INS-6", "INS-10", "INS-13", "INS-14",
    "INS-15", "INS-17", "INS-18", "INS-19", "INS-20", "INS-21", "INS-22",
    "INS-23", "INS-24", "INS-25", "INS-26", "INS-993", "INS-994", "INS-995",
    "INS-996", "INS-997", "INS-998", "INS-2001", "INS-2002", "INS-2006",
    "INS-2051", "INS-2057",
}

TERMINAL_SUCCESS_STATUSES = {"completed", "success", "sucesso", "concluido", "concluida"}
TERMINAL_FAILED_STATUSES = {
    "cancelled", "canceled", "failed", "rejected", "expired", "error",
    "falha", "cancelado", "rejeitado",
}


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
    """Referência alfanumérica, máximo 20 caracteres."""
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
    """Formata valor sem zeros desnecessários."""
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def is_mpesa_c2b_accepted(response_code: str | None) -> bool:
    """C2B aceite — exactamente INS-0 (Skywallet)."""
    return str(response_code or "").strip() == MPESA_SUCCESS_CODE


def extract_transaction_status(api_response: dict[str, Any] | None) -> str:
    """Extrai estado da transação dos campos M-Pesa (Skywallet)."""
    if not api_response:
        return "N/A"
    status_value = (
        api_response.get("output_ResponseTransactionStatus")
        or api_response.get("output_TransactionStatus")
        or api_response.get("output_TransactionStatusDesc")
        or api_response.get("output_TransactionStatusDescription")
        or api_response.get("status_da_transacao_resposta")
        or api_response.get("status_da_transação_resposta")
        or api_response.get("statusDaTransacaoResposta")
        or api_response.get("statusDaTransaçãoResposta")
    )
    if status_value is None:
        return "N/A"
    return str(status_value)


def classify_mpesa_status(
    response_code: str | None,
    transaction_status: str | None,
    response_desc: str | None = None,
) -> str:
    """
    Classifica estado do pagamento: success | failed | pending.
    Estado desconhecido NUNCA é tratado como sucesso (Skywallet).
    """
    _ = response_desc  # não usar ResponseDesc para classificar
    code = str(response_code or "").strip()
    status_text = str(transaction_status or "").strip().lower()
    has_terminal_success = any(word in status_text for word in TERMINAL_SUCCESS_STATUSES)
    has_terminal_failure = any(word in status_text for word in TERMINAL_FAILED_STATUSES)

    if code in MPESA_FAILED_CODES:
        return "failed"
    if code in MPESA_PENDING_CODES:
        return "pending"

    if code == MPESA_SUCCESS_CODE:
        if has_terminal_success:
            return "success"
        if has_terminal_failure:
            return "failed"
        return "pending"

    if has_terminal_success:
        return "success"
    if has_terminal_failure:
        return "failed"

    return "pending"
