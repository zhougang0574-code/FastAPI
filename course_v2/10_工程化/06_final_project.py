"""
【工程化 / 06】综合项目：任务管理 API（Todo App）

把整套课程的核心串成一个能跑的真实小项目。综合运用：
    1. Pydantic 请求体 + response_model + Field 校验   〔03 / 04〕
    2. SQLAlchemy ORM + yield 依赖管理会话             〔06/02 · 09/01〕
    3. 完整 CRUD + get_or_404 + 软删除 + 分页过滤       〔09/02〕
    4. 多对多关系（Task ↔ Tag）+ joinedload 防 N+1      〔09/04 · 09/05〕
    5. JWT 认证：登录拿 token + get_current_user 保护    〔08/03 · 08/04〕
    6. APIRouter 按模块分组 + tags                       〔10/01〕
    7. HTTPException 错误处理                            〔05/01〕

启动：cd course_v2/10_工程化 && uvicorn 06_final_project:app --reload
文档：http://127.0.0.1:8000/docs   （先 POST /auth/token 登录拿 token，再点 Authorize）

注：为单文件可运行，所有模块写在一起；真实项目应按 〔10/01〕拆成多文件 + 用 〔10/02〕管配置。
"""

from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, String, Table,
                        create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, joinedload,
                            mapped_column, relationship, sessionmaker)

# ── 配置（真实项目用 〔10/02〕Settings 从环境读）──
SECRET_KEY, ALGORITHM, EXPIRE_MIN = "dev-secret-change-me", "HS256", 30

# ── 数据库 ──
engine = create_engine("sqlite:///./todo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


task_tag = Table(
    "task_tag", Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class TaskStatus(str, PyEnum):
    todo = "todo"
    doing = "doing"
    done = "done"


class TaskORM(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default=TaskStatus.todo.value)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    tags: Mapped[list["TagORM"]] = relationship(secondary=task_tag, back_populates="tasks")


class TagORM(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    tasks: Mapped[list["TaskORM"]] = relationship(secondary=task_tag, back_populates="tags")


Base.metadata.create_all(bind=engine)

# ── Schemas ──


class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: TaskStatus = TaskStatus.todo
    tag_names: list[str] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[TaskStatus] = None


class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    tags: list[TagOut] = []
    model_config = {"from_attributes": True}


# ── 公共依赖 ──


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
_USERS = {"alice": pwd_context.hash("pwd123")}   # 假用户库


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证无效",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    except JWTError:
        raise exc
    if username not in _USERS:
        raise exc
    return username


CurrentUser = Annotated[str, Depends(get_current_user)]


def get_task_or_404(task_id: int, db: Session) -> TaskORM:
    task = (db.query(TaskORM).options(joinedload(TaskORM.tags))
            .filter(TaskORM.id == task_id, TaskORM.is_deleted == False).first())
    if task is None:
        raise HTTPException(404, f"task {task_id} 不存在")
    return task


def resolve_tags(names: list[str], db: Session) -> list[TagORM]:
    tags = []
    for n in names:
        tag = db.query(TagORM).filter(TagORM.name == n).first() or TagORM(name=n)
        tags.append(tag)
    return tags


# ── 认证路由组 ──
auth_router = APIRouter(prefix="/auth", tags=["认证"])


@auth_router.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    hashed = _USERS.get(form.username)
    if not hashed or not pwd_context.verify(form.password, hashed):
        raise HTTPException(401, "用户名或密码错误")
    payload = {"sub": form.username,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN)}
    return {"access_token": jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM),
            "token_type": "bearer"}


# ── 任务路由组（全部需要登录）──
tasks_router = APIRouter(prefix="/tasks", tags=["任务"])


@tasks_router.post("", response_model=TaskOut, status_code=201)
def create_task(data: TaskCreate, db: DbDep, user: CurrentUser):
    task = TaskORM(title=data.title, status=data.status.value,
                   tags=resolve_tags(data.tag_names, db))
    db.add(task); db.commit(); db.refresh(task)
    return task


@tasks_router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DbDep, user: CurrentUser,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
):
    q = (db.query(TaskORM).options(joinedload(TaskORM.tags))   # joinedload 防 N+1
         .filter(TaskORM.is_deleted == False))
    if status_filter:
        q = q.filter(TaskORM.status == status_filter.value)
    return q.offset(skip).limit(limit).all()


@tasks_router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: DbDep, user: CurrentUser):
    return get_task_or_404(task_id, db)


@tasks_router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, patch: TaskUpdate, db: DbDep, user: CurrentUser):
    task = get_task_or_404(task_id, db)
    data = patch.model_dump(exclude_unset=True)
    if "status" in data and data["status"]:
        data["status"] = data["status"].value
    for k, v in data.items():
        setattr(task, k, v)
    db.commit(); db.refresh(task)
    return task


@tasks_router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: DbDep, user: CurrentUser):
    task = get_task_or_404(task_id, db)
    task.is_deleted = True       # 软删除
    db.commit()


# ── 组装主应用 ──
app = FastAPI(title="Todo 任务管理 API", description="FastAPI 综合实战", version="1.0.0")
app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/", tags=["根"])
def root():
    return {"msg": "见 /docs；先 POST /auth/token 登录（alice/pwd123）拿 token 再 Authorize"}


"""
API 总览
========
认证:
  POST /auth/token       登录拿 JWT（表单 username=alice & password=pwd123）
任务（需 Bearer token）:
  POST   /tasks          创建（可带 tag_names 自动建标签）
  GET    /tasks          列表（status 过滤 + 分页，joinedload 防 N+1）
  GET    /tasks/{id}     详情
  PATCH  /tasks/{id}     部分更新（exclude_unset）
  DELETE /tasks/{id}     软删除（204）

综合运用的知识点 ★
==================
★ APIRouter 把认证/任务分成两组，tags 在 /docs 分模块（〔10/01〕）
★ get_current_user 依赖保护所有 /tasks 路由，未登录 401（〔08/04〕）
★ yield 依赖 get_db 管会话；get_task_or_404 复用「查不到→404」（〔06/02 · 09/02〕）
★ 多对多 Task↔Tag + joinedload 一次查回标签，避免列表 N+1（〔09/04 · 09/05〕）
★ response_model + Field 校验 + 软删除 + 分页，全部来自前面各域，这里只是「组装」
★ 真实项目还应：路由拆多文件、配置走 Settings、表结构用 Alembic、补 pytest 测试
"""
