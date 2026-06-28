"""
【数据库SQLAlchemy / 01】数据库接入：engine / Session / get_db / Model vs Schema

与上一课的区别：
    前面数据都存在内存 dict 里。本课接真数据库：用 SQLAlchemy ORM 把 Python 类
    映射到表，用 yield 依赖（回顾 〔06_依赖注入/02〕）管理会话。

本课知识点：
    1. create_engine + SessionLocal：连接 + 会话工厂        —— ≈ DataSource + EntityManager
    2. DeclarativeBase 子类 = 表（ORM Model）               —— ≈ @Entity
    3. get_db 用 yield 管理会话生命周期（请求结束自动关）   —— ≈ 每请求一个 Session + 自动关闭
    4. ORM Model 与 Pydantic Schema 分离，from_attributes 桥接 —— ≈ Entity 与 DTO 分离

为什么需要：
    这是数据库域的地基。重点理解两套模型的分工：SQLAlchemy Model 管「存数据库」，
    Pydantic Schema 管「收发 JSON」，二者职责分离，靠 from_attributes 互转。
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# engine：数据库连接（≈ DataSource）。SQLite 需要 check_same_thread=False 配合多线程
engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
# SessionLocal：会话工厂，每次请求 new 一个（≈ 每请求一个 EntityManager）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ORM Model：映射到数据库表（≈ @Entity）。注意这是「持久化」用的类
class ItemORM(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[float] = mapped_column()


Base.metadata.create_all(bind=engine)   # 建表（生产用 Alembic 迁移，见 〔09/06〕）


# Pydantic Schema：收发 JSON 用（≈ DTO）。和 ORM Model 分开，职责清晰
class ItemCreate(BaseModel):
    name: str
    price: float


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    # from_attributes=True：允许从 ORM 对象（按属性）构建这个 Schema
    model_config = {"from_attributes": True}


app = FastAPI(title="数据库接入")


# get_db：yield 依赖，每请求开一个会话，请求结束自动关闭（回顾 〔06/02〕）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemCreate, db: DbDep):
    obj = ItemORM(name=item.name, price=item.price)   # Schema → ORM Model
    db.add(obj)
    db.commit()              # 提交事务
    db.refresh(obj)          # 刷新拿到自增 id
    return obj               # ORM 对象 → 经 from_attributes 转 ItemOut


@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: DbDep):
    return db.get(ItemORM, item_id)


"""
执行流程图
==========

请求进入
    │
    ▼
get_db（yield 依赖）开会话 Session
    │
    ▼
路由用 db 操作：
    add/commit/refresh（写）  或  db.get/query（读）
    Schema(收 JSON) → ORM(存库) → ORM(查出) → Schema(发 JSON)
    │
    ▼
响应返回后 get_db 的 finally 关闭会话

两套模型分工：
    SQLAlchemy ORM Model（@Entity）  ←持久化→  数据库表
    Pydantic Schema（DTO）           ←序列化→  JSON
            └────── from_attributes 互转 ──────┘

核心知识点 ★
============
★ engine=连接、SessionLocal=会话工厂、get_db=每请求一会话（yield 自动关）
★ ORM Model（≈@Entity）管存储，Pydantic Schema（≈DTO）管 JSON，务必分离
★ Schema 加 from_attributes=True 才能从 ORM 对象构建（配合 response_model 直接 return ORM）
★ 写操作三连：add → commit → refresh（refresh 拿自增主键等 DB 生成的值）
★ create_all 仅适合学习；生产环境表结构变更用 Alembic 迁移 〔09/06〕
"""
