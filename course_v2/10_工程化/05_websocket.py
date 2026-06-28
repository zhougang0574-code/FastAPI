"""
【工程化 / 05】WebSocket 双向通信（进阶）

与上一课的区别：
    前面全是 HTTP「请求-响应」一来一回。WebSocket 是「长连接、双向、可服务器主动推」，
    用于聊天、实时通知、协同编辑——HTTP 做不到服务器主动推。

本课知识点：
    1. @app.websocket 定义 WebSocket 端点
    2. await ws.accept() 握手、receive_text/send_text 收发、循环保持连接
    3. WebSocketDisconnect 捕获断开
    4. 简单广播：维护连接列表，群发消息

为什么需要：
    需要服务器主动推、低延迟双向的场景，HTTP 轮询太笨。WebSocket 是标准方案
    （≈ Spring 的 @ServerEndpoint / STOMP）。

    测试：用 /docs 不行（不支持 ws）；可用浏览器控制台 new WebSocket("ws://127.0.0.1:8000/ws")。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="WebSocket")


# 回声端点：收到什么原样回送
@app.websocket("/ws")
async def ws_echo(ws: WebSocket):
    await ws.accept()                         # 握手，建立连接
    try:
        while True:                           # 循环保持长连接
            msg = await ws.receive_text()     # 等客户端发消息（异步阻塞）
            await ws.send_text(f"echo: {msg}")  # 服务器主动回发
    except WebSocketDisconnect:
        print("[ws] 客户端断开")              # 客户端关闭时跳出


# 极简广播：维护所有活跃连接，一人发、全员收
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: str):
        for conn in self.active:              # 群发给所有在线连接
            await conn.send_text(message)


manager = ConnectionManager()


@app.websocket("/chat/{name}")
async def chat(ws: WebSocket, name: str):
    await manager.connect(ws)
    await manager.broadcast(f"[系统] {name} 加入了")
    try:
        while True:
            text = await ws.receive_text()
            await manager.broadcast(f"{name}: {text}")
    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast(f"[系统] {name} 离开了")


"""
执行流程图
==========

HTTP：  请求 ──▶ 响应（一次性，连接即关，服务器不能主动推）

WebSocket：
    客户端 ──握手 accept()──▶ 建立长连接
        ⇅  receive_text / send_text  双向收发（服务器可主动 push）
    客户端关闭 ──▶ WebSocketDisconnect ──▶ 清理

广播：
    多个连接存进 manager.active
    任一连接发消息 → manager.broadcast → 遍历群发给所有人

核心知识点 ★
============
★ @app.websocket 定义端点；await ws.accept() 握手后用 receive/send 双向收发
★ while True 循环保持长连接，用 try/except WebSocketDisconnect 捕获断开做清理
★ 服务器可主动 send（HTTP 做不到），适合聊天/实时通知/推送
★ 广播 = 维护连接列表 + 遍历群发；生产多进程要用 Redis 等做跨进程广播
★ WebSocket 端点天然是 async（全程 await），别在里面写阻塞代码（回顾 〔01/02〕）
"""
