"""AEGIS Real-time Event Management & WebSocket Broadcaster.

Maintains active WebSocket subscriber channels and broadcasts real-time
telemetry, hospital updates, and recommendation recalculations.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket
from sqlalchemy.orm import Session
from aegis_backend.models import EmergencyEvent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and pub/sub broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts a JSON message payload to all connected clients."""
        payload = json.dumps(message, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


def record_event(
    db: Session,
    event_type: str,
    summary: str,
    emergency_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    actor: str = "AEGIS_CORE"
) -> EmergencyEvent:
    """Persists an audit event to the database."""
    ev = EmergencyEvent(
        emergency_id=emergency_id,
        event_type=event_type,
        summary=summary,
        actor=actor,
        timestamp=datetime.now(timezone.utc)
    )
    if details:
        ev.details = details
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
