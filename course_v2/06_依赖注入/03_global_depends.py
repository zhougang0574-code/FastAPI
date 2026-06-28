"""
【依赖注入 / 03】路由组依赖 / 全局依赖（进阶）

与上一课的区别：
    前两课的依赖都「注入一个值」给路由用。本课的依赖「只为副作用」（如鉴权校验），
    不需要返回值给路由，而是挂在「整组路由」或「整个应用」上统一生效。

本课知识点：
    1. 路由级 dependencies=[...]：依赖只执行不注入值（做校验/拦截）  —— ≈ 方法级拦截
    2. APIRouter(dependencies=[...])：一组路由统一加依赖             —— ≈ 给 Controller 加拦截器
    3. FastAPI(dependencies=[...])：全局所有路由都加                 —— ≈ 全局 Filter/Interceptor

为什么需要：
    「这一组接口都要校验 API Key」这种需求，不该在每个函数参数里都写一遍。
    用 dependencies=[...] 在路由组/应用层统一挂，就是 Spring 的拦截器思路。
"""

from fastapi import Depends, FastAPI, Header, HTTPException


# 一个「只校验、不返回值」的依赖：校验请求头里的 API Key
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "secret-key":
        raise HTTPException(401, "API Key 无效")
    # 注意：没有 return，它的作用纯粹是「校验失败就拦下来」


# dependencies=[...] 把依赖挂在 app 全局：所有路由请求前都会先跑 verify_api_key
# ≈ 注册一个全局拦截器/Filter
app = FastAPI(title="全局依赖", dependencies=[Depends(verify_api_key)])


@app.get("/ping")
def ping():
    # 走到这里说明 API Key 已校验通过（否则 401，根本进不来）
    return {"msg": "pong"}


# 也可以只给单个路由挂（路由级），同样是「执行但不注入」
def log_access():
    print("[审计] 有人访问了敏感接口")


@app.get("/admin", dependencies=[Depends(log_access)])
def admin():
    return {"msg": "admin area"}


"""
执行流程图
==========

请求进入任意路由
    │
    ▼
先执行 app 级 dependencies：verify_api_key
    ├─ Key 错 → 401（不进路由）
    └─ Key 对 → 继续
    │
    ▼
再执行该路由自己的 dependencies（如 log_access）
    │
    ▼
执行路由函数

三个层级（范围由大到小）：
    FastAPI(dependencies=[...])      全局，所有路由（≈ 全局 Filter）
    APIRouter(dependencies=[...])    一组路由（≈ Controller 级拦截器）
    @app.get(dependencies=[...])     单个路由（≈ 方法级）

核心知识点 ★
============
★ dependencies=[Depends(fn)] 里的依赖「只执行、不把返回值注入」，适合做校验/拦截
★ 三个挂载层级：FastAPI（全局）/ APIRouter（路由组）/ 单路由，对应 Spring 拦截器范围
★ 校验类逻辑（鉴权、限流、审计）用它统一挂，避免每个函数参数里重复声明
★ 需要把值用在函数里（如当前用户对象）→ 仍用参数级 Depends（〔06/01〕）
★ APIRouter 怎么拆分大项目见 〔10_工程化/01〕
"""
