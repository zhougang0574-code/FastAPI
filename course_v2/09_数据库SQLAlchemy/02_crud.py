"""
【数据库SQLAlchemy / 02】完整 CRUD + get_or_404 + 软删除 + 分页过滤

与上一课的区别：
    〔09_数据库SQLAlchemy/01〕只有「建/查单条」。本课补齐增删改查全套，并加上三个
    工程常用模式：查不到抛 404、软删除、分页过滤。

本课知识点（合并讲，都是 CRUD 套路）：
    1. POST/GET/PATCH/DELETE 对应 增/查/改/删               —— ≈ Spring Data Repository
    2. get_or_404：查到返回、查不到抛 404，消除重复          —— ≈ findById().orElseThrow()
    3. PATCH 用 exclude_unset 只更新传入字段                  —— 部分更新
    4. 软删除：标记 is_deleted 而非真删；分页用 offset/limit

为什么需要：
    这是每个 CRUD 接口的标准骨架。get_or_404 和软删除是工程上几乎必用的两个模式。
"""

from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Boolean, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

engine = create_engine("sqlite:///./crud.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


class ItemORM(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column()
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)   # 软删除标记


Base.metadata.create_all(bind=engine)


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    model_config = {"from_attributes": True}


app = FastAPI(title="完整 CRUD")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# get_or_404：查到返回，查不到抛 404（≈ findById().orElseThrow），消除每个接口的重复判断
def get_item_or_404(item_id: int, db: Session) -> ItemORM:
    obj = db.query(ItemORM).filter(ItemORM.id == item_id, ItemORM.is_deleted == False).first()
    if obj is None:
        raise HTTPException(404, f"item {item_id} 不存在")
    return obj


@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemCreate, db: DbDep):
    obj = ItemORM(**item.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.get("/items", response_model=list[ItemOut])
def list_items(
    db: DbDep,
    keyword: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    q = db.query(ItemORM).filter(ItemORM.is_deleted == False)
    if keyword:
        q = q.filter(ItemORM.name.contains(keyword))   # 条件过滤
    return q.offset(skip).limit(limit).all()           # 分页


@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: DbDep):
    return get_item_or_404(item_id, db)


@app.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, patch: ItemUpdate, db: DbDep):
    obj = get_item_or_404(item_id, db)
    # exclude_unset=True：只取客户端实际传了的字段，没传的不动（部分更新）
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: DbDep):
    obj = get_item_or_404(item_id, db)
    obj.is_deleted = True    # 软删除：不真删，标记即可（可恢复、留痕）
    db.commit()


"""
执行流程图
==========

POST   /items        → 创建（add/commit/refresh）
GET    /items?...    → 列表（filter 过滤 + offset/limit 分页，排除已软删）
GET    /items/{id}   → 详情（get_or_404）
PATCH  /items/{id}   → 部分更新（exclude_unset 只改传入字段）
DELETE /items/{id}   → 软删除（is_deleted=True，返回 204）

核心知识点 ★
============
★ get_or_404 把「查不到→404」收口成一个函数，所有接口复用（≈ orElseThrow）
★ PATCH 用 model_dump(exclude_unset=True) 实现「只更新传了的字段」
★ 软删除 = is_deleted 标记 + 查询统一过滤 is_deleted==False（数据可恢复、可审计）
★ 分页用 .offset(skip).limit(limit)，并用 Query(ge/le) 约束参数范围
★ 多表关系（一对多/多对多）见 〔09/03〕〔09/04〕
"""
