"""
第 9 课：安全认证 —— OAuth2 + JWT

学习要点：
1. OAuth2PasswordBearer：声明 token 从哪个 URL 获取，/docs 自动生成授权按钮
2. JWT（JSON Web Token）：无状态令牌，服务器不存状态，通过签名验证合法性
3. 密码用 bcrypt 哈希存储，永不明文，verify_password 对比哈希
4. get_current_user 是核心依赖：从请求头提取 Bearer token → 解码 → 返回用户
5. 保护路由只需在参数里注入 get_current_user 依赖
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# 生产环境用 secrets.token_hex(32) 生成随机密钥，不要硬编码！
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# bcrypt 上下文：用于密码哈希（hash）和校验（verify）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl 告诉 FastAPI 获取 token 的接口地址，/docs 会自动生成"Authorize"按钮
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# 模拟用户数据库（实际项目换成真实 DB）
fake_users_db = {
    "alice": {
        "username": "alice",
        "hashed_password": pwd_context.hash("secret"),  # 存储哈希，不存明文
        "disabled": False,
    },
    "bob": {
        "username": "bob",
        "hashed_password": pwd_context.hash("password123"),
        "disabled": True,
    },
}


class Token(BaseModel):
    access_token: str
    token_type: str   # 固定是 "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: Optional[bool] = None


def verify_password(plain: str, hashed: str) -> bool:
    # bcrypt 单向哈希：只能 verify，不能反推明文
    return pwd_context.verify(plain, hashed)


def authenticate_user(db: dict, username: str, password: str):
    user = db.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    payload["exp"] = expire   # JWT 标准字段：过期时间
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# 核心依赖：从 Authorization: Bearer <token> 头部提取并验证 JWT
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")  # "sub" 是 JWT 标准主题字段
        if username is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc
    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exc
    return user


async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    if current_user.get("disabled"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ── 登录接口 ──
# OAuth2PasswordRequestForm 自动读取 form 表单里的 username/password
@app.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


# ── 受保护接口：注入依赖即可 ──
@app.get("/users/me", response_model=User)
async def read_users_me(
    current_user: Annotated[dict, Depends(get_current_active_user)]
):
    return current_user


@app.get("/protected")
async def protected_route(
    current_user: Annotated[dict, Depends(get_current_active_user)]
):
    return {"message": f"Hello {current_user['username']}, you are authenticated!"}


"""
认证流程图
==========

1. 登录：POST /token (username=alice, password=secret)
       │
       ▼
   authenticate_user → 验证密码（bcrypt verify）
       │ 成功
       ▼
   create_access_token → JWT（含 sub=alice，30分钟过期）
       │
       ▼
   返回 {"access_token": "eyJ...", "token_type": "bearer"}

2. 访问受保护接口：GET /users/me
   请求头：Authorization: Bearer eyJ...
       │
       ▼
   get_current_user 依赖被触发
       │
       ▼
   jwt.decode → 验证签名 + 过期时间 → 取出 username
       │
       ▼
   查数据库返回用户对象 → 注入路由函数


核心知识点 ★
============
★ JWT 是无状态的：服务器不存 session，靠签名验证合法性
★ bcrypt 是单向哈希：无法从哈希值反推密码，即使数据库泄露也安全
★ SECRET_KEY 是唯一的安全密钥，生产环境必须用环境变量注入
★ 依赖链：get_current_active_user → get_current_user → oauth2_scheme
★ /docs 中点击 Authorize 输入账密，后续请求自动带 Bearer token
"""
