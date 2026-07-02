"""黑名单请求处理API
"""
from fastapi import APIRouter, Request, Response, Depends
from .db import get_db, Session, Blacklist, Token, SessionLocal
from .websocket import manager as ws_manager
from .YHlib import *
import time
import asyncio
import datetime
import requests
import uuid

router = APIRouter(prefix="/blacklist", tags=["Blacklist"])


@router.get("/init")
async def inittoken(response: Response, db: Session = Depends(get_db)):
    bots = ["39032934", "98963403", "77341955", "30858771", "76965303"]
    tokens = {}
    if not db.query(Token).all():
        for bot in bots:
            token = str(uuid.uuid4())
            tokens[bot] = token
            db.add(Token(botid=bot, token=token))
        db.commit()
    response.status_code = 200
    return {"msg": "success", "data": tokens}


@router.post("/add")
async def adduser(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").strip()
    if not token:
        response.status_code = 401
        return {"msg": "无效的Token", "data": {}}
    botid = db.query(Token.botid).filter(Token.token == token).all()
    if not botid:
        response.status_code = 401
        return {"msg": "无效的Token", "data": {}}
    botid = botid[0][0]
    body = await request.json()
    if not "userId" in body or not "reason" in body:
        response.status_code = 400
        return {"msg": "参数错误", "data": {}}
    ret = requests.get(
        f'https://chat-web-go.jwzhd.com/v1/user/homepage?userId={body["userId"]}').json()
    if not ret["data"]["user"]["userId"]:
        response.status_code = 400
        return {"msg": "用户不存在", "data": {}}
    if db.query(Blacklist).filter(Blacklist.userid == body["userId"]):
        response.status_code = 400
        return {"msg": "用户已在黑名单中", "data": {}}
    db.add(Blacklist(
        userid=body["userId"],
        username=ret["data"]["user"]["nickname"],
        reason=body["reason"],
        operator=body.get("operator", botid),
        created_at=datetime.datetime.now()
    ))
    db.commit()
    # ws推送
    asyncio.create_task(ws_manager.broadcast({
        "event": "new_blacklist",
        "data": {
            "userId": body["userId"],
            "username": ret["data"]["user"]["nickname"],
            "reason": body["reason"],
            "operator": body.get("operator", botid),
            "created_at": time.time()
        }
    }))
    # 群聊推送
    sendMsg(FFL_ID, "group", "markdown",
            f'#### **{ret["data"]["user"]["nickname"]}**(`{body["userId"]}`)被加入黑名单，原因：`{body["reason"]}`\n操作人：**{body.get("operator", botid)}**')
    response.status_code = 200
    return {"msg": "success", "data": {}}


@router.get("/list")
async def listuser(response: Response, db: Session = Depends(get_db), userid=""):
    if userid:
        users = db.query(Blacklist).filter(Blacklist.userid == userid).all()
    else:
        users = db.query(Blacklist).all()
    blacklist = []
    for user in users:
        blacklist.append({
            "userId": user.userid,
            "username": user.username,
            "reason": user.reason,
            "operator": user.operator,
            "created_at": user.created_at.timestamp()
        })
    response.status_code = 200
    return {"msg": "success", "data": {"blacklist": blacklist}}


@router.post("/del")
async def deluser(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").strip()
    if not token:
        response.status_code = 401
        return {"msg": "无效的Token", "data": {}}
    botid = db.query(Token.botid).filter(Token.token == token).all()
    if not botid:
        response.status_code = 401
        return {"msg": "无效的Token", "data": {}}
    botid = botid[0][0]
    body = await request.json()
    if db.query(Blacklist).filter(Blacklist.userid == body["userId"]).delete() == 0:
        response.status_code = 400
        return {"msg": "用户不在黑名单中", "data": {}}
    db.commit()
    asyncio.create_task(ws_manager.broadcast({
        "event": "del_blacklist",
        "data": {
            "userId": body["userId"],
            "reason": body["reason"],
            "operator": body.get("operator", botid),
            "created_at": time.time()
        }
    }))
    sendMsg(FFL_ID, "group", "markdown",
            f'#### **{body["userId"]}**被移除黑名单，原因：`{body["reason"]}`\n操作人：**{body.get("operator", botid)}**')
    response.status_code = 200
    return {"msg": "success", "data": {}}


@router.post("/bot")
async def bot(request: Request, response: Response, db: Session = Depends(get_db)):
    if request.client.host not in ["192.144.130.26", "82.157.170.175", "8.140.51.215", "81.70.146.99", "120.53.8.151", "8.140.254.106"]:
        response.status_code = 403
        return {"msg": "无效的IP", "data": {}}
    body = await request.json()
    body = resolvBody(body)
    if not body:
        response.status_code = 400
        return {"msg": "参数错误", "data": {}}
    if body['eventType'] == 'message.receive.instruction':
        if body["commandName"] == "黑名单列表":
            users = db.query(Blacklist).all()
            msg = '''<details>
    <summary style="color: #8080ff;">黑名单用户列表</summary>
    <div>
        <table>
            <thead>
                <tr style="background-color: #ffffff; color: #000000;">
	                <th style="text-align: left;">用户名</th>
		            <th style="text-align: left;">ID</th>
                    <th style="text-align: left;">原因</th>
                    <th style="text-align: left;">添加人</th>
                    <th style="text-align: left;">添加时间</th>
                </tr>
            </thead>
            <tbody>'''
            for user in users:
                msg += f'''
                <tr style="background-color: #000000; color: #ffffff;">
                    <td>{user.username}</td>
                    <td>{user.userid}</td>
                    <td>{user.reason}</td>
                    <td>{user.operator}</td>
                    <td>{user.created_at.strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>'''
            msg += '''
            </tbody>
        </table>
    </div>
</details>'''
            sendMsg(body['id'], body['recvType'], 'html', msg)
        elif body["commandName"] == "添加黑名单":
            if body["id"] != FFL_ID or body["senderInfo"]["level"] == "member":
                sendMsg(body['id'], body['recvType'], 'text', '你没有权限使用这条指令。')
            else:
                params = body["msg"].split(" ", 2)
                if not params or len(params) < 2 or not params[0].strip() or not params[1].strip():
                    sendMsg(body["id"], body["recvType"], "text", "参数错误")
                    return
                ret = requests.get(
                    f'https://chat-web-go.jwzhd.com/v1/user/homepage?userId={params[0]}').json()
                if not ret["data"]["user"]["userId"]:
                    sendMsg(body["id"], body["recvType"], "text", "用户不存在")
                    return
                db.add(Blacklist(
                    userid=params[0],
                    username=ret["data"]["user"]["nickname"],
                    reason=params[1],
                    operator=body["sender"],
                    created_at=datetime.datetime.fromtimestamp(body["time"])
                ))
                db.commit()
                asyncio.create_task(ws_manager.broadcast({
                    "event": "new_blacklist",
                    "data": {
                        "userId": params[0],
                        "username": ret["nickname"],
                        "reason": params[1],
                        "operator": body["sender"],
                        "created_at": datetime.datetime.fromtimestamp(body["time"])
                    }
                }))
                sendMsg(body["id"], body["recvType"], "text", "已添加")
        elif body["commandName"] == "移除黑名单":
            if body["id"] != FFL_ID or body["senderInfo"]["level"] == "member":
                sendMsg(body['id'], body['recvType'], 'text', '你没有权限使用这条指令。')
            else:
                params = body["msg"].split(" ", 2)
                if len(params) < 2:
                    params.append("无")
                if not params or not params[0].strip():
                    sendMsg(body["id"], body["recvType"], "text", "参数错误")
                    return
                if db.query(Blacklist).filter(Blacklist.userid == params[0]).delete() == 0:
                    sendMsg(body['id'], body['recvType'], 'text', '用户不在黑名单中')
                    return
                db.commit()
                asyncio.create_task(ws_manager.broadcast({
                    "event": "del_blacklist",
                    "data": {
                        "userId": params[0],
                        "reason": params[1],
                        "operator": body["sender"],
                        "created_at": body["time"]
                    }
                }))
                sendMsg(body["id"], body["recvType"], "text", "已移除")
    return


def cleanup_blacklist():
    while True:
        time.sleep(604800)
        db: Session = SessionLocal()
        cleaned = []
        for user in db.query(Blacklist.userid).all():
            if not requests.get(f'https://chat-web-go.jwzhd.com/v1/user/homepage?userId={user[0]}').json()["data"]["user"]["userId"]:
                db.query(Blacklist).filter(
                    Blacklist.userid == user[0]).delete()
                cleaned.append(user[0])
        db.commit()
        asyncio.run(ws_manager.broadcast({
            "event": "auto_clean_blacklist",
            "data": {
                "userIds": cleaned,
                "reason": "用户不存在,自动清理",
                "operator": "system",
                "created_at": time.time()
            }
        }))
        msg = f'''<details>
        <summary style="color: #8080ff;">自动清理的黑名单</summary>
        <div>
            {" ".join(cleaned)}
        </div>
    </details>'''
        sendMsg(FFL_ID, "group", "html", msg)
