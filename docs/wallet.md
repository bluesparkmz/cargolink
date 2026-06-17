# Sistema de Wallet com M-Pesa

## Visão Geral

O sistema de wallet permite que os utilizadores façam depósitos via M-Pesa (Moçambique). A implementação suporta:

- **Depósito via M-Pesa**: Requisição POST para a API Mpesa
- **Confirmação via Callback**: Webhook que recebe confirmação do Mpesa
- **Modo Desenvolvimento**: Auto-confirmação para testes
- **Modo Produção**: Aguarda callback do Mpesa para confirmar

## Endpoints

### 1. GET `/wallet`
**Autenticação**: Requerida (token JWT)

Retorna o saldo atual da carteira do utilizador.

**Resposta**:
```json
{
  "available_balance": 1500.00,
  "pending_balance": 0.00,
  "blocked_balance": 0.00,
  "currency": "MT"
}
```

### 2. POST `/wallet/deposits`
**Autenticação**: Requerida (token JWT)

Inicia um novo depósito via M-Pesa.

**Corpo da Requisição**:
```json
{
  "amount": 100.00,
  "phone": "258843330333",
  "method": "mpesa"
}
```

**Parâmetros**:
- `amount` (obrigatório): Valor a depositar (MT) - máximo 5.000.000
- `phone` (opcional): Número de telefone do cliente. Se omitido, usa o telefone do utilizador
- `method` (obrigatório): "mpesa"

**Resposta** (Status 201):
```json
{
  "payment_id": 123,
  "transaction_id": 456,
  "amount": 100.00,
  "status": "pending",
  "external_reference": "MPESA-ABC123DEF456",
  "phone": "258843330333",
  "message": "Depósito registado. Aguarde confirmação M-Pesa no telemóvel."
}
```

**Comportamento**:
- **Em desenvolvimento** (`AUTO_CONFIRM_MPESA_DEPOSITS=true`):
  - A resposta terá status "completed"
  - O saldo será creditado imediatamente
  
- **Em produção** (`AUTO_CONFIRM_MPESA_DEPOSITS=false`):
  - A resposta terá status "pending"
  - O M-Pesa enviará um callback para confirmar
  - O saldo será creditado apenas após confirmação

### 3. POST `/wallet/deposits/{payment_id}/confirm`
**Autenticação**: Requerida (token JWT)

Confirma um depósito pendente manualmente (para testes ou em casos de erro).

**Parâmetros**:
- `payment_id` (URL): ID do pagamento

**Resposta**:
```json
{
  "payment_id": 123,
  "transaction_id": 456,
  "amount": 100.00,
  "status": "completed",
  "external_reference": "MPESA-ABC123DEF456",
  "phone": "258843330333",
  "message": "Depósito confirmado. Saldo atualizado."
}
```

### 4. GET `/wallet/transactions`
**Autenticação**: Requerida (token JWT)

Lista todas as transações (movimentos) da carteira.

**Query Parameters**:
- `limit` (opcional): Número máximo de resultados (padrão: 50, máximo: 200)
- `offset` (opcional): Paginação (padrão: 0)

**Resposta**:
```json
[
  {
    "id": 456,
    "transaction_type": "deposit",
    "amount": 100.00,
    "status": "completed",
    "reference": "MPESA-ABC123DEF456",
    "description": "Depósito MPESA via 258843330333",
    "created_at": "2026-06-17T10:30:00Z"
  }
]
```

### 5. POST `/wallet/mpesa-callback`
**Autenticação**: Não requerida

Webhook chamado pelo servidor M-Pesa para confirmar/rejeitar pagamentos.

**Corpo da Requisição** (enviado por Mpesa):
```json
{
  "output_ConversationID": "12345678",
  "output_ResponseCode": "INS0",
  "output_ResponseDesc": "Success",
  "input_ThirdPartyReference": "H5QZ68",
  "input_TransactionReference": "T12344C"
}
```

**Resposta**:
```json
{
  "status": "success",
  "message": "Depósito confirmado",
  "payment_id": 123
}
```

## Fluxo de Depósito

### Modo Desenvolvimento (AUTO_CONFIRM_MPESA_DEPOSITS=true)

```
1. Cliente POST /wallet/deposits
   ↓
2. Backend cria Payment (pending) e Transaction (pending)
   ↓
3. Backend faz requisição a Mpesa
   ↓
4. Backend auto-confirma (simula callback)
   ↓
5. Status muda para "completed"
   ↓
6. Saldo creditado na carteira
```

### Modo Produção (AUTO_CONFIRM_MPESA_DEPOSITS=false)

```
1. Cliente POST /wallet/deposits
   ↓
2. Backend cria Payment (pending) e Transaction (pending)
   ↓
3. Backend faz requisição a Mpesa
   ↓
4. Resposta: "Aguarde confirmação M-Pesa no telemóvel"
   ↓
5. Mpesa envia SMS ao telemóvel
   ↓
6. Cliente confirma no telemóvel
   ↓
7. Mpesa POST /wallet/mpesa-callback
   ↓
8. Backend confirma pagamento
   ↓
9. Saldo creditado na carteira
```

## Variáveis de Ambiente

### Configuração M-Pesa

Adicionar ao `.env`:

```bash
# M-Pesa Sandbox (padrão)
MPESA_HOST=https://api.sandbox.vm.co.mz

# Bearer token do Mpesa (sandbox fornecido)
MPESA_BEARER_TOKEN=UELjHuIUTK0VelJ68L4gx95py5nLmoMhCL0R2iL/Q7N0IOzqmDS/MD6vvfeb6koVeKlmZoY/ritM44pY7g4TQKhKNm/CI7UwWgwkENIAUlV0m6mhU8KaSVILG8mmJsk21wJEJxLjNJQnLDyn+hQfMh/DxEOv4ZCid0crCRFtC/H6FWR9aQHnfbTMsnZVreKWDWFGbElQzVFAFfLHocC5Z+vv1ehY5uF92nUFuI7jnCHEsTsXWTpaa8BgXA93Qv/dVpyoCBM3fonCJ1OioIV04A3lkseuWX+6CpOnQVoHl/bKYlNwjd7yArRI7xlwWtbxt7Wz+RNJZDd1gzP2LnyXY++8z/naZ/sPTx56wHweYHJoeiveeKwWMUZ9k6pgF8Ka+ejRjl9U04AZQ4MFmabXKvf6sP+/ZHtcoGrQK7e9H9L5rzGtfp2fdCVRt/KpxHqfYGJWhpstmvAEQfsV+hPbVER4GSO3Rf+a+ECbaWbp7dBbOCkYXbb9dpvcAeZd6ACF4y8o9ClUPm1o3gOq1h9dB7jKbL4TAyBC1pTmtAefnTHv3gj2z0iRDquuDI7cMrcoL/3IEesYBouuR849/QA91Vo+M7YRdHjOnDys/5oYyVlMXPpm3bMxprS+hwiyfHlRNiA6rIGyJZNpuFummIgjmSb90bczaWmAz7WsOSYqZ4g=

# Código do provedor de serviço
MPESA_SERVICE_PROVIDER_CODE=171717

# AUTO_CONFIRM (desenvolvimento: true, produção: false)
AUTO_CONFIRM_MPESA_DEPOSITS=false
```

## Estrutura de Dados

### Wallet
```python
class Wallet:
    id: int
    user_id: int
    available_balance: Decimal        # Saldo disponível
    pending_balance: Decimal          # Aguardando confirmação
    blocked_balance: Decimal          # Bloqueado por motivos legais
    updated_at: datetime
```

### Payment
```python
class Payment:
    id: int
    user_id: int
    method: str                       # "mpesa"
    phone: str                        # Telemóvel do cliente
    amount: Decimal                   # Valor
    status: str                       # "pending", "completed", "failed"
    external_reference: str           # "MPESA-..."
    gateway_response: dict            # Resposta JSON do Mpesa
    created_at: datetime
```

### Transaction
```python
class Transaction:
    id: int
    wallet_id: int
    transaction_type: str             # "deposit", "withdrawal", etc
    amount: Decimal
    status: str                       # "pending", "completed", "failed"
    reference: str                    # Externa (payment_id)
    description: str
    created_at: datetime
```

## Testes

### 1. Teste com Auto-Confirmação (Desenvolvimento)

```bash
# Fazer depósito (será auto-confirmado)
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "phone": "258843330333", "method": "mpesa"}'

# Resposta (status 201):
# {
#   "status": "completed",
#   "message": "Depósito confirmado (modo desenvolvimento). Saldo atualizado."
# }
```

### 2. Teste Manual em Produção

```bash
# 1. Iniciar depósito
curl -X POST http://localhost:8000/wallet/deposits \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "phone": "258843330333", "method": "mpesa"}'

# Resposta (status 201):
# {
#   "payment_id": 123,
#   "status": "pending",
#   "message": "Depósito registado. Aguarde confirmação M-Pesa no telemóvel."
# }

# 2. Confirmar manualmente
curl -X POST http://localhost:8000/wallet/deposits/123/confirm \
  -H "Authorization: Bearer <token>"

# Resposta:
# {
#   "status": "completed",
#   "message": "Depósito confirmado. Saldo atualizado."
# }
```

## Tratamento de Erros

### Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| 404 Payment not found | Pagamento não existe | Verificar payment_id |
| 403 Forbidden | Utilizador não é dono do pagamento | Usar seu próprio token |
| 400 Deposit already confirmed | Tentativa de confirmar 2x | Não é possível confirmar novamente |
| 400 Deposit failed | Mpesa rejeitou o pagamento | Iniciar novo depósito |
| 502 Bad Gateway | Erro na integração com Mpesa | Verificar credenciais do Mpesa |

## Callbacks do Mpesa

Para receber callbacks do Mpesa em produção:

1. **Configurar URL pública**: A URL `https://seu-dominio.com/wallet/mpesa-callback` deve ser registada no Mpesa
2. **Validar assinatura** (opcional): Implementar validação de assinatura se Mpesa exigir
3. **Idempotência**: Processar callbacks apenas uma vez (usar conversation_id)

## Próximas Funcionalidades

- [ ] Levantamento de fundos (withdrawal)
- [ ] Histórico detalhado com filtros
- [ ] Saque para conta bancária
- [ ] Integração com outras formas de pagamento
- [ ] Relatórios financeiros
- [ ] Transações recorrentes
