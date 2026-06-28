"""
【请求参数 / 02】参数进阶：Enum 限值 / 路由顺序 / Query 约束（进阶·合并）

与上一课的区别：
    〔02_请求参数/01〕讲了路径/查询参数的「能用」。本课补 4 个「用好」的点：
    限制取值、避开路由顺序陷阱、给查询参数加校验约束与文档。

本课知识点（合并讲，都是小增量）：
    1. Enum 限制路径参数合法取值（传非法值自动 422）   —— ≈ 枚举入参 / @Pattern
    2. 路由顺序陷阱：固定路径必须写在变量路径之前      —— Spring 按精确度匹配，FastAPI 按声明顺序
    3. Query() 给查询参数加约束（ge/le/min_length 等）   —— ≈ @Min/@Max/@Size
    4. Query() 的 description/title 直接进 /docs 文档     —— ≈ Swagger 注解

为什么需要：
    路由顺序陷阱是 FastAPI 新手最常踩的坑（Spring 不会有，因为它按精确度匹配）；
    Query() 则是把「校验 + 文档」一次写全的标准做法。
"""

from enum import Enum

from fastapi import FastAPI, Query

app = FastAPI(title="参数进阶")


# Enum 限制取值：路径参数只能是 small/medium/large，传别的自动 422
# ≈ Java 枚举入参；/docs 里会渲染成下拉选择
class Size(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


@app.get("/cups/{size}")
def get_cup(size: Size):
    return {"size": size, "ml": {"small": 250, "medium": 400, "large": 600}[size]}


# ── 路由顺序陷阱（重点） ──
# FastAPI 按「声明顺序」从上往下匹配，先匹配上的赢。
# /users/me 必须写在 /users/{user_id} 前面，否则 "me" 会被当成 user_id 传进去。
@app.get("/users/me")          # 固定路径，写在前面
def get_me():
    return {"user": "当前登录用户"}


@app.get("/users/{user_id}")   # 变量路径，写在后面
def get_user(user_id: int):
    return {"user_id": user_id}


# Query() 给查询参数加约束 + 文档：
#   ...（Ellipsis）表示必填；ge/le 数值范围；min_length/max_length 字符串长度
# ≈ @RequestParam + @Min/@Max/@Size + Swagger description
@app.get("/items")
def list_items(
    keyword: str = Query(..., min_length=2, max_length=20, description="搜索关键词，2-20 字"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页条数，1-100"),
):
    return {"keyword": keyword, "page": page, "size": size}


"""
执行流程图
==========

路由匹配（按声明顺序，从上往下）：
    GET /users/me
        │
        ├─ 先碰到 @get("/users/me")      → 命中，返回当前用户   ✓
        └─ 若把 {user_id} 写在前面        → "me" 被当 user_id → int 转换失败 422  ✗

Query 校验：
    GET /items?keyword=a   → keyword 长度<2 → 422（带 description 提示）
    GET /items?page=0      → page<1 → 422

核心知识点 ★
============
★ Enum(str, Enum) 路径/查询参数 → 限定合法取值 + /docs 自动下拉
★ 路由顺序陷阱：固定路径写在变量路径之前（FastAPI 按声明顺序匹配，不像 Spring 按精确度）
★ Query(默认值, ge/le/min_length/max_length, description=...) = 校验 + 文档一次写全
★ Query(...) 的 ... 表示必填；想可选就给真实默认值
★ 复杂结构入参（JSON 请求体）不该用查询参数，见 〔03_请求体与Pydantic/01〕
"""
