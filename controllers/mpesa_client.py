"""
Cliente HTTP para integração com M-Pesa API (Sandbox).
Alinhado com Skywallet: URLs com portas, refs normalizadas, polling.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Any

import httpx
import requests

from config import settings
from controllers.mpesa_utils import (
    format_mpesa_amount,
    is_mpesa_accepted,
    normalize_mpesa_reference,
)

logger = logging.getLogger(__name__)


class MpesaClient:
    """Cliente para requisições à API M-Pesa (C2B + query + polling)."""

    def __init__(self):
        self.c2b_url = settings.MPESA_C2B_URL
        self.query_url = settings.MPESA_QUERY_URL
        self.service_provider_code = settings.MPESA_SERVICE_PROVIDER_CODE
        self.default_third_party_reference = settings.MPESA_THIRD_PARTY_REFERENCE
        raw_token = settings.MPESA_BEARER_TOKEN or ""
        self.bearer_token = raw_token.replace("Bearer ", "").strip()
        logger.info("MpesaClient [sandbox] c2b=%s", self.c2b_url)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "developer.mpesa.vm.co.mz",
        }

    def _resolve_references(
        self,
        transaction_reference: str,
        third_party_reference: str | None,
    ) -> tuple[str, str]:
        tx_ref = normalize_mpesa_reference(transaction_reference, fallback_prefix="TX")
        tp_ref = normalize_mpesa_reference(
            third_party_reference or self.default_third_party_reference or transaction_reference,
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
        """Inicia pagamento C2B (Customer-to-Business) via M-Pesa."""
        if not self.bearer_token:
            logger.error("MPESA_BEARER_TOKEN não configurado.")
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
                tx_ref,
                tp_ref,
                customer_msisdn,
                payload["input_Amount"],
            )

            async with httpx.AsyncClient(timeout=30, verify=True) as client:
                response = await client.post(
                    self.c2b_url,
                    json=payload,
                    headers=self._get_headers(),
                )

            logger.info("M-Pesa HTTP %s: %s", response.status_code, response.text[:300])

            try:
                result = response.json()
            except ValueError:
                result = {
                    "output_ResponseCode": "999",
                    "output_ResponseDesc": f"HTTP {response.status_code}",
                }

            result["_transaction_reference"] = tx_ref
            result["_third_party_reference"] = tp_ref

            if response.status_code >= 400:
                result["http_status"] = response.status_code
                logger.error("M-Pesa API error %s: %s", response.status_code, result)
                return result

            logger.info("M-Pesa C2B response: %s", result)
            return result

        except httpx.TimeoutException as exc:
            logger.error("M-Pesa timeout: %s", exc)
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": "Timeout ao contactar M-Pesa",
                "http_status": 504,
            }
        except httpx.RequestError as exc:
            logger.error("M-Pesa connection error: %s", exc)
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": f"Erro de conexão: {str(exc)[:100]}",
                "http_status": 503,
            }
        except Exception as exc:
            logger.error("M-Pesa unexpected error: %s", exc, exc_info=True)
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": f"Erro inesperado: {str(exc)[:100]}",
                "http_status": 500,
            }

    def query_payment_status(
        self,
        transaction_id: str,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """Consulta estado de pagamento junto ao M-Pesa."""
        if not self.bearer_token:
            return {"success": False, "message": "M-Pesa token não configurado."}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "developer.mpesa.vm.co.mz",
            "User-Agent": "Mozilla/5.0",
        }

        tp_ref = normalize_mpesa_reference(
            third_party_reference or self.default_third_party_reference,
            fallback_prefix="TP",
        )
        params = {
            "input_ThirdPartyReference": tp_ref,
            "input_QueryReference": transaction_id,
            "input_ServiceProviderCode": self.service_provider_code or "171717",
        }

        try:
            logger.info("M-Pesa query: ref=%s tp=%s", transaction_id, tp_ref)

            response = requests.get(
                self.query_url,
                headers=headers,
                params=params,
                verify=True,
                timeout=30,
            )

            if response.status_code in (405, 404):
                response = requests.post(
                    self.query_url,
                    headers=headers,
                    json=params,
                    verify=True,
                    timeout=30,
                )

            if response.status_code not in (200, 201):
                logger.error("M-Pesa query HTTP %s", response.status_code)
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }

            api_response = response.json()
            response_code = api_response.get("output_ResponseCode", "")
            response_desc = api_response.get("output_ResponseDesc", "")
            transaction_status = (
                api_response.get("status_da_transacao_resposta")
                or api_response.get("status_da_transação_resposta")
                or api_response.get("output_TransactionStatus")
                or api_response.get("output_TransactionStatusDesc")
                or api_response.get("output_TransactionStatusDescription")
                or response_desc
                or "Unknown"
            )

            logger.info("M-Pesa query: code=%s status=%s", response_code, transaction_status)

            return {
                "success": True,
                "response_code": response_code,
                "response_description": response_desc,
                "transaction_status": transaction_status,
                "api_response": api_response,
            }
        except requests.exceptions.Timeout:
            logger.error("M-Pesa query timeout")
            return {"success": False, "message": "M-Pesa API timeout"}
        except Exception as exc:
            logger.error("Error querying M-Pesa status: %s", exc)
            return {"success": False, "message": str(exc)}

    def _evaluate_polling_result(self, query_result: dict[str, Any]) -> str | None:
        """Retorna 'confirmed', 'rejected' ou None se ainda pendente."""
        status_text = query_result.get("transaction_status", "").strip().lower()
        response_code = query_result.get("response_code", "")

        success_keywords = [
            "success", "sucesso", "completed", "concluido", "concluído",
            "approved", "aprovado", "accepted", "done", "pago",
        ]
        failed_keywords = [
            "failed", "falhou", "rejected", "rejeitado", "cancelled",
            "cancelado", "declined", "error", "expired", "falha",
        ]

        if is_mpesa_accepted(response_code) and any(kw in status_text for kw in success_keywords):
            return "confirmed"
        if any(kw in status_text for kw in failed_keywords):
            return "rejected"
        if is_mpesa_accepted(response_code) and status_text in ("", "unknown"):
            return None
        return None

    async def wait_for_payment_confirmation_async(
        self,
        conversation_id: str,
        third_party_reference: str,
        max_wait_seconds: int = 60,
        poll_interval_seconds: int = 6,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Aguarda confirmação via polling (como Skywallet).
        Usa output_TransactionID quando disponível para query.
        """
        start_time = time.time()
        max_attempts = max(1, max_wait_seconds // poll_interval_seconds)
        query_ref = transaction_id or conversation_id
        failed_queries = 0

        logger.info(
            "Polling M-Pesa: query_ref=%s tp=%s max=%ss",
            query_ref,
            third_party_reference,
            max_wait_seconds,
        )

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                elapsed = time.time() - start_time
                if elapsed >= max_wait_seconds:
                    break
                await asyncio.sleep(poll_interval_seconds)

            query_result = self.query_payment_status(
                transaction_id=query_ref,
                third_party_reference=third_party_reference,
            )

            if not query_result.get("success"):
                failed_queries += 1
                if failed_queries >= 3:
                    break
                continue

            failed_queries = 0
            verdict = self._evaluate_polling_result(query_result)
            elapsed = int(time.time() - start_time)

            if verdict == "confirmed":
                logger.info("M-Pesa CONFIRMED após %ss (tentativa %s)", elapsed, attempt)
                return {
                    "confirmed": True,
                    "status": "confirmed",
                    "attempts": attempt,
                    "wait_time_seconds": elapsed,
                    "query_result": query_result,
                }

            if verdict == "rejected":
                status_text = query_result.get("transaction_status", "")
                logger.warning("M-Pesa REJECTED após %ss: %s", elapsed, status_text)
                return {
                    "confirmed": False,
                    "status": "rejected",
                    "attempts": attempt,
                    "wait_time_seconds": elapsed,
                    "query_result": query_result,
                    "message": f"Pagamento rejeitado: {status_text}",
                }

        elapsed = int(time.time() - start_time)
        logger.warning("M-Pesa polling timeout após %ss", elapsed)
        return {
            "confirmed": False,
            "status": "timeout",
            "attempts": max_attempts,
            "wait_time_seconds": elapsed,
            "message": f"Timeout aguardando confirmação após {elapsed}s",
        }

    def wait_for_payment_confirmation(
        self,
        conversation_id: str,
        third_party_reference: str,
        max_wait_seconds: int = 60,
        poll_interval_seconds: int = 6,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """Wrapper síncrono para polling."""
        return asyncio.run(
            self.wait_for_payment_confirmation_async(
                conversation_id=conversation_id,
                third_party_reference=third_party_reference,
                max_wait_seconds=max_wait_seconds,
                poll_interval_seconds=poll_interval_seconds,
                transaction_id=transaction_id,
            )
        )


mpesa_client = MpesaClient()
