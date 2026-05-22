# Documentacao do Cliente

Esta documentacao cobre apenas a parte do **cliente** no CargoLink.

## Papel do cliente

O cliente e a pessoa ou empresa que precisa transportar uma carga.

Responsabilidades principais:

- Criar conta como cliente.
- Atualizar perfil.
- Publicar cargas.
- Adicionar imagens da carga.
- Ver cargas publicadas.
- Ver propostas recebidas das empresas transportadoras.
- Aceitar ou recusar propostas.
- Acompanhar a viagem.
- Confirmar entrega da carga.

Regra principal:

```text
Cliente publica e contrata.
Empresa negocia e fornece transporte.
Motorista executa a viagem.
```

## Modelo de dados

### User

O cliente tambem e um utilizador do sistema.

```text
users.tipo = "cliente"
```

### Client

Perfil especifico do cliente.

Tabela:

```text
clients
```

Campos principais:

```text
id
user_id
tipo_cliente
nome_empresa
nuit
endereco
cidade
provincia
created_at
```

### Relacoes

```text
Client 1 -> N Loads
Load 1 -> N LoadImages
Load 1 -> N LoadProposals
Load 1 -> 1 Trip
```

## Autenticacao

Todas as rotas do cliente exigem token Bearer.

Header:

```http
Authorization: Bearer <token>
```

Para rotas de gestao do proprio cliente, o utilizador autenticado precisa ter:

```text
user_type = "cliente"
```

## Registar cliente

Endpoint:

```http
POST /auth/register
```

Body para cliente individual:

```json
{
  "name": "Maria Cliente",
  "email": "maria@email.com",
  "password": "123456",
  "user_type": "cliente",
  "phone": "840000010",
  "client_type": "individual",
  "city": "Maputo",
  "state": "Maputo"
}
```

Body para cliente empresarial:

```json
{
  "name": "Compras Matola",
  "email": "compras@empresa.co.mz",
  "password": "123456",
  "user_type": "cliente",
  "phone": "840000011",
  "client_type": "empresa",
  "company_name": "Empresa Cliente Lda",
  "city": "Matola",
  "state": "Maputo"
}
```

Resultado:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

Ao registar com `user_type = "cliente"`, o sistema cria:

```text
users
clients
wallets
```

## Perfil do cliente

### Ver perfil autenticado

```http
GET /clients/me
```

Permissao:

```text
cliente
```

Resposta:

```json
{
  "id": 1,
  "client_type": "individual",
  "company_name": null,
  "tax_id": null,
  "address": null,
  "city": "Maputo",
  "state": "Maputo",
  "user": {
    "id": 2,
    "name": "Maria Cliente",
    "phone": "840000010",
    "email": "maria@email.com",
    "profile_photo": null,
    "verified": false
  }
}
```

### Atualizar perfil

```http
PATCH /clients/me
```

Permissao:

```text
cliente
```

Body:

```json
{
  "client_type": "empresa",
  "company_name": "Empresa Cliente Lda",
  "tax_id": "400000010",
  "address": "Av. Eduardo Mondlane, Maputo",
  "city": "Maputo",
  "state": "Maputo"
}
```

## Estatisticas e atividades

### Ver estatisticas do cliente

```http
GET /clients/me/stats
```

Permissao:

```text
cliente
```

Resposta:

```json
{
  "published_loads": 10,
  "active_loads": 2,
  "completed_loads": 5,
  "average_rating": 0
}
```

### Ver atividades recentes

```http
GET /clients/me/activities
```

Query opcional:

```text
limit=20
```

Exemplo:

```http
GET /clients/me/activities?limit=10
```

## Cargas do cliente

Tabela principal:

```text
loads
```

Campos principais:

```text
client_id
codigo
tipo_carga
nome_carga
descricao
peso
peso_unidade
volume
valor
negociavel
origem
destino
data_saida
tipo_carga_volume
tipo_veiculo_sugerido
instrucoes
status
```

### Publicar carga

```http
POST /loads
```

Permissao:

```text
cliente
```

Body:

```json
{
  "load_type": "cimento",
  "load_name": "Cimento para obra",
  "description": "Sacos de cimento para entrega em Nampula",
  "weight": 20,
  "weight_unit": "ton",
  "volume": 40,
  "value": 30000,
  "negotiable": true,
  "origin": "Maputo",
  "destination": "Nampula",
  "origin_lat": -25.9655,
  "origin_lng": 32.5832,
  "destination_lat": -15.1165,
  "destination_lng": 39.2666,
  "departure_date": "2026-05-30",
  "load_fill": "completa",
  "suggested_vehicle_type": "Camiao fechado",
  "instructions": "Carga deve estar protegida da chuva",
  "images": [
    {
      "image_url": "https://exemplo.com/carga1.jpg",
      "is_primary": true
    }
  ]
}
```

Campos obrigatorios:

```text
load_type
origin
destination
```

Regras:

- Apenas cliente pode publicar carga.
- Pode enviar ate 5 imagens no mesmo pedido.
- O sistema gera automaticamente o `codigo` da carga.
- A carga nasce com status `disponivel`.

### Listar minhas cargas

```http
GET /loads/me
```

Permissao:

```text
cliente
```

Retorna apenas cargas publicadas pelo cliente autenticado.

### Ver detalhe da carga

```http
GET /loads/{load_id}
```

Retorna:

- Dados da carga.
- Imagens.
- Dados do remetente.
- Rota estimada.
- Quantidade de propostas.

### Atualizar carga

```http
PATCH /loads/{load_id}
```

Permissao:

```text
cliente dono da carga
```

Body exemplo:

```json
{
  "value": 35000,
  "negotiable": true,
  "instructions": "Cliente precisa de entrega urgente"
}
```

Regras:

- Cliente so pode atualizar carga propria.
- Campos enviados parcialmente sao atualizados.

### Cancelar carga

```http
DELETE /loads/{load_id}
```

Permissao:

```text
cliente dono da carga
```

Efeito:

```text
loads.status = "cancelada"
```

Resposta:

```http
204 No Content
```

## Imagens da carga

### Adicionar imagem

```http
POST /loads/{load_id}/images
```

Permissao:

```text
cliente dono da carga
```

Body:

```json
{
  "image_url": "https://exemplo.com/carga2.jpg",
  "is_primary": false
}
```

Regras:

- Maximo de 5 imagens por carga.
- Se `is_primary = true`, as outras imagens deixam de ser principais.

## Propostas recebidas

As propostas sao enviadas por empresas transportadoras.

Tabela:

```text
load_proposals
```

Campos importantes:

```text
load_id
company_id
driver_id
vehicle_id
valor_proposto
mensagem
status
```

### Listar propostas de uma carga

```http
GET /loads/{load_id}/proposals
```

Permissao:

```text
cliente dono da carga
```

Resposta:

```json
[
  {
    "id": 9,
    "load_id": 4,
    "company_id": 1,
    "driver_id": 2,
    "vehicle_id": 5,
    "proposed_value": 25000,
    "message": "Temos camiao disponivel para esta rota.",
    "status": "pendente",
    "created_at": "2026-05-22T10:30:00"
  }
]
```

Status possiveis:

```text
pendente
aceite
recusada
```

### Aceitar proposta

```http
POST /loads/{load_id}/proposals/{proposal_id}/accept
```

Permissao:

```text
cliente dono da carga
```

Efeito:

- A proposta escolhida fica `aceite`.
- As outras propostas pendentes da mesma carga ficam `recusada`.
- A carga muda para `aceite`.
- O sistema cria uma `Trip`.

Resposta:

```json
{
  "id": 12,
  "load_id": 4,
  "company_id": 1,
  "driver_id": 2,
  "vehicle_id": 5,
  "status": "aguardando_inicio",
  "started_at": null,
  "arrived_at": null,
  "client_confirmed_at": null,
  "completed_at": null,
  "total_distance_km": null,
  "traveled_distance_km": null,
  "estimated_time": null,
  "created_at": "2026-05-22T11:00:00"
}
```

### Recusar proposta

```http
POST /loads/{load_id}/proposals/{proposal_id}/reject
```

Permissao:

```text
cliente dono da carga
```

Efeito:

```text
load_proposals.status = "recusada"
```

## Viagens do cliente

Quando o cliente aceita uma proposta, nasce uma viagem.

Tabela:

```text
trips
```

Campos importantes:

```text
load_id
company_id
driver_id
vehicle_id
status
started_at
arrived_at
client_confirmed_at
completed_at
```

### Listar minhas viagens

```http
GET /trips/me
```

Permissao:

```text
cliente
```

Retorna viagens relacionadas as cargas do cliente autenticado.

### Ver detalhe da viagem

```http
GET /trips/{trip_id}
```

Permissao:

```text
cliente dono da carga
```

### Confirmar entrega

```http
PATCH /trips/{trip_id}/confirm
```

Permissao:

```text
cliente dono da carga
```

Regra:

- A viagem precisa estar com status `aguardando_cliente`.

Efeito:

```text
trips.status = "concluida"
loads.status = "concluida"
trips.client_confirmed_at = agora
trips.completed_at = agora
```

## Tracking da carga

### Rastrear carga

```http
GET /loads/{load_id}/tracking
```

Permissao:

```text
cliente dono da carga
```

Retorna:

- Status da carga.
- Status da viagem.
- Se esta rastreavel.
- Historico de localizacoes.
- Ultima localizacao.

Exemplo de resposta:

```json
{
  "load_id": 4,
  "load_code": "CL-ABC12345",
  "load_status": "em_viagem",
  "trip_id": 12,
  "trip_status": "viagem_iniciada",
  "trackable": true,
  "locations": [
    {
      "id": 1,
      "trip_id": 12,
      "latitude": -25.9655,
      "longitude": 32.5832,
      "speed": 60,
      "created_at": "2026-05-22T12:00:00"
    }
  ],
  "last_location": {
    "id": 1,
    "trip_id": 12,
    "latitude": -25.9655,
    "longitude": 32.5832,
    "speed": 60,
    "created_at": "2026-05-22T12:00:00"
  }
}
```

## Fluxo completo do cliente

```text
1. Cliente cria conta com user_type = "cliente"
2. Cliente atualiza perfil
3. Cliente publica carga
4. Empresas transportadoras veem a carga
5. Empresas enviam propostas
6. Cliente lista propostas recebidas
7. Cliente aceita uma proposta
8. Sistema cria viagem
9. Motorista inicia e executa viagem
10. Cliente acompanha tracking
11. Motorista confirma chegada
12. Cliente confirma entrega
13. Carga e viagem ficam concluidas
```

## Resumo de rotas do cliente

```text
Perfil:
GET    /clients/me
PATCH  /clients/me
GET    /clients/me/stats
GET    /clients/me/activities

Cargas:
POST   /loads
GET    /loads/me
GET    /loads/{load_id}
PATCH  /loads/{load_id}
DELETE /loads/{load_id}
POST   /loads/{load_id}/images

Propostas:
GET    /loads/{load_id}/proposals
POST   /loads/{load_id}/proposals/{proposal_id}/accept
POST   /loads/{load_id}/proposals/{proposal_id}/reject

Viagens:
GET    /trips/me
GET    /trips/{trip_id}
PATCH  /trips/{trip_id}/confirm

Tracking:
GET    /loads/{load_id}/tracking
GET    /trips/{trip_id}/locations

Consulta publica:
GET    /clients
GET    /clients/{client_id}
```

## O que o cliente nao faz

O cliente nao deve:

- Cadastrar camiao. Isso e papel da empresa.
- Associar motorista. Isso e papel da empresa.
- Enviar proposta. Isso e papel da empresa.
- Iniciar viagem. Isso e papel do motorista.
- Enviar GPS. Isso e papel do motorista.
- Confirmar chegada. Isso e papel do motorista.

## Permissoes resumidas

```text
Cliente:
  - gere perfil
  - publica cargas
  - gere suas cargas
  - ve propostas recebidas
  - aceita ou recusa propostas
  - acompanha viagens
  - confirma entrega

Empresa:
  - gere frota
  - gere motoristas
  - envia propostas
  - acompanha viagens da empresa

Motorista:
  - executa viagem
  - envia GPS
  - confirma chegada
```
