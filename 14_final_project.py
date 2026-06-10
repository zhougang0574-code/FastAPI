"""
第 14 课：综合项目 —— 任务管理 API（Todo App）

综合运用所有知识点：
1. Pydantic 请求体 + 响应模型 + Field 校验（第 4-5 课）
2. SQLAlchemy ORM + SQLite（第 10 课）
3. 完整 CRUD + 软删除（第 11 课）
4. 多对多关系（Task ↔ Tag）（第 12 课）
5. 依赖注入：数据库会话 + 公共过滤参数（第 7 课）
6. 错误处理：HTTPException（第 6 课）
7. CORS 中间件（第 8 课）
8. Enum 状态限制（第 2 课）
9. 统计接口：多条件聚合查询

启动：uvicorn 14_final_project:app --reload
文档：http://127.0.0.1:8000/docs
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Table, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, joinedload, relationship, sessionmaker

# ── 数据库 ──

DATABASE_URL = "sqlite:///./todo_app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# 多对多关联表
task_tag_table = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class TaskStatus(str, PyEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default=TaskStatus.todo.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    tags = relationship("TagModel", secondary=task_tag_table, back_populates="tasks")


class TagModel(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    tasks = relationship("TaskModel", secondary=task_tag_table, back_populates="tags")


Base.metadata.create_all(bind=engine)


# ── Pydantic Schemas ──

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class TagResponse(BaseModel):
    id: int
    name: str
    class Config: from_attributes = True


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: TaskStatus = TaskStatus.todo
    tag_ids: list[int] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    tag_ids: Optional[list[int]] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []
    class Config: from_attributes = True


class StatsResponse(BaseModel):
    total: int
    todo: int
    in_progress: int
    done: int
    total_tags: int


# ── 应用 ──

app = FastAPI(
    title="Todo Task Manager API",
    description="FastAPI 综合实战：任务管理系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


def get_task_or_404(task_id: int, db: Session) -> TaskModel:
    task = (
        db.query(TaskModel)
        .options(joinedload(TaskModel.tags))
        .filter(TaskModel.id == task_id, TaskModel.is_deleted == False)
        .first()
    )
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return task


# ── 标签 CRUD ──

@app.post("/tags", response_model=TagResponse, status_code=201, tags=["Tags"])
def create_tag(tag: TagCreate, db: DbDep):
    if db.query(TagModel).filter(TagModel.name == tag.name).first():
        raise HTTPException(400, f"Tag '{tag.name}' already exists")
    db_tag = TagModel(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@app.get("/tags", response_model=list[TagResponse], tags=["Tags"])
def list_tags(db: DbDep):
    return db.query(TagModel).all()


@app.delete("/tags/{tag_id}", status_code=204, tags=["Tags"])
def delete_tag(tag_id: int, db: DbDep):
    tag = db.query(TagModel).get(tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    db.delete(tag)
    db.commit()


# ── 任务 CRUD ──

@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["Tasks"])
def create_task(task: TaskCreate, db: DbDep):
    db_task = TaskModel(
        title=task.title,
        description=task.description,
        status=task.status.value,
    )
    if task.tag_ids:
        tags = db.query(TagModel).filter(TagModel.id.in_(task.tag_ids)).all()
        if len(tags) != len(task.tag_ids):
            raise HTTPException(400, "One or more tag IDs not found")
        db_task.tags = tags
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/tasks", response_model=list[TaskResponse], tags=["Tasks"])
def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="按状态过滤"),
    tag_name: Optional[str] = Query(None, description="按标签名过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: DbDep = None,
):
    query = (
        db.query(TaskModel)
        .options(joinedload(TaskModel.tags))
        .filter(TaskModel.is_deleted == False)
    )
    if status:
        query = query.filter(TaskModel.status == status.value)
    if tag_name:
        query = query.join(TaskModel.tags).filter(TagModel.name == tag_name)
    return query.offset(skip).limit(limit).all()


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def get_task(task_id: int, db: DbDep):
    return get_task_or_404(task_id, db)


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def update_task(task_id: int, task_update: TaskUpdate, db: DbDep):
    db_task = get_task_or_404(task_id, db)
    update_data = task_update.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)
    for key, value in update_data.items():
        if key == "status" and isinstance(value, TaskStatus):
            value = value.value
        setattr(db_task, key, value)
    if tag_ids is not None:
        tags = db.query(TagModel).filter(TagModel.id.in_(tag_ids)).all()
        db_task.tags = tags
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}", status_code=204, tags=["Tasks"])
def delete_task(task_id: int, db: DbDep):
    db_task = get_task_or_404(task_id, db)
    db_task.is_deleted = True
    db.commit()


# ── 统计接口 ──

@app.get("/stats", response_model=StatsResponse, tags=["Stats"])
def get_stats(db: DbDep):
    active = TaskModel.is_deleted == False
    return StatsResponse(
        total=db.query(TaskModel).filter(active).count(),
        todo=db.query(TaskModel).filter(active, TaskModel.status == "todo").count(),
        in_progress=db.query(TaskModel).filter(active, TaskModel.status == "in_progress").count(),
        done=db.query(TaskModel).filter(active, TaskModel.status == "done").count(),
        total_tags=db.query(TagModel).count(),
    )


"""
API 结构总览
============

Tags:
  POST   /tags          → 创建标签
  GET    /tags          → 标签列表
  DELETE /tags/{id}     → 删除标签

Tasks:
  POST   /tasks         → 创建任务（支持关联标签）
  GET    /tasks         → 任务列表（支持 status/tag_name 过滤 + 分页）
  GET    /tasks/{id}    → 任务详情（含标签）
  PATCH  /tasks/{id}    → 部分更新（支持更新标签）
  DELETE /tasks/{id}    → 软删除

Stats:
  GET    /stats         → 按状态统计任务数量


综合运用的核心知识点 ★
======================
★ Annotated + Depends 简化重复的依赖声明（DbDep）
★ joinedload 避免 N+1，一次查询获取 Task + Tags
★ exclude_unset 让 PATCH 只更新传入字段
★ Enum 状态值同时充当文档和校验
★ /docs 页面的 tags 参数把接口按模块分组，大项目必用
"""
