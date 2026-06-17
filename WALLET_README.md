# 💳 Sistema de Wallet com M-Pesa - Implementação Completa

## 📋 Resumo

Implementei um sistema completo de **Wallet (Carteira)** para o CargoLink que permite aos utilizadores fazer **depósitos via M-Pesa** no sandbox de Moçambique.

## ✨ Funcionalidades Implementadas

### 1. **Cliente HTTP para M-Pesa** 
- Arquivo: [`controllers/mpesa_client.py`](../controllers/mpesa_client.py)
- Faz requisições POST ao endpoint: `POST /ipg/v1x/c2bPayment/singleStage/`
- Headers: Authorization com Bearer token
- Tratamento de erros HTTP

### 2. **Depósito via M-Pesa**
- POST `/wallet/deposits` com:
  - `amount`: Valor a depositar (MT)
  - `phone`: Número de telemóvel
  - `method`: "mpesa"
- Criação automática de Payment + Transaction
- Resposta com ID de pagamento e referência

### 3. **Confirmação de Depósitos**
- **Modo Desenvolvimento**: Auto-confirmação imediata
- **Modo Produção**: Aguarda callback do M-Pesa
- POST `/wallet/deposits/{id}/confirm` para confirmação manual

### 4. **Webhook para Callbacks**
- POST `/wallet/mpesa-callback` (sem autenticação)
- Recebe confirmação do M-Pesa
- Credita saldo automaticamente

### 5. **API de Wallet Completa**
- `GET /wallet`: Saldo (available, pending, blocked)
- `GET /wallet/transactions`: Histórico de movimentos
- `POST /wallet/deposits`: Criar depósito
- `POST /wallet/deposits/{id}/confirm`: Confirmar depósito
- `POST /wallet/mpesa-callback`: Webhook M-Pesa

## 📁 Arquivos Criados/Modificados

### Criados
```
✅ controllers/mpesa_client.py          - Cliente HTTP M-Pesa
✅ scripts/test_wallet.py               - Script de testes
✅ .env.example                         - Variáveis de ambiente
✅ docs/wallet.md                       - Documentação completa
```

### Modificados
```
✅ controllers/wallet_controller.py     - Integração com M-Pesa
✅ routers/wallet.py                    - Novo endpoint callback
✅ config.py                            - Variáveis M-Pesa
✅ models/models.py                     - Relationships Payment<->User
```

## 🔄 Fluxo de Depósito

### Desenvolvimento (AUTO_CONFIRM=true)
```
┌─────────────────────────────────────────────────────────────┐
│ Cliente POST /wallet/deposits                                │
│ {amount: 100, phone: "258843330333", method: "mpesa"}       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend:                                                     │
│ 1. Cria Payment (pending)                                   │
│ 2. Cria Transaction (pending)                               │
│ 3. POST ao M-Pesa com credenciais                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ M-Pesa responde com status "INS0" (sucesso)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend auto-confirma:                                      │
│ 1. Payment → completed                                      │
│ 2. Transaction → completed                                  │
│ 3. Wallet.available_balance += 100 MT                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Resposta 201:                                               │
│ {                                                            │
│   "payment_id": 123,                                        │
│   "status": "completed",                                    │
│   "amount": 100.00,                                         │
│   "message": "Depósito confirmado. Saldo atualizado."     │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

### Produção (AUTO_CONFIRM=false)
```
┌──────────────────────────────────────────────────────────────┐
│ Cliente POST /wallet/deposits                                 │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ Payment (pending)    │
         │ Transaction (pending)│
         └─────────┬───────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ POST ao M-Pesa      │
         └─────────┬───────────┘
                   │
         ┌─────────▼───────────┐
         │ Resposta "pending"  │
         │ (aguarde SMS)       │
         └─────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │ Cliente confirma       │
      │ no telemóvel (SMS)     │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │ M-Pesa POST callback   │
      │ /wallet/mpesa-callback │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────────────────┐
      │ Backend processa callback:          │
      │ 1. Payment → completed              │
      │ 2. Transaction → completed          │
      │ 3. Wallet.balance += 100 MT        │
      └────────────┬───────────────────────┘
                   │
                   ▼
      ┌────────────────────────────────────┐
      │ Saldo creditado na carteira!       │
      └────────────────────────────────────┘
```

## 🛠️ Configuração

### 1. Copiar variáveis de ambiente
```bash
cp .env.example .env
```

### 2. Variáveis necessárias (já preenchidas com sandbox)
```bash
MPESA_HOST=https://api.sandbox.vm.co.mz
MPESA_BEARER_TOKEN=UELjHu...  # Token sandbox fornecido
MPESA_SERVICE_PROVIDER_CODE=171717
AUTO_CONFIRM_MPESA_DEPOSITS=true  # Alterar para false em produção
```

### 3. Iniciar servidor
```bash
cd cargolink_api
python main.py
```

## 🧪 Testes

### Script automático
```bash
python scripts/test_wallet.py
```

### Teste manual
```bash
# 1. Fazer login e obter token
TOKEN=$(curl -X POST http://localhost:8000/auth/login ...)

# 2. Criar depósito
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "phone": "258843330333", "method": "mpesa"}'

# 3. Verificar saldo
curl -X GET http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN"

# 4. Listar transações
curl -X GET http://localhost:8000/wallet/transactions \
  -H "Authorization: Bearer $TOKEN"
```

## 📊 Estrutura de Dados

### Wallet
```json
{
  "id": 1,
  "user_id": 123,
  "available_balance": 1500.00,
  "pending_balance": 0.00,
  "blocked_balance": 0.00,
  "currency": "MT"
}
```

### Payment
```json
{
  "id": 1,
  "user_id": 123,
  "method": "mpesa",
  "phone": "258843330333",
  "amount": 100.00,
  "status": "completed",
  "external_reference": "MPESA-ABC123DEF456",
  "gateway_response": {
    "output_ConversationID": "...",
    "output_ResponseCode": "INS0",
    "output_ResponseDesc": "Success"
  }
}
```

### Transaction
```json
{
  "id": 1,
  "wallet_id": 1,
  "transaction_type": "deposit",
  "amount": 100.00,
  "status": "completed",
  "reference": "MPESA-ABC123DEF456",
  "description": "Depósito MPESA via 258843330333"
}
```

## ⚠️ Pontos Importantes

1. **Token M-Pesa Sandbox**: É de teste, use credenciais reais em produção
2. **Service Provider Code**: Sempre 171717 no sandbox, será diferente em produção
3. **Auto-confirmação**: Apenas para desenvolvimento, desativar em produção
4. **Webhook**: Deve ser acessível externamente (não localhost) para receber callbacks
5. **Validação**: Implementar validação de assinatura digital quando em produção

## 📖 Documentação

- **Completo**: [`docs/wallet.md`](../docs/wallet.md)
- **API Mpesa**: [developer.mpesa.vm.co.mz](https://developer.mpesa.vm.co.mz)
- **Exemplos**: Ver `scripts/test_wallet.py`

## 🚀 Próximas Funcionalidades

- [ ] Levantamento de fundos (Withdrawal)
- [ ] Integração com outras formas de pagamento
- [ ] Autenticação webhook (validar assinatura M-Pesa)
- [ ] Relatórios financeiros
- [ ] Transações recorrentes
- [ ] Integração com gateway de pagamento Stripe/Paypal

## ✅ Status

**Implementação Concluída!**

Todos os arquivos estão prontos e testados. O sistema está funcional em modo desenvolvimento com auto-confirmação. Pronto para testes em produção com callbacks reais do M-Pesa.
