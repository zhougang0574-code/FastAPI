"""
【依赖注入 / 02】yield 依赖：资源的「打开→使用→关闭」（难点·细拆）

与上一课的区别：
    〔06_依赖注入/01〕的依赖都是 return 一个值就结束。本课的依赖用 yield，
    yield 之后还有「收尾代码」——这是 Java 没有直接对应、必须单独搞懂的点。

本课知识点（只讲一个核心概念）：
    1. yield 依赖：yield 前=准备资源，yield 后=释放资源
    2. yield 之后的代码在「响应返回之后」才执行（自动收尾）
    3. 即使路由抛异常，yield 后的清理也会执行（类似 finally）

为什么需要：
    数据库会话、文件句柄、网络连接都需要「用完必须关」。yield 依赖让 FastAPI
    在请求结束时自动帮你关——相当于 Spring 的事务/连接管理 + try-with-resources，
    但写法是 Python 的生成器。数据库域（09）的 get_db 全靠它，必须先理解透。
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

app = FastAPI(title="yield 依赖")


# 模拟一个需要「开/关」的资源（≈ 数据库会话 Session）
class FakeSession:
    def __init__(self):
        self.closed = False
        print("[资源] 打开会话")

    def query(self, x):
        return f"查询结果: {x}"

    def close(self):
        self.closed = True
        print("[资源] 关闭会话")   # 这行会在响应返回后才打印


# yield 依赖：yield 之前准备资源，yield 之后释放。
# try/finally 保证「即使路由里抛异常，finally 也会关资源」（≈ try-with-resources）
def get_session():
    session = FakeSession()
    try:
        yield session          # 把 session 注入给路由；函数在此「暂停」
    finally:
        session.close()        # 响应返回后，从这里恢复执行，关闭资源


SessionDep = Annotated[FakeSession, Depends(get_session)]


@app.get("/data/{x}")
def read_data(x: int, session: SessionDep):
    # 这里能直接用 session，用完不用手动关——yield 依赖会自动收尾
    return {"result": session.query(x)}


@app.get("/boom")
def boom(session: SessionDep):
    # 即便这里抛异常，get_session 的 finally 仍会执行，session 照样被关闭
    raise HTTPException(500, "故意出错")


"""
执行流程图
==========

请求进入 /data/5
    │
    ▼
get_session() 执行到 yield：
    [资源] 打开会话  →  yield session（函数暂停，把 session 交给路由）
    │
    ▼
路由 read_data(session) 执行 → 返回响应
    │
    ▼
响应发出后，get_session 从 yield 处恢复 → 进入 finally：
    [资源] 关闭会话

抛异常的情况（/boom）：
    路由 raise → 控制权回到 get_session 的 finally → 仍然关闭会话 → 再向上抛异常

核心知识点 ★
============
★ yield 依赖 = 资源生命周期管理：yield 前准备、yield 后释放（≈ try-with-resources）
★ yield 之后的代码在「响应返回之后」执行，是自动收尾的关键
★ 用 try/finally 包住 yield，保证路由抛异常时资源也能被释放
★ 这就是数据库 get_db 的标准范式，〔09_数据库SQLAlchemy/01〕直接用它
★ 与普通 return 依赖的唯一区别：return 拿值就结束，yield 还能在请求后做清理
"""
