# Documentacao da Empresa Transportadora

Esta documentacao cobre apenas a parte da **empresa transportadora** no novo
modelo do CargoLink.

## Papel da empresa

A empresa e a entidade que negocia com o cliente e gere a operacao de transporte.

Responsabilidades principais:

- Gerir perfil da empresa.
- Associar e remover motoristas.
- Cadastrar, editar e desativar camioes.
- Enviar propostas para cargas publicadas por clientes.
- Acompanhar propostas enviadas.
- Acompanhar viagens criadas a partir das propostas aceites.

Regra principal:

```text
Empresa negocia.
Motorista executa.
Cliente contrata e confirma.
```

## Modelo de dados

### User

A empresa tambem e um utilizador do sistema.

```text
users.tipo = "empresa"
```

### Company

Perfil especifico da empresa transportadora.

Tabela:

```text
companies
```

Campos principais:

```text
id
user_id
nome_empresa
nuit
numero_licenca
endereco
cidade
provincia
avaliacao_media
total_viagens
verificada
created_at
```

### Relacoes

```text
Company 1 -> N Drivers
Company 1 -> N Vehicles
Company 1 -> N LoadProposals
Company 1 -> N Trips
```

## Autenticacao

Todas as rotas da empresa exigem token Bearer.

Header:

```http
Authorization: Bearer <token>
```

Para rotas de gestao da propria empresa, o utilizador autenticado precisa ter:

```text
user_type = "empresa"
```

## Registar empresa

Endpoint:

```http
POST /auth/register
```

Body:

```json
{
  "name": "TransMoz Admin",
  "email": "admin@transmoz.co.mz",
  "password": "123456",
  "user_type": "empresa",
  "phone": "840000001",
  "company_name": "TransMoz Transportes",
  "city": "Maputo",
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

Ao registar com `user_type = "empresa"`, o sistema cria:

```text
users
companies
wallets
```

## Perfil da empresa

### Ver perfil autenticado

```http
GET /companies/me
```

Permissao:

```text
empresa
```

Resposta:

```json
{
  "id": 1,
  "company_name": "TransMoz Transportes",
  "tax_id": null,
  "license_number": null,
  "address": null,
  "city": "Maputo",
  "state": "Maputo",
  "average_rating": 0,
  "total_trips": 0,
  "verified": false,
  "user": {
    "id": 3,
    "name": "TransMoz Admin",
    "phone": "840000001",
    "email": "admin@transmoz.co.mz",
    "profile_photo": null,
    "verified": false
  }
}
```

### Atualizar perfil

```http
PATCH /companies/me
```

Permissao:

```text
empresa
```

Body:

```json
{
  "company_name": "TransMoz Transportes Lda",
  "tax_id": "400000001",
  "license_number": "ALV-2026-001",
  "address": "Av. Julius Nyerere, Maputo",
  "city": "Maputo",
  "state": "Maputo"
}
```

## Motoristas da empresa

Motoristas sao contas separadas com:

```text
users.tipo = "motorista"
```

A empresa pode associar motoristas existentes ao seu perfil.

### Listar motoristas da empresa

```http
GET /companies/me/drivers
```

Permissao:

```text
empresa
```

Resposta:

```json
[
  {
    "id": 2,
    "user_id": 10,
    "company_id": 1,
    "name": "Joao Motorista",
    "average_rating": 0,
    "total_trips": 0,
    "available": true,
    "profile_photo": null,
    "verified": false,
    "current_lat": null,
    "current_lng": null,
    "location_updated_at": null
  }
]
```

### Associar motorista

```http
POST /companies/me/drivers
```

Permissao:

```text
empresa
```

Body:

```json
{
  "driver_id": 2
}
```

Regras:

- O motorista precisa existir.
- O motorista nao pode estar associado a outra empresa.
- Se ja estiver associado a mesma empresa, continua valido.

### Remover motorista

```http
DELETE /companies/me/drivers/{driver_id}
```

Permissao:

```text
empresa
```

Efeito:

- Remove o `company_id` do motorista.
- Remove esse motorista dos camioes da empresa onde ele estava atribuido.

Resposta:

```http
204 No Content
```

## Frota / camioes da empresa

Os camioes pertencem a empresa, nao ao motorista.

Tabela:

```text
vehicles
```

Campos importantes:

```text
company_id
driver_id
matricula
marca
modelo
tipo
capacidade_toneladas
status
```

### Listar camioes da empresa

```http
GET /vehicles/me
```

Permissao:

```text
empresa
```

Observacao:

Esta rota tambem pode ser usada por motorista, mas nesse caso retorna apenas os
camioes atribuidos a ele.

### Cadastrar camiao

```http
POST /vehicles
```

Permissao:

```text
empresa
```

Body (`multipart/form-data`):

```text
plate=ABC-123-MP
brand=Volvo
model_name=FH
vehicle_type=Camiao basculante
tonnage_capacity=30
driver_id=2
photo=<ficheiro jpg/png>
status=disponivel
current_lat=-25.9655
current_lng=32.5832
```

Campos obrigatorios:

```text
plate
```

Campos opcionais:

```text
driver_id
brand
model_name
vehicle_type
tonnage_capacity
photo (ficheiro jpg/png)
status
current_lat
current_lng
```

Regras:

- Apenas empresa pode cadastrar camiao.
- Se `driver_id` for informado, o motorista deve pertencer a empresa.
- A matricula deve ser unica.

Resposta:

```json
{
  "id": 5,
  "company_id": 1,
  "driver_id": 2,
  "plate": "ABC-123-MP",
  "brand": "Volvo",
  "model_name": "FH",
  "vehicle_type": "Camiao basculante",
  "tonnage_capacity": 30,
  "photo": "/uploads/vehicles/aa82ce092d4f4c809fd4c6596015897e.png",
  "status": "disponivel",
  "current_lat": -25.9655,
  "current_lng": 32.5832,
  "location_updated_at": "2026-05-22T10:00:00"
}
```

### Atualizar camiao

```http
PATCH /vehicles/{vehicle_id}
```

Permissao:

```text
empresa
```

Body:

```json
{
  "driver_id": 3,
  "status": "manutencao"
}
```

Regras:

- Apenas empresa dona do camiao pode editar.
- Se trocar `driver_id`, o novo motorista deve pertencer a empresa.

### Desativar camiao

```http
DELETE /vehicles/{vehicle_id}
```

Permissao:

```text
empresa
```

Efeito:

```text
vehicles.status = "inativo"
```

Resposta:

```http
204 No Content
```

### Ver detalhe do camiao

```http
GET /vehicles/{vehicle_id}
```

Retorna dados do camiao, empresa e motorista atribuido.

## Propostas da empresa

A empresa envia propostas para cargas publicadas por clientes.

Tabela:

```text
load_proposals
```

Campos principais:

```text
load_id
company_id
driver_id
vehicle_id
valor_proposto
mensagem
status
```

### Enviar proposta para uma carga

```http
POST /loads/{load_id}/proposals
```

Permissao:

```text
empresa
```

Body:

```json
{
  "proposed_value": 25000,
  "message": "Temos camiao disponivel para esta rota.",
  "driver_id": 2,
  "vehicle_id": 5
}
```

Regras:

- A carga precisa estar com status `disponivel`.
- O motorista deve pertencer a empresa.
- O camiao deve pertencer a empresa.
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
  "proposed_value": 25000,
  "message": "Temos camiao disponivel para esta rota.",
  "status": "pendente",
  "created_at": "2026-05-22T10:30:00"
}
```

### Listar propostas da empresa

```http
GET /companies/me/proposals
```

Permissao:

```text
empresa
```

Status possiveis:

```text
pendente
aceite
recusada
```

## Viagens da empresa

Quando o cliente aceita uma proposta, o sistema cria uma viagem com:

```text
trip.company_id
trip.driver_id
trip.vehicle_id
```

### Listar viagens da empresa

```http
GET /companies/me/trips
```

Permissao:

```text
empresa
```

Resposta:

```json
[
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
]
```

Estados principais:

```text
aguardando_inicio
viagem_iniciada
aguardando_cliente
concluida
```

Importante:

- A empresa acompanha a viagem.
- O motorista executa a viagem nas rotas `/driver/trips`.
- O cliente confirma a entrega.

## Listagens publicas de empresas

### Listar empresas

```http
GET /companies
```

Retorna empresas transportadoras registadas.

### Ver empresa por ID

```http
GET /companies/{company_id}
```

Retorna detalhe publico da empresa.

## Fluxo completo da empresa

```text
1. Empresa cria conta com user_type = "empresa"
2. Empresa atualiza perfil
3. Empresa associa motoristas
4. Empresa cadastra camioes
5. Empresa atribui motorista ao camiao
6. Empresa consulta cargas disponiveis em GET /loads
7. Empresa envia proposta em POST /loads/{load_id}/proposals
8. Cliente aceita proposta
9. Sistema cria viagem
10. Empresa acompanha em GET /companies/me/trips
11. Motorista executa viagem em /driver/trips
12. Cliente confirma entrega
```

## Resumo de rotas da empresa

```text
Perfil:
GET    /companies/me
PATCH  /companies/me

Motoristas:
GET    /companies/me/drivers
POST   /companies/me/drivers
DELETE /companies/me/drivers/{driver_id}

Frota:
GET    /vehicles/me
POST   /vehicles
PATCH  /vehicles/{vehicle_id}
DELETE /vehicles/{vehicle_id}
GET    /vehicles/{vehicle_id}

Propostas:
POST   /loads/{load_id}/proposals
GET    /companies/me/proposals

Viagens:
GET    /companies/me/trips

Consulta publica:
GET    /companies
GET    /companies/{company_id}
```

## O que a empresa nao faz

A empresa nao deve:

- Publicar carga. Isso e papel do cliente.
- Iniciar viagem. Isso e papel do motorista.
- Confirmar chegada. Isso e papel do motorista.
- Confirmar entrega. Isso e papel do cliente.
- Atualizar GPS do motorista. Isso e papel do motorista.

## Permissoes resumidas

```text
Empresa:
  - gere perfil
  - gere motoristas
  - gere camioes
  - envia propostas
  - acompanha propostas
  - acompanha viagens

Motorista:
  - executa viagem
  - envia GPS
  - regista paragens

Cliente:
  - publica carga
  - aceita proposta
  - confirma entrega
```
