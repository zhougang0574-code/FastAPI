"""
【响应 / 02】自定义 Response / 多形态返回 / 流式响应（进阶·合并）

与上一课的区别：
    〔04_响应/01〕返回的都是「dict/模型 → 自动 JSON」。本课处理需要绕过默认 JSON
    的场景：自定义状态码与响应头、返回多种结构、流式（边生成边发）。

本课知识点（合并讲）：
    1. 直接返回 Response / JSONResponse 自定义状态码、headers  —— ≈ ResponseEntity
    2. Union 返回多种结构（用 response_model=Union[...]）        —— ≈ 多态返回
    3. StreamingResponse 流式返回（大文件 / SSE / 边算边发）      —— ≈ StreamingResponseBody

为什么需要：
    下载大文件不能先全读进内存；AI 流式输出、Server-Sent Events 需要边产边发。
    需要精确控制响应头/状态码时，直接构造 Response 比返回 dict 更灵活。
"""

import asyncio
from typing import Union

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="自定义响应与流式")


# 直接返回 JSONResponse：自定义状态码 + 响应头（≈ ResponseEntity.status(...).header(...)）
@app.get("/custom")
def custom():
    return JSONResponse(
        status_code=418,
        content={"msg": "I'm a teapot"},
        headers={"X-Custom-Header": "hello"},
    )


# Union 多形态返回：成功返回 User，失败返回 Error，两种结构
class User(BaseModel):
    id: int
    name: str


class Error(BaseModel):
    error: str


@app.get("/users/{uid}", response_model=Union[User, Error])
def get_user(uid: int):
    if uid == 0:
        return Error(error="invalid id")
    return User(id=uid, name="Tom")


# StreamingResponse：边生成边发，不把全部内容堆进内存
# generator 每 yield 一段就立刻发出去（≈ SSE / 大文件下载 / AI 打字机）
async def number_stream():
    for i in range(5):
        yield f"data: chunk {i}\n\n"
        await asyncio.sleep(0.3)   # 异步等待，期间不阻塞事件循环


@app.get("/stream")
def stream():
    return StreamingResponse(number_stream(), media_type="text/event-stream")


"""
执行流程图
==========

普通返回 dict/模型 → FastAPI 自动包成 JSONResponse（默认路径）
自定义需求时：
    ├─ JSONResponse(status_code, content, headers) → 精确控制状态码/头
    ├─ response_model=Union[A,B]                    → 允许多种结构
    └─ StreamingResponse(generator)                 → 边 yield 边发，不堆内存
                │
                ▼
        客户端逐块收到（SSE / 大文件 / 打字机效果）

核心知识点 ★
============
★ 返回 dict/模型走默认 JSON；要控状态码/响应头就直接返回 JSONResponse（≈ ResponseEntity）
★ response_model=Union[A, B] 表达「可能返回多种结构」
★ StreamingResponse 接一个生成器，边 yield 边发，适合大文件/SSE/AI 流式
★ 流式里用 async generator + await asyncio.sleep，别用阻塞 sleep（回顾 〔01_基础/02〕）
★ 用 StreamingResponse 做 SSE 时 media_type 用 text/event-stream
"""
