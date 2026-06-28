"""
【请求体与Pydantic / 01】请求体 + Field 约束 + 嵌套模型（易点·合并）

与上一课的区别：
    〔02_请求参数〕传的都是 URL 上的简单参数。本课传「结构化 JSON 请求体」——
    用 Pydantic BaseModel 定义结构，这正是 SpringBoot 的 DTO + Bean Validation。

本课知识点（Java 老手秒懂，合并讲）：
    1. 继承 BaseModel 定义请求体结构              —— ≈ DTO 类
    2. 函数参数是 BaseModel 子类 → 自动从 body 读  —— ≈ @RequestBody
    3. Field() 加约束 + 文档（gt/le/min_length 等）—— ≈ @Min/@NotBlank/@Size
    4. 嵌套模型：字段类型是另一个 BaseModel        —— ≈ DTO 里嵌 DTO
    5. 路径参数 + 查询参数 + 请求体可同时存在        —— FastAPI 按来源自动区分

为什么需要：
    创建/更新资源该用 JSON 请求体而不是查询串。Pydantic 一个类同时搞定
    「反序列化 + 校验 + 文档 + IDE 类型提示」，比 Spring 的 DTO+注解还省事。
"""

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="请求体 + Pydantic")


# 嵌套用的子模型（≈ 内嵌 DTO）
class Address(BaseModel):
    city: str
    zipcode: str = Field(pattern=r"^\d{6}$", description="6 位邮编")


# 请求体模型：≈ 一个带 Bean Validation 注解的 DTO
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="用户名")
    age: int = Field(gt=0, le=150, description="年龄 1-150")
    email: Optional[str] = Field(default=None, description="可选邮箱")
    address: Optional[Address] = None   # 嵌套模型，body 里是嵌套 JSON


# 函数参数是 BaseModel 子类 → FastAPI 自动从 request body 读取并校验
# ≈ public X create(@RequestBody @Valid UserCreate user)
@app.post("/users")
def create_user(user: UserCreate):
    # user 已经是校验通过的对象，可直接用属性访问
    return {"created": user.name, "age": user.age, "city": user.address.city if user.address else None}


# 路径参数 + 查询参数 + 请求体同时存在，FastAPI 按来源自动区分：
#   group_id 在路径 → 路径参数；notify 是简单类型没在路径 → 查询参数；user 是模型 → 请求体
@app.post("/groups/{group_id}/users")
def add_user_to_group(group_id: int, user: UserCreate, notify: bool = False):
    return {"group_id": group_id, "user": user.name, "notify": notify}


"""
执行流程图
==========

POST /groups/7/users?notify=true
Body: {"name":"Tom","age":30,"address":{"city":"BJ","zipcode":"100000"}}
        │
        ▼
FastAPI 按来源分配参数：
    group_id ← 路径    user ← body(JSON→UserCreate)    notify ← 查询串
        │
        ▼
Pydantic 校验 body：
    ├─ age=200 → 不满足 le=150 → 422（指明哪个字段错）
    ├─ zipcode="abc" → 不匹配正则 → 422
    └─ 全合法 → 反序列化成 UserCreate 对象传进函数

核心知识点 ★
============
★ BaseModel 子类做函数参数 → 自动当请求体（≈ @RequestBody），无需任何注解
★ Field(约束, description=...) ≈ Bean Validation 注解 + Swagger 说明，一处写全
★ 嵌套模型 = DTO 套 DTO，body 里就是嵌套 JSON，自动递归校验
★ 路径/查询/请求体可同函数共存，FastAPI 按「在不在路径 + 是不是模型」自动分流
★ 想限制返回给客户端的字段（隐藏密码等）→ 见 〔04_响应/01〕response_model
"""
