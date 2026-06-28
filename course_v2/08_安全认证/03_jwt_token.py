"""
【安全认证 / 03】JWT：签发与解码令牌（难点·细拆）

与上一课的区别：
    前两课返回的 access_token 是「假的」（=用户名）。本课只改这一点：
    登录成功后签发真正的 JWT，里面带过期时间和用户标识，且有签名防篡改。

本课知识点（只加一层）：
    1. JWT = 三段（header.payload.signature），无状态、自带签名
    2. jose.jwt.encode(payload, SECRET, algorithm) 签发
    3. payload 里 sub=用户标识、exp=过期时间
    4. decode 时验签 + 验过期，篡改/过期都会抛异常

为什么需要：
    JWT 让服务器「不存会话状态」也能认证——token 自带签名，服务器只验签即可。
    这和 Java 生态的 jjwt / Spring Security JWT 是同一套概念。
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

app = FastAPI(title="JWT")

# JWT 配置：SECRET 生产环境必须放环境变量（见 〔10_工程化/02〕），别硬编码
SECRET_KEY = "dev-secret-change-me"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_USERS = {"alice": pwd_context.hash("pwd123")}


# 签发 JWT：payload 里放 sub（谁）+ exp（何时过期），用 SECRET 签名
def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    hashed = _USERS.get(form.username)
    if not hashed or not pwd_context.verify(form.password, hashed):
        raise HTTPException(401, "用户名或密码错误")
    # 关键变化：返回真正的 JWT，而不是用户名
    return {"access_token": create_token(form.username), "token_type": "bearer"}


# 演示解码：验签 + 验过期，任何不对都抛 JWTError
@app.get("/decode")
def decode(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "token 无效或已过期")
    return {"sub": payload["sub"], "exp": payload["exp"]}


"""
执行流程图
==========

签发：登录通过 → create_token(username)
        payload{sub, exp} ──用 SECRET 签名──▶ header.payload.signature

校验：jwt.decode(token, SECRET)
        ├─ 验签失败（被篡改）   → JWTError → 401
        ├─ exp 已过            → JWTError → 401
        └─ 通过               → 拿回 payload（sub=用户名）

★ 服务器不存任何会话：token 自带签名与过期，验签即可 = 无状态认证

核心知识点 ★
============
★ JWT 三段自带签名：服务器只需用 SECRET 验签，无需存会话（无状态）
★ jwt.encode(payload, SECRET, algorithm) 签发；payload 放 sub（用户）+ exp（过期）
★ jwt.decode 自动验签 + 验过期，篡改或过期都抛 JWTError → 转 401
★ SECRET 绝不能硬编码进代码/提交 git，应放环境变量（〔10_工程化/02〕）
★ 现在还要每次手动 decode——下一课把「decode→取出当前用户」做成依赖，见 〔08/04〕
"""
