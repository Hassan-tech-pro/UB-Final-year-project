import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..orchestrator.engine import engine

logger = logging.getLogger(__name__)
ws_router = APIRouter()

@ws_router.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket_endpoint(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    logger.info(f"WebSocket client connected to workflow '{workflow_id}'")

    async def event_listener(event: dict):
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    engine.subscribe(workflow_id, event_listener)

    try:
        while True:
            # Keep connection open and receive any client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from workflow '{workflow_id}'")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        engine.unsubscribe(workflow_id, event_listener)
