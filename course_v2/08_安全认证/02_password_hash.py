"""
【安全认证 / 02】密码哈希：bcrypt 存储与校验（难点·细拆）

与上一课的区别：
    〔08_安全认证/01〕的密码是明文比较（_FAKE_USERS 里存的是明文）。本课只改一件事：
    密码用 bcrypt 哈希存储，登录时比对哈希——其它登录流程不变。

本课知识点（只加一层）：
    1. passlib 的 CryptContext 统一管理哈希算法（bcrypt）
    2. hash(明文) → 存哈希；verify(明文, 哈希) → 校验           —— ≈ Spring Security 的 PasswordEncoder
    3. 哈希不可逆、加盐、同一密码每次哈希结果都不同

为什么需要：
    数据库绝不能存明文密码——一旦泄露就是灾难。bcrypt 是行业标准。
    这正是 Spring Security 的 BCryptPasswordEncoder，概念完全一致。
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext

app = FastAPI(title="密码哈希")

# CryptContext 统一管理密码哈希（≈ PasswordEncoder），schemes 选 bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)            # 明文 → 哈希（加盐，不可逆）


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)  # 校验明文是否匹配哈希


# 用户库存的是「哈希」而非明文（注册时就该 hash 后入库）
_USERS = {"alice": hash_password("pwd123")}


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    hashed = _USERS.get(form.username)
    # 关键变化：不再明文比较，而是 verify(输入明文, 存储哈希)
    if not hashed or not verify_password(form.password, hashed):
        raise HTTPException(401, "用户名或密码错误")
    return {"access_token": form.username, "token_type": "bearer"}


"""
执行流程图
==========

注册时：明文密码 ──hash()──▶ 哈希串（加盐）──▶ 存数据库
                                              （绝不存明文）

登录时：
   POST /token (username, password明文)
        │
        ▼
   从库里取该用户的哈希 → verify(输入明文, 存储哈希)
        ├─ 匹配 → 签发 token
        └─ 不匹配 → 401

★ 同一密码每次 hash() 结果都不同（盐不同），但 verify 都能通过

核心知识点 ★
============
★ 数据库只存 bcrypt 哈希，永不存明文（≈ Spring Security BCryptPasswordEncoder）
★ CryptContext.hash() 加盐生成哈希；verify(明文, 哈希) 做校验
★ 哈希不可逆：找回密码只能「重置」，不能「解密」
★ 相对上一课只改了「明文比较 → verify 哈希」，登录流程其余不变（概念累积）
★ 下一课把返回的假 token 换成真正的 JWT，见 〔08/03〕
"""
