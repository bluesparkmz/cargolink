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
aceite
recusada
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

Neste momento ainda nao existe uma tabela propria de negociacao ou
contrapropostas.

O que existe hoje:

- `Load.negotiable` indica se a carga aceita negociacao.
- `LoadProposal.proposed_value` guarda o valor proposto.
- `LoadProposal.message` guarda a mensagem inicial da empresa.
- `/messages/loads/{load_id}` permite conversa livre entre as partes.

Para uma negociacao completa no futuro, o ideal sera criar uma tabela propria,
por exemplo:

```text
proposal_negotiations
```

Com campos como:

```text
proposal_id
sender_id
amount
delivery_days
message
status
created_at
```

## Resumo das rotas

```text
POST /proposals/loads/{load_id}
GET  /proposals/me
GET  /proposals/received
GET  /proposals/{proposal_id}
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
