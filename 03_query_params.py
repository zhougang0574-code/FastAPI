"""
第 3 课：查询参数 Query Parameters

学习要点：
1. 函数参数不在路径里 → 自动成为查询参数（?key=value）
2. 有默认值 = 可选；无默认值 = 必填（不传则 422）
3. Optional[X] = None 显式表达可为 None
4. bool 类型自动转换：1/true/on/yes → True（不区分大小写）
5. 查询参数 + 路径参数 + 请求体可同时存在，FastAPI 自动区分
"""

from typing import Optional
from fastapi import FastAPI, Query

app = FastAPI()


# skip/limit 有默认值 → 可选
# 访问：/items            → skip=0, limit=10
# 访问：/items?skip=20    → skip=20, limit=10
@app.get("/items")
def list_items(skip: int = 0, limit: int = 10):
    fake_db = [{"id": i, "name": f"Item {i}"} for i in range(100)]
    return fake_db[skip: skip + limit]


# q：Optional[str] = None → 可选字符串，不传时为 None
# short：bool，访问 ?short=1 或 ?short=true 都会变成 True
@app.get("/items/{item_id}")
def get_item(item_id: int, q: Optional[str] = None, short: bool = False):
    item = {"item_id": item_id}
    if q:
        item["q"] = q
    if not short:
        item["description"] = "This is a very long description, only shown when short=False"
    return item


# needy 没有默认值 → 必填，不传返回 422
# URL: /required?needy=hello&skip=5
@app.get("/required")
def required_param(needy: str, skip: int = 0, limit: Optional[int] = None):
    return {"needy": needy, "skip": skip, "limit": limit}


# Query() 添加额外约束和文档：min_length、max_length、pattern
# Annotated 写法（推荐）：类型和约束分离，更清晰
from typing import Annotated

@app.get("/search")
def search(
    q: Annotated[Optional[str], Query(min_length=2, max_length=50, description="搜索关键词")] = None,
    page: Annotated[int, Query(ge=1, description="页码，从1开始")] = 1,
):
    return {"q": q, "page": page}


"""
执行流程图
==========

请求：GET /items?skip=20&limit=5
    │
    ▼
FastAPI 解析 URL query string
    │
    ▼
参数注入：skip=20（int 转换成功），limit=5
    │
    ▼
执行 list_items(skip=20, limit=5) → 返回 items[20:25]

请求：GET /items?skip=abc
    │
    ▼
类型转换失败（"abc" 不能转 int）
    │
    ▼
422 Unprocessable Entity（自动返回）


核心知识点 ★
============
★ 区分路径参数 vs 查询参数：看函数参数是否出现在路径字符串里
★ 默认值 = None 不等于可选：建议用 Optional[X] = None 明确意图
★ bool 类型的自动转换很方便：?active=true / ?active=1 都能用
★ Query() 是查询参数的 "加强版声明"，可加验证、描述、别名
"""
