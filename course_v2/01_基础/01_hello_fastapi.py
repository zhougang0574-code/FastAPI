"""
【基础 / 01】Hello FastAPI —— 一次 HTTP 来回的最小闭环

与上一课的区别：
    这是第一课，没有上一课。

本课知识点（易点合并，Java 老手秒懂）：
    1. FastAPI() 创建应用实例                  —— ≈ SpringBoot 的 @SpringBootApplication 启动类
    2. @app.get / @app.post 装饰器注册路由      —— ≈ @GetMapping / @PostMapping，函数 ≈ Controller 方法
    3. 返回 dict / list 自动序列化为 JSON       —— ≈ @RestController + Jackson 自动转 JSON
    4. 函数签名的类型提示 = 参数声明的唯一依据   —— ≈ 方法形参 + @RequestParam，但靠「类型注解」驱动
    5. uvicorn 启动 ASGI 服务                   —— ≈ 内嵌 Tomcat，uvicorn 是异步版的 servlet 容器
    6. /docs 自动交互文档                       —— ≈ 自带且免配置的 Swagger UI（SpringBoot 要手动加依赖）

为什么需要：
    FastAPI 的核心卖点是「类型提示即契约」——你写的 Python 类型注解，
    同时承担了 SpringBoot 里 @RequestParam 校验 + DTO 反序列化 + Swagger 文档三件事。
    这一课先把「请求进来 → 函数处理 → 返回值自动变 JSON」这条最小闭环跑通。
"""

from fastapi import FastAPI

# FastAPI() 创建应用实例。title/description/version 会显示在 /docs 文档页顶部。
# ≈ SpringBoot 的启动类，但这里 app 是一个普通对象，路由靠装饰器往上挂。
app = FastAPI(
    title="FastAPI 学习项目",
    description="从零学习 FastAPI（Java 程序员视角）",
    version="0.1.0",
)


# @app.get("/") 把下面的函数注册为 “GET /” 的处理器。
# 返回的 dict 会被自动序列化成 JSON：{"message": "Hello, FastAPI!"}
# ≈ @GetMapping("/") + @ResponseBody，但 FastAPI 默认就是 RestController 行为。
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


# 路径参数：URL 里用 {item_id} 占位，函数签名里必须有同名参数。
# 关键点：item_id: int 这个「类型注解」让 FastAPI 自动做类型转换 + 校验。
#   - 传 /items/3   → item_id = 3（int）
#   - 传 /items/abc → 自动返回 422，根本进不到函数体（≈ Spring 的参数绑定失败）
# 路径参数的完整用法（Enum 限值、路由顺序陷阱）留到 〔02_请求参数/01〕。
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}


# POST 路由：通常用于创建资源。
# 注意：这里 name / price 没有出现在路径里，又是简单类型 → FastAPI 当成「查询参数」，
#       即 POST /items?name=book&price=9.9。这其实不符合 REST 习惯（创建应该用请求体）。
#       用 Pydantic 请求体传 JSON 的「正确姿势」留到 〔03_请求体与Pydantic/01〕。
@app.post("/items")
def create_item(name: str, price: float):
    return {"name": name, "price": price, "status": "created"}


"""
执行流程图
==========

客户端 HTTP 请求
    │
    ▼
uvicorn（ASGI 服务器，≈ 内嵌 Tomcat）接收请求
    │
    ▼
FastAPI 按 (路径 + 方法) 匹配路由
    │
    ├─ 匹配成功 → 按类型注解解析/校验参数 → 执行函数 → 返回值自动转 JSON → 200
    │                                          └─ 参数类型不对 → 422（不进函数体）
    │
    └─ 匹配失败 → 404 Not Found

启动命令（文件名以数字开头不是合法模块名，先 cd 进本目录）：
    cd course_v2/01_基础
    uvicorn 01_hello_fastapi:app --reload
    # --reload：开发模式，改代码自动重启；生产环境不加

启动后访问：
    http://127.0.0.1:8000/docs    ← Swagger UI，可直接点按钮测试接口
    http://127.0.0.1:8000/redoc   ← ReDoc 风格文档


核心知识点 ★
============
★ FastAPI = Starlette（异步框架，≈ 异步版 servlet）+ Pydantic（数据校验，≈ Bean Validation）
★ 装饰器即路由注册：@app.get/post/put/delete/patch("/path")
★ 函数返回 dict/list/Pydantic 模型 → 自动 JSON，无需 @ResponseBody
★ 类型注解是 FastAPI 理解参数的唯一依据：路径里有同名 → 路径参数；简单类型没在路径里 → 查询参数
★ /docs 是「免费」的交互式文档，开发调试必用，这是 FastAPI 相对 SpringBoot 的最大便利
★ 本课所有函数都用普通 def；下一课 〔01_基础/02〕讲为什么 FastAPI 真正的灵魂是 async def
"""
