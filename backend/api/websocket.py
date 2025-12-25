"""
WebSocket connection manager for real-time updates
Broadcasts agent state changes to connected frontend clients
"""
import logging
import json
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to GitHub Triage Agent",
            "timestamp": self._get_timestamp()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected clients
        
        Args:
            message: Dictionary with type, data, and optional timestamp
        """
        if not message.get("timestamp"):
            message["timestamp"] = self._get_timestamp()
        
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {str(e)}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_state_update(self, state: Dict[str, Any]):
        """Convenience method to broadcast state updates"""
        await self.broadcast({
            "type": "state_update",
            "data": state
        })
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current UTC timestamp as ISO string"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
