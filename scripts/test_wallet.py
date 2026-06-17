#!/usr/bin/env python3
"""
Script de teste para o sistema de Wallet com M-Pesa.

Testa:
1. Criar depósito
2. Confirmar depósito
3. Obter saldo
4. Listar transações
5. Simular callback do Mpesa
"""

import json
import requests
from decimal import Decimal

# ===== CONFIGURAÇÃO =====
BASE_URL = "http://localhost:8000"
WALLET_PREFIX = "/wallet"

# Token JWT (substituir com token real após login)
TOKEN = "seu-token-jwt-aqui"


def get_headers():
    """Headers para requisições autenticadas."""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def print_section(title):
    """Imprime título de seção."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_response(title, response):
    """Imprime resposta formatada."""
    print(f"[{response.status_code}] {title}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print()


# ===== TESTES =====

def test_get_balance():
    """Teste 1: Obter saldo atual."""
    print_section("Teste 1: Obter Saldo Atual")
    
    url = f"{BASE_URL}{WALLET_PREFIX}"
    response = requests.get(url, headers=get_headers())
    print_response("GET /wallet", response)
    
    return response.json() if response.status_code == 200 else None


def test_create_deposit():
    """Teste 2: Criar novo depósito."""
    print_section("Teste 2: Criar Novo Depósito")
    
    url = f"{BASE_URL}{WALLET_PREFIX}/deposits"
    payload = {
        "amount": 100.00,
        "phone": "258843330333",
        "method": "mpesa"
    }
    
    response = requests.post(url, json=payload, headers=get_headers())
    print_response("POST /wallet/deposits", response)
    
    return response.json() if response.status_code == 201 else None


def test_confirm_deposit(payment_id):
    """Teste 3: Confirmar depósito pendente."""
    print_section("Teste 3: Confirmar Depósito Pendente")
    
    if not payment_id:
        print("⚠️  Payment ID não disponível. Pulando teste.")
        return
    
    url = f"{BASE_URL}{WALLET_PREFIX}/deposits/{payment_id}/confirm"
    response = requests.post(url, headers=get_headers())
    print_response(f"POST /wallet/deposits/{payment_id}/confirm", response)
    
    return response.json() if response.status_code == 200 else None


def test_list_transactions():
    """Teste 4: Listar transações."""
    print_section("Teste 4: Listar Transações")
    
    url = f"{BASE_URL}{WALLET_PREFIX}/transactions"
    params = {
        "limit": 10,
        "offset": 0
    }
    
    response = requests.get(url, params=params, headers=get_headers())
    print_response("GET /wallet/transactions", response)
    
    return response.json() if response.status_code == 200 else None


def test_mpesa_callback():
    """Teste 5: Simular callback do Mpesa."""
    print_section("Teste 5: Simular Callback do Mpesa")
    
    url = f"{BASE_URL}{WALLET_PREFIX}/mpesa-callback"
    payload = {
        "output_ConversationID": "12345678",
        "output_ResponseCode": "INS0",
        "output_ResponseDesc": "Success",
        "input_ThirdPartyReference": "H5QZ68",
        "input_TransactionReference": "T12344C"
    }
    
    # ⚠️  Este endpoint NÃO requer autenticação
    response = requests.post(url, json=payload)
    print_response("POST /wallet/mpesa-callback (Webhook)", response)
    
    return response.json() if response.status_code == 200 else None


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("  TESTES DO SISTEMA DE WALLET COM M-PESA")
    print("="*60)
    
    # Verificar conectividade
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("⚠️  Backend não está respondendo corretamente.")
            print("    Verifique se o servidor está rodando: python main.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não é possível conectar ao backend.")
        print("   Certifique-se de que o servidor está rodando em http://localhost:8000")
        return
    
    print("✅ Backend está online\n")
    
    # 1. Obter saldo
    balance = test_get_balance()
    
    # 2. Criar depósito
    deposit = test_create_deposit()
    payment_id = deposit.get("payment_id") if deposit else None
    
    # 3. Confirmar depósito (se não foi auto-confirmado)
    if deposit and deposit.get("status") == "pending":
        test_confirm_deposit(payment_id)
    
    # 4. Listar transações
    transactions = test_list_transactions()
    
    # 5. Simular callback (em produção, Mpesa chamaria isto)
    test_mpesa_callback()
    
    # Resumo
    print_section("Resumo dos Testes")
    print("""
✅ Testes completados!

Próximos passos:
1. Verifique se o saldo foi creditado após depósito
2. Em produção, configure MPESA_BEARER_TOKEN com credenciais reais
3. Configure AUTO_CONFIRM_MPESA_DEPOSITS=false para testar callbacks reais
4. Registar URL de callback no Mpesa: https://seu-dominio.com/wallet/mpesa-callback

Recursos úteis:
- Documentação: docs/wallet.md
- API Mpesa: https://developer.mpesa.vm.co.mz
    """)


if __name__ == "__main__":
    main()
