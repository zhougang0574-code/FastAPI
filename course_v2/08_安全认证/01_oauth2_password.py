"""
【安全认证 / 01】OAuth2 密码模式骨架：登录端点 + 受保护路由（难点·细拆，整域第 1 课）

与上一课的区别：
    这是认证域的起点。本课先搭「形」：一个 /token 登录端点 + 一个用
    OAuth2PasswordBearer 保护的路由。先不管密码哈希和 JWT（后面三课逐个加）。

本课知识点（认证整域细拆，每课只加一层）：
    1. OAuth2PasswordBearer(tokenUrl="token")：声明「token 从哪个 URL 拿」
    2. /docs 自动出现「Authorize」按钮，能填 token 测试
    3. OAuth2PasswordRequestForm：标准登录表单（username/password 表单字段）
    4. 受保护路由注入 token 参数 → 没带 token 自动 401

为什么需要：
    OAuth2 密码模式是最常见的「用户名密码换 token」流程。本课先把骨架跑通，
    理解「登录拿 token → 带 token 访问」的闭环，后三课再把它做安全。
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI(title="OAuth2 骨架")

# 声明 token 的获取地址；FastAPI 据此在 /docs 生成 Authorize 按钮
# 受保护路由注入它 → 自动从 Authorization: Bearer xxx 头里取 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 假用户库（本课明文，仅演示骨架；下一课换成哈希）
_FAKE_USERS = {"alice": "pwd123"}


# 登录端点：OAuth2PasswordRequestForm 自动解析表单里的 username/password
# ≈ 一个 /login 接口，返回令牌
@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if _FAKE_USERS.get(form.username) != form.password:
        raise HTTPException(401, "用户名或密码错误")
    # 本课先返回「假 token」=用户名；下一课起换成真 JWT
    return {"access_token": form.username, "token_type": "bearer"}


# 受保护路由：注入 oauth2_scheme → 请求必须带 Bearer token，否则 401
@app.get("/me")
def read_me(token: Annotated[str, Depends(oauth2_scheme)]):
    # 本课 token 就是用户名（假的）；真正「解析 token→用户」在 〔08/04〕
    return {"token": token, "note": "拿到 token 说明已带 Bearer 头"}


"""
执行流程图
==========

1) 登录换 token：
   POST /token  (form: username=alice&password=pwd123)
        │
        ▼
   校验通过 → 返回 {"access_token": "...", "token_type": "bearer"}

2) 带 token 访问受保护资源：
   GET /me   Header: Authorization: Bearer <access_token>
        │
        ▼
   oauth2_scheme 从 Header 提取 token → 注入 → 进函数
        └─ 没带/格式错 → 自动 401

核心知识点 ★
============
★ OAuth2PasswordBearer(tokenUrl=...) 声明「token 从哪拿」，并驱动 /docs 的 Authorize 按钮
★ OAuth2PasswordRequestForm 是标准登录表单（username/password），靠 python-multipart 解析
★ 受保护路由注入 Depends(oauth2_scheme) → 自动要求 Bearer token，缺了就 401
★ 本课 token 是假的（=用户名）：先理解登录→带 token 的闭环
★ 接下来三课逐层加固：密码哈希 〔08/02〕→ JWT 〔08/03〕→ 解析出当前用户 〔08/04〕
"""
