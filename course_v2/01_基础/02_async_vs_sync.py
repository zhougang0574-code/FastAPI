"""
【基础 / 02】async def vs def —— 为什么异步是 FastAPI 的灵魂（难点·细拆）

与上一课的区别：
    〔01_基础/01〕所有路由都用普通 def。本课只引入一个新东西：async def，
    并讲清「同步 / 异步」在 FastAPI 里到底差在哪——这是和 Java 最不一样、必须单独搞懂的点。

本课知识点（只讲一个核心概念，因为它没有 Java 类比）：
    1. def 路由     → FastAPI 丢到「线程池」里跑（≈ SpringBoot 每请求一个线程的传统模型）
    2. async def 路由 → 在「单线程事件循环」里跑（≈ Node.js / Spring WebFlux，但写法是同步直觉）
    3. 致命陷阱：在 async def 里调用「阻塞」代码（time.sleep、普通 requests）会卡死整个事件循环
    4. 判断法则：里面 await 的是异步库 → 用 async def；只有阻塞调用或纯 CPU → 用普通 def

为什么需要：
    Java 的 Tomcat 是「一请求一线程」，你几乎不用关心阻塞——线程多就行。
    FastAPI 的高性能来自「单线程事件循环」：一个线程靠 await 在 IO 等待时切去处理别的请求。
    但这有个反直觉的代价——你一旦在 async def 里写了阻塞代码，事件循环被独占，
    所有并发请求一起卡住。这一节就是要把这个「Java 没有的坑」一次讲透。
"""

import asyncio
import time

import httpx
from fastapi import FastAPI

app = FastAPI(title="async vs sync 演示")


# ── 1) 普通 def 路由：FastAPI 自动丢到线程池执行 ──
# 即使这里 time.sleep 阻塞 1 秒，也只是占用线程池里的「一个线程」，
# 不会卡住事件循环，其他请求照常被别的线程处理。
# ≈ SpringBoot 传统 Controller：阻塞没关系，反正线程多。
@app.get("/sync-sleep")
def sync_sleep():
    time.sleep(1)  # 阻塞调用，但在线程池里，安全
    return {"type": "def", "note": "阻塞跑在线程池，不影响事件循环"}


# ── 2) 正确的 async def 路由：await 一个「真异步」的 IO ──
# asyncio.sleep 是异步等待：await 时把控制权交还事件循环，
# 这 1 秒里事件循环可以去处理成千上万个别的请求。这才是 FastAPI 高并发的来源。
@app.get("/async-sleep")
async def async_sleep():
    await asyncio.sleep(1)  # 异步等待，期间事件循环不空转
    return {"type": "async def", "note": "await 期间事件循环去服务别的请求"}


# ── 3) 反面教材：async def 里写阻塞代码（绝对不要这样） ──
# time.sleep 是阻塞的，它没有 await，会霸占事件循环整整 1 秒，
# 这期间「所有」并发请求（包括上面两个路由）全部被卡住。这是 FastAPI 最经典的性能事故。
@app.get("/async-blocking-BAD")
async def async_blocking_bad():
    time.sleep(1)  # ✗ 致命：在事件循环里同步阻塞，拖垮整个服务的并发
    return {"type": "async def + blocking", "note": "错误示范：会卡死事件循环"}


# ── 4) 真实场景：异步访问外部接口，就该用 async def ──
# httpx.AsyncClient 是异步 HTTP 客户端（≈ 异步版 RestTemplate/WebClient）。
# 调外部 API 是典型 IO 等待，用 await 让出事件循环，并发能力立刻上来。
@app.get("/fetch")
async def fetch():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://httpbin.org/uuid")
    return {"type": "async def + httpx", "data": resp.json()}


"""
执行流程图
==========

                     请求进入 FastAPI
                          │
            ┌─────────────┴──────────────┐
            ▼                            ▼
       路由是 def                   路由是 async def
            │                            │
   FastAPI 丢进线程池              直接在事件循环里跑
   （一函数占一线程）                     │
            │                  ┌─────────┴──────────┐
   阻塞也没事，                 ▼                    ▼
   线程池扛着                await 异步IO        写了阻塞调用(time.sleep)
            │              （让出循环，         （霸占循环，✗）
            ▼                别的请求继续）            │
        返回响应                  │                整个服务卡住
                                  ▼
                              返回响应

判断该用哪个（背下来）：
    用到的库提供 await 接口（httpx / 异步数据库驱动 / asyncio）  → async def
    只有阻塞调用（requests / time.sleep / 同步 SQLAlchemy）       → 普通 def（让 FastAPI 丢线程池）
    纯 CPU 计算（大循环 / 图像处理）                              → 普通 def（async 救不了 CPU 密集）

实测建议：
    用两个终端，一个连发 /async-sleep，一个连发 /async-blocking-BAD，
    观察后者会把前者也一起拖慢——这就是阻塞事件循环的代价。


核心知识点 ★
============
★ def → 线程池（Java 直觉，阻塞安全）；async def → 单线程事件循环（高并发但禁止阻塞）
★ 高并发的来源是 await：IO 等待时让出循环去服务别的请求，而不是堆线程
★ 头号事故：在 async def 里调用阻塞代码（time.sleep / requests / 同步 DB），会拖垮全局并发
★ 不确定就用普通 def——FastAPI 会安全地丢线程池，绝不会比写错的 async 更糟
★ 后续凡是 IO 课（数据库 〔09_数据库SQLAlchemy/01〕、后台任务 〔07_中间件与后台/02〕）都会回到这个选择
"""
