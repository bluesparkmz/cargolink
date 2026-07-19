# Documentacao de Propostas

Esta documentacao cobre a parte de propostas no CargoLink: envio pela empresa,
listagem de "minhas propostas", propostas recebidas pelo cliente, detalhe,
aceite e recusa.

## Papel das propostas

A proposta e a oferta feita por uma empresa transportadora para transportar uma
carga publicada por um cliente.

Fluxo principal:

```text
1. Cliente publica carga
2. Empresa envia proposta
3. Empresa acompanha em Minhas propostas
4. Cliente ve propostas recebidas
5. Cliente aceita ou recusa
6. Ao aceitar, o sistema cria uma viagem
```

## Modelo usado

Tabela principal:

```text
load_proposals
```

Campos principais:

```text
id
load_id
company_id
driver_id
vehicle_id
valor_proposto
mensagem
status
created_at
```

Status atuais:

```text
pendente
em_negociacao
aceite
recusada
```

## Modelo de negociacao

Negociacao por contrapropostas com regras de negocio:

```text
loads.valor              = valor indicado pelo dono da carga (referencia/orcamento)
load_proposals.valor     = oferta inicial da empresa (>= valor da carga, se existir)
proposal_negotiations    = ajustes depois da proposta inicial
```

Regras de valor:

```text
1. Empresa envia proposta inicial >= valor indicado na carga
2. Cliente pode aceitar, recusar ou contrapropor um valor MENOR
3. Empresa responde com valor MAIOR que a oferta do cliente
4. Empresa nao pode ultrapassar a sua proposta inicial
5. O ciclo repete ate aceite ou recusa
```

Exemplo:

```text
Carga publicada:     30.000 MT (valor indicado)
Empresa propoe:      32.000 MT
Cliente contrapropoe: 28.000 MT
Empresa contrapropoe: 29.000 MT
Cliente aceita:      29.000 MT -> viagem criada
```

Tabela:

```text
proposal_negotiations
```

Campos:

```text
id
proposal_id
sender_id
valor
mensagem
status
created_at
```

Status dos itens de negociacao:

```text
pendente
aceite
recusada
substituida
```

## Autenticacao

Todas as rotas exigem token Bearer.

```http
Authorization: Bearer <token>
```

## Enviar proposta

Endpoint novo:

```http
POST /proposals/loads/{load_id}
```

Permissao:

```text
empresa
```

Body:

```json
{
  "proposed_value": 24500,
  "message": "Temos camiao disponivel para esta rota.",
  "driver_id": 2,
  "vehicle_id": 5
}
```

Regras:

- A carga precisa estar com status `disponivel`.
- O utilizador autenticado precisa ser `empresa`.
- O motorista precisa pertencer a empresa.
- O camiao precisa pertencer a empresa.
- Se o camiao ja tiver motorista atribuido, deve ser o mesmo motorista da proposta.
- A mesma empresa nao pode enviar duas propostas para a mesma carga.

Resposta:

```json
{
  "id": 9,
  "load_id": 4,
  "company_id": 1,
  "driver_id": 2,
  "vehicle_id": 5,
  "proposed_value": 24500,
  "message": "Temos camiao disponivel para esta rota.",
  "status": "pendente",
  "created_at": "2026-05-25T10:30:00",
  "load": {
    "id": 4,
    "code": "CL24562",
    "load_type": "mercadoria_geral",
    "load_name": "Produtos embalados",
    "origin": "Maputo",
    "destination": "Nampula",
    "value": 25000,
    "negotiable": true,
    "status": "disponivel",
    "departure_date": "2026-06-15"
  },
  "company": {
    "id": 1,
    "company_name": "TransMoz Transportes",
    "average_rating": 0,
    "total_trips": 0,
    "verified": false
  },
  "driver": {
    "id": 2,
    "name": "Joao Motorista",
    "average_rating": 0,
    "total_trips": 0,
    "available": true
  },
  "vehicle": {
    "id": 5,
    "plate": "ABC-123-MP",
    "brand": "Volvo",
    "model_name": "FH",
    "vehicle_type": "Camiao basculante",
    "tonnage_capacity": 30,
    "status": "disponivel"
  }
}
```

Rota antiga equivalente, mantida por compatibilidade:

```http
POST /loads/{load_id}/proposals
```

## Minhas propostas

Lista as propostas enviadas pela empresa autenticada.

```http
GET /proposals/me
```

Permissao:

```text
empresa
```

Filtro opcional:

```http
GET /proposals/me?status=pendente
GET /proposals/me?status=aceite
GET /proposals/me?status=recusada
```

Rota antiga equivalente:

```http
GET /companies/me/proposals
```

Observacao:

```text
/proposals/me retorna dados detalhados da carga, empresa, motorista e camiao.
/companies/me/proposals retorna o formato simples antigo.
```

## Propostas recebidas

Lista propostas recebidas nas cargas do cliente autenticado.

```http
GET /proposals/received
```

Permissao:

```text
cliente
```

Filtro opcional:

```http
GET /proposals/received?status=pendente
GET /proposals/received?status=aceite
GET /proposals/received?status=recusada
```

Tambem existe a rota antiga para uma carga especifica:

```http
GET /loads/{load_id}/proposals
```

## Detalhe de uma proposta

```http
GET /proposals/{proposal_id}
```

Permissao:

```text
cliente dono da carga
empresa dona da proposta
motorista indicado na proposta
admin
```

## Aceitar proposta

Endpoint novo:

```http
POST /proposals/{proposal_id}/accept
```

Permissao:

```text
cliente dono da carga
```

Body:

```text
sem body
```

Efeito:

- A proposta escolhida fica `aceite`.
- As outras propostas pendentes da mesma carga ficam `recusada`.
- A carga fica com status `aceite`.
- O sistema cria uma viagem com `company_id`, `driver_id` e `vehicle_id` da proposta.

Rota antiga equivalente:

```http
POST /loads/{load_id}/proposals/{proposal_id}/accept
```

## Recusar proposta

Endpoint novo:

```http
POST /proposals/{proposal_id}/reject
```

Permissao:

```text
cliente dono da carga
```

Body:

```text
sem body
```

Efeito:

```text
load_proposals.status = "recusada"
```

Rota antiga equivalente:

```http
POST /loads/{load_id}/proposals/{proposal_id}/reject
```

## Negociacao

Negociacao e feita por contrapropostas fechadas sobre uma proposta existente.

Fluxo:

```text
1. Empresa envia proposta inicial
2. Cliente aceita, recusa ou sugere outro valor
3. Empresa aceita, recusa ou sugere outro valor
4. O ciclo repete ate alguem aceitar ou recusar
```

### Ver historico de negociacao

```http
GET /proposals/{proposal_id}/negotiations
```

Permissao:

```text
cliente dono da carga
empresa dona da proposta
motorista indicado na proposta
admin
```

### Sugerir outro valor

```http
POST /proposals/{proposal_id}/negotiations
```

Permissao:

```text
cliente dono da carga
empresa dona da proposta
```

Body:

```json
{
  "amount": 24800,
  "message": "Consigo fechar neste valor."
}
```

Regras:

- A carga precisa aceitar negociacao (`negotiable = true`).
- A proposta nao pode estar `aceite` nem `recusada`.
- **Cliente**: contraproposta deve ser **inferior** ao valor em vigor.
- **Empresa**: contraproposta deve ser **superior** a oferta do cliente e **nao pode ultrapassar** a proposta inicial.
- A empresa nao pode iniciar nova contraproposta sem resposta do cliente.
- Quem enviou a ultima contraproposta pendente precisa aguardar a outra parte.
- Ao criar contraproposta, a proposta fica `em_negociacao`.

### Aceitar contraproposta

```http
POST /proposals/{proposal_id}/negotiations/{negotiation_id}/accept
```

Permissao:

```text
cliente dono da carga
empresa dona da proposta
```

Efeito:

- A contraproposta fica `aceite`.
- `load_proposals.valor_proposto` passa a ser o valor aceite.
- A proposta fica `aceite`.
- As outras propostas pendentes/em negociacao da mesma carga ficam `recusada`.
- A carga fica `aceite`.
- O sistema cria uma viagem.

### Recusar contraproposta

```http
POST /proposals/{proposal_id}/negotiations/{negotiation_id}/reject
```

Permissao:

```text
cliente dono da carga
empresa dona da proposta
```

Efeito:

- A contraproposta fica `recusada`.
- A proposta fica `recusada`.
- A negociacao encerra.

Exemplo:

```text
1. Empresa envia proposta: 28.000 MT
2. Cliente sugere: 24.500 MT
3. Empresa sugere: 25.000 MT
4. Cliente aceita 25.000 MT
5. Sistema cria viagem
```

## Resumo das rotas

```text
POST /proposals/loads/{load_id}
GET  /proposals/me
GET  /proposals/received
GET  /proposals/{proposal_id}
GET  /proposals/{proposal_id}/negotiations
POST /proposals/{proposal_id}/negotiations
POST /proposals/{proposal_id}/negotiations/{negotiation_id}/accept
POST /proposals/{proposal_id}/negotiations/{negotiation_id}/reject
POST /proposals/{proposal_id}/accept
POST /proposals/{proposal_id}/reject
```

Rotas antigas ainda disponiveis:

```text
POST /loads/{load_id}/proposals
GET  /loads/{load_id}/proposals
POST /loads/{load_id}/proposals/{proposal_id}/accept
POST /loads/{load_id}/proposals/{proposal_id}/reject
GET  /companies/me/proposals
```
