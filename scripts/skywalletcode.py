import logging
import os
import re
import time
import json
import base64
from decimal import Decimal
from typing import Any, Dict, Optional

import requests
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_der_public_key

from core import WalletService

logger = logging.getLogger(__name__)

MPESA_C2B_URL = os.getenv("MPESA_C2B_URL", "https://api.vm.co.mz:18352/ipg/v1x/c2bPayment/singleStage/")
MPESA_B2C_URL = os.getenv("MPESA_B2C_URL", "https://api.vm.co.mz:18345/ipg/v1x/b2cPayment/")
MPESA_QUERY_URL = os.getenv("MPESA_QUERY_URL", "https://api.vm.co.mz:18353/ipg/v1x/queryTransactionStatus/")
MPESA_TOKEN = os.getenv("MPESA_TOKEN", "").strip()
MPESA_API_KEY = os.getenv("MPESA_API_KEY", "").strip()
MPESA_PUBLIC_KEY = os.getenv("MPESA_PUBLIC_KEY", "").strip()
MPESA_SERVICE_PROVIDER_CODE = os.getenv("MPESA_SERVICE_PROVIDER_CODE", "171717")
MPESA_THIRD_PARTY_REFERENCE = os.getenv("MPESA_THIRD_PARTY_REFERENCE", "11114")
MPESA_AUTO_CREDIT_ON_ACCEPT = os.getenv("MPESA_AUTO_CREDIT_ON_ACCEPT", "false").strip().lower() in {"1", "true", "yes"}
MPESA_B2C_VERIFY_STATUS = os.getenv("MPESA_B2C_VERIFY_STATUS", "false").strip().lower() in {"1", "true", "yes"}

MPESA_SUCCESS_CODE = "INS-0"
MPESA_PENDING_CODES = {"INS-9", "INS-16"}
MPESA_FAILED_CODES = {
    "INS-1",
    "INS-2",
    "INS-4",
    "INS-5",
    "INS-6",
    "INS-10",
    "INS-13",
    "INS-14",
    "INS-15",
    "INS-17",
    "INS-18",
    "INS-19",
    "INS-20",
    "INS-21",
    "INS-22",
    "INS-23",
    "INS-24",
    "INS-25",
    "INS-26",
    "INS-993",
    "INS-994",
    "INS-995",
    "INS-996",
    "INS-997",
    "INS-998",
    "INS-2001",
    "INS-2002",
    "INS-2006",
    "INS-2051",
    "INS-2057",
}

TERMINAL_SUCCESS_STATUSES = {"completed", "success", "sucesso", "concluido", "concluida"}
TERMINAL_FAILED_STATUSES = {"cancelled", "canceled", "failed", "rejected", "expired", "error", "falha", "cancelado", "rejeitado"}


def _normalize_base64(value: str) -> str:
    return "".join((value or "").split())


def _encrypt_api_key_with_public_key(api_key: str, public_key_b64: str) -> str:
    der_bytes = base64.b64decode(_normalize_base64(public_key_b64))
    public_key = load_der_public_key(der_bytes)
    encrypted = public_key.encrypt(
        api_key.encode("utf-8"),
        padding.PKCS1v15(),  # compativel com o exemplo Java Cipher("RSA")
    )
    return base64.b64encode(encrypted).decode("utf-8")


def _resolve_mpesa_auth_token() -> str:
    token_from_env = MPESA_TOKEN.replace("Bearer ", "").strip() if MPESA_TOKEN else ""
    if token_from_env:
        return token_from_env

    if MPESA_API_KEY and MPESA_PUBLIC_KEY:
        try:
            token = _encrypt_api_key_with_public_key(MPESA_API_KEY, MPESA_PUBLIC_KEY)
            logger.info("M-Pesa bearer generated from MPESA_API_KEY + MPESA_PUBLIC_KEY.")
            return token
        except Exception as exc:
            logger.error("Failed to generate M-Pesa bearer from API/Public key: %s", exc, exc_info=True)
            return ""
    return ""


MPESA_AUTH_TOKEN = _resolve_mpesa_auth_token()


def _normalize_mpesa_reference(value: str, *, fallback_prefix: str) -> str:
    raw = (value or "").strip().upper()
    cleaned = re.sub(r"[^A-Z0-9]", "", raw)
    if not cleaned:
        cleaned = f"{fallback_prefix}{int(time.time())}"
    return cleaned[:20]


def _format_mpesa_amount(amount: Decimal) -> str:
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _auth_headers() -> Optional[dict[str, str]]:
    if not MPESA_AUTH_TOKEN:
        logger.error("M-Pesa auth token is not configured (set MPESA_TOKEN or MPESA_API_KEY+MPESA_PUBLIC_KEY).")
        return None
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {MPESA_AUTH_TOKEN}",
        "Origin": "developer.mpesa.vm.co.mz",
        "User-Agent": "SkyWallet/1.0",
    }


def _extract_transaction_status(api_response: dict[str, Any]) -> str:
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


def _classify_status(response_code: Optional[str], transaction_status: Optional[str], response_desc: Optional[str]) -> str:
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

    # Unknown or non-terminal status must never be treated as success.
    return "pending"


def _record_deposit_failure(
    *,
    wallet_service: WalletService,
    user_id: int,
    amount: Decimal,
    reference: str,
    msisdn: str,
    details: dict[str, Any],
) -> None:
    try:
        wallet_service.deposit_with_status(
            user_id=user_id,
            amount=amount,
            reference=reference,
            status="failed",
            details={"msisdn": msisdn, **details},
        )
    except Exception as exc:
        logger.error("Failed to persist failed deposit transaction: %s", exc, exc_info=True)


def _parse_error_payload(response: requests.Response) -> tuple[Optional[str], Optional[str], Any]:
    raw_text = (response.text or "").strip()
    payload: Any = raw_text
    response_code: Optional[str] = None
    response_desc: Optional[str] = None

    try:
        payload = response.json()
    except Exception:
        try:
            payload = json.loads(raw_text) if raw_text else raw_text
        except Exception:
            payload = raw_text

    if isinstance(payload, dict):
        response_code = payload.get("output_ResponseCode")
        response_desc = payload.get("output_ResponseDesc")
    elif isinstance(payload, str):
        match = re.search(r"(INS-\d+)", payload, flags=re.IGNORECASE)
        if match:
            response_code = match.group(1).upper()
        if payload:
            response_desc = payload[:220]

    return response_code, response_desc, payload


def _build_raw_error_hint(error_payload: Any) -> Optional[str]:
    if isinstance(error_payload, str):
        compact = " ".join(error_payload.split())
        return compact[:240] if compact else None
    if isinstance(error_payload, dict):
        for key in ("message", "error", "detail", "description"):
            value = error_payload.get(key)
            if value:
                text = " ".join(str(value).split())
                return text[:240]
    return None


def _extract_response_preview(response: requests.Response) -> str:
    raw_text = (response.text or "").strip()
    if not raw_text:
        return "<empty-response-body>"
    compact = " ".join(raw_text.split())
    return compact[:320]


def _build_mpesa_error_message(*, http_status: int, response_code: Optional[str], response_desc: Optional[str]) -> str:
    logger.error("M-Pesa API error (%s): %s - %s", http_status, response_code, response_desc)
    return "Ocorreu um erro temporário na comunicação com a operadora. Por favor, tente novamente mais tarde."


class MpesaProvider:
    @staticmethod
    def request_deposit(
        *,
        reference: str,
        msisdn: str,
        amount: Decimal,
        wallet_service: WalletService,
        user_id: int,
        third_party_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        transaction_reference = _normalize_mpesa_reference(reference, fallback_prefix="TX")
        resolved_third_party_reference = _normalize_mpesa_reference(
            third_party_reference or transaction_reference or MPESA_THIRD_PARTY_REFERENCE,
            fallback_prefix="TP",
        )
        headers = _auth_headers()
        if not headers:
            _record_deposit_failure(
                wallet_service=wallet_service,
                user_id=user_id,
                amount=amount,
                reference=transaction_reference,
                msisdn=msisdn,
                details={"mpesa_error": "token_not_configured", "third_party_reference": resolved_third_party_reference},
            )
            return {"success": False, "status": "failed", "message": "M-Pesa integration is not configured."}

        payload = {
            "input_TransactionReference": transaction_reference,
            "input_CustomerMSISDN": msisdn,
            "input_Amount": _format_mpesa_amount(amount),
            "input_ThirdPartyReference": resolved_third_party_reference,
            "input_ServiceProviderCode": MPESA_SERVICE_PROVIDER_CODE or "171717",
        }

        try:
            response = requests.post(MPESA_C2B_URL, headers=headers, json=payload, verify=True, timeout=60)
            if response.status_code not in (200, 201):
                error_code, error_desc, error_payload = _parse_error_payload(response)
                message = _build_mpesa_error_message(
                    http_status=response.status_code,
                    response_code=error_code,
                    response_desc=error_desc,
                )
                raw_hint = _build_raw_error_hint(error_payload)
                raw_preview = _extract_response_preview(response)
                if raw_hint and not error_desc and not error_code:
                    message = f"{message}. Raw response: {raw_hint}"
                elif not raw_hint and not error_desc and not error_code:
                    message = f"{message}. Raw response: {raw_preview}"
                logger.warning(
                    (
                        "M-Pesa C2B rejected request: http=%s code=%s desc=%s ref=%s third_party_ref=%s msisdn=%s "
                        "amount=%s content_type=%s raw=%s"
                    ),
                    response.status_code,
                    error_code,
                    error_desc,
                    transaction_reference,
                    resolved_third_party_reference,
                    msisdn,
                    _format_mpesa_amount(amount),
                    response.headers.get("Content-Type"),
                    raw_preview,
                )
                _record_deposit_failure(
                    wallet_service=wallet_service,
                    user_id=user_id,
                    amount=amount,
                    reference=transaction_reference,
                    msisdn=msisdn,
                    details={
                        "mpesa_error": error_payload,
                        "mpesa_error_raw_hint": raw_hint,
                        "mpesa_error_raw_preview": raw_preview,
                        "mpesa_http_status": response.status_code,
                        "mpesa_response_content_type": response.headers.get("Content-Type"),
                        "third_party_reference": resolved_third_party_reference,
                    },
                )
                return {
                    "success": False,
                    "status": "failed",
                    "message": message,
                    "response_code": error_code,
                    "response": error_payload,
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            api_response = response.json()
            response_code = api_response.get("output_ResponseCode")
            response_desc = api_response.get("output_ResponseDesc")

            if response_code != MPESA_SUCCESS_CODE:
                _record_deposit_failure(
                    wallet_service=wallet_service,
                    user_id=user_id,
                    amount=amount,
                    reference=transaction_reference,
                    msisdn=msisdn,
                    details={"mpesa_response": api_response, "third_party_reference": resolved_third_party_reference},
                )
                return {
                    "success": False,
                    "status": "failed",
                    "message": response_desc or "M-Pesa error",
                    "response_code": response_code,
                    "api_response": api_response,
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            if MPESA_AUTO_CREDIT_ON_ACCEPT:
                wallet_service.deposit_with_status(
                    user_id=user_id,
                    amount=amount,
                    reference=transaction_reference,
                    status="success",
                    details={"msisdn": msisdn, "mpesa_response": api_response},
                )
                return {
                    "success": True,
                    "status": "success",
                    "message": "Deposit confirmed.",
                    "api_response": api_response,
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            wallet_service.deposit_with_status(
                user_id=user_id,
                amount=amount,
                reference=transaction_reference,
                status="pending",
                details={
                    "msisdn": msisdn,
                    "third_party_reference": resolved_third_party_reference,
                    "mpesa_response": api_response,
                    "mpesa_query_reference": (
                        api_response.get("output_TransactionID")
                        or api_response.get("output_ConversationID")
                        or api_response.get("output_ThirdPartyReference")
                        or resolved_third_party_reference
                    ),
                },
            )

            max_retries = 10
            poll_interval_seconds = 6
            for _attempt in range(max_retries):
                time.sleep(poll_interval_seconds)
                query_ref = (
                    api_response.get("output_TransactionID")
                    or api_response.get("output_ConversationID")
                    or transaction_reference
                )
                status_result = MpesaProvider.query_status(reference=str(query_ref), third_party_ref=resolved_third_party_reference)
                if not status_result.get("success"):
                    continue

                final_state = status_result.get("status")
                if final_state == "success":
                    wallet_service.deposit_with_status(
                        user_id=user_id,
                        amount=amount,
                        reference=transaction_reference,
                        status="success",
                        details={
                            "msisdn": msisdn,
                            "third_party_reference": resolved_third_party_reference,
                            "mpesa_status": status_result,
                            "mpesa_query_reference": str(query_ref),
                        },
                    )
                    return {
                        "success": True,
                        "status": "success",
                        "message": "Payment confirmed.",
                        "api_response": status_result.get("api_response"),
                        "transaction_reference": transaction_reference,
                        "third_party_reference": resolved_third_party_reference,
                    }

                if final_state == "failed":
                    wallet_service.deposit_with_status(
                        user_id=user_id,
                        amount=amount,
                        reference=transaction_reference,
                        status="failed",
                        details={
                            "msisdn": msisdn,
                            "third_party_reference": resolved_third_party_reference,
                            "mpesa_status": status_result,
                            "mpesa_query_reference": str(query_ref),
                        },
                    )
                    return {
                        "success": False,
                        "status": "failed",
                        "message": status_result.get("response_description") or "Payment failed.",
                        "api_response": status_result.get("api_response"),
                        "transaction_reference": transaction_reference,
                        "third_party_reference": resolved_third_party_reference,
                    }

            return {
                "success": True,
                "status": "pending",
                "message": "Deposit accepted and pending confirmation.",
                "api_response": api_response,
                "transaction_reference": transaction_reference,
                "third_party_reference": resolved_third_party_reference,
            }
        except requests.exceptions.Timeout:
            _record_deposit_failure(
                wallet_service=wallet_service,
                user_id=user_id,
                amount=amount,
                reference=transaction_reference,
                msisdn=msisdn,
                details={"mpesa_error": "timeout", "third_party_reference": resolved_third_party_reference},
            )
            return {"success": False, "status": "failed", "message": "M-Pesa API timeout."}
        except requests.exceptions.RequestException as exc:
            _record_deposit_failure(
                wallet_service=wallet_service,
                user_id=user_id,
                amount=amount,
                reference=transaction_reference,
                msisdn=msisdn,
                details={"mpesa_error": f"request_exception:{exc}", "third_party_reference": resolved_third_party_reference},
            )
            return {"success": False, "status": "failed", "message": f"Failed to contact M-Pesa API: {exc}"}
        except Exception as exc:
            logger.error("Unexpected M-Pesa C2B error: %s", exc, exc_info=True)
            _record_deposit_failure(
                wallet_service=wallet_service,
                user_id=user_id,
                amount=amount,
                reference=transaction_reference,
                msisdn=msisdn,
                details={"mpesa_error": f"unexpected:{exc}", "third_party_reference": resolved_third_party_reference},
            )
            return {"success": False, "status": "failed", "message": "Unexpected error."}

    @staticmethod
    def request_withdrawal(
        *,
        reference: str,
        msisdn: str,
        gross_amount: Decimal,
        mpesa_amount: Decimal,
        wallet_service: WalletService,
        user_id: int,
        third_party_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = _auth_headers()
        if not headers:
            return {"success": False, "status": "failed", "message": "M-Pesa integration is not configured."}

        transaction_reference = _normalize_mpesa_reference(reference, fallback_prefix="WD")
        resolved_third_party_reference = _normalize_mpesa_reference(
            third_party_reference or transaction_reference or MPESA_THIRD_PARTY_REFERENCE,
            fallback_prefix="WT",
        )
        payload = {
            "input_TransactionReference": transaction_reference,
            "input_CustomerMSISDN": msisdn,
            "input_Amount": _format_mpesa_amount(mpesa_amount),
            "input_ThirdPartyReference": resolved_third_party_reference,
            "input_ServiceProviderCode": MPESA_SERVICE_PROVIDER_CODE or "171717",
        }

        try:
            response = requests.post(MPESA_B2C_URL, headers=headers, json=payload, verify=True, timeout=60)
            if response.status_code not in (200, 201):
                error_code, error_desc, error_payload = _parse_error_payload(response)
                message = _build_mpesa_error_message(
                    http_status=response.status_code,
                    response_code=error_code,
                    response_desc=error_desc,
                )
                raw_hint = _build_raw_error_hint(error_payload)
                raw_preview = _extract_response_preview(response)
                logger.error("M-Pesa B2C failure details: raw_hint=%s, raw_preview=%s", raw_hint, raw_preview)
                return {
                    "success": False,
                    "status": "failed",
                    "message": message,
                    "response_code": error_code,
                    "response": None, # Masked
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            api_response = response.json()
            response_code = api_response.get("output_ResponseCode")
            response_desc = api_response.get("output_ResponseDesc")
            if response_code != MPESA_SUCCESS_CODE:
                wallet_service.withdraw_with_status(
                    user_id=user_id,
                    amount=gross_amount,
                    reference=transaction_reference,
                    status="failed",
                    details={
                        "msisdn": msisdn,
                        "provider": "mpesa_b2c",
                        "third_party_reference": resolved_third_party_reference,
                        "mpesa_response": api_response,
                    },
                )
                return {
                    "success": False,
                    "status": "failed",
                    "message": response_desc or "M-Pesa error",
                    "response_code": response_code,
                    "api_response": api_response,
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            if not MPESA_B2C_VERIFY_STATUS:
                wallet_service.withdraw_with_status(
                    user_id=user_id,
                    amount=gross_amount,
                    reference=transaction_reference,
                    status="success",
                    details={
                        "msisdn": msisdn,
                        "provider": "mpesa_b2c",
                        "third_party_reference": resolved_third_party_reference,
                        "mpesa_response": api_response,
                        "verification_mode": "acceptance_only",
                    },
                )
                return {
                    "success": True,
                    "status": "success",
                    "message": response_desc or "Withdrawal accepted and processed.",
                    "api_response": api_response,
                    "transaction_reference": transaction_reference,
                    "third_party_reference": resolved_third_party_reference,
                }

            wallet_service.withdraw_with_status(
                user_id=user_id,
                amount=gross_amount,
                reference=transaction_reference,
                status="pending",
                details={
                    "msisdn": msisdn,
                    "provider": "mpesa_b2c",
                    "third_party_reference": resolved_third_party_reference,
                    "mpesa_response": api_response,
                    "mpesa_query_reference": (
                        api_response.get("output_TransactionID")
                        or api_response.get("output_ConversationID")
                        or api_response.get("output_ThirdPartyReference")
                        or resolved_third_party_reference
                    ),
                },
            )

            max_retries = 10
            poll_interval_seconds = 6
            for _attempt in range(max_retries):
                time.sleep(poll_interval_seconds)
                query_ref = (
                    api_response.get("output_TransactionID")
                    or api_response.get("output_ConversationID")
                    or transaction_reference
                )
                status_result = MpesaProvider.query_status(reference=str(query_ref), third_party_ref=resolved_third_party_reference)
                if not status_result.get("success"):
                    continue

                final_state = status_result.get("status")
                if final_state == "success":
                    wallet_service.withdraw_with_status(
                        user_id=user_id,
                        amount=gross_amount,
                        reference=transaction_reference,
                        status="success",
                        details={
                            "msisdn": msisdn,
                            "provider": "mpesa_b2c",
                            "third_party_reference": resolved_third_party_reference,
                            "mpesa_status": status_result,
                            "mpesa_query_reference": str(query_ref),
                        },
                    )
                    return {
                        "success": True,
                        "status": "success",
                        "message": "Withdrawal confirmed.",
                        "api_response": status_result.get("api_response"),
                        "transaction_reference": transaction_reference,
                        "third_party_reference": resolved_third_party_reference,
                    }

                if final_state == "failed":
                    wallet_service.withdraw_with_status(
                        user_id=user_id,
                        amount=gross_amount,
                        reference=transaction_reference,
                        status="failed",
                        details={
                            "msisdn": msisdn,
                            "provider": "mpesa_b2c",
                            "third_party_reference": resolved_third_party_reference,
                            "mpesa_status": status_result,
                            "mpesa_query_reference": str(query_ref),
                        },
                    )
                    return {
                        "success": False,
                        "status": "failed",
                        "message": status_result.get("response_description") or "Withdrawal failed.",
                        "api_response": status_result.get("api_response"),
                        "transaction_reference": transaction_reference,
                        "third_party_reference": resolved_third_party_reference,
                    }

            return {
                "success": True,
                "status": "pending",
                "message": "Withdrawal accepted and pending confirmation.",
                "api_response": api_response,
                "transaction_reference": transaction_reference,
                "third_party_reference": resolved_third_party_reference,
            }
        except requests.exceptions.Timeout:
            return {"success": False, "status": "failed", "message": "M-Pesa API timeout."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "status": "failed", "message": f"Failed to contact M-Pesa API: {exc}"}
        except Exception as exc:
            logger.error("Unexpected M-Pesa B2C error: %s", exc, exc_info=True)
            return {"success": False, "status": "failed", "message": "Unexpected error."}

    @staticmethod
    def query_status(
        *,
        reference: str,
        third_party_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = _auth_headers()
        if not headers:
            return {"success": False, "message": "M-Pesa integration is not configured."}

        params = {
            "input_ThirdPartyReference": third_party_ref or MPESA_THIRD_PARTY_REFERENCE or "11114",
            "input_QueryReference": reference,
            "input_ServiceProviderCode": MPESA_SERVICE_PROVIDER_CODE or "171717",
        }
        logger.info(
            "M-Pesa query_status request: query_reference=%s third_party_reference=%s service_provider_code=%s",
            params.get("input_QueryReference"),
            params.get("input_ThirdPartyReference"),
            params.get("input_ServiceProviderCode"),
        )

        try:
            response = requests.get(MPESA_QUERY_URL, headers=headers, params=params, verify=True, timeout=60)
            if response.status_code in (403, 404, 405):
                logger.warning(
                    "M-Pesa query_status GET blocked/not allowed (http=%s). Retrying with POST. query_reference=%s third_party_reference=%s",
                    response.status_code,
                    params.get("input_QueryReference"),
                    params.get("input_ThirdPartyReference"),
                )
                response = requests.post(MPESA_QUERY_URL, headers=headers, json=params, verify=True, timeout=60)

            if response.status_code not in (200, 201):
                logger.warning(
                    "M-Pesa query_status failed: http=%s query_reference=%s third_party_reference=%s raw=%s",
                    response.status_code,
                    params.get("input_QueryReference"),
                    params.get("input_ThirdPartyReference"),
                    _extract_response_preview(response),
                )
                return {
                    "success": False,
                    "status": "failed",
                    "message": "Serviço da operadora indisponível.",
                    "http_status": response.status_code,
                    "api_response": None, # Masked
                }

            api_response = response.json()
            response_code = api_response.get("output_ResponseCode")
            response_description = api_response.get("output_ResponseDesc")
            transaction_status = _extract_transaction_status(api_response)
            classification = _classify_status(response_code, transaction_status, response_description)
            logger.info(
                "M-Pesa query_status response: query_reference=%s third_party_reference=%s http=%s code=%s tx_status=%s classified=%s desc=%s",
                params.get("input_QueryReference"),
                params.get("input_ThirdPartyReference"),
                response.status_code,
                response_code,
                transaction_status,
                classification,
                response_description,
            )

            return {
                "success": True,
                "status": classification,
                "response_code": response_code,
                "response_description": response_description,
                "transaction_status": transaction_status,
                "api_response": api_response,
            }
        except Exception as exc:
            logger.error("Error querying M-Pesa status: %s", exc, exc_info=True)
            return {"success": False, "status": "failed", "message": str(exc)}