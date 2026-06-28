"""
【安全认证 / 04】get_current_user 依赖：把「token→用户」做成可复用依赖（难点·细拆）

与上一课的区别：
    〔08_安全认证/03〕每个路由都要自己 decode token。本课把「提取 token → 解码 →
    查出用户」封装成一个依赖 get_current_user，受保护路由注入它就拿到当前用户对象。

本课知识点（把前几课收口）：
    1. get_current_user 依赖：组合 oauth2_scheme + jwt.decode + 查用户
    2. 受保护路由注入它 → 直接拿到 User 对象（≈ Spring 的 @AuthenticationPrincipal）
    3. 一处定义、所有受保护路由复用——这就是认证的最终形态

为什么需要：
    认证逻辑只该写一遍。把它做成依赖后，保护任意路由只需在参数里加
    `user: Annotated[User, Depends(get_current_user)]`，干净且统一。
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI(title="当前用户依赖")

SECRET_KEY, ALGORITHM, EXPIRE_MINUTES = "dev-secret-change-me", "HS256", 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    username: str
    full_name: str


# 假用户库：用户名 → (哈希密码, 资料)
_USERS = {"alice": {"hash": pwd_context.hash("pwd123"), "full_name": "Alice Liu"}}


def create_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    rec = _USERS.get(form.username)
    if not rec or not pwd_context.verify(form.password, rec["hash"]):
        raise HTTPException(401, "用户名或密码错误")
    return {"access_token": create_token(form.username), "token_type": "bearer"}


# 核心：把「token → 当前用户」封装成依赖。oauth2_scheme 注入 token，本函数解码并查库。
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证无效",
                             headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise cred_exc
    rec = _USERS.get(username)
    if rec is None:
        raise cred_exc
    return User(username=username, full_name=rec["full_name"])


# 复用别名：任何路由想要「当前登录用户」，注入它即可
CurrentUser = Annotated[User, Depends(get_current_user)]


@app.get("/me", response_model=User)
def read_me(user: CurrentUser):       # ≈ @AuthenticationPrincipal User user
    return user


@app.get("/my-orders")
def my_orders(user: CurrentUser):     # 任意路由复用同一个依赖
    return {"owner": user.username, "orders": ["o1", "o2"]}


"""
执行流程图
==========

GET /me   Authorization: Bearer <jwt>
        │
        ▼
get_current_user 依赖链：
    oauth2_scheme 取 token ─▶ jwt.decode 验签/验期 ─▶ 取 sub ─▶ 查用户库
        │                         │                            │
      没带→401              失效→401                     查不到→401
        │
        ▼ 全过
    返回 User 对象 → 注入路由 → 直接可用 user.username

核心知识点 ★
============
★ get_current_user 把「oauth2_scheme + decode + 查库」收口成一个依赖，认证只写一遍
★ 受保护路由注入 CurrentUser 即拿到 User 对象（≈ @AuthenticationPrincipal）
★ 各种失败（无 token/失效/用户不存在）统一抛 401 + WWW-Authenticate 头
★ 这是认证域的「最终形态」：08/01→04 一层层叠上来（骨架→哈希→JWT→当前用户）
★ 想再按角色/权限细分访问，见 〔08/05〕Scopes
"""
