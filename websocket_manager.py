from typing import List, Dict
from fastapi import WebSocket
import json
from datetime import datetime

class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to all connected clients.
    """
    def __init__(self):
        # Store active connections with user_id
        self.active_connections: Dict[int, WebSocket] = {}
        self.connections_by_role: Dict[str, List[WebSocket]] = {
            "staff": [],
            "it_support": [],
            "admin": []
        }

    async def connect(self, websocket: WebSocket, user_id: int, role: str = "staff"):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if role in self.connections_by_role:
            self.connections_by_role[role].append(websocket)
        print(f"✅ User {user_id} connected (Role: {role})")

    def disconnect(self, user_id: int, role: str = "staff"):
        """Remove a disconnected WebSocket"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if role in self.connections_by_role:
            websocket = self.active_connections.get(user_id)
            if websocket in self.connections_by_role[role]:
                self.connections_by_role[role].remove(websocket)
        print(f"❌ User {user_id} disconnected")

    async def broadcast_to_all(self, message: dict):
        """Send message to ALL connected clients"""
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")

    async def broadcast_to_role(self, role: str, message: dict):
        """Send message only to users with a specific role"""
        if role in self.connections_by_role:
            for connection in self.connections_by_role[role]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    print(f"Error sending to role {role}: {e}")

    async def send_to_user(self, user_id: int, message: dict):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")

    async def broadcast_ticket_update(self, ticket_data: dict, action: str = "updated"):
        """Broadcast ticket updates to all users"""
        message = {
            "type": "ticket_update",
            "action": action,
            "ticket": ticket_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_all(message)

# Create a global instance
manager = ConnectionManager()