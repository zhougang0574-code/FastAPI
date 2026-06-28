"""
【工程化 / 01】APIRouter：把大项目拆成多文件（重要）

与上一课的区别：
    前面所有路由都挂在一个 app 上。真实项目几十上百个接口不能堆一个文件。
    本课用 APIRouter 把路由按模块拆开，再用 include_router 组装——就是 Spring 拆多个 Controller。

本课知识点：
    1. APIRouter() 定义一组路由（一个模块/资源）        —— ≈ 一个 @RestController
    2. prefix 统一前缀、tags 在 /docs 分组              —— ≈ @RequestMapping("/users")
    3. app.include_router(router) 把模块挂到主应用       —— ≈ 组件扫描装配
    4. router 级 dependencies 给整组路由统一加依赖

为什么需要：
    模块化是工程的基本要求。每个资源（users/items/orders）一个 router 一个文件，
    主文件只负责组装。结构清晰、易维护，和 SpringBoot 的多 Controller 完全对应。

    注：真实项目里 router 会拆到独立文件（routers/users.py），本课为可单文件运行，
        把两个 router 写在一起演示，组装方式与多文件完全一致。
"""

from fastapi import APIRouter, FastAPI

# ── 模块 A：用户路由（真实项目放 routers/users.py）──
# prefix 给本组所有路由加 /users 前缀；tags 让它们在 /docs 里归到 "用户" 分组
users_router = APIRouter(prefix="/users", tags=["用户"])


@users_router.get("")          # 实际路径 = prefix + "" = /users
def list_users():
    return [{"id": 1, "name": "alice"}]


@users_router.get("/{user_id}")   # 实际路径 = /users/{user_id}
def get_user(user_id: int):
    return {"id": user_id}


# ── 模块 B：商品路由（真实项目放 routers/items.py）──
items_router = APIRouter(prefix="/items", tags=["商品"])


@items_router.get("")
def list_items():
    return [{"id": 1, "name": "book"}]


# ── 主应用：只负责组装（真实项目的 main.py）──
app = FastAPI(title="APIRouter 拆分演示")
app.include_router(users_router)    # 把用户模块挂上来
app.include_router(items_router)    # 把商品模块挂上来


@app.get("/")
def root():
    return {"msg": "见 /docs，用户和商品已按 tags 分组"}


"""
执行流程图
==========

项目结构（真实多文件）：
    routers/users.py   → users_router  (prefix=/users, tags=["用户"])
    routers/items.py   → items_router  (prefix=/items, tags=["商品"])
    main.py            → app.include_router(各 router)

组装：
    APIRouter(prefix, tags) 定义模块  ──include_router──▶  挂到主 app
            │                                                 │
    ≈ @RestController + @RequestMapping              ≈ 组件扫描装配

核心知识点 ★
============
★ APIRouter ≈ 一个 Controller：按资源/模块拆，每个一个 router（通常一个文件）
★ prefix 统一路径前缀、tags 在 /docs 分组，include_router 把模块挂到主 app
★ router 也能挂 dependencies（整组加鉴权，回顾 〔06/03〕）
★ 主文件（main.py）只做组装与全局配置，保持轻薄
★ 配置（数据库 URL、SECRET）别散落各处，集中管理见 〔10/02〕
"""
