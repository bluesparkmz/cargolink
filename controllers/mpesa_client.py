"""
Cliente HTTP para integração com M-Pesa API (Sandbox).
"""

import asyncio
import logging
import time
from typing import Any

import httpx
import requests
from fastapi import HTTPException, status

from config import settings

logger = logging.getLogger(__name__)


class MpesaClient:
    """Cliente para fazer requisições à API M-Pesa (suporta síncrono e assíncrono)."""

    def __init__(self):
        self.base_url = settings.MPESA_HOST
        self.bearer_token = settings.MPESA_BEARER_TOKEN
        self.service_provider_code = settings.MPESA_SERVICE_PROVIDER_CODE
        self.query_url = f"{self.base_url}/ipg/v1x/queryTransactionStatus/"

    def _get_headers(self) -> dict[str, str]:
        """Headers necessários para todas as requisições."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "developer.mpesa.vm.co.mz",
        }

    async def initiate_payment_async(
        self,
        transaction_reference: str,
        customer_msisdn: str,
        amount: float,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """
        Inicia pagamento C2B (Customer-to-Business) via M-Pesa - ASSÍNCRONO.

        Args:
            transaction_reference: Referência única da transação (ex: T12344C)
            customer_msisdn: Número de telemóvel do cliente (ex: 258843330333)
            amount: Valor a cobrar (ex: 10)
            third_party_reference: Referência para rastreio (ex: H5QZ68)

        Returns:
            Resposta da API M-Pesa com confirmação ou erro.
        """
        url = f"{self.base_url}/ipg/v1x/c2bPayment/singleStage/"

        payload = {
            "input_TransactionReference": transaction_reference,
            "input_CustomerMSISDN": customer_msisdn,
            "input_Amount": str(amount),
            "input_ThirdPartyReference": third_party_reference,
            "input_ServiceProviderCode": self.service_provider_code,
        }

        try:
            logger.info(
                f"M-Pesa payment request (async): {transaction_reference} "
                f"for {customer_msisdn} (MT {amount})"
            )
            
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
            
            logger.info(f"M-Pesa HTTP {response.status_code}: {response.text[:200]}")
            
            # Tenta extrair JSON mesmo se status não for 200
            try:
                result = response.json()
            except:
                result = {"output_ResponseCode": "999", "output_ResponseDesc": f"HTTP {response.status_code}"}
            
            # Se não foi sucesso (2xx), adiciona o código de erro HTTP
            if response.status_code >= 400:
                result["http_status"] = response.status_code
                logger.error(f"M-Pesa API error: {response.status_code} - {result}")
                return result
            
            logger.info(f"M-Pesa response: {result}")
            return result
            
        except httpx.TimeoutException as e:
            logger.error(f"M-Pesa timeout: {str(e)}")
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": "Timeout ao contactar M-Pesa",
                "http_status": 504,
            }
        except httpx.RequestError as e:
            logger.error(f"M-Pesa API error: {str(e)}")
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": f"Erro de conexão: {str(e)[:100]}",
                "http_status": 503,
            }
        except Exception as e:
            logger.error(f"M-Pesa unexpected error: {str(e)}", exc_info=True)
            return {
                "output_ResponseCode": "999",
                "output_ResponseDesc": f"Erro inesperado: {str(e)[:100]}",
                "http_status": 500,
            }

    def initiate_payment(
        self,
        transaction_reference: str,
        customer_msisdn: str,
        amount: float,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """
        Wrapper síncrono para `initiate_payment_async`.
        Use em contextos síncronos ou quando não puder usar async/await.
        """
        try:
            # Tenta rodar assíncrono se houver event loop ativo
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Em FastAPI async, não pode usar get_event_loop().run_until_complete()
                # Vai retornar erro. Use initiate_payment_async() diretamente!
                logger.warning("Usando initiate_payment() síncrono em contexto async!")
                return {
                    "success": False,
                    "status": "failed",
                    "message": "Use initiate_payment_async() em rotas async",
                }
            return asyncio.run(self.initiate_payment_async(
                transaction_reference,
                customer_msisdn,
                amount,
                third_party_reference,
            ))
        except RuntimeError:
            # Sem event loop
            return asyncio.run(self.initiate_payment_async(
                transaction_reference,
                customer_msisdn,
                amount,
                third_party_reference,
            ))

    def query_payment_status(
        self,
        transaction_id: str,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """
        Consulta o estado de um pagamento junto ao M-Pesa.

        Args:
            transaction_id: ID ou ConversationID da transação no M-Pesa
            third_party_reference: Referência do terceiro (ex: H5QZ68)

        Returns:
            Dicionário com o estado da transação.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "developer.mpesa.vm.co.mz",
            "User-Agent": "Mozilla/5.0",
        }

        params = {
            "input_ThirdPartyReference": third_party_reference,
            "input_QueryReference": transaction_id,
            "input_ServiceProviderCode": self.service_provider_code,
        }

        try:
            logger.info(f"Querying M-Pesa status for transaction: {transaction_id}")
            
            # Tenta GET primeiro, depois POST se falhar
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
                logger.error(f"M-Pesa query error: {response.status_code}")
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }
            
            api_response = response.json()
            response_code = api_response.get("output_ResponseCode", "")
            response_desc = api_response.get("output_ResponseDesc", "")
            
            # Extrai status da transação (pode estar em vários campos)
            transaction_status = (
                api_response.get("output_TransactionStatus")
                or api_response.get("output_TransactionStatusDesc")
                or api_response.get("output_TransactionStatusDescription")
                or response_desc
                or "Unknown"
            )
            
            logger.info(f"M-Pesa status response: {response_code} - {transaction_status}")
            
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
        except Exception as e:
            logger.error(f"Error querying M-Pesa status: {str(e)}")
            return {"success": False, "message": str(e)}

    def wait_for_payment_confirmation(
        self,
        conversation_id: str,
        third_party_reference: str,
        max_wait_seconds: int = 60,
        poll_interval_seconds: int = 6,
    ) -> dict[str, Any]:
        """
        Aguarda e verifica se o usuário confirmou o pagamento M-Pesa.
        
        Esta função faz polling (consultas periódicas) até que:
        - O pagamento seja confirmado (sucesso)
        - O pagamento seja rejeitado (falha)
        - O tempo máximo de espera seja atingido (timeout)
        
        Args:
            conversation_id: ID da conversa retornado por initiate_payment()
            third_party_reference: Referência de terceiros (ex: H5QZ68)
            max_wait_seconds: Tempo máximo de espera em segundos (padrão: 60 = 1 minuto)
            poll_interval_seconds: Intervalo entre tentativas em segundos (padrão: 6)
        
        Returns:
            Dict com resultado:
            {
                "confirmed": True/False,
                "status": "confirmed"/"rejected"/"timeout",
                "attempts": número de tentativas feitas,
                "wait_time_seconds": tempo total de espera,
                "query_result": resultado da última query,
            }
        """
        start_time = time.time()
        max_attempts = max(1, max_wait_seconds // poll_interval_seconds)
        
        logger.info(
            f"Starting payment confirmation polling: conversation_id={conversation_id}, "
            f"max_attempts={max_attempts}, poll_interval={poll_interval_seconds}s"
        )
        
        for attempt in range(1, max_attempts + 1):
            # Aguarda antes de cada tentativa (exceto a primeira)
            if attempt > 1:
                elapsed = time.time() - start_time
                if elapsed >= max_wait_seconds:
                    logger.warning(
                        f"Payment confirmation timeout after {elapsed:.1f}s "
                        f"(conversation_id={conversation_id})"
                    )
                    return {
                        "confirmed": False,
                        "status": "timeout",
                        "attempts": attempt - 1,
                        "wait_time_seconds": int(elapsed),
                        "message": "Timeout aguardando confirmação do pagamento",
                    }
                time.sleep(poll_interval_seconds)
            
            # Query o status
            query_result = self.query_payment_status(
                transaction_id=conversation_id,
                third_party_reference=third_party_reference,
            )
            
            if not query_result.get("success"):
                logger.debug(
                    f"Payment status query failed (attempt {attempt}/{max_attempts}): "
                    f"{query_result.get('message')}"
                )
                continue
            
            # Extrai o status da transação
            status_text = query_result.get("transaction_status", "").strip().lower()
            response_code = query_result.get("response_code", "")
            
            logger.debug(
                f"Payment status (attempt {attempt}/{max_attempts}): "
                f"status={status_text}, code={response_code}"
            )
            
            # Verifica se foi confirmado
            success_keywords = ["success", "sucesso", "completed", "concluido", 
                              "approved", "aprovado", "accepted"]
            if any(keyword in status_text for keyword in success_keywords):
                elapsed = time.time() - start_time
                logger.info(
                    f"Payment CONFIRMED after {elapsed:.1f}s (attempt {attempt}): "
                    f"conversation_id={conversation_id}, status={status_text}"
                )
                return {
                    "confirmed": True,
                    "status": "confirmed",
                    "attempts": attempt,
                    "wait_time_seconds": int(elapsed),
                    "transaction_status": status_text,
                    "response_code": response_code,
                    "query_result": query_result,
                }
            
            # Verifica se foi rejeitado
            failed_keywords = ["failed", "falhou", "rejected", "rejeitado", 
                             "cancelled", "cancelado", "declined", "error"]
            if any(keyword in status_text for keyword in failed_keywords):
                elapsed = time.time() - start_time
                logger.warning(
                    f"Payment REJECTED after {elapsed:.1f}s (attempt {attempt}): "
                    f"conversation_id={conversation_id}, status={status_text}"
                )
                return {
                    "confirmed": False,
                    "status": "rejected",
                    "attempts": attempt,
                    "wait_time_seconds": int(elapsed),
                    "transaction_status": status_text,
                    "response_code": response_code,
                    "query_result": query_result,
                    "message": f"Pagamento rejeitado: {status_text}",
                }
        
        # Timeout após todas as tentativas
        elapsed = time.time() - start_time
        logger.warning(
            f"Payment confirmation timeout after {elapsed:.1f}s and {max_attempts} attempts: "
            f"conversation_id={conversation_id}"
        )
        return {
            "confirmed": False,
            "status": "timeout",
            "attempts": max_attempts,
            "wait_time_seconds": int(elapsed),
            "message": f"Timeout aguardando confirmação após {int(elapsed)}s",
        }

    async def wait_for_payment_confirmation_async(
        self,
        conversation_id: str,
        third_party_reference: str,
        max_wait_seconds: int = 60,
        poll_interval_seconds: int = 6,
    ) -> dict[str, Any]:
        """
        Versão assíncrona de wait_for_payment_confirmation().
        Use em rotas FastAPI async.
        """
        start_time = time.time()
        max_attempts = max(1, max_wait_seconds // poll_interval_seconds)
        
        logger.info(
            f"Starting async payment confirmation polling: conversation_id={conversation_id}, "
            f"max_attempts={max_attempts}, poll_interval={poll_interval_seconds}s"
        )
        
        for attempt in range(1, max_attempts + 1):
            # Aguarda antes de cada tentativa (exceto a primeira)
            if attempt > 1:
                elapsed = time.time() - start_time
                if elapsed >= max_wait_seconds:
                    logger.warning(
                        f"Payment confirmation timeout after {elapsed:.1f}s "
                        f"(conversation_id={conversation_id})"
                    )
                    return {
                        "confirmed": False,
                        "status": "timeout",
                        "attempts": attempt - 1,
                        "wait_time_seconds": int(elapsed),
                        "message": "Timeout aguardando confirmação do pagamento",
                    }
                await asyncio.sleep(poll_interval_seconds)
            
            # Query o status
            query_result = self.query_payment_status(
                transaction_id=conversation_id,
                third_party_reference=third_party_reference,
            )
            
            if not query_result.get("success"):
                logger.debug(
                    f"Payment status query failed (attempt {attempt}/{max_attempts}): "
                    f"{query_result.get('message')}"
                )
                continue
            
            # Extrai o status da transação
            status_text = query_result.get("transaction_status", "").strip().lower()
            response_code = query_result.get("response_code", "")
            
            logger.debug(
                f"Payment status (attempt {attempt}/{max_attempts}): "
                f"status={status_text}, code={response_code}"
            )
            
            # Verifica se foi confirmado
            success_keywords = ["success", "sucesso", "completed", "concluido", 
                              "approved", "aprovado", "accepted"]
            if any(keyword in status_text for keyword in success_keywords):
                elapsed = time.time() - start_time
                logger.info(
                    f"Payment CONFIRMED after {elapsed:.1f}s (attempt {attempt}): "
                    f"conversation_id={conversation_id}, status={status_text}"
                )
                return {
                    "confirmed": True,
                    "status": "confirmed",
                    "attempts": attempt,
                    "wait_time_seconds": int(elapsed),
                    "transaction_status": status_text,
                    "response_code": response_code,
                    "query_result": query_result,
                }
            
            # Verifica se foi rejeitado
            failed_keywords = ["failed", "falhou", "rejected", "rejeitado", 
                             "cancelled", "cancelado", "declined", "error"]
            if any(keyword in status_text for keyword in failed_keywords):
                elapsed = time.time() - start_time
                logger.warning(
                    f"Payment REJECTED after {elapsed:.1f}s (attempt {attempt}): "
                    f"conversation_id={conversation_id}, status={status_text}"
                )
                return {
                    "confirmed": False,
                    "status": "rejected",
                    "attempts": attempt,
                    "wait_time_seconds": int(elapsed),
                    "transaction_status": status_text,
                    "response_code": response_code,
                    "query_result": query_result,
                    "message": f"Pagamento rejeitado: {status_text}",
                }
        
        # Timeout após todas as tentativas
        elapsed = time.time() - start_time
        logger.warning(
            f"Payment confirmation timeout after {elapsed:.1f}s and {max_attempts} attempts: "
            f"conversation_id={conversation_id}"
        )
        return {
            "confirmed": False,
            "status": "timeout",
            "attempts": max_attempts,
            "wait_time_seconds": int(elapsed),
            "message": f"Timeout aguardando confirmação após {int(elapsed)}s",
        }


# Instância global
mpesa_client = MpesaClient()
