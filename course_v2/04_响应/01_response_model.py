"""
【响应 / 01】响应模型 response_model + 状态码 status_code（易点·合并）

与上一课的区别：
    前面都在管「请求怎么进来」。本课管「响应怎么出去」：
    用 response_model 控制返回哪些字段，用 status_code 设置 HTTP 状态码。

本课知识点（合并讲）：
    1. response_model 控制返回结构，自动过滤多余字段       —— ≈ 返回 DTO 而非实体
    2. 用 Output 模型隐藏敏感字段（密码等）                 —— ≈ 不把 password 放进响应 DTO
    3. status_code 设置状态码（201 Created / 204 等）        —— ≈ @ResponseStatus
    4. response_model_exclude_unset：只返回赋过值的字段       —— 适合 PATCH 的部分响应

为什么需要：
    数据库对象常含 password_hash、内部字段，绝不能原样返回。response_model
    是 FastAPI 的「出参契约」：即便函数返回了多余字段，也会被它过滤掉，安全。
"""

from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(title="响应模型")


# 输入模型：客户端提交的，含密码
class UserIn(BaseModel):
    username: str
    password: str
    email: str


# 输出模型：返回给客户端的，没有 password（敏感字段被排除在契约外）
# ≈ 返回 UserResponseDTO 而不是把实体直接吐出去
class UserOut(BaseModel):
    username: str
    email: str


_FAKE_DB = {}


# response_model=UserOut：哪怕函数 return 了带 password 的对象，
# FastAPI 也只按 UserOut 的字段输出，password 被自动过滤掉。
# status_code=201：创建成功返回 201 Created（≈ @ResponseStatus(CREATED)）
@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserIn):
    _FAKE_DB[user.username] = user
    return user   # 返回了 password，但 UserOut 里没有 → 不会泄露


class Profile(BaseModel):
    nickname: str | None = None
    bio: str | None = None
    avatar: str | None = None


# response_model_exclude_unset=True：只返回「实际赋过值」的字段，
# 没赋值的 None 字段不出现在响应里（PATCH 部分更新的响应很合适）
@app.get("/profile", response_model=Profile, response_model_exclude_unset=True)
def get_profile():
    return Profile(nickname="Tom")   # 响应里只有 nickname，没有 bio/avatar


"""
执行流程图
==========

函数 return 对象（可能字段很多，含敏感字段）
        │
        ▼
response_model 当「出参模子」过滤：
    ├─ 只保留模子里声明的字段（password 不在 → 丢弃）
    ├─ exclude_unset=True → 再丢掉没赋值的字段
    └─ 按模子序列化成 JSON
        │
        ▼
带 status_code 返回（201/204/...）

核心知识点 ★
============
★ response_model 是「出参契约」：函数返回多余字段会被自动过滤，天然防泄露
★ 输入用 XxxIn、输出用 XxxOut，分离请求/响应模型（密码只进不出）
★ status_code 设状态码：创建 201、无内容 204（≈ @ResponseStatus）
★ response_model_exclude_unset=True 只返回赋过值的字段，适合 PATCH 响应
★ 自定义 Response 类型、流式响应见 〔04_响应/02〕
"""
