import requests,json
rs = requests.Session()
rs.headers['referer'] = 'http://myapp.jwznb.com'

def setToken(token: str):
    global tok
    tok = token

def editMsg(msgId: str, recvId: str, recvType: str, contentType: str, content='', Key='', parentId='', buttons=False):
    data = {
        'msgId': msgId,
        'recvId': recvId,
        'recvType': recvType,
        'contentType': contentType,
        'content': {
            'text': content
        },
        'parentId': parentId
    }
    if contentType == 'image':
        data['content'] = {'imageKey': Key}
    elif contentType == 'file':
        data['content'] = {'fileKey': Key}
    elif contentType == 'video':
        data['content'] = {'videoKey': Key}
    if buttons:
        data['content']['buttons'] = buttons
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/edit?token={tok}'
    response = rs.post(url, json=data, timeout=15)
    return response.json()

def sendMsg(recvId: str, recvType: str, contentType: str, content='', Key='', parentId='', ats=[], buttons=False):
    data = {
        'recvId': recvId,
        'recvType': recvType,
        'contentType': contentType,
        'content': {
            'text': content,
            'at': ats
        },
        'parentId': parentId
    }
    if contentType == 'image':
        data['content'] = {'imageKey': Key}
    elif contentType == 'file':
        data['content'] = {'fileKey': Key}
    elif contentType == 'video':
        data['content'] = {'videoKey': Key}
    if buttons:
        data['content']['buttons'] = buttons
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/send?token={tok}'
    response = rs.post(url, json=data, timeout=15)
    return response.json()['data']

def setBoard(contentType: str, content: str, Global=False, recvId='', recvType='', expireTime=0, memberId=''):
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/board-all?token={tok}'
    data = {
        'contentType': contentType,
        'content': content,
        'expireTime': expireTime
    }
    if not Global:
        data['chatId'] = recvId
        data['chatType'] = recvType
        data['memberId'] = memberId
        url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/board?token={tok}'
    response = rs.post(url, json=data, timeout=15)
    return response.json()

def dismissBoard(Global=False, recvId='', recvType=''):
    data = {}
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/board-all-dismiss?token={tok}'
    if not Global:
        data['chatId'] = recvId
        data['chatType'] = recvType
        url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/board-dismiss?token={tok}'
    response = rs.post(url, json=data, timeout=15)
    return response.json()

def recallMsg(msgId: str, recvId: str, recvType: str):
    data = {
        'msgId': msgId,
        'chatId': recvId,
        'chatType': recvType
    }
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/recall?token={tok}'
    response = rs.post(url, json=data, timeout=15)
    return response.json()

def msgList(recvId: str, recvType: str, messageId='', before=0, after=0):
    url = f'https://chat-go.jwzhd.com/open-apis/v1/bot/messages?token={tok}&chat-id={recvId}&chat-type={recvType}&message-id={messageId}&before={str(before)}&after={str(after)}'
    response = rs.get(url, timeout=15)
    return response.json()

def resolvBody(body):
    if 'header' not in body:
        return
    msgbox = {}
    msgbox['time'] = body['header']['eventTime']
    msgbox['eventType'] = eventType = body['header']['eventType']
    if eventType == 'bot.setting':
        msgbox['id'] = body['event']['groupId']
        msgbox['setjson'] = json.loads(body['event']['settingJson'])
        return msgbox
    if eventType == 'button.report.inline':
        msgbox['msgId'] = body['event']['msgId']
        msgbox['sender'] = body['event']['userId']
        msgbox['id'] = body['event']['recvId']
        msgbox['recvType'] = body['event']['recvType']
        msgbox['value'] = body['event']['value']
        return msgbox
    try:
        msgbox['type'] = body['event']['chat']['chatType']
    except:
        msgbox['type'] = body['event']['chatType']
    if eventType == 'message.receive.instruction':
        msgbox['commandName'] = body['event']['message']['commandName']
    if eventType == 'message.receive.normal' or eventType == 'message.receive.instruction':
        msgbox['contentType'] = body['event']['message']['contentType']
        msgbox['msgId'] = body['event']['message']['msgId']
        if 'parentId' in body['event']['message'].keys():
            msgbox['parentId'] = body['event']['message']['parentId']
        if 'at' in body['event']['message']['content'].keys():
            msgbox['ats'] = body['event']['message']['content']['at']
        if msgbox['contentType'] in ('text', 'markdown', 'post', 'html'):
            msgbox['msg'] = body['event']['message']['content']['text']
        elif msgbox['contentType'] == 'image':
            msgbox['url'] = body['event']['message']['content']['imageUrl']
        elif msgbox['contentType'] == 'expression':
            msgbox['url'] = 'https://chat-img.jwznb.com/' + \
                body['event']['message']['content']['imageName']
        elif msgbox['contentType'] == 'file':
            msgbox['fileName'] = body['event']['message']['content']['fileName']
            msgbox['url'] = 'https://chat-file.jwznb.com/' + \
                body['event']['message']['content']['fileUrl']
        elif msgbox['contentType'] == 'form':
            msgbox['form'] = body['event']['message']['content']['formJson']
        msgbox['sender'] = body['event']['sender']['senderId']
        msgbox['senderInfo'] = {'nickname': body['event']['sender']
                                ['senderNickname'], 'level': body['event']['sender']['senderUserLevel']}
    if msgbox['type'] == 'group' and (eventType == 'message.receive.normal' or eventType == 'message.receive.instruction'):
        msgbox['id'] = body['event']['message']['chatId']
    elif msgbox['type'] == 'group':
        msgbox['id'] = body['event']['chatId']
        msgbox['nickname'] = body['event']['nickname']
        msgbox['avatar'] = body['event']['avatarUrl']
        msgbox['sender'] = body['event']['userId']
    elif eventType == 'message.receive.normal' or eventType == 'message.receive.instruction':
        msgbox['id'] = body['event']['sender']['senderId']
    else:
        msgbox['id'] = body['event']['userId']
        msgbox['sender'] = body['event']['userId']
        msgbox['nickname'] = body['event']['nickname']
        msgbox['avatar'] = body['event']['avatarUrl']
    if msgbox['type'] == 'group':
        msgbox['recvType'] = 'group'
    elif msgbox['type'] == 'bot':
        msgbox['recvType'] = 'user'
    return msgbox