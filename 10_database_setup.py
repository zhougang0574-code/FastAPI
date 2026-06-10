"""
第 10 课：数据库基础 —— SQLAlchemy + SQLite

学习要点：
1. SQLAlchemy ORM：把 Python 类（DeclarativeBase 子类）映射到数据库表
2. create_engine 创建连接，SessionLocal 是每次请求独立的会话工厂
3. get_db 依赖用 yield 管理会话生命周期（请求结束自动关闭）
4. ORM Model（SQLAlchemy）和 Pydantic Schema 分离：职责清晰，避免混用
5. from_attributes=True 允许 Pydantic 从 ORM 对象构建
"""

from typing import Optional
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from pydantic import BaseModel

# ── 数据库连接配置 ──

# SQLite 文件数据库：数据保存在当前目录的 .db 文件里
SQLALCHEMY_DATABASE_URL = "sqlite:///./items_db.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # check_same_thread=False：允许多线程共享 SQLite 连接（SQLite 专属参数）
    connect_args={"check_same_thread": False},
)

# autocommit=False：需要手动 commit；autoflush=False：需要手动 flush
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── ORM 模型定义 ──

class Base(DeclarativeBase):
    pass


class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    # SQLite 没有原生 Boolean，存 0/1
    is_active = Column(Boolean, default=True)


# 启动时自动建表（生产环境推荐用 Alembic 做迁移管理）
Base.metadata.create_all(bind=engine)


# ── Pydantic Schema（API 层）──
# 与 ORM 模型分离：输入/输出用 Pydantic，数据库操作用 SQLAlchemy

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    is_active: bool

    class Config:
        # 允许从 ORM 对象直接构建 Pydantic 模型（读取 .属性 而非 dict key）
        from_attributes = True


# ── FastAPI 应用 ──

app = FastAPI()


# 数据库会话依赖：每个请求独立会话，请求结束自动关闭
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemModel(**item.model_dump())
    db.add(db_item)
    db.commit()
    # refresh：从数据库重新加载对象，获取自增的 id 等字段
    db.refresh(db_item)
    return db_item


@app.get("/items", response_model=list[ItemResponse])
def list_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(ItemModel).offset(skip).limit(limit).all()


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


"""
数据库交互流程图
================

POST /items (body: {"name":"Phone","price":999})
    │
    ▼
Pydantic 校验 ItemCreate
    │
    ▼
get_db 依赖 → 创建 Session
    │
    ▼
ItemModel(**item.model_dump()) → 构建 ORM 对象
    │
    ▼
db.add() → db.commit() → db.refresh()
    │
    ▼
ORM 对象 → Pydantic ItemResponse (from_attributes=True)
    │
    ▼
JSON 响应 + 201 Created
    │
    ▼
get_db finally → db.close()


核心知识点 ★
============
★ ORM Model 和 Pydantic Schema 分开：一个管数据库，一个管 API，职责清晰
★ db.refresh(obj) 必须在 commit 之后调用，否则自增 id 读不到
★ from_attributes=True 是 ORM → Pydantic 转换的必要配置
★ 每个请求一个 Session（不共享），防止事务相互污染
★ 生产环境换 PostgreSQL：只需改 SQLALCHEMY_DATABASE_URL，代码不变
"""
