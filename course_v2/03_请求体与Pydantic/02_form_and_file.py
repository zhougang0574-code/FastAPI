"""
【请求体与Pydantic / 02】表单 Form + 文件上传 File / UploadFile

与上一课的区别：
    〔03_请求体与Pydantic/01〕的请求体是 JSON。本课处理另两种 body：
    表单（application/x-www-form-urlencoded）和文件上传（multipart/form-data）。

本课知识点：
    1. Form() 接收表单字段（不是 JSON）            —— ≈ 传统 @RequestParam 表单提交
    2. File() / bytes 接收小文件（一次读进内存）     —— ≈ @RequestParam MultipartFile（小文件）
    3. UploadFile 接收大文件（流式，有文件名/类型）  —— ≈ MultipartFile（推荐，省内存）
    4. 表单字段 + 文件可同时出现在一个 multipart 请求

为什么需要：
    HTML 表单登录、头像/附件上传走的不是 JSON。注意：用 Form/File 需要装
    python-multipart（requirements.txt 已含），否则启动报错。
"""

from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI(title="表单与文件上传")


# Form() 接收表单字段：OAuth2 登录就是这种（≈ 传统表单 POST）
# ≈ public X login(@RequestParam String username, @RequestParam String password)
@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username, "received_password_len": len(password)}


# bytes + File()：小文件一次性读进内存，拿到的是字节内容
@app.post("/upload-bytes")
def upload_bytes(file: bytes = File(...)):
    return {"size_bytes": len(file)}


# UploadFile：推荐方式，流式不占内存，带文件名/类型，可 await 异步读
# ≈ MultipartFile：getOriginalFilename() / getContentType()
@app.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()          # 异步读取内容
    return {
        "filename": file.filename,        # 原始文件名
        "content_type": file.content_type,
        "size": len(content),
    }


# 表单字段 + 文件混合（multipart 里两者共存）
@app.post("/profile")
async def update_profile(name: str = Form(...), avatar: UploadFile = File(...)):
    return {"name": name, "avatar": avatar.filename}


"""
执行流程图
==========

multipart/form-data 请求
    ├─ 文本字段 → Form(...)        （username / name ...）
    └─ 文件部分 → UploadFile/File  （avatar / file ...）
            │
            ▼
   UploadFile：流式，.filename/.content_type/await .read()
   bytes+File：直接读进内存（仅适合小文件）

★ 用 Form/File 必须装 python-multipart，否则启动即报错

核心知识点 ★
============
★ Form(...) 收表单字段（非 JSON）；一个请求里有 Form 就整体按表单解析，不能再混 JSON body
★ 小文件用 bytes=File(...)（进内存）；大文件用 UploadFile（流式省内存，推荐）
★ UploadFile ≈ MultipartFile：有 .filename / .content_type，await file.read() 读内容
★ 表单字段 + 文件可在同一 multipart 请求共存
★ OAuth2 密码登录就是表单提交，见 〔08_安全认证/01〕
"""
