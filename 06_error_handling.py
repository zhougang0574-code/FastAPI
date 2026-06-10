"""
第 6 课：错误处理 HTTPException & 自定义异常

学习要点：
1. HTTPException 抛出标准 HTTP 错误，detail 可以是字符串或任意 JSON
2. headers 参数随异常一起返回自定义响应头
3. @app.exception_handler 注册自定义异常处理器
4. 覆盖 RequestValidationError 自定义 422 响应格式
5. status 模块提供可读性好的状态码常量
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# 模拟数据库
fake_items_db = {"foo": "Foo Item", "bar": "Bar Item"}


@app.get("/items/{item_id}")
def read_item(item_id: str):
    if item_id not in fake_items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found",
            # headers 会附加到错误响应里，可用于标识错误类型
            headers={"X-Error": "item-not-found"},
        )
    return {"item": fake_items_db[item_id]}


# detail 可以是任意可序列化对象，不必是字符串
@app.get("/items-detailed/{item_id}")
def read_item_detailed(item_id: str):
    if item_id not in fake_items_db:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ITEM_NOT_FOUND",
                "message": f"'{item_id}' does not exist",
                "hint": "Check /items for available items",
            },
        )
    return {"item": fake_items_db[item_id]}


# ── 自定义业务异常 ──

class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name


# 注册处理器：捕获 UnicornException，返回自定义 JSON 格式
@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=418,  # I'm a teapot
        content={"message": f"Oops! '{exc.name}' did something unspeakable."},
    )


@app.get("/unicorns/{name}")
def read_unicorn(name: str):
    if name == "yolo":
        raise UnicornException(name=name)
    return {"unicorn_name": name}


# ── 覆盖默认的 422 验证错误格式 ──

# FastAPI 默认的 422 响应格式有时不符合团队规范
# 可以覆盖 RequestValidationError 处理器统一格式
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),   # 保留原始详细错误信息
            "body": str(exc.body) if hasattr(exc, "body") else None,
        },
    )


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item):
    return item


"""
执行流程图
==========

路径不存在的 item：GET /items/xyz
    │
    ▼
raise HTTPException(404, detail="...")
    │
    ▼
FastAPI 捕获，自动构建 JSON 响应：
{"detail": "Item 'xyz' not found"}
+ 响应头 X-Error: item-not-found
    │
    ▼
客户端收到 404

业务异常：GET /unicorns/yolo
    │
    ▼
raise UnicornException("yolo")
    │
    ▼
unicorn_exception_handler 捕获
    │
    ▼
自定义 JSON 格式 + 418 状态码


核心知识点 ★
============
★ HTTPException 是最常用的报错方式，覆盖 99% 场景
★ detail 支持任意 JSON 结构，团队可约定统一的错误响应格式
★ 自定义异常 + exception_handler 解耦业务错误和 HTTP 细节
★ 覆盖 RequestValidationError 处理器统一 422 响应格式是实际项目常见做法
"""
