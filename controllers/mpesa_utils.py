"""Utilitários partilhados para integração M-Pesa (alinhado com Skywallet)."""

import random
import re
import string
import time
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

MPESA_SUCCESS_CODES = {"INS-0", "INS0"}


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
