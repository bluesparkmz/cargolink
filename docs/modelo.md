# Modelo CargoLink: Cliente, Empresa e Motorista

## O que e o CargoLink

CargoLink e uma plataforma de transporte de cargas que liga clientes que precisam
enviar mercadorias a empresas transportadoras com camioes e motoristas.

O objetivo do app e organizar todo o fluxo de transporte:

- o cliente publica uma carga;
- empresas transportadoras analisam a carga e enviam propostas;
- o cliente compara e aceita uma proposta;
- a empresa disponibiliza camiao e motorista;
- o motorista executa a viagem;
- o cliente acompanha a carga e confirma a entrega.

## O que o app faz

O app suporta tres experiencias principais:

- **Cliente**: publica cargas, recebe propostas, acompanha viagens e confirma entrega.
- **Empresa transportadora**: gere frota, associa motoristas, envia propostas e acompanha viagens.
- **Motorista**: ve viagens atribuidas, inicia viagem, envia GPS, regista paragens e confirma chegada.

Tambem existem funcionalidades de apoio:

- mensagens entre utilizadores;
- notificacoes;
- documentos;
- carteira;
- pagamentos;
- rastreio por GPS;
- historico de atividades.

## Como esta feito

O backend e uma API FastAPI com SQLAlchemy e PostgreSQL.

Principais camadas:

```text
routers      -> endpoints HTTP
controllers  -> regras de negocio
schemas      -> validacao e formatos de entrada/saida
models       -> tabelas e relacoes SQLAlchemy
database     -> conexao e sessoes da base de dados
docs         -> documentacao Markdown servida em HTML
```

As documentacoes ficam em Markdown dentro da pasta `docs/` e sao renderizadas
em HTML pela rota segura `/documentation`.

Esta documentacao descreve o novo modelo da plataforma depois da separacao entre
empresa transportadora e motorista.
## Ideia principal
O sistema tem tres papeis principais:
- **Cliente**: publica cargas e aceita ou recusa propostas.
- **Empresa transportadora**: gere frota, motoristas e envia propostas para cargas.
- **Motorista**: executa a viagem, acompanha a carga e envia localizacao.
Ou seja:
```text
Cliente publica carga
Empresa envia proposta com camiao e motorista
Cliente aceita proposta
Sistema cria viagem
Motorista executa a viagem
Cliente confirma entrega
```
## Tipos de utilizador
A tabela `users` continua a ser a conta principal de login.
Campo importante:
```text
users.tipo = cliente | empresa | motorista | admin
```
Cada tipo pode ter um perfil complementar:
```text
users
  -> clients    quando tipo = cliente
  -> companies  quando tipo = empresa
  -> drivers    quando tipo = motorista
```
## Cliente
O cliente e quem precisa transportar uma carga.
Tabela principal:
```text
clients
```
Responsabilidades:
- Criar cargas.
- Editar/cancelar as suas cargas.
- Ver propostas recebidas.
- Aceitar ou recusar propostas.
- Acompanhar a carga em viagem.
- Confirmar entrega.
Principais relacoes:
```text
Client 1 -> N Loads
Load 1 -> N LoadProposals
Load 1 -> 1 Trip
```
Principais endpoints:
```text
POST   /loads
GET    /loads/me
PATCH  /loads/{load_id}
DELETE /loads/{load_id}
GET    /loads/{load_id}/proposals
POST   /loads/{load_id}/proposals/{proposal_id}/accept
POST   /loads/{load_id}/proposals/{proposal_id}/reject
GET    /loads/{load_id}/tracking
```
## Empresa Transportadora
A empresa transportadora e quem negocia com o cliente.
Tabela principal:
```text
companies
```
Responsabilidades:
- Gerir dados da empresa.
- Associar motoristas.
- Cadastrar camioes.
- Atribuir motoristas a camioes.
- Enviar propostas para cargas.
- Acompanhar propostas e viagens da empresa.
Principais relacoes:
```text
Company 1 -> N Drivers
Company 1 -> N Vehicles
Company 1 -> N LoadProposals
Company 1 -> N Trips
```
Principais endpoints da empresa:
```text
GET    /companies/me
PATCH  /companies/me
GET    /companies/me/drivers
POST   /companies/me/drivers
DELETE /companies/me/drivers/{driver_id}
GET    /companies/me/proposals
GET    /companies/me/trips
```
### Associar motorista a empresa
Um motorista pode existir como conta propria e depois ser associado a uma empresa.
Endpoint:
```text
POST /companies/me/drivers
```
Body:
```json
{
  "email": "motorista@exemplo.com"
}
```
Regras:
- Apenas utilizador `tipo = empresa` pode associar motorista.
- O motorista nao pode pertencer a outra empresa.
- Ao remover motorista da empresa, os camioes dessa empresa que estavam ligados a ele ficam sem motorista atribuido.
## Motorista
O motorista agora nao negocia carga e nao cadastra camiao.
Tabela principal:
```text
drivers
```
Responsabilidades:
- Atualizar perfil de motorista.
- Definir disponibilidade.
- Enviar localizacao atual.
- Ver viagens atribuidas.
- Iniciar viagem.
- Confirmar chegada.
- Enviar localizacao GPS durante a viagem.
- Registar paragens.
Principais relacoes:
```text
Driver N -> 1 Company
Driver 1 -> N Vehicles atribuídos
Driver 1 -> N Trips
```
Principais endpoints:
```text
GET   /drivers/me
PATCH /drivers/me
PATCH /drivers/me/location
PATCH /drivers/me/availability
GET   /driver/trips
GET   /driver/trips/{trip_id}
PATCH /driver/trips/{trip_id}/start
PATCH /driver/trips/{trip_id}/end
POST  /driver/trips/{trip_id}/locations
POST  /driver/trips/{trip_id}/stops
```
## Camioes / Veiculos
Os camioes pertencem a empresa, nao ao motorista.
Tabela principal:
```text
vehicles
```
Campos importantes:
```text
vehicles.company_id  -> dono do camiao
vehicles.driver_id   -> motorista atribuido, opcional
```
Regras:
- Apenas empresa cadastra camiao.
- Apenas empresa edita/desativa camiao.
- Empresa pode cadastrar camiao sem motorista.
- Empresa pode cadastrar camiao ja atribuido a um motorista.
- O motorista so pode atualizar GPS do camiao se ele estiver atribuido a ele.
Principais endpoints:
```text
POST   /vehicles
GET    /vehicles/me
PATCH  /vehicles/{vehicle_id}
DELETE /vehicles/{vehicle_id}
PATCH  /vehicles/{vehicle_id}/location
GET    /vehicles
GET    /vehicles/{vehicle_id}
```
Exemplo de cadastro:
```text
POST /vehicles
Content-Type: multipart/form-data

plate=ABC-123-MP
brand=Volvo
model_name=FH
vehicle_type=Camiao basculante
tonnage_capacity=30
driver_id=2
photo=<ficheiro jpg/png>
status=disponivel
```
## Propostas
As propostas agora pertencem a empresa transportadora.
Tabela principal:
```text
load_proposals
```
Campos importantes:
```text
load_proposals.load_id
load_proposals.company_id
load_proposals.driver_id
load_proposals.vehicle_id
load_proposals.valor_proposto
load_proposals.status
```
Regras:
- Apenas empresa envia proposta.
- A proposta deve indicar motorista e camiao.
- O motorista informado deve pertencer a empresa.
- O camiao informado deve pertencer a empresa.
- A mesma empresa nao pode enviar duas propostas para a mesma carga.
- O cliente aceita ou recusa propostas.
Endpoint:
```text
POST /loads/{load_id}/proposals
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
## Viagens
A viagem nasce quando o cliente aceita uma proposta.
Tabela principal:
```text
trips
```
Campos importantes:
```text
trips.load_id
trips.company_id
trips.driver_id
trips.vehicle_id
trips.status
```
Fluxo:
```text
1. Cliente publica carga
2. Empresa envia proposta com motorista e camiao
3. Cliente aceita proposta
4. Sistema cria Trip com company_id, driver_id e vehicle_id
5. Motorista inicia viagem
6. Motorista envia GPS/paragens
7. Motorista confirma chegada
8. Cliente confirma entrega
9. Viagem fica concluida
```
Estados principais:
```text
aguardando_inicio
viagem_iniciada
aguardando_cliente
concluida
```
## Resumo das permissoes
```text
Cliente:
  - publica carga
  - ve propostas
  - aceita/recusa proposta
  - acompanha viagem
  - confirma entrega
Empresa:
  - gere perfil da empresa
  - associa motoristas
  - cadastra camioes
  - envia propostas
  - ve suas propostas
  - ve suas viagens
Motorista:
  - atualiza disponibilidade/localizacao
  - ve viagens atribuidas
  - inicia/encerra viagem
  - envia GPS
  - regista paragens
```
## Diagrama simples
```text
User
 ├── Client
 │    └── Loads
 │         ├── LoadProposals
 │         └── Trip
 │
 ├── Company
 │    ├── Drivers
 │    ├── Vehicles
 │    ├── LoadProposals
 │    └── Trips
 │
 └── Driver
      ├── Vehicles atribuidos
      └── Trips atribuidas
```
## Regra de negocio mais importante
```text
Empresa negocia.
Motorista executa.
Cliente contrata e confirma.
```

---

# WebSocket: Rastreamento GPS em Tempo Real

## Objetivo do WebSocket

O WebSocket permite comunicacao em tempo real entre:

- **Motoristas**: enviar localizacao GPS em segundos
- **Clientes**: acompanhar a carga e o camiao em tempo real
- **Empresas**: monitorar a frota
- **Chat**: mensagens instantaneas entre utilizadores

## Conexao WebSocket

Protocolo:
```text
ws://host/ws?token=<jwt>     (desenvolvimento)
wss://host/ws?token=<jwt>    (producao com HTTPS)
```

Exemplo JavaScript:
```javascript
const token = localStorage.getItem("cargolink_token");
const socket = new WebSocket("wss://api.cargolink.com/ws?token=" + token);

socket.onopen = () => console.log("Conectado");
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Mensagem recebida:", data);
};
socket.onerror = (error) => console.error("Erro:", error);
```

## Tipos de Mensagens

### 1. Localizacao do Motorista

**Motorista envia**:
```json
{
  "type": "driver_location",
  "trip_id": 1,
  "latitude": -25.9692,
  "longitude": 32.5732
}
```

**Backend recebe e distribui para**:
- Cliente (acompanhamento da carga)
- Empresa (monitoramento da frota)
- Admin (auditoria)

**Log JSON salvo no servidor**:
```json
{
  "type": "driver_location_log",
  "timestamp": "2026-05-27T14:30:00Z",
  "trip_id": 1,
  "driver_id": 5,
  "vehicle_id": 3,
  "vehicle_plate": "ABC-123-MP",
  "latitude": -25.9692,
  "longitude": 32.5732,
  "driver_name": "Joao Silva",
  "vehicle_brand": "Volvo",
  "vehicle_model": "FH",
  "location_name": "Avenida Julius Nyerere, Maputo"
}
```

### 2. Chat em Tempo Real

**Utilizador envia**:
```json
{
  "type": "message_send",
  "load_id": 1,
  "receiver_id": 2,
  "body": "Chegando em 5 minutos"
}
```

**Distribuido para**:
- Receptor (notificacao instantanea)
- Otros utilizadores na mesma carga (opcional)

### 3. Subscrever a Viagem

**Cliente/Empresa envia**:
```json
{
  "type": "subscribe_trip",
  "trip_id": 1
}
```

**Efeito**:
- Utilizador entra em sala `trip:1`
- Recebe todas as mensagens desta viagem

### 4. Negociacao em Tempo Real

**Empresa negocia valor**:
```json
{
  "type": "negotiation_create",
  "proposal_id": 1,
  "amount": 24000
}
```

## Salas (Rooms) Internas

O backend organiza mensagens em salas:

```text
user:{user_id}              -> notificacoes do utilizador
role:{user_type}            -> broadcast por tipo (empresa, cliente, motorista)
client:{client_id}          -> notificacoes do cliente
company:{company_id}        -> notificacoes da empresa
driver:{driver_id}          -> notificacoes do motorista
trip:{trip_id}              -> mensagens da viagem
load:{load_id}              -> mensagens da carga
proposal:{proposal_id}      -> mensagens da proposta
```

## Rastreamento GPS: Fluxo Completo

### 1. Motorista inicia viagem
```text
PATCH /trips/{trip_id}/start
└─ Backend marca trip.status = "viagem_iniciada"
└─ Motorista conecta ao WebSocket
```

### 2. Motorista envia GPS periodicamente
```text
Cada 3-10 segundos:
WS: {"type": "driver_location", "trip_id": 1, "latitude": -25.9692, "longitude": 32.5732}
└─ Backend processa e guarda em trip_locations
└─ Envia para clientes conectados
└─ Log em JSON
```

### 3. Cliente recebe atualizacoes
```text
Cliente conectado ao WebSocket e inscrito na viagem
└─ Recebe: {"type": "driver_location", "latitude": ..., "longitude": ...}
└─ Atualiza mapa em tempo real
└─ Ve posicao do motorista e camiao
```

### 4. Empresa monitora frota
```text
Empresa conectada e inscrita em suas viagens
└─ Recebe todas as localizacoes dos seus motoristas
└─ Pode ver quantos camioes estao em transito
└─ Pode calcular ETA (tempo estimado de chegada)
```

## Log de GPS em JSON

Cada vez que o motorista envia localizacao, o backend salva:

```json
{
  "id": 1,
  "trip_id": 1,
  "driver_id": 5,
  "vehicle_id": 3,
  "timestamp": "2026-05-27T14:30:15Z",
  "latitude": -25.9692,
  "longitude": 32.5732,
  "accuracy": 5.0,
  "speed": 85.5,
  "heading": 180,
  "meta": {
    "driver_name": "Joao Silva",
    "vehicle_plate": "ABC-123-MP",
    "vehicle_brand": "Volvo",
    "vehicle_model": "FH",
    "trip_status": "viagem_iniciada",
    "load_id": 10,
    "client_name": "Pedro Costa"
  }
}
```

Tabela no banco:
```sql
CREATE TABLE trip_locations (
  id SERIAL PRIMARY KEY,
  trip_id INT NOT NULL,
  driver_id INT NOT NULL,
  vehicle_id INT NOT NULL,
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  timestamp DATETIME DEFAULT NOW(),
  accuracy FLOAT,
  speed FLOAT,
  heading FLOAT,
  created_at DATETIME DEFAULT NOW()
);
```

## Casos de Uso

### 1. Cliente acompanha carga
```text
1. Cliente faz login
2. Cliente clica em "Acompanhar viagem"
3. Front-end conecta ao WebSocket
4. Front-end inscreve-se na viagem
5. Recebe GPS do motorista a cada 5 segundos
6. Mapa em tempo real mostra posicao do camiao
```

### 2. Motorista registra rotas
```text
1. Motorista inicia viagem (PATCH /trips/start)
2. App comeca a enviar GPS via WebSocket a cada 10 seg
3. Backend salva historico completo em trip_locations
4. Motorista ve "Viagem registada com sucesso"
```

### 3. Empresa monitora frota
```text
1. Gerente conecta ao dashboard
2. Ve todos os camioes "em transito" com cores diferentes
3. Clica em camiao e ve GPS em tempo real
4. Exporta relatorio de rotas realizadas
```

## Teste no Frontend

A pagina de teste em `/test` inclui:

- **Conectar WebSocket**: liga ao servidor em tempo real
- **Chat Online**: enviar e receber mensagens
- **Simular GPS**: envia coordenadas de teste a cada 3 segundos
- **Logs GPS**: painel mostrando historico em JSON
- **Subscrever Viagem**: para receber atualizacoes de uma viagem especifica

### Exemplo de teste:

1. Faca login com motorista
2. Clique em "Conectar WebSocket"
3. Informe Trip ID (ex: 1)
4. Clique em "Subscribe Viagem"
5. Clique em "Simular GPS"
6. Observe o painel de chat e logs JSON atualizando a cada 3 segundos
7. Em outra abinha, faca login com cliente e veja o mesmo GPS chegando

## Performance e Limites

Recomendacoes:

```text
Intervalo minimo de envio de GPS: 3 segundos
Intervalo recomendado: 5-10 segundos
Intervalo maximo: 30 segundos

Salas por usuario: ~5-10 (user, role, client/company/driver, trip, load)
Utilizadores por sala: ilimitado (limitado por memoria do servidor)

Bandwidth por motorista: ~500 bytes / 5 segundos = 100 bytes/seg ~= 360KB/dia
```

## Autenticacao WebSocket

O token JWT e validado na conexao:

```text
- Token ausente: recusa com codigo 1008
- Token expirado: recusa com codigo 1008
- Token invalido: recusa com codigo 1008
- Utilizador inativo: recusa com codigo 1008
- OK: conexao aceita, utilizador conectado
```

Renovar token:
```javascript
// Token expira em ~30 minutos
// Cliente pode:
1. Desconectar e reconectar com novo token
2. Usar refresh token (se implementado)
```

