"""
【工程化 / 04】测试：TestClient + pytest

与上一课的区别：
    前面都靠 /docs 手点验证。本课用 TestClient 写自动化测试——就是 SpringBoot 的
    MockMvc + JUnit，不用真正启服务就能调接口、断言响应。

本课知识点：
    1. TestClient(app)：内存里直接调接口，无需启 uvicorn   —— ≈ MockMvc
    2. pytest 用 test_ 开头函数 + assert 断言                —— ≈ JUnit @Test + assertEquals
    3. dependency_overrides 替换依赖（如换测试库）           —— ≈ @MockBean
    4. 测响应状态码 + JSON 内容

为什么需要：
    手点不可复现、易遗漏。自动化测试是工程底线。FastAPI 的 TestClient 基于 httpx，
    用法直观，和你熟悉的 MockMvc 思路一致。

    运行：pytest 04_testing.py   （需要 pytest + httpx，requirements.txt 已含）
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

app = FastAPI(title="测试演示")


# 一个依赖：真实环境给真实数据；测试时可被 override 替换
def get_greeting() -> str:
    return "hello from prod"


@app.get("/greet")
def greet(g: Annotated[str, Depends(get_greeting)]):
    return {"greeting": g}


@app.get("/add")
def add(a: int, b: int):
    return {"result": a + b}


# ── 下面就是测试（pytest 自动发现 test_ 开头的函数）──

client = TestClient(app)   # ≈ MockMvc，内存里直接打接口，不启服务


def test_add():
    resp = client.get("/add", params={"a": 2, "b": 3})
    assert resp.status_code == 200              # 断言状态码
    assert resp.json() == {"result": 5}         # 断言响应体


def test_add_validation_error():
    resp = client.get("/add", params={"a": "x", "b": 3})
    assert resp.status_code == 422              # 类型不对应返回 422


def test_dependency_override():
    # 用 dependency_overrides 把 get_greeting 换成测试版（≈ @MockBean）
    app.dependency_overrides[get_greeting] = lambda: "hello from test"
    resp = client.get("/greet")
    assert resp.json() == {"greeting": "hello from test"}
    app.dependency_overrides.clear()           # 用完清掉，别污染别的测试


"""
执行流程图
==========

pytest 04_testing.py
    │
    ▼
自动发现 test_* 函数 → 逐个执行
    │
    ▼
TestClient(app).get/post(...)  ← 内存中直达 app，不经网络/不启 uvicorn
    │
    ▼
assert 状态码 + assert resp.json()  ← 不满足即 FAIL

替换依赖：
    app.dependency_overrides[真依赖] = 测试依赖   （≈ @MockBean）
    用完 .clear() 复原

核心知识点 ★
============
★ TestClient(app) ≈ MockMvc：内存直调接口，无需启服务，基于 httpx
★ pytest：test_ 开头函数 + assert 断言（≈ JUnit @Test）
★ 断言要同时覆盖状态码和响应体；记得测 422 等错误路径
★ dependency_overrides 替换依赖（换测试数据库/外部服务，≈ @MockBean），用完 clear
★ 测数据库接口时常 override get_db 指向独立测试库，避免污染真实数据
"""
