"""
Cliente HTTP para integração com M-Pesa API (Sandbox).
"""

import logging
import time
from typing import Any

import requests
from fastapi import HTTPException, status

from config import settings

logger = logging.getLogger(__name__)


class MpesaClient:
    """Cliente para fazer requisições à API M-Pesa."""

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

    def initiate_payment(
        self,
        transaction_reference: str,
        customer_msisdn: str,
        amount: float,
        third_party_reference: str,
    ) -> dict[str, Any]:
        """
        Inicia pagamento C2B (Customer-to-Business) via M-Pesa.

        Args:
            transaction_reference: Referência única da transação (ex: T12344C)
            customer_msisdn: Número de telemóvel do cliente (ex: 258843330333)
            amount: Valor a cobrar (ex: 10)
            third_party_reference: Referência para rastreio (ex: H5QZ68)

        Returns:
            Resposta da API M-Pesa com confirmação ou erro.

        Raises:
            HTTPException se a requisição falhar.
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
                f"M-Pesa payment request: {transaction_reference} "
                f"for {customer_msisdn} (MT {amount})"
            )
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"M-Pesa response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa API error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro na integração com M-Pesa: {str(e)}",
            )
        except ValueError as e:
            logger.error(f"M-Pesa JSON error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Resposta inválida do M-Pesa",
            )

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


# Instância global
mpesa_client = MpesaClient()
