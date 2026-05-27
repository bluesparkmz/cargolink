"""
Router WebSocket para rastreamento GPS em tempo real.
Motoristas enviam localização em tempo real, clientes recebem atualizações.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
import json
from datetime import datetime

from controllers.gps_tracker import gps_tracker, GPSData
from database import get_db

router = APIRouter(prefix="/gps", tags=["GPS Rastreamento"])


@router.get("/driver/{driver_id}")
async def get_driver_location(driver_id: int):
    """Retorna localização atual de um motorista (última)."""
    location = gps_tracker.get_driver_location(driver_id)
    if location:
        return {
            "status": "success",
            "driver_id": driver_id,
            "location": location
        }
    return {
        "status": "not_found",
        "message": f"Motorista {driver_id} não está com rastreamento ativo"
    }


@router.get("/all-active")
async def get_all_active_drivers():
    """Retorna localização de todos os motoristas ativos."""
    drivers = gps_tracker.get_all_active_drivers()
    return {
        "status": "success",
        "total_active": len(drivers),
        "drivers": drivers
    }


@router.websocket("/ws/driver/{driver_id}")
async def websocket_driver_tracker(
    websocket: WebSocket,
    driver_id: int,
    truck_plate: str = Query("", description="Placa do camião")
):
    """
    WebSocket para motorista enviar sua localização em tempo real.
    
    Esperado: JSON com latitude, longitude, opcional: speed, heading, altitude, accuracy
    ```json
    {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "speed": 60.5,
        "heading": 180.0,
        "altitude": 750.2,
        "accuracy": 5.2
    }
    ```
    """
    await websocket.accept()
    await gps_tracker.register_driver_connection(driver_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Cria objeto GPS
            gps_data = GPSData(
                driver_id=driver_id,
                latitude=float(payload.get("latitude", 0)),
                longitude=float(payload.get("longitude", 0)),
                timestamp=datetime.now().isoformat(),
                truck_plate=truck_plate,
                speed=float(payload.get("speed", 0)),
                heading=float(payload.get("heading", 0)),
                altitude=float(payload.get("altitude", 0)),
                accuracy=float(payload.get("accuracy", 0))
            )
            
            # Atualiza localização e notifica clientes
            # await gps_tracker.update_driver_location(gps_data, db)
            await gps_tracker.update_driver_location(gps_data)
            
            # Confirma recebimento
            await websocket.send_json({
                "type": "location_received",
                "status": "ok",
                "timestamp": gps_data.timestamp
            })
            
    except WebSocketDisconnect:
        await gps_tracker.unregister_driver_connection(driver_id, websocket)
    except Exception as e:
        print(f"Erro WebSocket driver {driver_id}: {e}")
        await gps_tracker.unregister_driver_connection(driver_id, websocket)


@router.websocket("/ws/client/{client_id}")
async def websocket_client_tracker(
    websocket: WebSocket,
    client_id: int,
    driver_ids: str = Query("", description="IDs dos motoristas a rastrear (separados por vírgula)")
):
    """
    WebSocket para cliente receber localização em tempo real de motoristas.
    
    Enviar JSON para se inscrever em motoristas:
    ```json
    {
        "action": "subscribe",
        "driver_ids": [1, 2, 3]
    }
    ```
    
    Ou para se desinscrever:
    ```json
    {
        "action": "unsubscribe",
        "driver_ids": [1]
    }
    ```
    """
    await websocket.accept()
    
    # Parse driver_ids iniciais
    watched_drivers = []
    if driver_ids:
        try:
            watched_drivers = [int(x.strip()) for x in driver_ids.split(",")]
        except ValueError:
            pass
    
    await gps_tracker.register_client_connection(client_id, websocket, watched_drivers)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")
            driver_list = msg.get("driver_ids", [])
            
            if action == "subscribe":
                for driver_id in driver_list:
                    await gps_tracker.subscribe_to_driver(client_id, driver_id, websocket)
                await websocket.send_json({
                    "type": "subscription_updated",
                    "status": "subscribed",
                    "drivers": driver_list
                })
            
            elif action == "unsubscribe":
                for driver_id in driver_list:
                    await gps_tracker.unsubscribe_from_driver(client_id, driver_id, websocket)
                await websocket.send_json({
                    "type": "subscription_updated",
                    "status": "unsubscribed",
                    "drivers": driver_list
                })
            
            elif action == "get_current":
                # Cliente pede localização atual de motoristas
                locations = {}
                for driver_id in driver_list:
                    loc = gps_tracker.get_driver_location(driver_id)
                    if loc:
                        locations[driver_id] = loc
                await websocket.send_json({
                    "type": "current_locations",
                    "locations": locations
                })
    
    except WebSocketDisconnect:
        await gps_tracker.unregister_client_connection(client_id, websocket)
    except Exception as e:
        print(f"Erro WebSocket cliente {client_id}: {e}")
        await gps_tracker.unregister_client_connection(client_id, websocket)


@router.post("/link-trip/{trip_id}/{driver_id}")
async def link_trip_to_driver(trip_id: int, driver_id: int):
    """Liga uma viagem a um motorista para rastreamento."""
    await gps_tracker.link_trip_driver(trip_id, driver_id)
    return {
        "status": "success",
        "trip_id": trip_id,
        "driver_id": driver_id,
        "message": f"Viagem {trip_id} vinculada ao motorista {driver_id}"
    }


@router.post("/unlink-trip/{trip_id}")
async def unlink_trip_driver(trip_id: int):
    """Remove vínculo de viagem e motorista."""
    await gps_tracker.unlink_trip_driver(trip_id)
    return {
        "status": "success",
        "trip_id": trip_id,
        "message": f"Viagem {trip_id} desvinculada"
    }
