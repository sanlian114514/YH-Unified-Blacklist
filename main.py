"""主程序
"""
from fastapi import FastAPI, Request
from v1 import blacklist, websocket
from v1.blacklist import cleanup_blacklist, init_data
from fastapi.responses import JSONResponse
from v1.YHlib import *
import traceback
import uvicorn
from json import JSONDecodeError
import asyncio
from contextlib import asynccontextmanager

# 生命周期事件：初始化


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- (Startup) ---
    # 1. 初始化黑名单数据(写入内存)
    await init_data()
    # 2. 启动后台清理任务
    cleanup_task = asyncio.create_task(cleanup_blacklist())
    yield  # 应用运行期间暂停在此处

    # --- (Shutdown) ---
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        print("清理任务已停止")

app = FastAPI(lifespan=lifespan)
setToken("ac7bd99fa0d94887b3f6eb2886baaad2")

app.include_router(blacklist.router, prefix="/v1")
app.include_router(websocket.router, prefix="/v1")


@app.exception_handler(JSONDecodeError)
def json_decode_exception_handler(request: Request, exc: JSONDecodeError):
    return JSONResponse(
        status_code=400,
        content={"msg": "非法Json", "data": {"error": str(exc)}},
    )


@app.exception_handler(Exception)
def exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"msg": "错误", "data": {"Exception": str(exc)}})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
