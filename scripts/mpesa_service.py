import base64
import os
import random
import re
import sys
import requests

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


if __name__ == "__main__":
    # Dados de teste fornecidos pelo usuário
    input_TransactionReference = "T12344C"
    input_CustomerMSISDN = "258852411827"
    input_Amount = 10.0
    input_ThirdPartyReference = "221ZPP"
    input_ServiceProviderCode = "171717"

    print("Iniciando pagamento de teste M-Pesa...")
    resultado = pagar_mpesa(
        telefone=input_CustomerMSISDN,
        valor=input_Amount,
        referencia=input_TransactionReference,
        third_party_ref=input_ThirdPartyReference
    )
    print("\nResultado obtido:")
    import json
    print(json.dumps(resultado, indent=4, ensure_ascii=False))
