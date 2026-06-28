"""
【错误处理 / 01】HTTPException + 自定义异常处理器 + 校验错误（易点·合并）

与上一课的区别：
    前面讲的都是「正常返回」。本课讲「出错怎么返回」：抛标准 HTTP 错误、
    注册全局异常处理器、自定义 422 校验错误格式。

本课知识点（Java 老手秒懂，合并讲）：
    1. HTTPException 抛标准 HTTP 错误（404/400...）       —— ≈ ResponseStatusException
    2. detail 可以是字符串或任意 JSON；headers 自定义响应头
    3. @app.exception_handler 注册全局处理器              —— ≈ @ControllerAdvice + @ExceptionHandler
    4. 覆盖 RequestValidationError 自定义 422 格式          —— ≈ 自定义 MethodArgumentNotValidException 处理

为什么需要：
    资源不存在该返回 404 而不是 500。HTTPException 是「就地抛」，
    exception_handler 是「全局兜底」，两者配合就是 Spring 的 @ControllerAdvice 体系。
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="错误处理")

_DB = {1: "apple", 2: "banana"}


# HTTPException：就地抛标准 HTTP 错误（≈ throw new ResponseStatusException(NOT_FOUND, ...)）
@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in _DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"item {item_id} 不存在",       # detail 可为字符串或任意 JSON
            headers={"X-Error": "not-found"},        # 可附带自定义响应头
        )
    return {"item_id": item_id, "name": _DB[item_id]}


# 自定义业务异常 + 全局处理器（≈ @ControllerAdvice 统一处理某类异常）
class BusinessError(Exception):
    def __init__(self, code: str, msg: str):
        self.code = code
        self.msg = msg


@app.exception_handler(BusinessError)
def handle_business_error(request: Request, exc: BusinessError):
    # 把业务异常统一转成结构化响应
    return JSONResponse(status_code=400, content={"code": exc.code, "message": exc.msg})


@app.get("/pay/{amount}")
def pay(amount: int):
    if amount <= 0:
        raise BusinessError("INVALID_AMOUNT", "金额必须大于 0")   # 被上面的处理器接住
    return {"paid": amount}


# 覆盖 FastAPI 默认的 422 校验错误格式（统一成自家结构）
@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "errors": exc.errors()},
    )


"""
执行流程图
==========

路由函数执行中抛异常
        │
        ├─ raise HTTPException(404, ...)        → FastAPI 内置处理 → 标准错误 JSON + headers
        │
        ├─ raise BusinessError(...)             → 匹配 @exception_handler(BusinessError)
        │                                          → 自定义结构化响应
        │
        └─ 请求参数校验失败（自动抛 RequestValidationError）
                                                 → 匹配自定义 handler → 统一 422 格式

核心知识点 ★
============
★ HTTPException 就地抛标准错误（≈ ResponseStatusException），detail 可字符串/JSON，可带 headers
★ @app.exception_handler(异常类) 注册全局处理器（≈ @ControllerAdvice + @ExceptionHandler）
★ 自定义业务异常 + 全局 handler = 业务码与 HTTP 解耦，响应结构统一
★ 覆盖 RequestValidationError 可统一 422 的返回格式
★ 别用裸 return {"error":...} + 200 表达错误，要用正确状态码
"""
