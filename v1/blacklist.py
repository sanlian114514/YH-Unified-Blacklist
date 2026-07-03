"""黑名单请求处理API
"""
from fastapi import APIRouter, Request, Response, Depends
from .db import get_db, Session, Blacklist, Token, SessionLocal
from .websocket import manager as ws_manager
from .YHlib import *
import time
import asyncio
import datetime
import uuid

router = APIRouter(prefix="/blacklist", tags=["Blacklist"])

BLACK_DATA = {}
FFL_ID = "911529425"

def init_data():
    global BLACK_DATA
    db = SessionLocal()
    try:
        users = db.query(Blacklist).all()
        BLACK_DATA = {
            user.userid: {
                "userid": user.userid,
                "username": user.username,
                "reason": user.reason,
                "operator": user.operator,
                "created_at": user.created_at.timestamp()
            }
            for user in users
        }
        return BLACK_DATA
    finally:
        db.close()
    

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
    global BLACK_DATA
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
    
    # 检查内存缓存
    if body["userId"] in BLACK_DATA:
        response.status_code = 400
        return {"msg": "用户已在黑名单中", "data": {}}
    
    # FTs：原requests.get
    ret = await getUserInfo(body["userId"])
    if not ret["data"]["user"]["userId"]:
        response.status_code = 400
        return {"msg": "用户不存在", "data": {}}
    
    # 添加到内存缓存
    BLACK_DATA[body["userId"]] = {
        "userid": body["userId"],
        "username": ret["data"]["user"]["nickname"],
        "reason": body["reason"],
        "operator": body.get("operator", botid),
        "created_at": time.time()
    }
    
    # FTs：持久化到数据库
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
    await sendMsg(FFL_ID, "group", "markdown",
            f'#### **{ret["data"]["user"]["nickname"]}**(`{body["userId"]}`)被加入黑名单，原因：`{body["reason"]}`\n操作人：**{body.get("operator", botid)}**')
    response.status_code = 200
    return {"msg": "success", "data": {}}


@router.get("/list")
async def listuser(response: Response, userid=""):
    # 有userid用查userid，没userid返回全部
    if userid:
        # 从内存缓存中查找
        if userid in BLACK_DATA:
            user_data = BLACK_DATA[userid]
            blacklist = [{
                "userId": user_data["userid"],
                "username": user_data["username"],
                "reason": user_data["reason"],
                "operator": user_data["operator"],
                "created_at": user_data["created_at"]
            }]
        else:
            blacklist = []
    else:
        blacklist = [{
            "userId": data["userid"],
            "username": data["username"],
            "reason": data["reason"],
            "operator": data["operator"],
            "created_at": data["created_at"]
        } for data in BLACK_DATA.values()]
    
    response.status_code = 200
    return {"msg": "success", "data": {"blacklist": blacklist}}


@router.post("/del")
async def deluser(request: Request, response: Response, db: Session = Depends(get_db)):
    global BLACK_DATA
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
    
    # 检查内存缓存
    if body["userId"] not in BLACK_DATA:
        response.status_code = 400
        return {"msg": "用户不在黑名单中", "data": {}}
    
    # 从数据库中删除
    db.query(Blacklist).filter(Blacklist.userid == body["userId"]).delete()
    db.commit()

    # 再从内存缓存中删除
    del BLACK_DATA[body["userId"]]
    
    asyncio.create_task(ws_manager.broadcast({
        "event": "del_blacklist",
        "data": {
            "userId": body["userId"],
            "reason": body["reason"],
            "operator": body.get("operator", botid),
            "created_at": time.time()
        }
    }))
    await sendMsg(FFL_ID, "group", "markdown",
            f'#### **{body["userId"]}**被移除黑名单，原因：`{body["reason"]}`\n操作人：**{body.get("operator", botid)}**')
    response.status_code = 200
    return {"msg": "success", "data": {}}


# 对接yunhu
@router.post("/bot")
async def bot(request: Request, response: Response, db: Session = Depends(get_db)):
    global BLACK_DATA
    # if request.client.host not in ["192.144.130.26", "82.157.170.175", "8.140.51.215", "81.70.146.99", "120.53.8.151", "8.140.254.106"]:
    #     response.status_code = 403
    #     return {"msg": "无效的IP", "data": {}}
    body = await request.json()
    body = resolvBody(body)
    if not body:
        response.status_code = 400
        return {"msg": "参数错误", "data": {}}
    if body['eventType'] == 'message.receive.instruction':
        if body["commandName"] == "黑名单列表":
            # 从内存缓存读取
            users_data = BLACK_DATA.values()
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
            for user_data in users_data:
                created_time = datetime.datetime.fromtimestamp(user_data["created_at"])
                msg += f'''
                <tr style="background-color: #000000; color: #ffffff;">
                    <td>{user_data["username"]}</td>
                    <td>{user_data["userid"]}</td>
                    <td>{user_data["reason"]}</td>
                    <td>{user_data["operator"]}</td>
                    <td>{created_time.strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>'''
            msg += '''
            </tbody>
        </table>
    </div>
</details>'''
            await sendMsg(body['id'], body['recvType'], 'html', msg)
        elif body["commandName"] == "添加黑名单":
            if body["id"] != FFL_ID or body["senderInfo"]["level"] == "member":
                await sendMsg(body['id'], body['recvType'], 'text', '你没有权限使用这条指令。')
            else:
                params = body["msg"].split(" ", 2)
                if not params or len(params) < 2 or not params[0].strip() or not params[1].strip():
                    await sendMsg(body["id"], body["recvType"], "text", "参数错误")
                    return
                
                # 检查内存缓存
                if params[0] in BLACK_DATA:
                    await sendMsg(body["id"], body["recvType"], "text", "用户已在黑名单中")
                    return
                
                # FTs：原requests.get
                ret = await getUserInfo(params[0])
                if not ret["data"]["user"]["userId"]:
                    response.status_code = 400
                    return {"msg": "用户不存在", "data": {}}
                
                # 添加到内存缓存
                BLACK_DATA[params[0]] = {
                    "userid": params[0],
                    "username": ret["data"]["user"]["nickname"],
                    "reason": params[1],
                    "operator": body["sender"],
                    "created_at": time.time()# 如果三连这边正常可以改回来
                }
                
                # FTs：持久化到数据库
                db.add(Blacklist(
                    userid=params[0],
                    username=ret["data"]["user"]["nickname"],
                    reason=params[1],
                    operator=body["sender"],
                    created_at=datetime.datetime.now()# 如果三连这边正常可以改回来
                ))
                db.commit()
                
                asyncio.create_task(ws_manager.broadcast({
                    "event": "new_blacklist",
                    "data": {
                        "userId": params[0],
                        "username": ret["data"]["user"]["nickname"],
                        "reason": params[1],
                        "operator": body["sender"],
                        "created_at": time.time()# 如果三连这边正常可以改回来
                    }
                }))
                await sendMsg(body["id"], body["recvType"], "text", "已添加")
        elif body["commandName"] == "移除黑名单":
            if body["id"] != FFL_ID or body["senderInfo"]["level"] == "member":
                await sendMsg(body['id'], body['recvType'], 'text', '你没有权限使用这条指令。')
            else:
                params = body["msg"].split(" ", 2)
                if len(params) < 2:
                    params.append("无")
                if not params or not params[0].strip():
                    await sendMsg(body["id"], body["recvType"], "text", "参数错误")
                    return
                
                # 检查内存缓存
                if params[0] not in BLACK_DATA:
                    await sendMsg(body['id'], body['recvType'], 'text', '用户不在黑名单中')
                    return

                # 从数据库中删除
                db.query(Blacklist).filter(Blacklist.userid == params[0]).delete()
                db.commit()
                
                # 从内存缓存中删除
                del BLACK_DATA[params[0]]

                asyncio.create_task(ws_manager.broadcast({
                    "event": "del_blacklist",
                    "data": {
                        "userId": params[0],
                        "reason": params[1],
                        "operator": body["sender"],
                        "created_at": time.time()# 如果三连这边正常可以改回来
                    }
                }))
                await sendMsg(body["id"], body["recvType"], "text", "已移除")
    return {"msg": "success", "data": {}}


async def cleanup_blacklist():
    global BLACK_DATA
    while True:
        await asyncio.sleep(604800)  # 7天
        db = SessionLocal()
        black_data_snapshot = BLACK_DATA.copy()
        cleaned = []
        
        try:
            blacklist_users = db.query(Blacklist.userid).all()

            for user in blacklist_users:
                user_id = user[0]
                ret = await getUserInfo(user_id)
                
                if not ret or not ret.get("data", {}).get("user", {}).get("userId"):
                    db.query(Blacklist).filter(
                        Blacklist.userid == user_id
                    ).delete()
                    
                    if user_id in BLACK_DATA:
                        del BLACK_DATA[user_id]
                    
                    cleaned.append(user_id)
                
                await asyncio.sleep(0.5)
            
            if cleaned:
                db.commit()  # 只在有清理时提交
                await ws_manager.broadcast({
                    "event": "auto_clean_blacklist",
                    "data": {
                        "userIds": cleaned,
                        "reason": "用户不存在,自动清理",
                        "operator": "system",
                        "created_at": time.time()
                    }
                })
                
                # 发送通知消息
                msg = f'''<details>
    <summary style="color: #8080ff;">自动清理的黑名单</summary>
    <div>
        {" ".join(cleaned)}
    </div>
</details>'''
                await sendMsg(FFL_ID, "group", "html", msg)
            else:
                db.rollback()  # 没有更改，回滚
        except Exception as e:
            db.rollback()
            BLACK_DATA = black_data_snapshot # 恢复 BLACK_DATA（如果出错）
            print(f"清理黑名单出错: {e}")
        finally:
            db.close()
