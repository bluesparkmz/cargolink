# M-Pesa Sandbox Setup

## Problema: Erro 403 Forbidden

Se você receber o seguinte erro ao tentar fazer um depósito:
```
Client error '403 Forbidden' for url 'https://api.sandbox.vm.co.mz/ipg/v1x/c2bPayment/singleStage/'
```

Significa que o **Bearer Token do M-Pesa expirou ou é inválido**.

## Solução: Renovar o Token

### 1. Aceda ao M-Pesa Developer Portal
- URL: https://developer.mpesa.vm.co.mz
- Faça login com suas credenciais

### 2. Gere um novo Bearer Token
- Vá para **API Keys** ou **Credentials**
- Gere um novo token de acesso
- Copie o token completo

### 3. Configure a Variável de Ambiente

#### Option A: Arquivo `.env`
```bash
MPESA_BEARER_TOKEN="SEU_NOVO_TOKEN_COMPLETO_AQUI"
```

#### Option B: Variável de Sistema (Production)
```bash
export MPESA_BEARER_TOKEN="SEU_NOVO_TOKEN_COMPLETO_AQUI"
```

#### Option C: Docker/Deployment
```yaml
environment:
  MPESA_BEARER_TOKEN: "SEU_NOVO_TOKEN_COMPLETO_AQUI"
```

### 4. Reinicie o Servidor
```bash
# Termina o servidor
Ctrl+C

# Reinicia
python -m uvicorn main:app --reload
```

### 5. Teste a Requisição
Use o Postman ou cURL para testar:

```bash
curl -X POST https://api.sandbox.vm.co.mz/ipg/v1x/c2bPayment/singleStage/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_NOVO_TOKEN" \
  -H "Origin: developer.mpesa.vm.co.mz" \
  -d '{
    "input_TransactionReference": "T12344C",
    "input_CustomerMSISDN": "258843330333",
    "input_Amount": "10",
    "input_ThirdPartyReference": "NQXY1H",
    "input_ServiceProviderCode": "171717"
  }'
```

**Resposta esperada:**
```json
{
  "output_ResponseCode": "INS-0",
  "output_ResponseDesc": "Requested accepted.",
  "output_TransactionID": "...",
  "output_ConversationID": "..."
}
```

## Configurações M-Pesa

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `MPESA_HOST` | `https://api.sandbox.vm.co.mz` | Endpoint da API |
| `MPESA_BEARER_TOKEN` | `seu_token_aqui` | Token de autenticação |
| `MPESA_SERVICE_PROVIDER_CODE` | `171717` | Código do provedor de serviços |

## Fluxo de Depósito

1. **Frontend** → POST `/wallet/deposits` com amount e phone
2. **Backend** → Faz requisição assíncrona ao M-Pesa (sem bloquear)
3. **Resposta**:
   - ✅ **INS-0 (Aceito)** → Retorna `status: "pendente"`, aguarda callback
   - ❌ **Outro código** → Retorna `status: "falhou"`
   - ❌ **Erro de conexão** → Retorna `status: "falhou"` com mensagem

4. **M-Pesa Callback** → POST `/mpesa-callback` (webhook)
5. **Backend** → Credita saldo se sucesso

## Testing

Para testar em desenvolvimento com confirmação automática:

```bash
# Arquivo .env
AUTO_CONFIRM_MPESA_DEPOSITS=true
```

Assim, depósitos são confirmados imediatamente sem esperar callback real.

## Suporte

- **M-Pesa Docs**: https://developer.mpesa.vm.co.mz/api-documentation
- **Token Issues**: Contacte M-Pesa Support
- **App Issues**: Verifique logs em `logs/cargolink_api.log`
