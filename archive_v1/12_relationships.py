"""
第 12 课：关系模型 Relationships

学习要点：
1. 一对多：User 拥有多个 Post（ForeignKey + relationship + back_populates）
2. 多对多：Post 有多个 Tag，通过中间关联表实现
3. relationship() 声明 ORM 层的关系，lazy loading vs eager loading
4. joinedload 一次查询拿所有关联数据，避免 N+1 查询问题
5. Response Schema 嵌套：UserWithPosts 里包含 PostResponse 列表
"""

from typing import Optional
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, joinedload, relationship, sessionmaker
from pydantic import BaseModel

SQLALCHEMY_DATABASE_URL = "sqlite:///./relations.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── 多对多关联表（纯中间表，不需要独立 ORM 类）──
post_tag_table = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


# ── ORM 模型 ──

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    # 一对多：User 有多个 Post
    # back_populates 建立双向引用（post.author ↔ user.posts）
    posts = relationship("PostModel", back_populates="author")


class PostModel(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    # ForeignKey 建立外键约束
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("UserModel", back_populates="posts")
    # 多对多：Post 有多个 Tag，secondary 指定关联表
    tags = relationship("TagModel", secondary=post_tag_table, back_populates="posts")


class TagModel(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    posts = relationship("PostModel", secondary=post_tag_table, back_populates="tags")


Base.metadata.create_all(bind=engine)


# ── Pydantic Schemas（嵌套结构）──

class TagResponse(BaseModel):
    id: int
    name: str
    class Config: from_attributes = True


class PostResponse(BaseModel):
    id: int
    title: str
    tags: list[TagResponse] = []
    class Config: from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str
    class Config: from_attributes = True


# 嵌套响应：包含完整的 posts 列表（每个 post 还含 tags）
class UserWithPosts(BaseModel):
    id: int
    username: str
    posts: list[PostResponse] = []
    class Config: from_attributes = True


app = FastAPI(title="Relationships Demo")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── 用户接口 ──

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(username: str, db: Session = Depends(get_db)):
    if db.query(UserModel).filter(UserModel.username == username).first():
        raise HTTPException(400, f"Username '{username}' already taken")
    user = UserModel(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# joinedload：一条 SQL 拿到 User + 所有 Posts + 每个 Post 的 Tags
# 避免 N+1 问题（否则每个 post 都会单独查一次 tags）
@app.get("/users/{user_id}", response_model=UserWithPosts)
def get_user_with_posts(user_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(UserModel)
        .options(joinedload(UserModel.posts).joinedload(PostModel.tags))
        .filter(UserModel.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(404, "User not found")
    return user


# ── 标签接口 ──

@app.post("/tags", response_model=TagResponse, status_code=201)
def create_tag(name: str, db: Session = Depends(get_db)):
    if db.query(TagModel).filter(TagModel.name == name).first():
        raise HTTPException(400, f"Tag '{name}' already exists")
    tag = TagModel(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@app.get("/tags", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    return db.query(TagModel).all()


# ── 帖子接口 ──

@app.post("/posts", response_model=PostResponse, status_code=201)
def create_post(
    title: str,
    user_id: int,
    tag_ids: list[int] = [],
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    post = PostModel(title=title, user_id=user_id)
    if tag_ids:
        tags = db.query(TagModel).filter(TagModel.id.in_(tag_ids)).all()
        post.tags = tags
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/posts", response_model=list[PostResponse])
def list_posts(db: Session = Depends(get_db)):
    return (
        db.query(PostModel)
        .options(joinedload(PostModel.tags))
        .all()
    )


"""
关系模型结构图
==============

User (1) ──────── (N) Post
    id                  id
    username            title
                        user_id (FK → users.id)
                        │
                        └── (N) ←→ (N) Tag
                                       id
                                       name
                        （通过 post_tags 关联表）

SQL 查询对比：
    有 joinedload：
        SELECT users.*, posts.*, tags.* FROM users
        LEFT JOIN posts ON posts.user_id = users.id
        LEFT JOIN post_tags ON post_tags.post_id = posts.id
        LEFT JOIN tags ON tags.id = post_tags.tag_id
        WHERE users.id = 1
        → 1 条 SQL

    无 joinedload（N+1 问题）：
        SELECT * FROM users WHERE id=1       → 1 条
        SELECT * FROM posts WHERE user_id=1  → 1 条
        SELECT * FROM tags WHERE post_id=1   → N 条（每个 post 一条）


核心知识点 ★
============
★ ForeignKey 是数据库约束，relationship 是 Python 层的关系导航
★ back_populates 两边都要写，建立双向引用
★ 多对多必须有关联表（中间表），SQLAlchemy 用 secondary 参数声明
★ joinedload 是生产级别的必备技能，防止 N+1 是数据库性能优化的基本功
★ Pydantic 嵌套 Schema：列表字段类型写 list[PostResponse]，自动递归序列化
"""
