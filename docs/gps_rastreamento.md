# Rastreamento GPS em Tempo Real - CargoLink

## Descrição

Sistema de rastreamento GPS em tempo real que permite:
- Motoristas enviar sua localização (latitude, longitude) em tempo real via WebSocket
- Clientes acompanhar onde motoristas e caminhões estão em tempo real
- Histórico completo de movimentações armazenado em JSON (latitude, longitude, timestamp, velocidade, direção)
- Localização atualizada a cada poucos segundos

## Arquitetura

### Componentes

1. **GPSTrackerManager** (`controllers/gps_tracker.py`)
   - Gerencia conexões WebSocket de motoristas e clientes
   - Mantém em cache as últimas localizações
   - Notifica clientes sobre movimentos de motoristas

2. **Modelo GPSLog** (`models/models.py`)
   - Tabela no banco de dados com histórico de GPS
   - Campos: driver_id, latitude, longitude, timestamp, velocidade, direção, altitude, precisão

3. **Router GPS** (`routers/gps_router.py`)
   - Endpoints REST e WebSocket
   - Gerencia inscrições de clientes
   - Vincula viagens a motoristas

## Endpoints

### REST - Consultar Localização

#### GET `/gps/driver/{driver_id}`
Retorna a última localização conhecida de um motorista.

**Response:**
```json
{
  "status": "success",
  "driver_id": 1,
  "location": {
    "driver_id": 1,
    "latitude": -23.5505,
    "longitude": -46.6333,
    "timestamp": "2026-05-27T14:30:00",
    "truck_plate": "ABC-1234",
    "speed": 65.5,
    "heading": 180.0,
    "altitude": 750.2,
    "accuracy": 5.2
  }
}
```

#### GET `/gps/all-active`
Retorna localização de todos os motoristas com rastreamento ativo.

**Response:**
```json
{
  "status": "success",
  "total_active": 5,
  "drivers": {
    "1": {...},
    "2": {...}
  }
}
```

#### POST `/gps/link-trip/{trip_id}/{driver_id}`
Liga uma viagem a um motorista para rastreamento.

#### POST `/gps/unlink-trip/{trip_id}`
Remove vínculo de viagem.

### WebSocket - Motorista Enviar Localização

**Endpoint:** `ws://api.cargolink.com/gps/ws/driver/{driver_id}?truck_plate=ABC-1234`

Motorista conecta e envia localização em tempo real.

**Formato de Envio (Motorista):**
```json
{
  "latitude": -23.5505,
  "longitude": -46.6333,
  "speed": 65.5,
  "heading": 180.0,
  "altitude": 750.2,
  "accuracy": 5.2
}
```

**Response (Confirmação):**
```json
{
  "type": "location_received",
  "status": "ok",
  "timestamp": "2026-05-27T14:30:00"
}
```

### WebSocket - Cliente Receber Localização

**Endpoint:** `ws://api.cargolink.com/gps/ws/client/{client_id}?driver_ids=1,2,3`

Cliente conecta e recebe atualizações em tempo real de motoristas assistidos.

**Ação 1: Se Inscrever em Motorista**
```json
{
  "action": "subscribe",
  "driver_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "type": "subscription_updated",
  "status": "subscribed",
  "drivers": [1, 2, 3]
}
```

**Ação 2: Se Desinscrever de Motorista**
```json
{
  "action": "unsubscribe",
  "driver_ids": [1]
}
```

**Ação 3: Obter Localização Atual**
```json
{
  "action": "get_current",
  "driver_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "type": "current_locations",
  "locations": {
    "1": {
      "driver_id": 1,
      "latitude": -23.5505,
      "longitude": -46.6333,
      "timestamp": "2026-05-27T14:30:00",
      "truck_plate": "ABC-1234",
      "speed": 65.5,
      "heading": 180.0,
      "altitude": 750.2,
      "accuracy": 5.2
    }
  }
}
```

**Recepção de Localização (Motorista está se movendo):**
```json
{
  "type": "driver_location",
  "data": {
    "driver_id": 1,
    "latitude": -23.5506,
    "longitude": -46.6334,
    "timestamp": "2026-05-27T14:30:05",
    "truck_plate": "ABC-1234",
    "speed": 65.8,
    "heading": 180.2,
    "altitude": 750.5,
    "accuracy": 5.1
  }
}
```

## Fluxo de Uso

### 1. Motorista Inicia Rastreamento

```javascript
// JavaScript no app do motorista
const driverId = 1;
const truckPlate = "ABC-1234";

const ws = new WebSocket(
  `ws://api.cargolink.com/gps/ws/driver/${driverId}?truck_plate=${truckPlate}`
);

ws.onopen = () => {
  console.log("Conectado! Enviando GPS...");
  
  // Usa geolocalização do navegador ou app
  navigator.geolocation.watchPosition((position) => {
    const { latitude, longitude } = position.coords;
    
    ws.send(JSON.stringify({
      latitude,
      longitude,
      speed: position.coords.speed || 0,
      heading: position.coords.heading || 0,
      altitude: position.coords.altitude || 0,
      accuracy: position.coords.accuracy || 0
    }));
  });
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log("GPS Confirmado:", msg.timestamp);
};
```

### 2. Cliente Acompanha Motorista

```javascript
// JavaScript no app do cliente
const clientId = 100;
const watchedDrivers = [1, 2, 3]; // IDs dos motoristas

const ws = new WebSocket(
  `ws://api.cargolink.com/gps/ws/client/${clientId}?driver_ids=${watchedDrivers.join(',')}`
);

ws.onopen = () => {
  console.log("Conectado! Recebendo rastreamento...");
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === "driver_location") {
    const { driver_id, latitude, longitude, speed } = msg.data;
    console.log(`Motorista ${driver_id} em (${latitude}, ${longitude}), velocidade: ${speed} km/h`);
    
    // Atualizar mapa com nova localização
    updateMapMarker(driver_id, latitude, longitude);
  }
};

// Se inscrever em novo motorista durante a conversa
function subscribeToDriver(driverId) {
  ws.send(JSON.stringify({
    action: "subscribe",
    driver_ids: [driverId]
  }));
}

// Desinscrever quando viagem termina
function unsubscribeFromDriver(driverId) {
  ws.send(JSON.stringify({
    action: "unsubscribe",
    driver_ids: [driverId]
  }));
}
```

### 3. Banco de Dados - Histórico de GPS

Todos os pontos de GPS são salvos na tabela `gps_logs`:

```sql
SELECT * FROM gps_logs
WHERE driver_id = 1
ORDER BY created_at DESC
LIMIT 100;
```

Estrutura:
- `id`: PK
- `driver_id`: FK para drivers
- `latitude`: Numeric(10,7) - ~1m de precisão
- `longitude`: Numeric(10,7) - ~1m de precisão
- `timestamp`: Quando a localização foi registrada
- `truck_plate`: Placa do camião
- `speed`: Velocidade em km/h
- `heading`: Direção em graus (0-360)
- `altitude`: Altitude em metros
- `accuracy`: Precisão do GPS em metros
- `created_at`: Quando foi salvo (índice para queries)

## Dados Armazenados em JSON

Exemplo de entrada no histórico (JSON):

```json
{
  "id": 12345,
  "driver_id": 1,
  "latitude": -23.5505,
  "longitude": -46.6333,
  "timestamp": "2026-05-27T14:30:00",
  "truck_plate": "ABC-1234",
  "speed": 65.5,
  "heading": 180.0,
  "altitude": 750.2,
  "accuracy": 5.2,
  "created_at": "2026-05-27T14:30:01"
}
```

## Recursos

### Geolocalização do Navegador (Web)

```javascript
// Permissão uma vez
navigator.permissions.query({ name: "geolocation" })
  .then(permission => {
    if (permission.state === "granted") {
      startTracking();
    }
  });

// Rastreamento contínuo
const watchId = navigator.geolocation.watchPosition(
  (position) => {
    console.log("Posição:", position.coords);
  },
  (error) => {
    console.error("Erro:", error);
  },
  {
    enableHighAccuracy: true,
    maximumAge: 0,
    timeout: 5000
  }
);

// Parar
navigator.geolocation.clearWatch(watchId);
```

### Geolocalização do React Native (Mobile)

```javascript
import * as Location from 'expo-location';

const watchId = await Location.watchPositionAsync(
  {
    accuracy: Location.Accuracy.High,
    timeInterval: 1000, // 1 segundo
    distanceInterval: 1 // 1 metro
  },
  (location) => {
    const { latitude, longitude, accuracy, altitude, heading, speed } = location.coords;
    
    ws.send(JSON.stringify({
      latitude,
      longitude,
      speed,
      heading,
      altitude,
      accuracy
    }));
  }
);
```

## Considerar

- **Frequência**: Enviar GPS a cada 1-5 segundos para boa precisão
- **Economia de Bateria**: Mobile deve usar `watchPosition` com `distanceInterval` para economizar
- **Precisão**: Usar GPS de alta precisão para transportes
- **Backup**: Se conexão cair, app deve reconectar automaticamente
- **Histórico**: Manter últimas 24h de dados para relatórios
- **Privacidade**: Armazenar dados apenas enquanto viagem está ativa

## Teste na Interface Web

Acesse `/frontend-test` para testar WebSocket de GPS em tempo real com interface visual!
