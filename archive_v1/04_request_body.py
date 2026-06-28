"""
第 4 课：请求体 + Pydantic 数据模型

学习要点：
1. 继承 BaseModel 定义请求体结构
2. Field() 添加验证约束（gt/ge/lt/le/min_length/max_length）和文档说明
3. 嵌套模型：模型的字段可以是另一个 BaseModel
4. 函数参数是 BaseModel 子类 → FastAPI 自动从 request body 读取
5. 路径参数 + 查询参数 + 请求体可以同时在一个函数里使用
"""

from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


# 嵌套模型：Image 会内嵌在 Item 里
class Image(BaseModel):
    url: str
    name: str


class Item(BaseModel):
    name: str
    # Field() 的 default 参数 + 约束 + description
    description: Optional[str] = Field(default=None, max_length=300, description="商品描述")
    # gt=0：price > 0（strictly greater than，不含0）
    price: float = Field(gt=0, description="价格，必须大于 0")
    tax: Optional[float] = None
    # 嵌套模型：image 字段是 Image 类型（或 None）
    image: Optional[Image] = None
    # 列表字段：默认空列表
    tags: list[str] = []


# 参数是 BaseModel 子类 → 从 POST body 读（JSON 格式）
# 请求示例：POST /items
# {"name":"Apple","price":9.9,"tags":["fruit","fresh"]}
@app.post("/items")
def create_item(item: Item):
    item_dict = item.model_dump()
    if item.tax is not None:
        item_dict["price_with_tax"] = item.price + item.tax
    return item_dict


# FastAPI 区分三种参数的规则：
#   item_id → 在路径里 → 路径参数
#   item    → BaseModel 子类 → 请求体
#   q       → 其他 → 查询参数
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, q: Optional[str] = None):
    result = {"item_id": item_id, **item.model_dump()}
    if q:
        result["q"] = q
    return result


# 多个 Body 参数：两个 BaseModel 会合并成一个 JSON 对象
# 请求格式：{"item": {...}, "user": {...}}
class User(BaseModel):
    username: str
    full_name: Optional[str] = None


@app.post("/order")
def create_order(item: Item, user: User):
    return {"item": item.model_dump(), "user": user.model_dump()}


"""
执行流程图
==========

客户端发送 POST /items
Content-Type: application/json
{"name":"Phone","price":999.9,"image":{"url":"http://...","name":"front"}}
    │
    ▼
FastAPI 读取 request body（JSON）
    │
    ▼
Pydantic 校验字段类型 + Field 约束
    ├─ 校验通过 → 构建 Item 实例 → 注入函数参数
    └─ 校验失败（如 price=-1）→ 422 + 详细错误信息


核心知识点 ★
============
★ BaseModel 的字段默认都是必填的，有 default/Optional 才可选
★ Field(gt=0) 中：gt=大于、ge=大于等于、lt=小于、le=小于等于
★ 嵌套模型直接写成字段类型即可，无需额外声明
★ model_dump() 把 Pydantic 对象转成普通 dict
★ 请求体格式：Content-Type 必须是 application/json
"""
