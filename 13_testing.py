"""
第 13 课：测试 Testing

学习要点：
1. TestClient 模拟 HTTP 请求，不需要真正启动服务器
2. pytest fixture 共享测试资源（TestClient、测试数据库）
3. 用内存数据库（sqlite:///:memory:）隔离测试，每次干净
4. dependency_overrides 替换真实依赖（用测试 DB 替换生产 DB）
5. 每个测试独立，fixture 保证状态隔离，互不影响

运行：
    pytest 13_testing.py -v
"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from pydantic import BaseModel

# ── 被测应用 ──

class Base(DeclarativeBase):
    pass


class NoteModel(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)


class NoteCreate(BaseModel):
    text: str


class NoteResponse(BaseModel):
    id: int
    text: str
    class Config: from_attributes = True


# 生产数据库（测试时会被替换）
PROD_DB_URL = "sqlite:///./notes.db"
prod_engine = create_engine(PROD_DB_URL, connect_args={"check_same_thread": False})
ProdSession = sessionmaker(autocommit=False, autoflush=False, bind=prod_engine)
Base.metadata.create_all(bind=prod_engine)

app = FastAPI()


def get_db():
    db = ProdSession()
    try:
        yield db
    finally:
        db.close()


@app.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    db_note = NoteModel(text=note.text)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


@app.get("/notes", response_model=list[NoteResponse])
def list_notes(db: Session = Depends(get_db)):
    return db.query(NoteModel).all()


@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()


# ── 测试配置 ──

# 内存数据库：每次运行都是全新状态，测试之间完全隔离
# StaticPool 确保所有连接共享同一个内存数据库实例（否则每次连接都是空库）
from sqlalchemy.pool import StaticPool
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# dependency_overrides：把 get_db 替换成测试版本
# 所有用 Depends(get_db) 的路由都会改用 override_get_db
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    # 每个测试前重建表（保证干净状态）
    Base.metadata.create_all(bind=test_engine)
    yield
    # 每个测试后删表
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── 测试用例 ──

def test_create_note(client):
    response = client.post("/notes", json={"text": "Hello pytest"})
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "Hello pytest"
    assert "id" in data


def test_list_notes_empty(client):
    response = client.get("/notes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_notes_after_creation(client):
    client.post("/notes", json={"text": "Note A"})
    client.post("/notes", json={"text": "Note B"})
    response = client.get("/notes")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_note_success(client):
    create_resp = client.post("/notes", json={"text": "Get me"})
    note_id = create_resp.json()["id"]
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["text"] == "Get me"


def test_get_note_not_found(client):
    response = client.get("/notes/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"


def test_delete_note(client):
    create_resp = client.post("/notes", json={"text": "Delete me"})
    note_id = create_resp.json()["id"]
    # 删除
    del_resp = client.delete(f"/notes/{note_id}")
    assert del_resp.status_code == 204
    # 再查应该 404
    get_resp = client.get(f"/notes/{note_id}")
    assert get_resp.status_code == 404


def test_validation_error(client):
    # 缺少必填字段 text → 422
    response = client.post("/notes", json={})
    assert response.status_code == 422


def test_create_note_empty_text_fails(client):
    # 空字符串通过 Pydantic 校验（str 允许空），但逻辑上可以加 min_length
    response = client.post("/notes", json={"text": ""})
    # 当前模型没有 min_length 限制，所以会 201（演示：可以加 Field(min_length=1)）
    assert response.status_code == 201


"""
执行流程图
==========

pytest 收集测试函数
    │
    ▼
setup_db fixture（autouse）: create_all 建表
    │
    ▼
client fixture: TestClient(app) 初始化
    │
    ▼
dependency_overrides 把 get_db → override_get_db（内存DB）
    │
    ▼
执行测试函数（client.post/get/delete...）
    │
    ▼
setup_db teardown: drop_all 删表
    │
    ▼
下一个测试：重新 create_all，状态干净


核心知识点 ★
============
★ TestClient 不需要启动服务器，直接在内存里模拟 HTTP 请求
★ 内存数据库（:memory:）是测试隔离的最佳实践，不产生文件
★ dependency_overrides 是 FastAPI 测试的杀手级特性，替换任何依赖
★ autouse=True 的 fixture 自动应用到所有测试，无需显式声明
★ 每个测试函数相互独立，不依赖执行顺序，是好测试的基本要求
"""
