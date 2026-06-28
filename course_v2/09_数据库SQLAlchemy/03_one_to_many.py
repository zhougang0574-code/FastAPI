"""
【数据库SQLAlchemy / 03】一对多关系：User 拥有多个 Post

与上一课的区别：
    前面都是单表。本课引入第一种关系：一对多（一个 User 有多个 Post），
    用外键 + relationship 把两张表关联起来。

本课知识点：
    1. ForeignKey 在「多」的一方建外键列            —— ≈ @ManyToOne 的外键
    2. relationship + back_populates 双向关联         —— ≈ @OneToMany / @ManyToOne
    3. 嵌套响应 Schema：UserOut 里带 list[PostOut]    —— ≈ DTO 里嵌子 DTO 列表

为什么需要：
    真实业务全是关系数据。一对多（用户-文章、订单-明细）是最基础的关系，
    理解 ForeignKey + relationship 的配合是后面多对多、N+1 的前提。
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship, sessionmaker)

engine = create_engine("sqlite:///./o2m.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    # 「一」的一方：posts 是该用户的所有文章；back_populates 指向 Post.author
    posts: Mapped[list["PostORM"]] = relationship(back_populates="author")


class PostORM(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    # 「多」的一方：外键指向 users.id（≈ @ManyToOne 的外键列）
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["UserORM"] = relationship(back_populates="posts")


Base.metadata.create_all(bind=engine)


# 嵌套响应：UserOut 里包含它的文章列表
class PostOut(BaseModel):
    id: int
    title: str
    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    name: str
    posts: list[PostOut] = []     # 嵌套子 DTO 列表
    model_config = {"from_attributes": True}


app = FastAPI(title="一对多关系")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


@app.post("/users/{name}/posts/{title}", response_model=UserOut)
def add_post(name: str, title: str, db: DbDep):
    user = db.query(UserORM).filter(UserORM.name == name).first()
    if user is None:
        user = UserORM(name=name)
        db.add(user)
    user.posts.append(PostORM(title=title))   # 直接操作关系集合，ORM 自动设外键
    db.commit(); db.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbDep):
    # 访问 user.posts 时 ORM 会自动再查一次 posts 表（懒加载）——这埋了 N+1 隐患，见 〔09/05〕
    return db.get(UserORM, user_id)


"""
执行流程图
==========

表结构：
    users(id, name)
    posts(id, title, author_id → users.id)   ← 外键在「多」的一方

关系声明：
    User.posts  ──back_populates──▶  Post.author   （双向关联）

读取嵌套：
    GET /users/1 → 查 user → 访问 user.posts（懒加载触发查 posts）
                 → UserOut 自动把 posts 序列化成 list[PostOut]

核心知识点 ★
============
★ 一对多：外键 ForeignKey 建在「多」的一方（posts.author_id）
★ relationship + back_populates 建立双向关联（≈ @OneToMany / @ManyToOne）
★ 操作关系集合（user.posts.append）即可，ORM 自动维护外键
★ 嵌套 Schema（UserOut 含 list[PostOut]）让响应自然带出关联数据
★ 默认懒加载：循环里逐个访问关系会触发 N+1，解决见 〔09/05〕
"""
