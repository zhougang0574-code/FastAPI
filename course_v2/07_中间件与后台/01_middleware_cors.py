"""
【中间件与后台 / 01】中间件 + CORS（易点·合并）

与上一课的区别：
    依赖注入是「按需注入到某些路由」。中间件是「拦截所有请求/响应」的更外层机制，
    对每个请求都生效。这正是 SpringBoot 的 Filter / HandlerInterceptor。

本课知识点（合并讲）：
    1. @app.middleware("http") 注册中间件，拦截所有请求/响应  —— ≈ Filter / Interceptor
    2. call_next(request) 把请求交给下一层（路由或下个中间件） —— ≈ chain.doFilter
    3. 洋葱模型：请求进时正序、响应出时逆序                    —— ≈ Filter 链
    4. CORSMiddleware 解决浏览器跨域                            —— ≈ CorsFilter / @CrossOrigin

为什么需要：
    统计耗时、加统一响应头、记录日志这类「横切所有请求」的逻辑，用中间件最合适。
    CORS 则是前后端分离项目必配，否则浏览器会拦掉跨域请求。
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="中间件与 CORS")


# 自定义 HTTP 中间件：统计每个请求耗时，加到响应头
# ≈ 一个 Filter：先处理请求 → 放行 → 再处理响应
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)        # 放行到下一层（≈ chain.doFilter），拿到响应
    response.headers["X-Process-Time"] = f"{time.time() - start:.4f}"
    return response


# CORS 中间件：允许指定来源的浏览器跨域访问（≈ CorsFilter）
# add_middleware 注册的中间件比 @app.middleware 更靠外层
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # 允许的前端地址；["*"] 表示全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"msg": "看响应头里的 X-Process-Time"}


"""
执行流程图（洋葱模型）
======================

请求 →  CORSMiddleware  →  add_process_time  →  路由函数
                                                    │
响应 ←  CORSMiddleware  ←  add_process_time  ←──────┘
        （加 CORS 头）      （加 X-Process-Time）

★ 进入时正序穿过，返回时逆序穿出，像剥洋葱——和 Servlet Filter 链一模一样

核心知识点 ★
============
★ @app.middleware("http") 拦截所有请求/响应（≈ Filter），await call_next 放行（≈ doFilter）
★ 洋葱模型：请求正序进、响应逆序出；后加的 add_middleware 在更外层
★ 中间件适合横切逻辑：耗时统计、统一响应头、日志、限流
★ CORSMiddleware 是前后端分离必配，allow_origins 生产环境别用 ["*"] 配合 credentials
★ 中间件是异步的（async def + await call_next），别在里面写阻塞代码
"""
