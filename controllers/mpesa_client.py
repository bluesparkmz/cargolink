"""
Cliente M-Pesa — polling e classificação iguais ao Skywallet.
Só confirma depósito quando query_status devolve status=success.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import httpx
import requests

from config import settings
from controllers.mpesa_utils import (
    classify_mpesa_status,
    extract_transaction_status,
    format_mpesa_amount,
    is_mpesa_c2b_accepted,
    normalize_mpesa_reference,
)

logger = logging.getLogger(__name__)

MPESA_POLL_MAX_RETRIES = 10
MPESA_POLL_INTERVAL_SECONDS = 6


class MpesaClient:
    """Cliente M-Pesa sandbox (C2B + query + polling Skywallet)."""

    def __init__(self):
        self.c2b_url = settings.MPESA_C2B_URL
        self.query_url = settings.MPESA_QUERY_URL
        self.service_provider_code = settings.MPESA_SERVICE_PROVIDER_CODE
        self.default_third_party_reference = settings.MPESA_THIRD_PARTY_REFERENCE
        raw_token = settings.MPESA_BEARER_TOKEN or ""
        self.bearer_token = raw_token.replace("Bearer ", "").strip()
        logger.info("MpesaClient [sandbox] c2b=%s", self.c2b_url)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "developer.mpesa.vm.co.mz",
            "User-Agent": "CargoLink/1.0",
        }

    def _resolve_references(
        self,
        transaction_reference: str,
        third_party_reference: str | None,
    ) -> tuple[str, str]:
        tx_ref = normalize_mpesa_reference(transaction_reference, fallback_prefix="TX")
        tp_ref = normalize_mpesa_reference(
            third_party_reference or tx_ref or self.default_third_party_reference,
            fallback_prefix="TP",
        )
        return tx_ref, tp_ref

    async def initiate_payment_async(
        self,
        transaction_reference: str,
        customer_msisdn: str,
        amount: float,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """Inicia pagamento C2B."""
        if not self.bearer_token:
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": "Integração M-Pesa não configurada.",
                "http_status": 503,
            }

        tx_ref, tp_ref = self._resolve_references(transaction_reference, third_party_reference)
        payload = {
            "input_TransactionReference": tx_ref,
            "input_CustomerMSISDN": customer_msisdn,
            "input_Amount": format_mpesa_amount(Decimal(str(amount))),
            "input_ThirdPartyReference": tp_ref,
            "input_ServiceProviderCode": self.service_provider_code or "171717",
        }

        try:
            logger.info(
                "M-Pesa C2B: tx=%s tp=%s msisdn=%s amount=%s",
                tx_ref, tp_ref, customer_msisdn, payload["input_Amount"],
            )
            async with httpx.AsyncClient(timeout=60, verify=True) as client:
                response = await client.post(
                    self.c2b_url,
                    json=payload,
                    headers=self._auth_headers(),
                )

            logger.info("M-Pesa C2B HTTP %s: %s", response.status_code, response.text[:300])

            try:
                result = response.json()
            except ValueError:
                result = {
                    "output_ResponseCode": "999",
                    "output_ResponseDesc": f"HTTP {response.status_code}",
                }

            result["_transaction_reference"] = tx_ref
            result["_third_party_reference"] = tp_ref

            if response.status_code not in (200, 201):
                result["http_status"] = response.status_code
                return result

            return result

        except httpx.TimeoutException:
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": "Timeout ao contactar M-Pesa",
                "http_status": 504,
            }
        except httpx.RequestError as exc:
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": f"Erro de conexão: {str(exc)[:100]}",
                "http_status": 503,
            }

    def query_status(
        self,
        reference: str,
        third_party_ref: str | None = None,
    ) -> dict[str, Any]:
        """Consulta estado — devolve status: success | failed | pending (Skywallet)."""
        if not self.bearer_token:
            return {"success": False, "status": "failed", "message": "Token M-Pesa não configurado."}

        tp_ref = third_party_ref or self.default_third_party_reference or "11114"
        params = {
            "input_ThirdPartyReference": tp_ref,
            "input_QueryReference": reference,
            "input_ServiceProviderCode": self.service_provider_code or "171717",
        }

        logger.info(
            "M-Pesa query_status: query_ref=%s tp=%s",
            params["input_QueryReference"],
            params["input_ThirdPartyReference"],
        )

        try:
            headers = self._auth_headers()
            response = requests.get(
                self.query_url, headers=headers, params=params, verify=True, timeout=60,
            )
            if response.status_code in (403, 404, 405):
                response = requests.post(
                    self.query_url, headers=headers, json=params, verify=True, timeout=60,
                )

            if response.status_code not in (200, 201):
                logger.warning(
                    "M-Pesa query_status HTTP %s ref=%s",
                    response.status_code,
                    reference,
                )
                return {
                    "success": False,
                    "status": "failed",
                    "message": "Serviço da operadora indisponível.",
                    "http_status": response.status_code,
                }

            api_response = response.json()
            response_code = api_response.get("output_ResponseCode")
            response_description = api_response.get("output_ResponseDesc")
            transaction_status = extract_transaction_status(api_response)
            classification = classify_mpesa_status(
                response_code, transaction_status, response_description,
            )

            logger.info(
                "M-Pesa query_status: ref=%s code=%s tx_status=%s classified=%s",
                reference, response_code, transaction_status, classification,
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
            logger.error("M-Pesa query_status error: %s", exc, exc_info=True)
            return {"success": False, "status": "failed", "message": str(exc)}

    async def wait_for_payment_confirmation_async(
        self,
        c2b_response: dict[str, Any],
        transaction_reference: str,
        third_party_reference: str,
        *,
        max_retries: int = MPESA_POLL_MAX_RETRIES,
        poll_interval_seconds: int = MPESA_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """
        Polling Skywallet: 10 tentativas × 6s, sleep antes de cada query.
        Só retorna success quando query_status.classified == success.
        """
        query_ref = (
            c2b_response.get("output_TransactionID")
            or c2b_response.get("output_ConversationID")
            or transaction_reference
        )
        tp_ref = c2b_response.get("_third_party_reference") or third_party_reference

        logger.info(
            "M-Pesa polling start: query_ref=%s tp=%s retries=%s interval=%ss",
            query_ref, tp_ref, max_retries, poll_interval_seconds,
        )

        for attempt in range(1, max_retries + 1):
            await asyncio.sleep(poll_interval_seconds)

            status_result = self.query_status(
                reference=str(query_ref),
                third_party_ref=tp_ref,
            )

            if not status_result.get("success"):
                logger.debug("M-Pesa poll %s/%s: query failed", attempt, max_retries)
                continue

            final_state = status_result.get("status")
            logger.info("M-Pesa poll %s/%s: state=%s", attempt, max_retries, final_state)

            if final_state == "success":
                return {
                    "status": "success",
                    "attempts": attempt,
                    "wait_time_seconds": attempt * poll_interval_seconds,
                    "query_result": status_result,
                    "message": "Pagamento confirmado.",
                }

            if final_state == "failed":
                return {
                    "status": "failed",
                    "attempts": attempt,
                    "wait_time_seconds": attempt * poll_interval_seconds,
                    "query_result": status_result,
                    "message": status_result.get("response_description") or "Pagamento falhou ou cancelado.",
                }

        return {
            "status": "pending",
            "attempts": max_retries,
            "wait_time_seconds": max_retries * poll_interval_seconds,
            "message": "Depósito aceite; confirmação ainda pendente.",
        }

    # Alias retrocompatível
    def query_payment_status(
        self,
        transaction_id: str,
        third_party_reference: str,
    ) -> dict[str, Any]:
        return self.query_status(reference=transaction_id, third_party_ref=third_party_reference)


mpesa_client = MpesaClient()
