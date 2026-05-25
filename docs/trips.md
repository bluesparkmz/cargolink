# Documentacao de Viagens

Esta documentacao cobre a parte de **viagens** no CargoLink: criacao apos aceite
de proposta, estados, GPS, rastreio e conclusao.

## Papel da viagem

A viagem e a operacao real de transporte da carga.

Ela nasce quando uma proposta ou contraproposta e aceite.

Fluxo principal:

```text
1. Cliente publica carga
2. Empresa envia proposta com motorista e camiao
3. Cliente aceita proposta ou alguem aceita contraproposta
4. Sistema cria viagem
5. Motorista inicia viagem
6. Motorista envia GPS durante o percurso
7. Empresa acompanha a posicao do camiao
8. Cliente acompanha a carga
9. Motorista confirma chegada
10. Cliente confirma entrega
```

## Modelo usado

Tabela principal:

```text
trips
```

Campos principais:

```text
id
load_id
company_id
driver_id
vehicle_id
status
started_at
arrived_at
client_confirmed_at
completed_at
distancia_total_km
distancia_percorrida_km
tempo_estimado
created_at
```

Tabela de GPS:

```text
trip_locations
```

Campos principais:

```text
id
trip_id
latitude
longitude
velocidade
created_at
```

## Estados da viagem

```text
aguardando_inicio
viagem_iniciada
aguardando_cliente
concluida
```

Significado:

- `aguardando_inicio`: viagem criada, motorista ainda nao iniciou.
- `viagem_iniciada`: motorista iniciou e o GPS pode ser enviado.
- `aguardando_cliente`: motorista confirmou chegada, cliente precisa confirmar.
- `concluida`: cliente confirmou entrega.

## Criacao da viagem

A viagem nao e cadastrada manualmente.

Ela e criada automaticamente quando:

- Cliente aceita uma proposta.
- Cliente ou empresa aceita uma contraproposta.

Efeito:

```text
proposta.status = "aceite"
loads.status = "aceite"
trips.load_id = carga aceite
trips.company_id = empresa da proposta
trips.driver_id = motorista da proposta
trips.vehicle_id = camiao da proposta
```

## Listar minhas viagens

```http
GET /trips/me
```

Permissao:

```text
cliente
empresa
motorista
admin
```

Retorno:

- Cliente ve viagens das suas cargas.
- Empresa ve viagens da propria empresa.
- Motorista ve viagens atribuidas a ele.
- Admin ve todas.

## Detalhe da viagem

```http
GET /trips/{trip_id}
```

Permissao:

```text
cliente dono da carga
empresa dona da viagem
motorista atribuido
admin
```

## Iniciar viagem

```http
PATCH /trips/{trip_id}/start
```

Permissao:

```text
motorista atribuido
```

Body:

```json
{
  "vehicle_id": 5,
  "total_distance_km": 450,
  "estimated_time": "7h30"
}
```

Campos opcionais:

- `vehicle_id`
- `total_distance_km`
- `estimated_time`

Regras:

- A viagem precisa estar com status `aguardando_inicio`.
- Apenas o motorista atribuido pode iniciar.
- Se `vehicle_id` for enviado, precisa pertencer a empresa da viagem.
- Se o camiao ja tiver motorista atribuido, precisa ser o mesmo motorista.

Efeito:

```text
trips.status = "viagem_iniciada"
trips.started_at = agora
loads.status = "em_viagem"
```

## Enviar GPS da viagem

```http
POST /trips/{trip_id}/locations
```

Tambem existe a rota especifica do app motorista:

```http
POST /driver/trips/{trip_id}/locations
```

Permissao:

```text
motorista atribuido
```

Body:

```json
{
  "latitude": -25.9655,
  "longitude": 32.5832,
  "speed": 64,
  "traveled_distance_km": 120
}
```

Regras:

- A viagem precisa estar com status `viagem_iniciada`.
- Latitude precisa estar entre `-90` e `90`.
- Longitude precisa estar entre `-180` e `180`.
- `speed` e `traveled_distance_km` sao opcionais.

Efeito:

- Atualiza a localizacao atual do motorista.
- Atualiza a localizacao atual do camiao da viagem.
- Atualiza `trips.distancia_percorrida_km` se `traveled_distance_km` for enviado.
- Guarda ponto em `trip_locations` quando a regra anti-sobrecarga permitir.

## Regra anti-sobrecarga do GPS

O app pode enviar GPS em intervalo curto.

O backend nao grava todos os pontos no historico.

Regras atuais:

```text
TRIP_LOCATION_MIN_INTERVAL_SECONDS = 10
TRIP_LOCATION_MIN_DISTANCE_METERS = 50
TRIP_LOCATION_HEARTBEAT_SECONDS = 120
```

Ou seja:

- So grava novo ponto de rota se passaram pelo menos 10 segundos.
- E se o motorista andou pelo menos 50 metros desde o ultimo ponto gravado.
- Se estiver parado, grava um ponto de confirmacao a cada 120 segundos.
- Mesmo quando nao grava no historico, atualiza a posicao atual do motorista/camiao.

## Historico GPS da viagem

```http
GET /trips/{trip_id}/locations
```

Permissao:

```text
cliente dono da carga
empresa dona da viagem
motorista atribuido
admin
```

Uso:

- Desenhar a rota no mapa.
- Mostrar pontos por onde o camiao passou.
- Auditar o percurso da viagem.

## Confirmar chegada

```http
PATCH /trips/{trip_id}/arrive
```

Permissao:

```text
motorista atribuido
```

Regras:

- A viagem precisa estar com status `viagem_iniciada`.

Efeito:

```text
trips.status = "aguardando_cliente"
trips.arrived_at = agora
```

## Confirmar entrega

```http
PATCH /trips/{trip_id}/confirm
```

Permissao:

```text
cliente dono da carga
```

Regras:

- A viagem precisa estar com status `aguardando_cliente`.

Efeito:

```text
trips.status = "concluida"
loads.status = "concluida"
trips.client_confirmed_at = agora
trips.completed_at = agora
drivers.total_viagens += 1
companies.total_viagens += 1
```

## Rotas do app motorista

O app do motorista tambem usa rotas especificas:

```http
GET   /driver/trips
GET   /driver/trips/{trip_id}
PATCH /driver/trips/{trip_id}/start
PATCH /driver/trips/{trip_id}/end
POST  /driver/trips/{trip_id}/locations
GET   /driver/trips/{trip_id}/locations
POST  /driver/trips/{trip_id}/stops
GET   /driver/trips/{trip_id}/stops
```

Essas rotas sao pensadas para o painel/app do motorista e retornam dados mais
uteis para a operacao diaria.

## Tracking da carga

Para o cliente acompanhar a carga pelo id da carga:

```http
GET /loads/{load_id}/tracking
```

Retorna:

- status da carga
- status da viagem
- `trip_id`
- se esta rastreavel
- historico GPS
- ultima localizacao

## Resumo de permissoes

```text
Cliente:
- ve viagens das proprias cargas
- ve GPS da propria carga
- confirma entrega

Empresa:
- ve viagens da propria empresa
- acompanha posicao do camiao

Motorista:
- ve viagens atribuidas
- inicia viagem
- envia GPS
- confirma chegada

Admin:
- pode consultar tudo
```
