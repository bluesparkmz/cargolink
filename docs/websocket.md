# Documentacao WebSocket Realtime

Esta documentacao cobre a comunicacao em tempo real do CargoLink via WebSocket.

O objetivo e permitir:

- Motorista enviar GPS em tempo real.
- Cliente acompanhar a carga em viagem.
- Empresa acompanhar camioes/viagens da frota.
- Backend distribuir eventos para os utilizadores corretos.

## Endpoint

```text
ws://host/ws?token=<jwt>
```

Em producao com HTTPS:

```text
wss://host/ws?token=<jwt>
```

O token e o mesmo JWT usado nas rotas HTTP.

Exemplo:

```javascript
const socket = new WebSocket("wss://api.exemplo.com/ws?token=" + token);
```

## Autenticacao

O WebSocket exige token no query param:

```text
token=<jwt>
```

Se o token estiver ausente, invalido, expirado ou o utilizador estiver inativo,
a conexao e recusada com codigo WebSocket `1008`.

Tipos de utilizador suportados:

```text
cliente
empresa
motorista
admin
```

## Salas internas

O backend organiza conexoes em salas.

Salas principais:

```text
user:{user_id}
role:{user_type}
client:{client_id}
company:{company_id}
driver:{driver_id}
trip:{trip_id}
load:{load_id}
```

Quando o utilizador conecta, o backend entra automaticamente nas salas do seu
perfil e nas viagens ativas relacionadas a ele.

## Quem entra em quais viagens

Motorista:

```text
viagens em andamento atribuidas ao motorista
```

Empresa:

```text
viagens em andamento da propria empresa
```

Cliente:

```text
viagens em andamento das proprias cargas
```

Admin:

```text
todas as viagens em andamento
```

Viagens em andamento incluem:

```text
aguardando_inicio
viagem_iniciada
aguardando_cliente
```

## Evento inicial

Depois da conexao ser aceite, o servidor envia:

```json
{
  "type": "websocket.connected",
  "user": {
    "id": 10,
    "type": "motorista",
    "name": "Motorista Teste"
  },
  "active_connections": 3
}
```

## Ping

Cliente envia:

```json
{
  "type": "ping"
}
```

Servidor responde:

```json
{
  "type": "pong"
}
```

## Subscrever viagem

Usado quando a app abre o detalhe de uma viagem especifica.

Cliente envia:

```json
{
  "type": "subscribe_trip",
  "trip_id": 12
}
```

Permissao:

```text
cliente dono da carga
empresa dona da viagem
motorista atribuido
admin
```

Servidor responde:

```json
{
  "type": "subscription_ok",
  "scope": "trip",
  "trip_id": 12,
  "load_id": 4
}
```

Se nao tiver acesso:

```json
{
  "type": "error",
  "code": "forbidden",
  "message": "Sem acesso a esta viagem"
}
```

## Sair de uma viagem

Cliente envia:

```json
{
  "type": "unsubscribe_trip",
  "trip_id": 12
}
```

Servidor responde:

```json
{
  "type": "subscription_closed",
  "scope": "trip",
  "trip_id": 12
}
```

## Subscrever carga

Usado para acompanhar eventos ligados a uma carga.

Cliente envia:

```json
{
  "type": "subscribe_load",
  "load_id": 4
}
```

Permissao:

```text
cliente dono da carga
empresa com proposta ou viagem nessa carga
motorista com proposta ou viagem nessa carga
admin
```

Servidor responde:

```json
{
  "type": "subscription_ok",
  "scope": "load",
  "load_id": 4
}
```

## Motorista envia GPS

Evento usado pelo app do motorista durante a viagem.

Cliente envia:

```json
{
  "type": "driver_location",
  "trip_id": 12,
  "latitude": -25.9655,
  "longitude": 32.5832,
  "speed": 64,
  "traveled_distance_km": 120
}
```

Permissao:

```text
apenas motorista atribuido a viagem
```

Regras:

- A viagem precisa estar com status `viagem_iniciada`.
- Latitude precisa estar entre `-90` e `90`.
- Longitude precisa estar entre `-180` e `180`.
- `speed` e `traveled_distance_km` sao opcionais.

Efeito no backend:

- Atualiza a localizacao atual do motorista.
- Atualiza a localizacao atual do camiao da viagem.
- Atualiza distancia percorrida se enviada.
- Grava ponto no historico se passar a regra anti-sobrecarga.
- Envia evento `trip.location` para quem acompanha a viagem/carga/empresa/driver.

## Evento recebido: trip.location

Quando o motorista envia GPS, o servidor transmite:

```json
{
  "type": "trip.location",
  "trip_id": 12,
  "load_id": 4,
  "company_id": 2,
  "driver_id": 7,
  "vehicle_id": 5,
  "location": {
    "latitude": -25.9655,
    "longitude": 32.5832,
    "speed": 64,
    "traveled_distance_km": 120,
    "stored_location_id": 31,
    "stored_location_created_at": "2026-05-26T12:00:00"
  }
}
```

Quem recebe:

```text
trip:{trip_id}
load:{load_id}
company:{company_id}
driver:{driver_id}
```

Na pratica:

- Motorista ligado na viagem.
- Cliente dono da carga, se conectado.
- Empresa dona da viagem, se conectada.
- Admin, se inscrito.

## Historico vs realtime

O WebSocket transmite a posicao recebida em tempo real.

O historico no banco nao salva todos os pontos.

Regra atual:

```text
minimo 10 segundos entre pontos
minimo 50 metros de deslocamento
heartbeat parado a cada 120 segundos
```

Campos:

- `stored_location_id`: id do ponto salvo em `trip_locations`.
- `stored_location_created_at`: data do ponto salvo.

Observacao:

Se o ponto realtime nao virou novo ponto historico, esses campos podem apontar
para o ultimo ponto salvo. A app deve usar `latitude` e `longitude` para animar
o mapa ao vivo, e buscar o historico HTTP para desenhar a rota consolidada.

## Enviar mensagem pelo WebSocket

```json
{
  "type": "message_send",
  "load_id": 4,
  "receiver_id": 10,
  "body": "Estou a caminho.",
  "attachment": null
}
```

O backend valida se o utilizador pode participar na conversa da carga.

Resposta para quem enviou:

```json
{
  "type": "message.sent",
  "load_id": 4,
  "message_id": 31
}
```

## Evento recebido: message.created

Emitido quando uma mensagem e criada via HTTP ou WebSocket:

```json
{
  "type": "message.created",
  "load_id": 4,
  "message": {
    "id": 31,
    "load_id": 4,
    "sender_id": 8,
    "receiver_id": 10,
    "body": "Estou a caminho.",
    "attachment": null,
    "read": false,
    "created_at": "2026-05-26T12:00:00"
  }
}
```

Quem recebe:

```text
user:{sender_id}
user:{receiver_id}
load:{load_id}
```

## Evento recebido: notification.created

Emitido quando o backend cria uma notificacao automatica:

```json
{
  "type": "notification.created",
  "notification": {
    "id": 20,
    "title": "Nova proposta recebida",
    "body": "A empresa enviou uma proposta para a sua carga.",
    "notification_type": "proposal.created",
    "read": false,
    "payload": {
      "load_id": 4,
      "proposal_id": 15
    },
    "created_at": "2026-05-26T12:00:00"
  }
}
```

Tipos emitidos automaticamente:

```text
proposal.created
proposal.accepted
proposal.rejected
negotiation.created
negotiation.accepted
negotiation.rejected
trip.started
trip.arrived
trip.completed
message.created
```

## Evento recebido: trip.status_changed

Emitido quando a viagem muda de estado:

```json
{
  "type": "trip.status_changed",
  "trip_id": 12,
  "load_id": 4,
  "status": "viagem_iniciada"
}
```

Estados emitidos:

```text
viagem_iniciada
aguardando_cliente
concluida
```

## Erros

Formato padrao:

```json
{
  "type": "error",
  "code": "validation_error",
  "message": "descricao do erro"
}
```

Codigos usados:

```text
bad_request
forbidden
validation_error
request_error
not_found
unknown_event
```

## Exemplo frontend

```javascript
const socket = new WebSocket(`wss://api.exemplo.com/ws?token=${token}`);

socket.onopen = () => {
  socket.send(JSON.stringify({
    type: "subscribe_trip",
    trip_id: 12
  }));
};

socket.onmessage = (message) => {
  const event = JSON.parse(message.data);

  if (event.type === "trip.location") {
    updateTruckMarker({
      latitude: event.location.latitude,
      longitude: event.location.longitude,
      speed: event.location.speed
    });
  }
};
```

## Exemplo app motorista

```javascript
function sendDriverLocation(position) {
  socket.send(JSON.stringify({
    type: "driver_location",
    trip_id: currentTripId,
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    speed: position.coords.speed
  }));
}
```

Recomendacao no app:

```text
enviar a cada 5 a 15 segundos durante viagem_iniciada
pausar envio quando a viagem nao estiver em curso
reativar envio quando o app voltar para foreground
usar HTTP como fallback se WebSocket cair
```

## Limitacao atual

O `ConnectionManager` esta em memoria.

Isso funciona bem em desenvolvimento e em uma instancia unica da API.

Em producao com varios workers/servidores, e necessario ligar essa camada a um
broker, por exemplo:

```text
Redis Pub/Sub
Redis Streams
RabbitMQ
NATS
```

Sem broker, um utilizador conectado no worker A nao recebe evento emitido pelo
worker B.
