"""
Guia Prático: Testando o Sistema de Wallet com M-Pesa
======================================================

Este guia mostra como testar passo-a-passo o sistema de wallet.
"""

# ============================================================================
# PASSO 1: Preparação
# ============================================================================

"""
1.1 Verificar se o Backend está rodando
```bash
# Terminal 1
cd d:\CargoLink\ App\cargolink_api
python main.py
```

Deve aparecer:
  INFO:     Uvicorn running on http://127.0.0.1:8000
  INFO:     Application startup complete

1.2 Abrir outro terminal para testes
```bash
# Terminal 2
cd d:\CargoLink\ App\cargolink_api
```
"""


# ============================================================================
# PASSO 2: Obter Token de Autenticação
# ============================================================================

"""
Primeiro, precisamos fazer login para obter um token JWT.

2.1 Criar um utilizador (se não existir)
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "phone": "258843330333",
    "email": "joao@example.com",
    "password": "senha123",
    "user_type": "cliente"
  }'
```

Resposta esperada (201):
{
  "id": 1,
  "name": "João Silva",
  "phone": "258843330333",
  "email": "joao@example.com",
  "user_type": "cliente",
  "verified": false,
  "access_token": "eyJhbGc..."
}

2.2 Guardar o token
```bash
# Guardar na variável TOKEN para usar nos próximos comandos
TOKEN="eyJhbGc..."
```

2.3 Se já tem utilizador, fazer login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "258843330333",
    "password": "senha123"
  }'
```

Resposta:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
"""


# ============================================================================
# PASSO 3: Testar Endpoints do Wallet
# ============================================================================

"""
3.1 Obter Saldo Atual
```bash
curl -X GET http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada (200):
{
  "available_balance": 0.00,
  "pending_balance": 0.00,
  "blocked_balance": 0.00,
  "currency": "MT"
}
"""

"""
3.2 Criar um Depósito
```bash
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "phone": "258843330333",
    "method": "mpesa"
  }'
```

Resposta esperada (201):
{
  "payment_id": 1,
  "transaction_id": 1,
  "amount": 100.00,
  "status": "completed",
  "external_reference": "MPESA-ABC123DEF456",
  "phone": "258843330333",
  "message": "Depósito confirmado (modo desenvolvimento). Saldo atualizado."
}

⚠️  Notar: status é "completed" porque AUTO_CONFIRM_MPESA_DEPOSITS=true
"""

"""
3.3 Verificar Saldo Atualizado
```bash
curl -X GET http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada (200):
{
  "available_balance": 100.00,
  "pending_balance": 0.00,
  "blocked_balance": 0.00,
  "currency": "MT"
}

✅ O saldo foi creditado!
"""

"""
3.4 Listar Transações
```bash
curl -X GET "http://localhost:8000/wallet/transactions?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada (200):
[
  {
    "id": 1,
    "transaction_type": "deposit",
    "amount": 100.00,
    "status": "completed",
    "reference": "MPESA-ABC123DEF456",
    "description": "Depósito MPESA via 258843330333",
    "created_at": "2026-06-17T10:30:00Z"
  }
]
"""

"""
3.5 Múltiplos Depósitos
```bash
# Primeiro depósito
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50.00, "method": "mpesa"}'

# Segundo depósito
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 200.00, "method": "mpesa"}'

# Verificar saldo (deve ser 250.00 total)
curl -X GET http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN"
```
"""


# ============================================================================
# PASSO 4: Testar Modo Produção (com Callbacks)
# ============================================================================

"""
4.1 Alterar para modo produção
Edit: .env
AUTO_CONFIRM_MPESA_DEPOSITS=false

Reiniciar o servidor:
python main.py
"""

"""
4.2 Criar depósito em modo pendente
```bash
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "phone": "258843330333",
    "method": "mpesa"
  }'
```

Resposta (201):
{
  "payment_id": 2,
  "transaction_id": 2,
  "amount": 100.00,
  "status": "pending",
  "external_reference": "MPESA-XYZ789ABC456",
  "phone": "258843330333",
  "message": "Depósito registado. Aguarde confirmação M-Pesa no telemóvel."
}

✅ Notar: status é "pending" e não foi creditado
"""

"""
4.3 Simular Callback do M-Pesa
Em produção, M-Pesa chamaria o webhook. Vamos simular:

```bash
curl -X POST http://localhost:8000/wallet/mpesa-callback \
  -H "Content-Type: application/json" \
  -d '{
    "output_ConversationID": "12345678",
    "output_ResponseCode": "INS0",
    "output_ResponseDesc": "Success",
    "input_ThirdPartyReference": "H5QZ68",
    "input_TransactionReference": "T12344C"
  }'
```

Resposta (200):
{
  "status": "success",
  "message": "Depósito confirmado",
  "payment_id": 2
}

✅ O backend processou o callback!
"""

"""
4.4 Verificar Saldo após Callback
```bash
curl -X GET http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN"
```

Resposta:
{
  "available_balance": 100.00,
  "pending_balance": 0.00,
  "blocked_balance": 0.00,
  "currency": "MT"
}

✅ O saldo foi creditado após callback!
"""


# ============================================================================
# PASSO 5: Testar Confirmação Manual
# ============================================================================

"""
5.1 Scenario: Depósito Pendente
Se criar outro depósito em modo produção, ficará pendente:

```bash
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00,
    "method": "mpesa"
  }'
```

Retorna: payment_id = 3, status = "pending"
"""

"""
5.2 Confirmar Manualmente
Sem esperar pelo M-Pesa (útil para testes):

```bash
curl -X POST http://localhost:8000/wallet/deposits/3/confirm \
  -H "Authorization: Bearer $TOKEN"
```

Resposta (200):
{
  "payment_id": 3,
  "transaction_id": 3,
  "amount": 50.00,
  "status": "completed",
  "external_reference": "MPESA-...",
  "phone": "258843330333",
  "message": "Depósito confirmado. Saldo atualizado."
}

✅ Depósito confirmado manualmente!
"""


# ============================================================================
# PASSO 6: Testes de Erro (Tratamento)
# ============================================================================

"""
6.1 Tentar confirmar depósito 2 vezes
```bash
# Primeira confirmação (sucesso)
curl -X POST http://localhost:8000/wallet/deposits/2/confirm \
  -H "Authorization: Bearer $TOKEN"

# Segunda confirmação (erro)
curl -X POST http://localhost:8000/wallet/deposits/2/confirm \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada (400):
{
  "detail": "Depósito já confirmado"
}

✅ Sistema previne duplicação!
"""

"""
6.2 Tentar confirmar depósito inexistente
```bash
curl -X POST http://localhost:8000/wallet/deposits/99999/confirm \
  -H "Authorization: Bearer $TOKEN"
```

Resposta (404):
{
  "detail": "Pagamento não encontrado"
}

✅ Sistema valida IDs!
"""

"""
6.3 Tentar acessar wallet sem token
```bash
curl -X GET http://localhost:8000/wallet
```

Resposta (401):
{
  "detail": "Not authenticated"
}

✅ Sistema requer autenticação!
"""


# ============================================================================
# PASSO 7: Monitorar Logs
# ============================================================================

"""
7.1 Ver Logs do Backend
No terminal onde rodou 'python main.py', verá logs como:

INFO:     127.0.0.1:49328 - "POST /wallet/deposits HTTP/1.1" 201
INFO:controllers.wallet_controller:M-Pesa payment request: T... for 258843330333
INFO:controllers.wallet_controller:M-Pesa response: {...}
INFO:controllers.wallet_controller:Auto-confirming M-Pesa deposit for user 1 (dev mode)

Procure por:
- "M-Pesa payment request"
- "M-Pesa response"
- "Auto-confirming"
- "Deposit confirmed"
"""


# ============================================================================
# PASSO 8: Testar API via Postman/Insomnia
# ============================================================================

"""
8.1 Importar coleção

Criar em Postman:
- Request: POST http://localhost:8000/wallet/deposits
  - Auth: Bearer Token
  - Body: { "amount": 100, "method": "mpesa" }
  
- Request: GET http://localhost:8000/wallet
  - Auth: Bearer Token
  
- Request: GET http://localhost:8000/wallet/transactions
  - Auth: Bearer Token

8.2 Testar sequência de requisições
- Login → obter token
- POST /deposits → obter payment_id
- GET /wallet → verificar saldo
- GET /transactions → ver histórico
"""


# ============================================================================
# RESUMO DE TESTES
# ============================================================================

"""
✅ Testes Básicos
- [x] Obter saldo (deve iniciar em 0)
- [x] Criar depósito (deve criar Payment + Transaction)
- [x] Verificar saldo atualizado

✅ Testes Auto-Confirmação
- [x] Depósito com status "completed" automaticamente
- [x] Saldo creditado imediatamente

✅ Testes Modo Produção
- [x] Depósito com status "pending"
- [x] Confirmação via callback
- [x] Confirmação manual
- [x] Saldo creditado após confirmação

✅ Testes de Erro
- [x] Não permite confirmar 2 vezes
- [x] Retorna 404 para ID inexistente
- [x] Requer autenticação

✅ Documentação
- [x] docs/wallet.md
- [x] WALLET_README.md
- [x] Este guia prático
"""


# ============================================================================
# COMANDOS RÁPIDOS (copy-paste)
# ============================================================================

"""
# Set token (após login)
TOKEN="seu_token_aqui"

# Obter saldo
curl -s http://localhost:8000/wallet \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Fazer depósito
curl -s -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "method": "mpesa"}' | python -m json.tool

# Listar transações
curl -s http://localhost:8000/wallet/transactions \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Simular callback
curl -s -X POST http://localhost:8000/wallet/mpesa-callback \
  -H "Content-Type: application/json" \
  -d '{
    "output_ConversationID": "123",
    "output_ResponseCode": "INS0",
    "output_ResponseDesc": "Success",
    "input_ThirdPartyReference": "ABC",
    "input_TransactionReference": "T123"
  }' | python -m json.tool
"""
