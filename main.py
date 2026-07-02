"""主程序
"""
from fastapi import FastAPI, Request
from v1 import blacklist, websocket
from v1.blacklist import cleanup_blacklist
from fastapi.responses import JSONResponse
from v1.YHlib import *
import traceback
import uvicorn
from json import JSONDecodeError
import threading

app = FastAPI()
setToken("botToken")
FFL_ID = "934215405"

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


clean = threading.Thread(target=cleanup_blacklist, daemon=True)

if __name__ == "__main__":
    clean.start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
