"""
【数据库SQLAlchemy / 05】N+1 查询问题与 joinedload 急加载（难点·细拆）

与上一课的区别：
    〔09/03〕〔09/04〕能跑通关系，但默认「懒加载」藏着性能陷阱。本课只讲一件事：
    N+1 问题是什么、为什么发生、怎么用 joinedload 一次查完解决。

本课知识点（只讲一个核心概念）：
    1. 懒加载：访问关系属性时才去查 → 列表场景触发 N+1
    2. N+1：查 1 次列表 + 对 N 条各查 1 次关系 = N+1 条 SQL
    3. joinedload / selectinload：急加载，一次（或两次）查完  —— ≈ JPA 的 fetch join / @EntityGraph

为什么需要：
    N+1 是 ORM 头号性能杀手，列表接口尤其容易中招（页面没几条数据却发了几百条 SQL）。
    这和 Hibernate 的 N+1 是同一个问题、同一个解法，必须单独讲透。
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, joinedload,
                            mapped_column, relationship, selectinload, sessionmaker)

engine = create_engine("sqlite:///./nplus1.db", connect_args={"check_same_thread": False})
# echo=True 会把执行的 SQL 打到控制台——开着它最能直观看到 N+1
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    posts: Mapped[list["PostORM"]] = relationship(back_populates="author")


class PostORM(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["UserORM"] = relationship(back_populates="posts")


Base.metadata.create_all(bind=engine)


class PostOut(BaseModel):
    id: int
    title: str
    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    name: str
    posts: list[PostOut] = []
    model_config = {"from_attributes": True}


app = FastAPI(title="N+1 与急加载")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# ✗ 反面：会触发 N+1。查 users 1 条 SQL，序列化时对每个 user 访问 .posts 又各发 1 条
@app.get("/users-bad", response_model=list[UserOut])
def list_users_bad(db: DbDep):
    return db.query(UserORM).all()           # 看似一句，实际 1 + N 条 SQL


# ✓ 正面：joinedload 用 JOIN 一次把 users + posts 查回来（≈ JPA fetch join）
@app.get("/users-joined", response_model=list[UserOut])
def list_users_joined(db: DbDep):
    return db.query(UserORM).options(joinedload(UserORM.posts)).all()


# ✓ 另一种：selectinload 用 2 条 SQL（IN 查询），一对多/集合通常比 joinedload 更高效
@app.get("/users-selectin", response_model=list[UserOut])
def list_users_selectin(db: DbDep):
    return db.query(UserORM).options(selectinload(UserORM.posts)).all()


"""
执行流程图
==========

懒加载（默认）查 N 个用户的文章：
    SELECT * FROM users;                 ← 1 条
    SELECT * FROM posts WHERE author_id=1;  ┐
    SELECT * FROM posts WHERE author_id=2;  │ ← N 条（每个用户一条）
    ...                                     ┘
    合计 1 + N  ← 这就是 N+1

joinedload（急加载）：
    SELECT ... FROM users LEFT JOIN posts ...   ← 1 条 JOIN 全搞定

selectinload（急加载）：
    SELECT * FROM users;
    SELECT * FROM posts WHERE author_id IN (1,2,...);   ← 共 2 条

核心知识点 ★
============
★ N+1 = 1 条列表查询 + N 条关系查询；懒加载在列表场景必然触发，是 ORM 头号性能坑
★ .options(joinedload(关系)) 用 JOIN 一次查完（≈ JPA fetch join / @EntityGraph）
★ 一对多/集合优先 selectinload（2 条 IN 查询，避免 JOIN 行数膨胀）；多对一可用 joinedload
★ 开 create_engine(..., echo=True) 打印 SQL，是定位 N+1 最直接的手段
★ 这与 Hibernate 的 N+1 完全同源，解决思路一致
"""
