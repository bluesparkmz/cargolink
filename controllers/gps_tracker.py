"""
Sistema de rastreamento GPS em tempo real via WebSocket.
Rastreia localização de motoristas e caminhões com atualização em segundos.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from models.models import GPSLog, Driver, Trip


@dataclass
class GPSData:
    """Dados de GPS: latitude, longitude, timestamp e informações do motorista."""
    driver_id: int
    latitude: float
    longitude: float
    timestamp: str
    truck_plate: str = ""
    speed: float = 0.0
    heading: float = 0.0  # direção em graus
    altitude: float = 0.0
    accuracy: float = 0.0


class GPSTrackerManager:
    """Gerencia rastreamento em tempo real e armazenamento de dados GPS."""
    
    def __init__(self):
        self.active_drivers: Dict[int, GPSData] = {}  # driver_id -> último GPS
        self.subscribers: Dict[int, Set] = {}  # driver_id -> conjunto de conexões WebSocket
        self.driver_websockets: Dict[int, Set] = {}  # driver_id -> conexões dos motoristas
        self.client_websockets: Dict[int, Set] = {}  # client_id -> conexões dos clientes
        self.trip_to_driver: Dict[int, int] = {}  # trip_id -> driver_id
    
    async def register_driver_connection(self, driver_id: int, websocket):
        """Registra conexão de um motorista."""
        if driver_id not in self.driver_websockets:
            self.driver_websockets[driver_id] = set()
        self.driver_websockets[driver_id].add(websocket)
        print(f"✓ Motorista {driver_id} conectado")
    
    async def unregister_driver_connection(self, driver_id: int, websocket):
        """Remove conexão de um motorista."""
        if driver_id in self.driver_websockets:
            self.driver_websockets[driver_id].discard(websocket)
            if not self.driver_websockets[driver_id]:
                del self.driver_websockets[driver_id]
                if driver_id in self.active_drivers:
                    del self.active_drivers[driver_id]
        print(f"✗ Motorista {driver_id} desconectado")
    
    async def register_client_connection(self, client_id: int, websocket, watched_drivers: List[int] = None):
        """Registra conexão de um cliente assistindo motoristas."""
        if client_id not in self.client_websockets:
            self.client_websockets[client_id] = set()
        self.client_websockets[client_id].add(websocket)
        
        # Cliente se inscreve para receber GPS de determinados motoristas
        if watched_drivers:
            for driver_id in watched_drivers:
                if driver_id not in self.subscribers:
                    self.subscribers[driver_id] = set()
                self.subscribers[driver_id].add((client_id, websocket))
        
        print(f"✓ Cliente {client_id} conectado, assistindo motoristas: {watched_drivers}")
    
    async def unregister_client_connection(self, client_id: int, websocket):
        """Remove conexão de um cliente."""
        if client_id in self.client_websockets:
            self.client_websockets[client_id].discard(websocket)
            if not self.client_websockets[client_id]:
                del self.client_websockets[client_id]
        
        # Remove das inscrições
        for driver_id in list(self.subscribers.keys()):
            self.subscribers[driver_id].discard((client_id, websocket))
            if not self.subscribers[driver_id]:
                del self.subscribers[driver_id]
        
        print(f"✗ Cliente {client_id} desconectado")
    
    async def update_driver_location(self, gps_data: GPSData, db: Session = None):
        """
        Atualiza localização de um motorista.
        - Armazena em cache (active_drivers)
        - Salva no banco de dados
        - Notifica todos os clientes assistindo este motorista
        """
        driver_id = gps_data.driver_id
        
        # Atualiza cache
        self.active_drivers[driver_id] = gps_data
        
        # Salva no banco de dados (histórico)
        if db:
            try:
                gps_log = GPSLog(
                    driver_id=driver_id,
                    latitude=gps_data.latitude,
                    longitude=gps_data.longitude,
                    timestamp=datetime.fromisoformat(gps_data.timestamp),
                    truck_plate=gps_data.truck_plate,
                    speed=gps_data.speed,
                    heading=gps_data.heading,
                    altitude=gps_data.altitude,
                    accuracy=gps_data.accuracy
                )
                db.add(gps_log)
                db.commit()
            except Exception as e:
                print(f"Erro ao salvar GPS: {e}")
                db.rollback()
        
        # Notifica clientes assistindo este motorista
        await self._broadcast_to_subscribers(driver_id, gps_data)
    
    async def _broadcast_to_subscribers(self, driver_id: int, gps_data: GPSData):
        """Envia dados de GPS para todos os clientes que assistem este motorista."""
        if driver_id not in self.subscribers:
            return
        
        message = json.dumps({
            "type": "driver_location",
            "data": asdict(gps_data)
        })
        
        disconnected = []
        for client_id, websocket in self.subscribers[driver_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Erro ao enviar GPS para cliente {client_id}: {e}")
                disconnected.append((client_id, websocket))
        
        # Remove conexões com erro
        for client_id, ws in disconnected:
            await self.unregister_client_connection(client_id, ws)
    
    async def link_trip_driver(self, trip_id: int, driver_id: int):
        """Liga uma viagem a um motorista para rastreamento."""
        self.trip_to_driver[trip_id] = driver_id
        print(f"✓ Viagem {trip_id} vinculada ao motorista {driver_id}")
    
    async def unlink_trip_driver(self, trip_id: int):
        """Remove vínculo de viagem e motorista."""
        if trip_id in self.trip_to_driver:
            del self.trip_to_driver[trip_id]
    
    def get_driver_location(self, driver_id: int) -> Dict or None:
        """Retorna localização atual de um motorista."""
        if driver_id in self.active_drivers:
            gps = self.active_drivers[driver_id]
            return asdict(gps)
        return None
    
    def get_all_active_drivers(self) -> Dict:
        """Retorna localização de todos os motoristas ativos."""
        return {
            driver_id: asdict(gps)
            for driver_id, gps in self.active_drivers.items()
        }
    
    async def subscribe_to_driver(self, client_id: int, driver_id: int, websocket):
        """Cliente se inscreve para receber atualizações de um motorista específico."""
        if driver_id not in self.subscribers:
            self.subscribers[driver_id] = set()
        self.subscribers[driver_id].add((client_id, websocket))
        
        # Se já há localização em cache, envia imediatamente
        if driver_id in self.active_drivers:
            gps = self.active_drivers[driver_id]
            message = json.dumps({
                "type": "driver_location",
                "data": asdict(gps)
            })
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Erro ao enviar localização inicial: {e}")
    
    async def unsubscribe_from_driver(self, client_id: int, driver_id: int, websocket):
        """Cliente se desinscreve de um motorista."""
        if driver_id in self.subscribers:
            self.subscribers[driver_id].discard((client_id, websocket))
            if not self.subscribers[driver_id]:
                del self.subscribers[driver_id]


# Instância global do gerenciador
gps_tracker = GPSTrackerManager()
