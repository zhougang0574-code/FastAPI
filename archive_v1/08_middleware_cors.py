"""
第 8 课：中间件与 CORS

学习要点：
1. 中间件拦截所有请求和响应（AOP 思想，与路由逻辑解耦）
2. @app.middleware("http") 注册自定义中间件
3. call_next(request) 把请求传给下一层（路由或下一个中间件）
4. CORSMiddleware 解决浏览器跨域（CORS）问题
5. 中间件执行顺序：最后注册的最先执行（洋葱模型）
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# ── 添加中间件 ──
# 注意：add_middleware 的调用顺序决定执行顺序（反序）

# CORSMiddleware：解决前端跨域请求被浏览器拦截的问题
# allow_origins=["*"] 允许所有来源（开发环境用，生产换具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 生产：["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],            # 允许所有 HTTP 方法
    allow_headers=["*"],
)

# TrustedHostMiddleware：防止 HTTP Host Header 攻击
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"],
)


# ── 自定义中间件：记录请求处理时间 ──

# @app.middleware("http") 注册的中间件捕获所有 HTTP 请求
# request: 进来的请求
# call_next: 调用下游（继续处理，必须 await）
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    # 在每个响应头里加上处理时长，方便监控接口性能
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    return response


# ── 自定义中间件：请求日志 ──

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 请求进来时记录基本信息
    print(f"[LOG] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[LOG] Status: {response.status_code}")
    return response


# ── 自定义中间件：全局错误捕获 ──

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        # 捕获未处理的异常，避免服务器崩溃
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": str(exc)},
        )


@app.get("/")
def index():
    return {"message": "Hello! Check X-Process-Time in response headers."}


@app.get("/slow")
async def slow_endpoint():
    import asyncio
    await asyncio.sleep(0.1)
    return {"message": "Took ~100ms"}


"""
中间件执行顺序（洋葱模型）
==========================

请求进入
    │
    ▼
catch_exceptions_middleware（最后注册，最先执行）
    │
    ▼
log_requests
    │
    ▼
add_process_time_header
    │
    ▼
TrustedHostMiddleware
    │
    ▼
CORSMiddleware
    │
    ▼
路由处理函数（核心逻辑）
    │
    ▼（响应往回走，顺序反过来）
CORSMiddleware（加 Access-Control 头）
    │
    ▼
add_process_time_header（加 X-Process-Time 头）
    │
    ▼
log_requests（打印状态码）
    │
    ▼
响应返回给客户端


核心知识点 ★
============
★ 中间件是横切关注点：日志、认证、限流、CORS 都适合放在中间件
★ CORS 错误 99% 靠 CORSMiddleware 解决，allow_origins 是关键
★ 必须 await call_next(request)，忘了 await 会导致请求挂起
★ 中间件里修改请求/响应要小心，可能影响所有接口
"""
