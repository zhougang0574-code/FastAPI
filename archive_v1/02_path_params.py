"""
第 2 课：路径参数 Path Parameters

学习要点：
1. {param} 在路径中声明参数，函数签名里同名接收
2. 类型提示（int/str/float）自动做类型转换和校验
3. Enum 限制路径参数的合法取值（传非法值自动 422）
4. path 类型：参数本身可以包含斜杠
5. 路由顺序陷阱：固定路径必须写在变量路径之前
"""

from enum import Enum
from fastapi import FastAPI

app = FastAPI()


class ModelName(str, Enum):
    # str 让枚举值同时是字符串，方便 JSON 序列化
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


# 固定路径 /users/me 必须注册在 /users/{user_id} 之前
# 否则 "me" 会先被 {user_id} 捕获，当成 int 导致 422
@app.get("/users/me")
def get_current_user():
    return {"user": "current_user"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}


# Enum 路径参数：只接受 alexnet / resnet / lenet
# 传其他值会返回 422 Unprocessable Entity
@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model": model_name.value, "message": "Deep Learning FTW!"}
    if model_name.value == "lenet":
        return {"model": model_name.value, "message": "LeCNN all the images"}
    return {"model": model_name.value, "message": "Have some residuals"}


# :path 类型声明：参数可以包含 /（正斜杠）
# 访问 /files/home/user/report.pdf → file_path = "home/user/report.pdf"
@app.get("/files/{file_path:path}")
def read_file(file_path: str):
    return {"file_path": file_path}


"""
执行流程图
==========

请求：GET /users/me
    │
    ▼
路由匹配（按注册顺序逐一对比）
    │
    ├─ /users/me    ← 第一个匹配，命中固定路由 → 返回 current_user
    │
    └─ /users/{user_id}  ← 不会到这里了

请求：GET /models/vgg
    │
    ▼
路由匹配到 /models/{model_name}
    │
    ▼
类型校验：model_name 不在 Enum 合法值里
    │
    ▼
422 Unprocessable Entity（FastAPI 自动处理）


核心知识点 ★
============
★ 类型提示 int 不只是注释，FastAPI 靠它做运行时校验
★ Enum 路径参数：合法值即文档，非法值即错误，代码更安全
★ 路由注册顺序 = 匹配优先级，固定路由永远写前面
★ {param:path} 用于文件系统路径、URL 转发等场景
"""
