"""
WebSocket routes for real-time collaborative editing (Phase 5 skeleton).
Provides per-project broadcast channels for row updates, cursor positions, and presence.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger("websocket_routes")

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_info: Dict[int, dict] = {}

    async def connect(self, project_id: str, websocket: WebSocket, user_id: str, user_name: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(project_id, []).append(websocket)
        self.user_info[id(websocket)] = {
            "user_id": user_id,
            "user_name": user_name,
            "project_id": project_id,
        }
        logger.info(f"[WS] connect project={project_id} user={user_name} ({user_id})")

    def disconnect(self, project_id: str, websocket: WebSocket) -> Optional[dict]:
        info = self.user_info.pop(id(websocket), None)
        conns = self.active_connections.get(project_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                self.active_connections.pop(project_id, None)
        logger.info(f"[WS] disconnect project={project_id}")
        return info

    async def broadcast_to_project(
        self,
        project_id: str,
        message: dict,
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        conns = list(self.active_connections.get(project_id, []))
        payload = json.dumps(message)
        for ws in conns:
            if ws is exclude_ws:
                continue
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"[WS] broadcast error: {e}")

    def connected_users(self, project_id: str) -> List[dict]:
        result = []
        for ws in self.active_connections.get(project_id, []):
            info = self.user_info.get(id(ws))
            if info:
                result.append({"user_id": info["user_id"], "user_name": info["user_name"]})
        return result


manager = ConnectionManager()


@router.websocket("/ws/project/{project_id}")
async def project_ws(
    websocket: WebSocket,
    project_id: str,
    user_id: str = Query(...),
    user_name: str = Query(...),
):
    await manager.connect(project_id, websocket, user_id, user_name)
    try:
        # Notify others that this user joined
        await manager.broadcast_to_project(
            project_id,
            {
                "type": "presence",
                "event": "join",
                "user_id": user_id,
                "user_name": user_name,
                "users": manager.connected_users(project_id),
            },
            exclude_ws=None,
        )

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            if mtype not in ("row_update", "cursor", "presence"):
                continue

            msg.setdefault("user_id", user_id)
            msg.setdefault("user_name", user_name)

            await manager.broadcast_to_project(project_id, msg, exclude_ws=websocket)
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
        await manager.broadcast_to_project(
            project_id,
            {
                "type": "presence",
                "event": "leave",
                "user_id": user_id,
                "user_name": user_name,
                "users": manager.connected_users(project_id),
            },
        )
    except Exception as e:
        logger.error(f"[WS] unexpected error: {e}")
        manager.disconnect(project_id, websocket)
