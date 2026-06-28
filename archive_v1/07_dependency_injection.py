"""
第 7 课：依赖注入 Dependency Injection

学习要点：
1. Depends() 声明依赖，FastAPI 自动解析并注入返回值
2. 依赖函数本身也可以有参数（查询参数等），FastAPI 递归解析
3. 类作为依赖：把参数放进 __init__，更结构化
4. 嵌套依赖：依赖可以依赖其他依赖，形成依赖树
5. yield 依赖：用于数据库连接等需要「打开→使用→关闭」的资源
"""

from typing import Annotated, Optional
from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI()


# 公共查询参数提取为依赖函数，多个路由复用，不重复写
def common_parameters(q: Optional[str] = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


# Annotated 写法（推荐）：把 Depends 声明内嵌进类型，复用更方便
CommonDeps = Annotated[dict, Depends(common_parameters)]


@app.get("/items")
def list_items(commons: CommonDeps):
    return {"commons": commons, "items": []}


@app.get("/users")
def list_users(commons: CommonDeps):
    return {"commons": commons, "users": []}


# ── 类作为依赖 ──

# 类比函数依赖：FastAPI 自动实例化，__init__ 参数就是依赖的参数
class ItemQueryFilter:
    def __init__(self, q: Optional[str] = None, skip: int = 0, limit: int = 10):
        self.q = q
        self.skip = skip
        self.limit = limit


@app.get("/filtered-items")
def filtered_items(f: Annotated[ItemQueryFilter, Depends(ItemQueryFilter)]):
    result = [{"id": i} for i in range(f.skip, f.skip + f.limit)]
    if f.q:
        result = [r for r in result if f.q in str(r["id"])]
    return result


# ── 嵌套依赖 ──

def verify_key(x_key: Annotated[str, Header()]):
    # Header() 读取请求头，参数名自动转为 X-Key 格式
    if x_key != "fake-super-secret-key":
        raise HTTPException(status_code=400, detail="X-Key header invalid")
    return x_key


def verify_token(token: Annotated[str, Header()]):
    if token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="Token header invalid")
    return token


# dependencies=[...] 列表里的依赖只运行副作用（校验），不注入返回值
@app.get("/secure", dependencies=[Depends(verify_key), Depends(verify_token)])
def secure_route():
    return {"message": "Authorized!"}


# ── yield 依赖 ──

# yield 前：setup（打开连接/事务）
# yield 的值：注入路由
# yield 后（finally）：teardown（关闭连接/回滚），请求结束时执行
def get_db():
    db = {"connection": "fake-db-session", "closed": False}
    try:
        yield db
    finally:
        db["closed"] = True  # 相当于 db.close()


@app.get("/db-items")
def db_items(db: Annotated[dict, Depends(get_db)]):
    # 这里 db 已经是打开的会话
    return {"db_status": "open" if not db["closed"] else "closed", "items": ["a", "b"]}


"""
执行流程图
==========

请求到达 /items?q=hello&skip=0
    │
    ▼
FastAPI 发现 commons: CommonDeps → 调用 common_parameters(q="hello", skip=0, limit=100)
    │
    ▼
返回值 {"q":"hello","skip":0,"limit":100} 注入 list_items 的 commons 参数
    │
    ▼
执行 list_items → 返回结果

yield 依赖生命周期：
    请求开始 → get_db() yield db → 路由执行 → 响应发送 → finally db.close()


核心知识点 ★
============
★ 依赖注入的核心价值：把「公共逻辑」从路由函数里解耦出去
★ Depends() 的参数可以是函数也可以是类（类更适合有状态的依赖）
★ 嵌套依赖：FastAPI 自动构建依赖树，相同依赖只执行一次（缓存）
★ yield 依赖是处理数据库会话的标准模式，比 try/finally 在路由里更整洁
"""
