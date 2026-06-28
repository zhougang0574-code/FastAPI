"""
【工程化 / 03】生命周期 lifespan：启动/关闭钩子

与上一课的区别：
    前面应用「一启动就绪」。但真实应用启动时要建连接池、加载模型、预热缓存，
    关闭时要优雅释放。本课用 lifespan 挂这两个钩子——就是 @PostConstruct / @PreDestroy。

本课知识点：
    1. @asynccontextmanager 写 lifespan：yield 前=启动、yield 后=关闭  —— ≈ 容器启停钩子
    2. FastAPI(lifespan=...) 注册
    3. 用 app.state 存全局资源（连接池、模型等），路由里取用
    4. lifespan 取代了旧的 @app.on_event("startup"/"shutdown")（已废弃）

为什么需要：
    数据库连接池、ML 模型这类「全应用共享、启动建一次、关闭释放」的资源，
    必须挂在生命周期上。这与 yield 依赖（每请求级）不同——lifespan 是应用级。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request


# 一个假的「全局资源」：假装是连接池 / 已加载的模型
class FakePool:
    def __init__(self):
        print("[启动] 创建连接池")

    def close(self):
        print("[关闭] 释放连接池")


# lifespan：yield 之前在「应用启动时」跑，yield 之后在「应用关闭时」跑
# 结构上很像 yield 依赖，但作用域是「整个应用」而非「单个请求」
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 启动阶段（≈ @PostConstruct）──
    app.state.pool = FakePool()      # 把全局资源存到 app.state
    yield                            # 应用运行中……
    # ── 关闭阶段（≈ @PreDestroy）──
    app.state.pool.close()


app = FastAPI(title="生命周期", lifespan=lifespan)


@app.get("/")
def root(request: Request):
    # 路由里通过 request.app.state 取启动时建好的全局资源
    pool = request.app.state.pool
    return {"pool_ready": pool is not None}


"""
执行流程图
==========

uvicorn 启动应用
    │
    ▼
lifespan: yield 之前 → 建连接池/加载模型，存入 app.state   （≈ @PostConstruct）
    │
    ▼
应用运行，处理所有请求（路由用 request.app.state.xxx 取资源）
    │
    ▼（收到关闭信号）
lifespan: yield 之后 → 释放资源                            （≈ @PreDestroy）

作用域对比：
    lifespan        → 应用级：启动建一次、关闭释放一次（连接池、模型）
    yield 依赖〔06/02〕→ 请求级：每请求建一个、请求结束释放（DB 会话）

核心知识点 ★
============
★ lifespan = 应用级启停钩子：@asynccontextmanager，yield 前启动、yield 后关闭
★ 全局共享资源（连接池/模型/缓存）存 app.state，路由经 request.app.state 取
★ 区分作用域：lifespan 应用级 vs yield 依赖请求级，别混用
★ lifespan 已取代废弃的 @app.on_event("startup"/"shutdown")
★ 配置在启动时读一次也常放这里（结合 〔10/02〕的 Settings）
"""
