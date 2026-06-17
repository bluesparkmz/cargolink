# 🔐 Fluxo de Confirmação M-Pesa com PIN

## ✅ Status Atual (Polling Implementado)

O sistema **agora aguarda confirmação do PIN do utilizador** fazendo polling automático:

- **Produção**: Backend faz polling (10 tentativas, 6 segundos cada = até 60 segundos)
- **Desenvolvimento**: Configure `AUTO_CONFIRM_MPESA_DEPOSITS=true` para auto-confirmar (testes rápidos)
- **Segurança**: Referência única (`third_party_ref`) para validar cada pagamento
- **Resultado**: Se PIN confirmado → Credita imediatamente. Se timeout → Aguarda callback

## Como Funciona o M-Pesa (Produção com Polling)

### Sequência de Eventos

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. UTILIZADOR INICIA DEPÓSITO (Frontend)                        │
│    POST /wallet/deposits                                         │
│    {amount: 100, phone: "258843330333", method: "mpesa"}        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. BACKEND FAZ REQUISIÇÃO AO M-PESA (Backend)                   │
│    POST https://api.sandbox.vm.co.mz/ipg/v1x/c2bPayment...      │
│    com Bearer token + third_party_ref                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. M-PESA RESPONDE IMEDIATAMENTE (M-Pesa)                      │
│    Status: INS0 (aceito, em processamento)                      │
│    Message: "Confirme no seu telemóvel"                         │
│    ConversationID: "12345678"                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼ (Backend já responde ao frontend)
┌──────────────────────────────────────────────────────────────────┐
│ 4. BACKEND INICIA POLLING AUTOMÁTICO (Backend)                  │
│    Polling: 10 tentativas × 6 segundos = até 60 segundos        │
│    Consulta: GET /ipg/v1x/queryTransactionStatus/               │
│    Procura: status = "success" ou "completed"                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. M-PESA ENVIA SMS COM PIN (M-Pesa → Utilizador)              │
│    "Código: 123456"                                              │
│    "Confirme no Banco"                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼ (Utilizador digita PIN no telemóvel)
┌──────────────────────────────────────────────────────────────────┐
│ 6. UTILIZADOR CONFIRMA PIN NO TELEMÓVEL (Utilizador)            │
│    Abre app Banco                                                │
│    Digita PIN                                                    │
│    Confirma pagamento                                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. M-PESA MUDA STATUS PARA SUCCESS (M-Pesa)                    │
│    Poll deteta: status = "success" ou "completed"               │
│    Resposta: output_ResponseCode = "INS-0" ✅                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. BACKEND CREDITA SALDO IMEDIATAMENTE (Backend)                │
│    Payment.status = "completed"                                  │
│    Wallet.available_balance += 100                              │
│    Transaction.status = "completed"                              │
│    ✅ Sem esperar por callback!                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 9. FRONTEND RECEBE RESPOSTA FINAL (Frontend)                    │
│    Response da requisição POST /wallet/deposits:                │
│    {                                                             │
│      "status": "completed",  ← JÁ CREDITADO!                   │
│      "payment_id": 123,                                          │
│      "amount": 100,                                              │
│      "message": "Depósito confirmado. Saldo atualizado."        │
│    }                                                             │
│    ✅ Nenhuma espera adicional necessária!                       │
└──────────────────────────────────────────────────────────────────┘
```

## Estados do Pagamento

| Estado | Quando | O Que Fazer |
|--------|--------|-----------|
| **pending** | Se polling timeout (10 tentativas) | Aguardar callback do M-Pesa |
| **completed** | Polling detecta status success/completed OU callback confirma | Saldo já creditado ✅ |
| **failed** | Se M-Pesa rejeita (fail/cancel/reject) | Mostrar erro, permitir novo tentativa |

## 🚀 Fluxo de Crédito

### Cenário 1: PIN Confirmado em até 60 segundos ✅

```
1. Frontend → POST /wallet/deposits
2. Backend → Requisição ao M-Pesa (INS0)
3. Backend → Inicia Polling (10 tentativas)
4. Utilizador → Confirma PIN no telemóvel
5. Poll #X → Detecta "success" ou "completed"
6. Backend → Credita imediatamente
7. Response → Status "completed" com saldo atualizado
8. Frontend → Mostra "Sucesso!" sem espera adicional
```

### Cenário 2: PIN Confirmado Depois de 60 segundos (ou polling falha)

```
1-7. [Polling completa sem encontrar status]
8. Response → Status "pending" + aviso "aguarde confirmação"
9. Backend → Continua aguardando callback do M-Pesa
10. M-Pesa → Envia callback após PIN confirmado
11. Callback Handler → Credita saldo
12. Frontend → Poll ou WebSocket detecta saldo aumentado
```

### Cenário 3: M-Pesa Rejeita PIN (fail/cancel/reject)

```
1-5. [Polling detecta "failed", "cancel", "reject" ou "expired"]
6. Backend → Marca Payment.status = "failed"
7. Response → Status "failed" + mensagem de erro
8. Frontend → Mostra "Pagamento rejeitado" + opção de retry
```

## ✅ Implementação de Segurança

### 1. **Referências Únicas por Pagamento**

Cada requisição ao M-Pesa usa 3 referências para máxima segurança:

```
transaction_ref (Backend)      → T{UUID}         (ex: TABC123DEF456789)
third_party_ref (M-Pesa)       → {UUID}          (ex: H5QZ68)  ← Usada no Poll
external_reference (Interno)   → MPESA-{UUID}    (ex: MPESA-XYZ789ABC123)
```

**Por que 3?**
- `transaction_ref`: ID único da transação no backend
- `third_party_ref`: Usada no polling para identificar o pagamento específico
- `external_reference`: Vincula pagamento à transação na carteira

### 2. **Validações no Polling**

```python
# Arquivo: controllers/wallet_controller.py

# Polling loop
for attempt in range(10):  # 10 × 6 segundos = até 60 segundos
    time.sleep(6)
    
    status_result = mpesa_client.query_payment_status(
        transaction_id=query_ref,
        third_party_reference=third_party_ref,  # ← Única referência
    )
    
    if status_result["success"]:
        status_desc = (status_result.get("transaction_status") or "").lower()
        resp_code = status_result.get("response_code", "")
        
        # ✅ Sucesso - Procura palavras-chave
        if resp_code == "INS-0" and any(
            kw in status_desc
            for kw in ["success", "completed", "done", "pago", "sucesso"]
        ):
            _complete_deposit(db, wallet, payment, transaction)  # Credita!
            break
        
        # ❌ Rejeição - Marcado como falha
        if any(kw in status_desc for kw in ["fail", "cancel", "reject", "expired"]):
            payment.status = "failed"
            break
```

### 3. **Validações no Callback (Fallback)**

Se polling não conseguir confirmar, o callback do M-Pesa ainda credita:

```python
def process_mpesa_callback(payload: dict):
    third_party_ref = payload.get("input_ThirdPartyReference")
    
    # ✅ Procura pagamento por referência específica (seguro!)
    payment = db.query(Payment).filter(
        Payment.mpesa_third_party_ref == third_party_ref
    ).first()
    
    # Validações:
    if payment.status != "pending":  # Previne confirmação dupla
        return {"status": "error"}
```

### 4. **Configuração por Ambiente**

```bash
# .env (Desenvolvimento)
AUTO_CONFIRM_MPESA_DEPOSITS=true  # Testes rápidos, sem M-Pesa

# .env (Produção)
AUTO_CONFIRM_MPESA_DEPOSITS=false  # ← Padrão seguro
```

### 5. **Timeout e Fallback**

```
Se Polling (60s) → Não confirmar
    ↓
Fica como "pending" 
    ↓
Aguarda Callback do M-Pesa
    ↓
Callback Handler → Credita saldo
```

## 📝 Resumo das Mudanças Implementadas

### Antes (Callback Only)
- ❌ Backend retornava "pending" imediatamente
- ❌ Frontend fazia polling para verificar saldo (esperava callback)
- ❌ Tempo até crédito: 5-15 minutos (depende do M-Pesa)
- ❌ Experiência: "Aguarde... carregando..."

### Depois (Polling + Callback)
- ✅ Backend faz polling automático (10 tentativas, 6s cada)
- ✅ Se PIN confirmado em 60s → Credita e retorna status "completed"
- ✅ Se timeout → Aguarda callback (como antes)
- ✅ Frontend não precisa fazer nada extra (resposta já tem status final)
- ✅ Tempo até crédito: Até 60 segundos (na maioria dos casos)
- ✅ Experiência: "Depósito confirmado! ✅"

## Implementação no Frontend

### ✅ Simples: Resposta Única

```typescript
// components/wallet/deposit-modal.tsx

const response = await walletService.createDeposit(amount, phone);

if (response.status === 'completed') {
  // ✅ Sucesso! Saldo já foi creditado
  setStep('success');
  await getWallet();  // Opcional: recarregar (saldo já está atualizado)
} else if (response.status === 'pending') {
  // ⏳ Ainda aguardando confirmação do PIN
  // (cenário raro: timeout de 60 segundos)
  setStep('waiting_pin');
  startPolling();  // Poll para saldo aumentado
} else if (response.status === 'failed') {
  // ❌ M-Pesa rejeitou
  setStep('error');
}
```

### ✅ Opção: Polling Adicional (Extra Safety)

```typescript
// Se preferir um layer adicional de segurança

async function waitForDepositConfirmation(paymentId: number) {
  const maxAttempts = 120; // 10 minutos (120 × 5 segundos)
  let attempts = 0;

  while (attempts < maxAttempts) {
    attempts++;
    
    try {
      // Verificar saldo a cada 5 segundos
      const wallet = await walletService.getWallet();
      
      // Se saldo aumentou, depósito foi confirmado
      if (wallet.available_balance > previousBalance) {
        return { success: true, wallet };
      }
    } catch (error) {
      console.error('Erro ao verificar:', error);
    }
    
    // Aguardar 5 segundos antes da próxima verificação
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  return { success: false, timeout: true };
}
```

### Opção 2: WebSocket (Melhor Experiência)

```typescript
// Em produção, usar WebSocket para notificações em tempo real
const ws = new WebSocket('wss://seu-dominio.com/wallet/subscribe');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'deposit_confirmed') {
    // Atualizar UI imediatamente
    setDepositStatus('completed');
    await getWallet();
  }
};
```

## Output do Script de Teste

```bash
cd d:\CargoLink\ App\cargolink_api
python scripts/test_mpesa_flow.py
```

Esperado:

```
[201] POST /wallet/deposits
{
  "payment_id": 1,
  "transaction_id": 1,
  "amount": 100.0,
  "status": "completed",    ← (em dev, auto-confirmado)
  "external_reference": "MPESA-ABC123DEF456",
  "phone": "258843330333",
  "message": "Depósito confirmado (modo desenvolvimento). Saldo atualizado."
}

📊 Análise do Status:
  🟢 CONFIRMADO (Modo Desenvolvimento)
  ✓ Depósito foi confirmado automaticamente
  ✓ Saldo já foi creditado

💰 Saldo antes: 0 MT
💰 Saldo depois: 100 MT
✅ CREDITADO: +100 MT
```

## Alterações Necessárias no Frontend

### 1. **DepositModal: Adicionar Estados**

```typescript
type DepositStep = 'input' | 'confirm' | 'processing' | 'waiting_pin' | 'success' | 'error';

export function DepositModal() {
  const [step, setStep] = useState<DepositStep>('input');
  const [depositStatus, setDepositStatus] = useState<'pending' | 'completed' | 'failed'>();
  const [isWaitingPin, setIsWaitingPin] = useState(false);
}
```

### 2. **Adicionar Tela de Espera**

```typescript
{step === 'waiting_pin' && (
  <>
    <View style={styles.waitingBox}>
      <LottieView
        source={require('@/assets/loading-dots.json')}
        autoPlay
        loop
      />
      <Text style={styles.waitingTitle}>Confirme no seu telemóvel</Text>
      <Text style={styles.waitingMessage}>
        Você receberá um SMS com um código. Digite o código para confirmar o pagamento.
      </Text>
      <View style={styles.timer}>
        <Text style={styles.timerText}>{formatTime(timeRemaining)}</Text>
      </View>
    </View>
  </>
)}
```

### 3. **Implementar Polling**

```typescript
async function handleDepositConfirm() {
  setStep('processing');
  
  try {
    const response = await walletService.createDeposit(amount, phone);
    
    if (response.status === 'pending') {
      // Modo produção: aguardar PIN
      setStep('waiting_pin');
      setDepositStatus('pending');
      
      const confirmed = await pollForConfirmation(response.payment_id);
      
      if (confirmed) {
        setStep('success');
        setDepositStatus('completed');
        await getWallet();
      } else {
        setStep('error');
        Alert.alert('Timeout', 'Depósito não foi confirmado');
      }
    } else if (response.status === 'completed') {
      // Modo desenvolvimento: auto-confirmado
      setStep('success');
      setDepositStatus('completed');
      await getWallet();
    }
  } catch (error) {
    setStep('error');
    Alert.alert('Erro', error.message);
  }
}

async function pollForConfirmation(paymentId: number): Promise<boolean> {
  const maxAttempts = 120; // 10 minutos
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const wallet = await walletService.getWallet();
      
      // Se saldo aumentou, sucesso!
      if (wallet.available_balance > previousBalance) {
        return true;
      }
    } catch (error) {
      console.error('Poll error:', error);
    }
    
    // Aguardar 5 segundos
    await new Promise(resolve => setTimeout(resolve, 5000));
    setTimeRemaining(prev => prev - 5);
  }
  
  return false;
}
```

## Testar Fluxo Completo

### Modo Desenvolvimento

```bash
# 1. Iniciar backend com AUTO_CONFIRM_MPESA_DEPOSITS=true
cd d:\CargoLink\ App\cargolink_api
python main.py

# 2. Em outro terminal, rodar teste
python scripts/test_mpesa_flow.py

# Resultado esperado: Status "completed" imediatamente
```

### Modo Produção (Simulado)

```bash
# 1. Alterar no .env
AUTO_CONFIRM_MPESA_DEPOSITS=false

# 2. Reiniciar backend
python main.py

# 3. Rodar teste
python scripts/test_mpesa_flow.py

# Resultado esperado:
# 1. Status "pending" imediatamente
# 2. Script simula callback do M-Pesa
# 3. Status muda para "completed"
```

## Fluxo Actual vs Esperado

### ❌ ATUAL (Incompleto)

```
Utilizador → [Depositar] → Modal fecha
Saldo: ??? (não atualiza)
```

### ✅ ESPERADO (Correto)

```
Utilizador → [Depositar] 
  ↓
Modal mostra "Input"
  ↓
Utilizador preenche dados
  ↓
Modal mostra "Confirmação"
  ↓
Utilizador confirma
  ↓
POST /wallet/deposits (Status: "pending")
  ↓
Modal mostra "Aguarde SMS"
  ↓
Frontend faz polling GET /wallet
  ↓
M-Pesa envia callback (backend recebe)
  ↓
Polling detecta saldo aumentado
  ↓
Modal mostra "Sucesso!"
  ↓
Saldo atualizado
```

## Próximos Passos

1. ✅ **Script de Teste**: [`scripts/test_mpesa_flow.py`] - já criado
2. 🔄 **Atualizar DepositModal**: Adicionar tela de espera com timer
3. 🔄 **Implementar Polling**: Verificar saldo a cada 5s
4. 🔄 **Estados de Erro**: Timeout, erro de conexão, etc
5. 🔄 **WebSocket (Opcional)**: Para notificações em tempo real

## Comandos Rápidos

```bash
# Testar fluxo
cd d:\CargoLink\ App\cargolink_api
python scripts/test_mpesa_flow.py

# Ver logs do backend
tail -f debug.log

# Verificar M-Pesa response
curl -X POST http://localhost:8000/wallet/mpesa-callback \
  -H "Content-Type: application/json" \
  -d '{"output_ConversationID": "123", "output_ResponseCode": "INS0", ...}'
```
