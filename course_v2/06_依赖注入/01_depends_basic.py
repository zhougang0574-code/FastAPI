"""
【依赖注入 / 01】Depends 基础：函数依赖 / 类依赖 / 嵌套依赖（易点·合并）

与上一课的区别：
    这是 FastAPI 的「粘合层」第一课。前面参数都直接来自请求；本课让参数来自
    「一个依赖函数的返回值」——这就是依赖注入，你在 Spring 里天天用。

本课知识点（DI 对 Java 老手很熟，合并讲）：
    1. Depends(fn)：注入 fn 的返回值                  —— ≈ @Autowired 注入 Bean
    2. 依赖函数自己也能有参数（查询参数等），递归解析   —— FastAPI 自动往下解析依赖树
    3. 类作为依赖：参数放 __init__，更结构化           —— ≈ 构造器注入
    4. 嵌套依赖：依赖可以依赖别的依赖                   —— ≈ Bean 依赖 Bean

为什么需要：
    「公共查询参数」「取当前用户」「数据库会话」这类横切逻辑，靠依赖注入抽出来复用，
    一处定义、多处注入。这是 FastAPI 组织代码的核心机制，认证/数据库全靠它。
"""

from typing import Annotated, Optional

from fastapi import Depends, FastAPI

app = FastAPI(title="依赖注入基础")


# 1) 函数依赖：把「公共分页参数」抽成一个依赖，多个路由复用
# 依赖函数本身可以有查询参数，FastAPI 会递归解析它们
def pagination(page: int = 1, size: int = 10) -> dict:
    return {"page": page, "size": size}


# Annotated[X, Depends(fn)] 是现代推荐写法（类型 + 依赖声明合一）
PageDep = Annotated[dict, Depends(pagination)]


@app.get("/items")
def list_items(page: PageDep):          # page 注入的是 pagination() 的返回值
    return {"pagination": page}


@app.get("/users")
def list_users(page: PageDep):          # 同一个依赖，复用
    return {"pagination": page}


# 2) 类作为依赖：参数放 __init__，比函数依赖更结构化（≈ 构造器注入）
class CommonQuery:
    def __init__(self, q: Optional[str] = None, page: int = 1):
        self.q = q
        self.page = page


@app.get("/search")
def search(params: Annotated[CommonQuery, Depends(CommonQuery)]):
    return {"q": params.q, "page": params.page}


# 3) 嵌套依赖：依赖依赖别的依赖（verify_token 依赖 get_token）
def get_token(token: str = "") -> str:
    return token


def verify_token(token: Annotated[str, Depends(get_token)]) -> str:
    return "valid" if token == "secret" else "invalid"


@app.get("/protected")
def protected(state: Annotated[str, Depends(verify_token)]):
    return {"token_state": state}


"""
执行流程图
==========

请求 GET /protected?token=secret
        │
        ▼
FastAPI 解析依赖树（自底向上）：
    get_token(token=...)  ──返回──▶  verify_token(...)  ──返回──▶  protected(state=...)
        │                              │                            │
   从查询串取 token              判断是否 valid               拿到 "valid"
        │
        ▼
执行路由函数

核心知识点 ★
============
★ Depends(fn) 注入 fn 的返回值（≈ @Autowired），把横切逻辑抽出来复用
★ 依赖函数自己能有请求参数，FastAPI 递归解析整棵依赖树
★ Annotated[类型, Depends(fn)] 是现代写法；可起别名（PageDep）到处复用
★ 类依赖 = 构造器注入：参数放 __init__，比函数依赖更结构化
★ 需要「打开→用→关闭」的资源（数据库会话）用 yield 依赖，见 〔06_依赖注入/02〕
"""
