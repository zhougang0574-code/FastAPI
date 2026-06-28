"""
【中间件与后台 / 02】后台任务 BackgroundTasks

与上一课的区别：
    中间件在「响应前后」做事但会拖住响应。本课的 BackgroundTasks 让某些活儿
    「先返回响应，再在后台慢慢干」，不让客户端干等。

本课知识点：
    1. BackgroundTasks 参数：注册「响应返回后」才执行的任务  —— ≈ @Async 方法
    2. 适合发邮件、写日志、清理等「不需要客户端等结果」的活
    3. 它跑在同一进程（不是分布式队列），重活仍应交给 Celery 等

为什么需要：
    注册成功要发欢迎邮件——发邮件慢，不该让用户卡在那等。用 BackgroundTasks
    先把「注册成功」返回，邮件在后台发。类似 Spring 的 @Async，但更轻量。
"""

from fastapi import BackgroundTasks, FastAPI

app = FastAPI(title="后台任务")


# 一个「慢活」：假装发邮件（真实场景可能耗时几秒）
def send_email(to: str, subject: str):
    # 这里若是阻塞 IO，它会在响应返回后于线程池执行，不拖慢请求
    print(f"[后台] 给 {to} 发邮件: {subject}")


def write_log(message: str):
    print(f"[后台] 写日志: {message}")


# 在参数里声明 BackgroundTasks，FastAPI 自动注入
# tasks.add_task(fn, 参数...) 登记任务，响应返回后才真正执行
@app.post("/register")
def register(email: str, tasks: BackgroundTasks):
    # ... 这里完成注册的核心逻辑（同步、要让用户等的部分）...
    tasks.add_task(send_email, email, "欢迎注册")    # 登记：响应后再发
    tasks.add_task(write_log, f"new user: {email}")  # 可登记多个，按顺序执行
    return {"msg": "注册成功"}   # 立刻返回，邮件/日志在后台跑


"""
执行流程图
==========

POST /register
    │
    ▼
执行注册核心逻辑（同步部分）
    │
    ├─ tasks.add_task(send_email, ...)  ← 只登记，不执行
    └─ tasks.add_task(write_log, ...)   ← 只登记
    │
    ▼
返回响应 {"msg":"注册成功"}  ← 客户端这里就拿到结果了
    │
    ▼（响应发出之后）
后台依次执行已登记任务：send_email → write_log

核心知识点 ★
============
★ 参数声明 BackgroundTasks → 注入；add_task(fn, args) 登记「响应后执行」的活（≈ @Async）
★ 适合发邮件/写日志/清理等「客户端不需要等结果」的轻量后台活
★ 多个任务按 add_task 顺序执行；它们跑在同一进程，非分布式
★ 真正的重活/可靠队列（要重试、要持久化）该上 Celery/RQ，BackgroundTasks 不替代它
★ 后台函数若是异步 IO 可定义成 async def，FastAPI 会正确调度
"""
