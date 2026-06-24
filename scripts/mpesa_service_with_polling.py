import base64
import os
import random
import re
import sys
import requests
import time
import json
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Adicionar diretório pai ao PATH para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import settings
    BEARER_TOKEN = settings.MPESA_BEARER_TOKEN
except ImportError:
    BEARER_TOKEN = None

API_KEY = "bm5pnzcepjt5hy0w2srayyiibh6l00g1"
PUBLIC_KEY_RAW = "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAmptSWqV7cGUUJJhUBxsMLonux24u+FoTlrb+4Kgc6092JIszmI1QUoMohaDDXSVueXx6IXwYGsjjWY32HGXj1iQhkALXfObJ4DqXn5h6E8y5/xQYNAyd5bpN5Z8r892B6toGzZQVB7qtebH4apDjmvTi5FGZVjVYxalyyQkj4uQbbRQjgCkubSi45Xl4CGtLqZztsKssWz3mcKncgTnq3DHGYYEYiKq0xIj100LGbnvNz20Sgqmw/cH+Bua4GJsWYLEqf/h/yiMgiBbxFxsnwZl0im5vXDlwKPw+QnO2fscDhxZFAwV06bgG0oEoWm9FnjMsfvwm0rUNYFlZ+TOtCEhmhtFp+Tsx9jPCuOd5h2emGdSKD8A6jtwhNa7oQ8RtLEEqwAn44orENa1ibOkxMiiiFpmmJkwgZPOG/zMCjXIrrhDWTDUOZaPx/lEQoInJoE2i43VN/HTGCCw8dKQAwg0jsEXau5ixD0GUothqvuX3B9taoeoFAIvUPEq35YulprMM7ThdKodSHvhnwKG82dCsodRwY428kg2xM/UjiTENog4B6zzZfPhMxFlOSFX4MnrqkAS+8Jamhy1GgoHkEMrsT5+/ofjCx0HjKbT5NuA2V/lmzgJLl3jIERadLzuTYnKGWxVJcGLkWXlEPYLbiaKzbJb2sYxt+Kt5OxQqC1MCAwEAAQ=="

SERVICE_PROVIDER_CODE = "171717"

ENDPOINT = "https://api.sandbox.vm.co.mz:18352/ipg/v1x/c2bPayment/singleStage/"
QUERY_ENDPOINT = "https://api.sandbox.vm.co.mz:18353/ipg/v1x/queryTransactionStatus/"


def normalizar_telefone(telefone: str):
    telefone = re.sub(r"\D", "", telefone or "")

    if re.match(r"^(84|85)\d{7}$", telefone):
        telefone = "258" + telefone

    if not re.match(r"^258(84|85)\d{7}$", telefone):
        return None

    return telefone


def gerar_security_credential():
    public_key = (
        "-----BEGIN PUBLIC KEY-----\n"
        + "\n".join(
            [PUBLIC_KEY_RAW[i:i + 64] for i in range(0, len(PUBLIC_KEY_RAW), 64)]
        )
        + "\n-----END PUBLIC KEY-----"
    )

    key = serialization.load_pem_public_key(public_key.encode())

    encrypted = key.encrypt(
        API_KEY.encode(),
        padding.PKCS1v15()
    )

    return base64.b64encode(encrypted).decode()


def pagar_mpesa(telefone: str, valor: float, referencia: str, third_party_ref: str = None):
    """Faz o request inicial do pagamento M-Pesa"""
    telefone_normalizado = normalizar_telefone(telefone)

    if not telefone_normalizado:
        return {
            "success": False,
            "message": "Número M-Pesa inválido. Use número 84 ou 85."
        }

    if valor <= 0:
        return {
            "success": False,
            "message": "Valor inválido."
        }

    try:
        security_credential = gerar_security_credential()
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro ao gerar SecurityCredential: {str(e)}"
        }

    payload = {
        "input_TransactionReference": re.sub(r"[^A-Za-z0-9]", "", referencia)[:20],
        "input_CustomerMSISDN": telefone_normalizado,
        "input_Amount": str(valor),
        "input_ThirdPartyReference": (third_party_ref or ("PED" + str(random.randint(1000, 9999))))[:20],
        "input_ServiceProviderCode": SERVICE_PROVIDER_CODE,
        "input_SecurityCredential": security_credential
    }

    try:
        token_autorizacao = BEARER_TOKEN or security_credential
        response = requests.post(
            ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token_autorizacao}",
                "Origin": "developer.mpesa.vm.co.mz",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Connection": "close"
            },
            timeout=(10, 90),
            verify=True
        )

        try:
            data = response.json()
        except Exception:
            data = {}

        response_code = data.get("output_ResponseCode", "")

        confirmado = (
            response.status_code >= 200
            and response.status_code < 300
            and response_code in ["INS-0", "0", "200", "SUCCESS"]
        )

        return {
            "success": confirmado,
            "http": response.status_code,
            "response_code": response_code,
            "response_desc": data.get("output_ResponseDesc", ""),
            "transaction_id": data.get("output_TransactionID", ""),
            "conversation_id": data.get("output_ConversationID", ""),
            "data": data,
            "raw": response.text
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def verificar_status_transacao(
    reference: str,
    third_party_ref: str = None,
    security_credential: str = None
) -> Dict[str, Any]:
    """
    Verifica o status de uma transação M-Pesa
    
    Args:
        reference: ID da transação (conversation_id ou transaction_id)
        third_party_ref: Referência de terceiros
        security_credential: Credencial de segurança (gerado automaticamente se não fornecido)
    
    Returns:
        Dict com status da transação
    """
    if not security_credential:
        try:
            security_credential = gerar_security_credential()
        except Exception as e:
            return {
                "success": False,
                "status": "erro",
                "message": f"Erro ao gerar credencial: {str(e)}"
            }

    payload = {
        "input_QueryReference": reference,
        "input_ThirdPartyReference": third_party_ref or "11114",
        "input_ServiceProviderCode": SERVICE_PROVIDER_CODE,
        "input_SecurityCredential": security_credential
    }

    try:
        token_autorizacao = BEARER_TOKEN or security_credential
        response = requests.get(
            QUERY_ENDPOINT,
            params=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token_autorizacao}",
                "Origin": "developer.mpesa.vm.co.mz",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            timeout=(10, 90),
            verify=True
        )

        # Se GET falhar, tenta com POST
        if response.status_code in (403, 404, 405):
            print(f"⚠️  GET retornou {response.status_code}, tentando com POST...")
            response = requests.post(
                QUERY_ENDPOINT,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token_autorizacao}",
                    "Origin": "developer.mpesa.vm.co.mz",
                },
                timeout=(10, 90),
                verify=True
            )

        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code not in (200, 201):
            return {
                "success": False,
                "status": "erro",
                "http_code": response.status_code,
                "message": data.get("output_ResponseDesc", "Erro ao verificar status"),
                "data": data
            }

        # Extrai o status da transação
        status_transacao = (
            data.get("output_TransactionStatus") or
            data.get("output_ResponseTransactionStatus") or
            data.get("output_TransactionStatusDesc") or
            "N/A"
        )

        return {
            "success": True,
            "response_code": data.get("output_ResponseCode", ""),
            "response_desc": data.get("output_ResponseDesc", ""),
            "status_transacao": status_transacao,
            "http_code": response.status_code,
            "data": data,
            "raw": response.text
        }

    except Exception as e:
        return {
            "success": False,
            "status": "erro",
            "message": str(e)
        }


def esperar_confirmacao_pagamento(
    conversation_id: str,
    third_party_ref: str = None,
    max_tentativas: int = 10,
    intervalo_segundos: int = 6,
    security_credential: str = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Espera e verifica se o usuário confirmou o pagamento
    
    Args:
        conversation_id: ID da conversa retornado pelo pagar_mpesa()
        third_party_ref: Referência de terceiros
        max_tentativas: Máximo de tentativas (padrão: 10 = ~60 segundos)
        intervalo_segundos: Intervalo entre tentativas (padrão: 6)
        security_credential: Credencial de segurança (gerado automaticamente se não fornecido)
        verbose: Se True, mostra logs detalhados
    
    Returns:
        Dict com resultado final da confirmação
    """
    
    if verbose:
        print(f"\n⏳ Aguardando confirmação do pagamento...")
        print(f"   Conversation ID: {conversation_id}")
        print(f"   Tentativas: {max_tentativas} (a cada {intervalo_segundos}s = ~{max_tentativas * intervalo_segundos}s total)")
        print(f"   {'─' * 60}")

    for tentativa in range(1, max_tentativas + 1):
        # Aguarda antes de verificar
        time.sleep(intervalo_segundos)

        if verbose:
            print(f"\n   [Tentativa {tentativa}/{max_tentativas}] Verificando status...", end=" ", flush=True)

        resultado = verificar_status_transacao(
            reference=conversation_id,
            third_party_ref=third_party_ref,
            security_credential=security_credential
        )

        if not resultado.get("success"):
            if verbose:
                print(f"❌ Erro na verificação")
            continue

        status = resultado.get("status_transacao", "").strip().lower()
        response_code = resultado.get("response_code", "")

        if verbose:
            print(f"Status: {status} (Code: {response_code})")

        # Verifica se está confirmado
        if any(word in status for word in ["success", "sucesso", "completado", "completed", "approved"]):
            if verbose:
                print(f"\n   ✅ PAGAMENTO CONFIRMADO!")
                print(f"   {'─' * 60}\n")
            return {
                "confirmado": True,
                "status": "confirmado",
                "tentativa": tentativa,
                "tempo_espera": tentativa * intervalo_segundos,
                "resultado": resultado
            }

        # Verifica se falhou
        if any(word in status for word in ["failed", "falhou", "rejected", "cancelado", "error"]):
            if verbose:
                print(f"\n   ❌ PAGAMENTO REJEITADO!")
                print(f"   {'─' * 60}\n")
            return {
                "confirmado": False,
                "status": "rejeitado",
                "tentativa": tentativa,
                "tempo_espera": tentativa * intervalo_segundos,
                "resultado": resultado
            }

    # Se completou todas as tentativas sem confirmação
    if verbose:
        print(f"\n   ⏱️  Timeout! Máximo de tentativas atingido.")
        print(f"   {'─' * 60}\n")

    return {
        "confirmado": False,
        "status": "pendente",
        "tentativa": max_tentativas,
        "tempo_espera": max_tentativas * intervalo_segundos,
        "message": "Pagamento ainda está pendente. Tente verificar mais tarde."
    }


if __name__ == "__main__":
    # Dados de teste fornecidos pelo usuário
    input_TransactionReference = "T12344C"
    input_CustomerMSISDN = "258848451424"
    input_Amount = 10.0
    input_ThirdPartyReference = "221ZPP"
    input_ServiceProviderCode = "171717"

    print("=" * 60)
    print("🚀 TESTE COMPLETO DE PAGAMENTO M-PESA COM CONFIRMAÇÃO")
    print("=" * 60)

    # PASSO 1: Fazer o request de pagamento
    print("\n1️⃣  Iniciando pagamento de teste M-Pesa...")
    resultado_pagamento = pagar_mpesa(
        telefone=input_CustomerMSISDN,
        valor=input_Amount,
        referencia=input_TransactionReference,
        third_party_ref=input_ThirdPartyReference
    )

    print("\n📋 Resultado do pagamento:")
    print(json.dumps(resultado_pagamento, indent=4, ensure_ascii=False))

    if not resultado_pagamento.get("success"):
        print("\n❌ Falha ao iniciar pagamento. Abortando.")
        sys.exit(1)

    # PASSO 2: Aguardar confirmação
    conversation_id = resultado_pagamento.get("conversation_id")
    third_party_ref = resultado_pagamento.get("data", {}).get("output_ThirdPartyReference")

    print("\n2️⃣  Aguardando confirmação do usuário...")
    resultado_confirmacao = esperar_confirmacao_pagamento(
        conversation_id=conversation_id,
        third_party_ref=third_party_ref,
        max_tentativas=10,  # Tenta 10 vezes
        intervalo_segundos=6,  # A cada 6 segundos
        verbose=True
    )

    print("\n3️⃣  Resultado Final:")
    print("=" * 60)
    print(json.dumps(resultado_confirmacao, indent=4, ensure_ascii=False))
    print("=" * 60)
