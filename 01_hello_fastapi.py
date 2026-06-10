"""
第 1 课：Hello FastAPI —— 快速开始

学习要点：
1. 什么是 FastAPI：基于 Python 类型提示的现代高性能 Web 框架
2. 创建 FastAPI 实例（app = FastAPI()）
3. 用装饰器定义路由：@app.get() / @app.post()
4. 路径操作函数的返回值自动序列化为 JSON
5. 用 uvicorn 启动服务：uvicorn 01_hello_fastapi:app --reload
6. 自动交互文档：/docs（Swagger UI）和 /redoc
"""

from fastapi import FastAPI

# FastAPI() 创建应用实例，title/description/version 会显示在 /docs 页面
app = FastAPI(
    title="FastAPI 学习项目",
    description="从零学习 FastAPI",
    version="0.1.0",
)


# @app.get("/") 把下面的函数注册为 GET "/" 的处理器
# FastAPI 自动把返回的 dict 序列化为 JSON 响应
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


# 路径参数：大括号 {item_id} 声明，函数签名里必须有同名参数
# Python 类型提示 item_id: int 让 FastAPI 自动做类型校验和转换
@app.get("/items/{item_id}")
def read_item(item_id: int):
    # 如果传 /items/abc，FastAPI 会自动返回 422 Unprocessable Entity
    return {"item_id": item_id}


# POST 路由：通常用于创建资源
@app.post("/items")
def create_item(name: str, price: float):
    # 这里 name 和 price 来自 query string（?name=xxx&price=yyy）
    # 第 3 课会学用请求体传参，更符合 REST 规范
    return {"name": name, "price": price, "status": "created"}


"""
执行流程图
==========

客户端请求
    │
    ▼
uvicorn（ASGI 服务器）接收 HTTP 请求
    │
    ▼
FastAPI 路由匹配（根据 path + method）
    │
    ├─ 匹配成功 → 执行路径操作函数 → 返回值自动 JSON 序列化 → 200 响应
    │
    └─ 匹配失败 → 404 Not Found

自动文档地址（启动后直接访问）：
    http://127.0.0.1:8000/docs   ← Swagger UI，可直接测试接口
    http://127.0.0.1:8000/redoc  ← ReDoc 风格文档

启动命令：
    uvicorn 01_hello_fastapi:app --reload
    # --reload 开发模式：代码变化自动重启，生产环境不加


核心知识点 ★
============
★ FastAPI 基于 Starlette（异步）+ Pydantic（数据校验）构建
★ 装饰器 = 路由注册：@app.get/post/put/delete("/path")
★ 函数签名里的类型提示是 FastAPI 理解参数的唯一依据
★ 返回 dict / list / Pydantic model → 自动变成 JSON 响应
★ /docs 是免费得来的交互式 API 文档，开发调试必用
"""
