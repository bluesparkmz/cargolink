# Documentacao do Motorista

Esta documentacao cobre apenas a parte do **motorista** no CargoLink.

## Papel do motorista

O motorista e o utilizador que executa a viagem.

Responsabilidades principais:

- Manter perfil de motorista atualizado.
- Informar disponibilidade.
- Enviar localizacao atual.
- Ver viagens atribuidas.
- Iniciar viagem.
- Enviar GPS durante a viagem.
- Registar paragens.
- Confirmar chegada ao destino.

Regra principal:

```text
Motorista executa.
Empresa negocia.
Cliente contrata e confirma.
```

## O que mudou no novo modelo

Antes o motorista estava ligado diretamente a camioes e propostas.

Agora:

- Motorista nao cadastra camiao.
- Motorista nao envia proposta.
- Motorista nao negocia com cliente.
- Motorista pode pertencer a uma empresa.
- Motorista acompanha apenas as viagens atribuidas a ele.

## Modelo de dados

### User

O motorista tambem e um utilizador do sistema.

```text
users.tipo = "motorista"
```

### Driver

Perfil especifico do motorista.

Tabela:

```text
drivers
```

Campos principais:

```text
id
user_id
company_id
numero_carta
validade_carta
experiencia_anos
avaliacao_media
total_viagens
disponivel
latitude_atual
longitude_atual
location_updated_at
created_at
```

### Relacoes

```text
Driver N -> 1 Company
Driver 1 -> N Vehicles atribuidos
Driver 1 -> N Trips atribuidas
```

Observacao:

```text
company_id pode ser null se o motorista ainda nao estiver associado a uma empresa.
```

## Autenticacao

Todas as rotas do motorista exigem token Bearer.

Header:

```http
Authorization: Bearer <token>
```

Para rotas operacionais do motorista, o utilizador autenticado precisa ter:

```text
user_type = "motorista"
```

## Registar motorista

Endpoint:

```http
POST /auth/register
```

Body:

```json
{
  "name": "Joao Motorista",
  "email": "joao@motorista.com",
  "password": "123456",
  "user_type": "motorista",
  "phone": "840000020"
}
```

Resultado:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

Ao registar com `user_type = "motorista"`, o sistema cria:

```text
users
drivers
wallets
```

Depois disso, uma empresa pode associar este motorista usando:

```http
POST /companies/me/drivers
```

## Perfil do motorista

### Ver perfil autenticado

```http
GET /drivers/me
```

Permissao:

```text
motorista
```

Resposta:

```json
{
  "id": 2,
  "company_id": 1,
  "license_number": "MZ-123456",
  "license_expiry": "2028-12-31",
  "years_experience": 5,
  "average_rating": 0,
  "total_trips": 0,
  "available": true,
  "current_lat": null,
  "current_lng": null,
  "location_updated_at": null,
  "user": {
    "id": 10,
    "name": "Joao Motorista",
    "phone": "840000020",
    "email": "joao@motorista.com",
    "profile_photo": null,
    "verified": false
  }
}
```

### Atualizar perfil

```http
PATCH /drivers/me
```

Permissao:

```text
motorista
```

Body:

```json
{
  "license_number": "MZ-123456",
  "license_expiry": "2028-12-31",
  "years_experience": 5,
  "available": true
}
```

## Disponibilidade

### Atualizar disponibilidade

```http
PATCH /drivers/me/availability
```

Permissao:

```text
motorista
```

Body:

```json
{
  "available": true
}
```

Uso:

- `true`: motorista disponivel.
- `false`: motorista indisponivel.

## Localizacao atual do motorista

### Atualizar localizacao

```http
PATCH /drivers/me/location
```

Permissao:

```text
motorista
```

Body:

```json
{
  "latitude": -25.9655,
  "longitude": 32.5832,
  "sync_vehicles": true
}
```

Regras:

- Atualiza a localizacao atual do motorista.
- Se `sync_vehicles = true`, replica a localizacao nos camioes disponiveis atribuidos ao motorista.

## Camioes atribuidos ao motorista

O motorista nao cadastra nem edita camiao.

Mas pode listar camioes atribuidos a ele:

```http
GET /vehicles/me
```

Permissao:

```text
motorista
```

Resposta:

```json
[
  {
    "id": 5,
    "company_id": 1,
    "driver_id": 2,
    "plate": "ABC-123-MP",
    "brand": "Volvo",
    "model_name": "FH",
    "vehicle_type": "Camiao basculante",
    "tonnage_capacity": 30,
    "photo": null,
    "status": "disponivel",
    "current_lat": -25.9655,
    "current_lng": 32.5832,
    "location_updated_at": "2026-05-22T10:00:00"
  }
]
```

### Atualizar GPS do camiao atribuido

```http
PATCH /vehicles/{vehicle_id}/location
```

Permissao:

```text
motorista atribuido ao camiao
```

Body:

```json
{
  "latitude": -25.9655,
  "longitude": 32.5832,
  "sync_vehicles": false
}
```

## Viagens do motorista

As viagens aparecem para o motorista quando uma empresa envia proposta com o seu
`driver_id` e o cliente aceita essa proposta.

Tabela:

```text
trips
```

Campos importantes:

```text
company_id
driver_id
vehicle_id
load_id
status
started_at
arrived_at
completed_at
```

### Listar minhas viagens

```http
GET /driver/trips
```

Permissao:

```text
motorista
```

Query opcional:

```text
group=em_andamento
group=concluidas
```

Exemplos:

```http
GET /driver/trips
GET /driver/trips?group=em_andamento
GET /driver/trips?group=concluidas
```

Resposta:

```json
[
  {
    "id": 12,
    "load_code": "CL-ABC12345",
    "origin": "Maputo",
    "destination": "Nampula",
    "client_name": "Maria Cliente",
    "status": "aguardando_inicio",
    "started_at": null,
    "estimated_time": null,
    "departure_date": "2026-05-30",
    "created_at": "2026-05-22T11:00:00"
  }
]
```

### Ver detalhe da viagem

```http
GET /driver/trips/{trip_id}
```

Permissao:

```text
motorista atribuido a viagem
```

Retorna:

- Dados da viagem.
- Dados da carga.
- Dados do cliente.
- Progresso.
- Paragens.

## Iniciar viagem

```http
PATCH /driver/trips/{trip_id}/start
```

Permissao:

```text
motorista atribuido a viagem
```

Body:

```json
{
  "vehicle_id": 5,
  "total_distance_km": 2200,
  "estimated_time": "2 dias"
}
```

Regras:

- Viagem precisa estar com status `aguardando_inicio`.
- O motorista autenticado precisa ser o motorista da viagem.
- O camiao deve pertencer a empresa da viagem.
- Se o camiao ja estiver atribuido a motorista, deve ser o motorista autenticado.

Efeito:

```text
trips.status = "viagem_iniciada"
loads.status = "em_viagem"
trips.started_at = agora
```

## Enviar GPS durante viagem

```http
POST /driver/trips/{trip_id}/locations
```

Permissao:

```text
motorista atribuido a viagem
```

Body:

```json
{
  "latitude": -24.5,
  "longitude": 33.1,
  "speed": 65,
  "traveled_distance_km": 120
}
```

Regras:

- A viagem precisa estar com status `viagem_iniciada`.
- Atualiza a distancia percorrida se `traveled_distance_km` for enviado.
- Regista ponto GPS em `trip_locations`.
- Tambem atualiza a localizacao atual do motorista.
- Tambem atualiza a localizacao atual do camiao usado na viagem, quando existir.
- No app, esta rota deve ser chamada automaticamente em intervalo curto enquanto a viagem estiver em curso.
- Para nao sobrecarregar o banco, o historico da rota so guarda um novo ponto quando passou pelo menos 10 segundos e o motorista andou pelo menos 50 metros.
- Se o motorista ficar parado, o historico guarda apenas um ponto de confirmacao a cada 120 segundos.
- Mesmo quando o ponto nao entra no historico, a localizacao atual do motorista/camiao continua sendo atualizada.

### Listar historico GPS da viagem

```http
GET /driver/trips/{trip_id}/locations
```

Permissao:

```text
motorista atribuido a viagem
```

## Paragens

### Listar tipos de paragem

```http
GET /driver/trips/stops/types
```

Resposta:

```json
[
  {
    "id": "abastecimento",
    "label": "Abastecimento"
  },
  {
    "id": "descanso",
    "label": "Descanso"
  }
]
```

### Registar paragem

```http
POST /driver/trips/{trip_id}/stops
```

Permissao:

```text
motorista atribuido a viagem
```

Body:

```json
{
  "stop_type": "abastecimento",
  "location_name": "Posto Xai-Xai",
  "address": "EN1, Gaza",
  "notes": "Abastecimento completo",
  "stopped_at": "2026-05-22T14:00:00"
}
```

Regras:

- `stop_type` precisa ser um dos tipos permitidos.
- A viagem precisa estar em curso.

### Listar paragens da viagem

```http
GET /driver/trips/{trip_id}/stops
```

Permissao:

```text
motorista atribuido a viagem
```

## Confirmar chegada ao destino

```http
PATCH /driver/trips/{trip_id}/end
```

Permissao:

```text
motorista atribuido a viagem
```

Regras:

- A viagem precisa estar com status `viagem_iniciada`.

Efeito:

```text
trips.status = "aguardando_cliente"
trips.arrived_at = agora
```

Depois disso, o cliente confirma entrega em:

```http
PATCH /trips/{trip_id}/confirm
```

## Consulta publica de motoristas

### Listar motoristas

```http
GET /drivers
```

Query opcional:

```text
available_only=true
```

### Ver motorista por ID

```http
GET /drivers/{driver_id}
```

## Fluxo completo do motorista

```text
1. Motorista cria conta com user_type = "motorista"
2. Motorista atualiza perfil e carta
3. Empresa associa motorista
4. Empresa atribui motorista a camiao
5. Empresa envia proposta com driver_id do motorista
6. Cliente aceita proposta
7. Sistema cria viagem para o motorista
8. Motorista ve viagem em /driver/trips
9. Motorista inicia viagem
10. Motorista envia GPS e paragens
11. Motorista confirma chegada
12. Cliente confirma entrega
13. Viagem fica concluida
```

## Resumo de rotas do motorista

```text
Perfil:
GET   /drivers/me
PATCH /drivers/me
PATCH /drivers/me/location
PATCH /drivers/me/availability

Camioes atribuidos:
GET   /vehicles/me
PATCH /vehicles/{vehicle_id}/location

Viagens:
GET   /driver/trips
GET   /driver/trips/{trip_id}
PATCH /driver/trips/{trip_id}/start
PATCH /driver/trips/{trip_id}/end

GPS:
POST  /driver/trips/{trip_id}/locations
GET   /driver/trips/{trip_id}/locations

Paragens:
GET   /driver/trips/stops/types
POST  /driver/trips/{trip_id}/stops
GET   /driver/trips/{trip_id}/stops

Consulta publica:
GET   /drivers
GET   /drivers/{driver_id}
```

## O que o motorista nao faz

O motorista nao deve:

- Publicar carga. Isso e papel do cliente.
- Cadastrar camiao. Isso e papel da empresa.
- Editar camiao. Isso e papel da empresa.
- Associar motorista a empresa. Isso e papel da empresa.
- Enviar proposta. Isso e papel da empresa.
- Aceitar ou recusar proposta. Isso e papel do cliente.
- Confirmar entrega final. Isso e papel do cliente.

## Permissoes resumidas

```text
Motorista:
  - gere perfil
  - informa disponibilidade
  - envia localizacao
  - ve viagens atribuidas
  - inicia viagem
  - envia GPS da viagem
  - regista paragens
  - confirma chegada

Empresa:
  - associa motorista
  - cadastra camiao
  - envia proposta

Cliente:
  - publica carga
  - aceita proposta
  - confirma entrega
```
