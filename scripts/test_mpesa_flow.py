#!/usr/bin/env python3
"""
Script de teste para o fluxo real de depósitos M-Pesa.

Simula o fluxo completo:
1. Utilizador faz login
2. Inicia depósito
3. Aguarda confirmação de PIN (modo produção)
4. Verifica se foi creditado

Nota: Em desenvolvimento, a confirmação é automática.
      Em produção, M-Pesa envia SMS e aguarda PIN do utilizador.
"""

import json
import time
import requests
from typing import Optional

# ===== CONFIGURAÇÃO =====
BASE_URL = "http://localhost:8000"
AUTO_CONFIRM = True  # Alterar para False em produção

class MpesaDepositTest:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user: Optional[dict] = None
        self.session = requests.Session()
    
    def print_section(self, title: str):
        """Imprime separador de seção."""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def print_response(self, title: str, response: requests.Response):
        """Imprime resposta formatada."""
        print(f"\n[{response.status_code}] {title}")
        print("-" * 70)
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
        print()
    
    def login(self, phone: str, password: str) -> bool:
        """Faz login e obtém token."""
        self.print_section("PASSO 1: Login")
        
        url = f"{self.base_url}/auth/login"
        payload = {
            "phone": phone,
            "password": password
        }
        
        try:
            response = self.session.post(url, json=payload)
            self.print_response("POST /auth/login", response)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                return True
            else:
                print("❌ Login falhou!")
                return False
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False
    
    def get_wallet(self) -> Optional[dict]:
        """Obtém saldo atual da carteira."""
        self.print_section("PASSO 2: Obter Saldo Antes do Depósito")
        
        url = f"{self.base_url}/wallet"
        
        try:
            response = self.session.get(url)
            self.print_response("GET /wallet", response)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def initiate_deposit(self, amount: float, phone: str) -> Optional[dict]:
        """Inicia depósito via M-Pesa."""
        self.print_section("PASSO 3: Iniciar Depósito via M-Pesa")
        
        print(f"📱 Depositando: {amount} MT para {phone}")
        print(f"⏳ Aguardando resposta do M-Pesa...\n")
        
        url = f"{self.base_url}/wallet/deposits"
        payload = {
            "amount": amount,
            "phone": phone,
            "method": "mpesa"
        }
        
        try:
            response = self.session.post(url, json=payload)
            self.print_response("POST /wallet/deposits", response)
            
            if response.status_code == 201:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def analyze_mpesa_response(self, deposit_response: dict):
        """Analisa resposta do M-Pesa."""
        self.print_section("ANÁLISE: Resposta do M-Pesa")
        
        print("📋 Informações do Depósito:\n")
        
        payment_id = deposit_response.get("payment_id")
        status = deposit_response.get("status")
        message = deposit_response.get("message")
        external_ref = deposit_response.get("external_reference")
        amount = deposit_response.get("amount")
        phone = deposit_response.get("phone")
        
        print(f"  Payment ID:          {payment_id}")
        print(f"  Status:              {status}")
        print(f"  Valor:               {amount} MT")
        print(f"  Telemóvel:           {phone}")
        print(f"  Referência Externa:  {external_ref}")
        print(f"  Mensagem:            {message}")
        
        print("\n📊 Análise do Status:\n")
        
        if status == "pending":
            print("  🟡 PENDENTE")
            print("  ✓ M-Pesa enviou SMS para confirmar")
            print("  ✓ Utilizador deve digitar PIN no telemóvel")
            print("  ✓ Após confirmação, M-Pesa enviará callback")
            print("  ✓ Backend creditará o saldo automaticamente")
            print("\n  ⏳ Aguardando confirmação do utilizador...")
            return "pending"
        
        elif status == "completed":
            print("  🟢 CONFIRMADO (Modo Desenvolvimento)")
            print("  ✓ Depósito foi confirmado automaticamente")
            print("  ✓ Saldo já foi creditado")
            return "completed"
        
        elif status == "failed":
            print("  🔴 FALHOU")
            print("  ✗ Erro ao processar depósito")
            return "failed"
        
        return status
    
    def wait_for_confirmation(self, payment_id: int, timeout: int = 300):
        """
        Aguarda confirmação do depósito (polling).
        Verifica a cada 5 segundos se o pagamento foi confirmado.
        """
        self.print_section("PASSO 4: Aguardando Confirmação")
        
        print(f"⏱️  Aguardando confirmação...")
        print(f"   Timeout: {timeout} segundos\n")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            # Verificar saldo a cada 5 segundos
            wallet = self.get_wallet_brief()
            
            if wallet:
                status = wallet.get("status")
                if status == "confirmed":
                    print(f"\n✅ CONFIRMADO! ({elapsed}s)")
                    return True
            
            print(f"   ⏳ Verificação #{check_count} ({elapsed}s)... ainda pendente")
            time.sleep(5)
        
        print(f"\n⏱️  Timeout! Não confirmado em {timeout}s")
        return False
    
    def get_wallet_brief(self) -> Optional[dict]:
        """Obtém saldo (versão silenciosa, sem print)."""
        url = f"{self.base_url}/wallet"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def check_wallet_after(self) -> Optional[dict]:
        """Verifica saldo após depósito."""
        self.print_section("PASSO 5: Verificar Saldo Após Depósito")
        
        url = f"{self.base_url}/wallet"
        
        try:
            response = self.session.get(url)
            self.print_response("GET /wallet (após depósito)", response)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def list_transactions(self) -> Optional[list]:
        """Lista transações recentes."""
        self.print_section("PASSO 6: Verificar Histórico de Transações")
        
        url = f"{self.base_url}/wallet/transactions"
        params = {"limit": 5, "offset": 0}
        
        try:
            response = self.session.get(url, params=params)
            self.print_response("GET /wallet/transactions", response)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def simulate_mpesa_callback(self, payment_id: int = 1):
        """Simula callback do M-Pesa (teste manual)."""
        self.print_section("TESTE MANUAL: Simular Callback do M-Pesa")
        
        print("📌 Nota: Este é um teste simulado!")
        print("    Em produção, M-Pesa enviaria este callback após o utilizador confirmar o PIN\n")
        
        url = f"{self.base_url}/wallet/mpesa-callback"
        payload = {
            "output_ConversationID": "12345678",
            "output_ResponseCode": "INS0",
            "output_ResponseDesc": "Success",
            "input_ThirdPartyReference": "TEST123",
            "input_TransactionReference": "T12344C"
        }
        
        try:
            response = requests.post(url, json=payload)
            self.print_response("POST /wallet/mpesa-callback", response)
            
            if response.status_code == 200:
                print("✅ Callback processado com sucesso!")
                return True
            else:
                return False
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False
    
    def run_full_test(self, phone: str, password: str, deposit_amount: float, deposit_phone: str):
        """Executa teste completo."""
        print("\n" + "="*70)
        print("  TESTE COMPLETO: FLUXO DE DEPÓSITO M-PESA")
        print("="*70)
        
        # Passo 1: Login
        if not self.login(phone, password):
            print("❌ Falha no login. Abortando.")
            return
        
        # Passo 2: Obter saldo antes
        wallet_before = self.get_wallet()
        if wallet_before:
            print(f"\n💰 Saldo antes: {wallet_before['available_balance']} {wallet_before['currency']}")
        
        # Passo 3: Iniciar depósito
        deposit = self.initiate_deposit(deposit_amount, deposit_phone)
        if not deposit:
            print("❌ Falha ao iniciar depósito. Abortando.")
            return
        
        # Analisar resposta
        status = self.analyze_mpesa_response(deposit)
        payment_id = deposit.get("payment_id")
        
        # Passo 4: Se pendente, aguardar confirmação
        if status == "pending" and AUTO_CONFIRM:
            print("\n💡 Sugestão: Em produção, o utilizador teria que confirmar o PIN.")
            print("   Simulando callback para fins de teste...\n")
            time.sleep(2)
            self.simulate_mpesa_callback(payment_id)
            time.sleep(1)
        
        # Passo 5: Verificar saldo após
        wallet_after = self.check_wallet_after()
        if wallet_after:
            print(f"\n💰 Saldo depois: {wallet_after['available_balance']} {wallet_after['currency']}")
            
            if wallet_before:
                diff = wallet_after['available_balance'] - wallet_before['available_balance']
                if diff > 0:
                    print(f"✅ CREDITADO: +{diff} MT")
                else:
                    print(f"⏳ AINDA PENDENTE: Aguardando confirmação do utilizador")
        
        # Passo 6: Listar transações
        self.list_transactions()
        
        # Resumo
        self.print_section("RESUMO DO TESTE")
        
        print("✅ Teste completado com sucesso!")
        print("\n📊 Resultado:")
        print(f"  - Depósito iniciado: {deposit_amount} MT")
        print(f"  - Status: {status}")
        print(f"  - Referência: {deposit.get('external_reference')}")
        
        if status == "pending":
            print("\n📱 Fluxo em Produção:")
            print("  1. ✅ Requisição enviada ao M-Pesa")
            print("  2. 📨 M-Pesa envia SMS com PIN")
            print("  3. ⏳ Utilizador aguarda confirmação")
            print("  4. 🔐 Utilizador digita PIN no telemóvel")
            print("  5. 📞 M-Pesa envia callback ao backend")
            print("  6. 💳 Backend credita saldo automaticamente")
        elif status == "completed":
            print("\n✅ Depósito confirmado!")
            print("   Saldo foi creditado imediatamente (modo desenvolvimento)")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  TESTE DE DEPÓSITO M-PESA                           ║
║                                                                      ║
║  Este script testa o fluxo completo de depósito via M-Pesa,         ║
║  incluindo:                                                          ║
║  • Login do utilizador                                              ║
║  • Verificação de saldo antes                                       ║
║  • Envio de requisição ao M-Pesa                                    ║
║  • Análise da resposta                                              ║
║  • Simulação de callback (se em desenvolvimento)                    ║
║  • Verificação de saldo após                                        ║
║  • Listagem de transações                                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Configuração de teste
    test = MpesaDepositTest()
    
    # Credenciais de teste (ajustar conforme necessário)
    # Primeira, criar um utilizador de teste via:
    # curl -X POST http://localhost:8000/auth/register \
    #   -H "Content-Type: application/json" \
    #   -d '{"name": "Teste", "phone": "258843330333", "email": "test@example.com", "password": "senha123", "user_type": "cliente"}'
    
    LOGIN_PHONE = "258843330333"
    LOGIN_PASSWORD = "senha123"
    DEPOSIT_AMOUNT = 100.00
    DEPOSIT_PHONE = "258843330333"
    
    # Executar teste
    test.run_full_test(
        phone=LOGIN_PHONE,
        password=LOGIN_PASSWORD,
        deposit_amount=DEPOSIT_AMOUNT,
        deposit_phone=DEPOSIT_PHONE
    )
    
    print("\n" + "="*70)
    print("  PRÓXIMOS PASSOS EM PRODUÇÃO")
    print("="*70 + "\n")
    print("""
1. Alterar AUTO_CONFIRM para False:
   AUTO_CONFIRM = False

2. Configurar a URL de callback no painel M-Pesa:
   https://seu-dominio.com/wallet/mpesa-callback

3. Executar o script e acompanhar:
   - SMS chegará ao telemóvel
   - Utilizador digita PIN
   - Callback será enviado ao backend
   - Saldo será creditado

4. Para testes locais, usar ngrok:
   ngrok http 8000
   E registar a URL de callback no Mpesa
    """)


if __name__ == "__main__":
    main()
