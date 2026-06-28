"""
【安全认证 / 05】权限作用域 Scopes（进阶）

与上一课的区别：
    〔08_安全认证/04〕只解决「是不是登录用户」。本课再进一步：区分「这个用户能不能
    干这件事」——用 OAuth2 scopes 表达细粒度权限（read / write / admin）。

本课知识点：
    1. token 里带 scopes 列表（签发时写入 payload）
    2. Security(dep, scopes=[...]) 声明「这个路由需要哪些权限」  —— ≈ @PreAuthorize("hasAuthority('write')")
    3. 依赖里校验 token 的 scopes 是否覆盖路由要求，不够则 403

为什么需要：
    登录了不等于什么都能干。Scopes 就是 Spring Security 的权限/角色机制，
    把「认证（你是谁）」和「授权（你能干嘛）」分开。
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

app = FastAPI(title="权限作用域")

# 声明可用的 scopes 及说明（会显示在 /docs 的 Authorize 弹窗里）
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"read": "读取权限", "write": "写入权限", "admin": "管理权限"},
)


# 模拟「已解码的 token」：实际应来自 JWT。这里直接给定用户拥有的 scopes。
def fake_decode(token: str) -> dict:
    # 约定 token 形如 "alice:read,write" 便于演示
    name, _, scope_str = token.partition(":")
    return {"sub": name, "scopes": scope_str.split(",") if scope_str else []}


# 校验依赖：SecurityScopes 自动收集「本次路由要求的 scopes」，与 token 实际拥有的比对
def check_scopes(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    user = fake_decode(token)
    for required in security_scopes.scopes:       # 路由要求的每个权限
        if required not in user["scopes"]:        # token 不具备 → 403
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"缺少权限: {required}",
                headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
            )
    return user


# Security(dep, scopes=[...]) 声明本路由需要的权限（≈ @PreAuthorize）
@app.get("/items")
def read_items(user: Annotated[dict, Security(check_scopes, scopes=["read"])]):
    return {"user": user["sub"], "data": ["i1", "i2"]}


@app.post("/items")
def create_item(user: Annotated[dict, Security(check_scopes, scopes=["write"])]):
    return {"user": user["sub"], "created": True}


@app.delete("/system")
def wipe(user: Annotated[dict, Security(check_scopes, scopes=["admin"])]):
    return {"user": user["sub"], "wiped": True}


"""
执行流程图
==========

GET /items  (要求 scope: read)
        │
        ▼
Security(check_scopes, scopes=["read"]) →
    SecurityScopes.scopes = ["read"]   （路由声明的要求）
    token 实际 scopes = ["read","write"]（从 token 解出）
        ├─ 要求 ⊆ 拥有 → 放行
        └─ 缺任一 → 403 Forbidden

认证 vs 授权：
    认证（你是谁）  = get_current_user 〔08/04〕
    授权（你能干嘛）= scopes 〔本课〕

核心知识点 ★
============
★ Scopes 表达细粒度权限：token 带拥有的 scopes，路由声明需要的 scopes
★ Security(dep, scopes=[...]) ≈ @PreAuthorize("hasAuthority(...)")，按路由声明要求
★ SecurityScopes 自动收集本次路由要求的权限，依赖里与 token 拥有的比对，不足则 403
★ 区分 401（没登录/认证失败）和 403（登录了但无权限）
★ 认证（你是谁）和授权（你能干嘛）是两件事，分开处理
"""
