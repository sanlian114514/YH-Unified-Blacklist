"""WebSocket处理
"""
from fastapi import APIRouter, Depends, WebSocket
from .db import get_db, Session, Token
from fastapi.exceptions import WebSocketException
from starlette.websockets import WebSocketDisconnect

router = APIRouter(prefix="/blacklist", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[str:WebSocket] = []

    def add(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    async def disconnect(self, bot: WebSocket):
        try:
            await bot.close()
        except:
            pass
        self.active_connections.remove(bot)

    async def broadcast(self, message: any):
        for bot in self.active_connections:
            try:
                await bot.send_json(message)
            except WebSocketException:
                self.disconnect(bot)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db), token: str = ""):
    await websocket.accept()
    try:
        if not token:
            await websocket.send_json({"msg": "无效的Token", "data": {}})
            await websocket.close()
            return
        botid = db.query(Token.botid).filter(Token.token == token).all()
        if not botid:
            await websocket.send_json({"msg": "无效的Token", "data": {}})
            await websocket.close()
            return
        manager.add(websocket)
        await websocket.send_json({"event": "connected", "data": {"msg": "success", "yourid": botid[0][0]}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
