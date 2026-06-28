"""
【数据库SQLAlchemy / 04】多对多关系：Post ↔ Tag

与上一课的区别：
    〔09_数据库SQLAlchemy/03〕是一对多（外键在一方）。本课是多对多：一篇 Post 有多个
    Tag，一个 Tag 也属于多篇 Post——需要一张「中间关联表」。

本课知识点：
    1. Table 定义中间关联表（只存两个外键）          —— ≈ @JoinTable
    2. relationship(secondary=关联表) 声明多对多       —— ≈ @ManyToMany
    3. 双向 back_populates：Post.tags ↔ Tag.posts

为什么需要：
    标签、角色权限、收藏这类「双方都可多」的关系，必须用中间表。
    这是关系建模的第二种基本型，掌握后常见关系就齐了。
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship, sessionmaker)

engine = create_engine("sqlite:///./m2m.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


# 中间关联表：只存两边的外键（≈ @JoinTable）。多对多必须有它。
post_tag = Table(
    "post_tag", Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class PostORM(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    # secondary=关联表 → 声明多对多（≈ @ManyToMany）
    tags: Mapped[list["TagORM"]] = relationship(secondary=post_tag, back_populates="posts")


class TagORM(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    posts: Mapped[list["PostORM"]] = relationship(secondary=post_tag, back_populates="tags")


Base.metadata.create_all(bind=engine)


class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: int
    title: str
    tags: list[TagOut] = []
    model_config = {"from_attributes": True}


app = FastAPI(title="多对多关系")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


@app.post("/posts/{title}", response_model=PostOut)
def create_post(title: str, tags: str, db: DbDep):
    post = PostORM(title=title)
    for tag_name in tags.split(","):                       # 如 ?tags=python,web
        tag = db.query(TagORM).filter(TagORM.name == tag_name).first()
        if tag is None:
            tag = TagORM(name=tag_name)                    # 不存在则新建
        post.tags.append(tag)                              # 关系集合 append，ORM 自动写中间表
    db.add(post); db.commit(); db.refresh(post)
    return post


@app.get("/tags/{name}/posts", response_model=list[PostOut])
def posts_by_tag(name: str, db: DbDep):
    tag = db.query(TagORM).filter(TagORM.name == name).first()
    return tag.posts if tag else []


"""
执行流程图
==========

三张表：
    posts(id, title)
    tags(id, name)
    post_tag(post_id, tag_id)   ← 中间关联表，只存两个外键

关系：
    Post.tags ──secondary=post_tag──▶ Tag.posts   （双向多对多）

写入：post.tags.append(tag) → ORM 自动往 post_tag 插一行
查询：tag.posts → 经中间表反查所有关联 Post

核心知识点 ★
============
★ 多对多必须有中间关联表（Table 定义，≈ @JoinTable），只存双方外键
★ relationship(secondary=关联表, back_populates=...) 声明多对多（≈ @ManyToMany）
★ 操作 post.tags.append(tag)，ORM 自动维护中间表，无需手动插
★ 一对多看 〔09/03〕、多对多看本课——两者覆盖绝大多数关系建模
★ 关系查询同样有 N+1 风险，统一在 〔09/05〕用 joinedload 解决
"""
