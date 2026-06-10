"""
第 5 课：响应模型 Response Model

学习要点：
1. response_model 参数控制返回给客户端的字段（自动过滤多余字段）
2. 用 Output 模型隐藏敏感字段（如密码、内部 ID 等）
3. response_model_exclude_unset=True：只返回实际赋值的字段，适合 PATCH
4. status_code 设置 HTTP 响应状态码（201 Created / 204 No Content 等）
5. Union 类型：路由可以返回多种不同结构的响应
"""

from typing import Optional, Union
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()


# ── 场景1：隐藏敏感字段 ──

class UserIn(BaseModel):
    username: str
    password: str        # 输入时包含密码
    email: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    username: str        # 输出时不含密码
    email: str
    full_name: Optional[str] = None


# response_model=UserOut：FastAPI 自动过滤掉 password 字段
# 即使函数 return 了 UserIn 对象（含 password），客户端也看不到
@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserIn):
    return user   # FastAPI 按 UserOut 过滤后再序列化


# ── 场景2：exclude_unset，适合局部更新 ──

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: float = 10.5     # 有默认值
    tags: list[str] = []


# response_model_exclude_unset=True：
# 只返回用户实际传入的字段，不返回带默认值但未赋值的字段
# 适合 GET/PATCH 接口，避免默认值 "污染" 响应
@app.get("/items/{item_id}", response_model=Item, response_model_exclude_unset=True)
def get_item(item_id: int):
    items = {
        1: Item(name="Portal Gun", price=42.0),                          # tax 有默认值但未设置
        2: Item(name="Plumbus", price=32.0, description="家用", tax=5.0), # tax 显式设置了
    }
    item = items.get(item_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# ── 场景3：Union 返回不同结构 ──

class PlaneItem(BaseModel):
    description: str
    type: str = "plane"


class CarItem(BaseModel):
    description: str
    type: str = "car"


# Union[PlaneItem, CarItem]：可以返回两种结构之一
@app.get("/vehicles/{vehicle_id}", response_model=Union[PlaneItem, CarItem])
def get_vehicle(vehicle_id: int):
    vehicles = {
        1: PlaneItem(description="Plane with propellers"),
        2: CarItem(description="Car with wheels"),
    }
    if vehicle_id not in vehicles:
        from fastapi import HTTPException
        raise HTTPException(404, "Vehicle not found")
    return vehicles[vehicle_id]


# ── 场景4：响应状态码常量 ──

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    # 204 No Content：删除成功，不返回 body
    pass


"""
执行流程图
==========

POST /users (body 含 password)
    │
    ▼
create_user 函数返回 UserIn 对象（含 password）
    │
    ▼
FastAPI 用 response_model=UserOut 过滤
    │
    ▼
响应 JSON 只含 username / email / full_name
password 字段被自动丢弃 ✓


核心知识点 ★
============
★ response_model 是安全的最后一道防线：即使函数意外返回了敏感字段，response_model 会拦截
★ exclude_unset 与 exclude_none 的区别：前者排除"没有赋值的字段"，后者排除"值为 None 的字段"
★ status.HTTP_201_CREATED 比魔法数字 201 更可读，IDE 也有提示
★ 删除接口返回 204 时不能有 response_model（204 不允许 body）
"""
