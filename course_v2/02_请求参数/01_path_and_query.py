"""
【请求参数 / 01】路径参数 + 查询参数（易点·合并）

与上一课的区别：
    〔01_基础/01〕只是顺带提了一句路径参数。本课把「客户端怎么传简单参数进来」讲全：
    路径参数（在 URL 路径里）+ 查询参数（URL 问号后面），以及类型注解如何自动校验。

本课知识点（Java 老手秒懂，合并讲）：
    1. 路径参数 {id}：写在路径里，函数同名接收     —— ≈ @PathVariable
    2. 查询参数：函数参数没在路径里且是简单类型      —— ≈ @RequestParam
    3. 有默认值=可选，无默认值=必填（不传 422）       —— ≈ @RequestParam(required=...)
    4. Optional[X] = None 显式表达「可不传，默认 None」 —— ≈ @RequestParam(required=false)
    5. bool 自动转换：1/true/on/yes → True            —— ≈ Spring 的类型转换器

为什么需要：
    这是最常见的两类入参。关键心智：FastAPI 靠「参数是否出现在路径里 + 是不是简单类型」
    自动区分它是路径参数还是查询参数，你不用像 Spring 那样挨个加注解。
"""

from typing import Optional

from fastapi import FastAPI

app = FastAPI(title="路径参数 + 查询参数")


# 路径参数：{user_id} 在路径里，函数签名同名接收，类型注解 int 自动转换+校验
# ≈ @GetMapping("/users/{userId}") public X get(@PathVariable int userId)
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}


# 查询参数：q 没在路径里，是简单类型 → FastAPI 当查询参数 /search?q=xxx
# q: str 无默认值 → 必填，不传返回 422
# limit: int = 10 有默认值 → 可选，不传则用 10
# ≈ public X search(@RequestParam String q, @RequestParam(defaultValue="10") int limit)
@app.get("/search")
def search(q: str, limit: int = 10):
    return {"q": q, "limit": limit}


# Optional[str] = None：显式表达「可不传，默认 None」
# active: bool = False：传 ?active=1 / true / on / yes 都会转成 True（不区分大小写）
@app.get("/products")
def list_products(category: Optional[str] = None, active: bool = False):
    return {"category": category, "active": active}


# 路径参数 + 查询参数可以同时存在，FastAPI 自动按「是否在路径里」区分
@app.get("/users/{user_id}/orders")
def user_orders(user_id: int, status: Optional[str] = None, page: int = 1):
    return {"user_id": user_id, "status": status, "page": page}


"""
执行流程图
==========

GET /users/42/orders?status=paid&page=2
        │
        ▼
FastAPI 拆解参数：
    user_id ← 路径里的 {user_id}    （路径参数，必填）
    status  ← 查询串 ?status=        （查询参数，可选，默认 None）
    page    ← 查询串 ?page=          （查询参数，可选，默认 1）
        │
        ▼
按类型注解转换 + 校验
    ├─ user_id="abc" → 422（不进函数体）
    └─ 全部合法 → 执行函数

核心知识点 ★
============
★ 在路径里有同名占位 → 路径参数（≈ @PathVariable）；简单类型没在路径里 → 查询参数（≈ @RequestParam）
★ 有默认值 = 可选；无默认值 = 必填（不传 422）
★ Optional[X] = None 是「可选且默认 None」的标准写法
★ bool 自动转换 1/true/on/yes（不区分大小写）→ True
★ Enum 限值、路由顺序陷阱、Query() 加约束等进阶用法见 〔02_请求参数/02〕
"""
