"""
【请求体与Pydantic / 03】自定义校验：field_validator / model_validator（进阶）

与上一课的区别：
    Field() 只能做「单字段、规则化」的约束（长度、范围、正则）。本课处理
    Field() 表达不了的校验：自定义逻辑、跨字段校验。

本课知识点：
    1. field_validator：对单个字段做自定义校验/转换   —— ≈ 自定义 ConstraintValidator
    2. model_validator(mode="after")：跨字段校验        —— ≈ 类级 @Constraint（如两次密码一致）
    3. 校验失败抛 ValueError → FastAPI 自动转 422

为什么需要：
    「密码必须含数字」「确认密码要和密码一致」「结束时间晚于开始时间」这类
    规则 Field() 写不出来，需要自定义校验器。这是 Pydantic v2 的现代写法。
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import FastAPI

app = FastAPI(title="自定义校验")


class Register(BaseModel):
    username: str = Field(min_length=3)
    password: str
    password2: str

    # field_validator：校验/转换单个字段，返回值会替换原值
    # ≈ 自定义 ConstraintValidator，作用在一个字段上
    @field_validator("username")
    @classmethod
    def username_lower(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("用户名只能是字母和数字")  # 抛 ValueError → 422
        return v.lower()   # 顺手把用户名转小写（校验器可改值）

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6 or not any(c.isdigit() for c in v):
            raise ValueError("密码至少 6 位且含数字")
        return v

    # model_validator(after)：所有字段都校验完后跑，能跨字段比较
    # ≈ 类级别的校验注解（如 @PasswordMatches）
    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password2:
            raise ValueError("两次密码不一致")
        return self


@app.post("/register")
def register(data: Register):
    return {"username": data.username}   # 已被转成小写


"""
执行流程图
==========

POST /register  {username, password, password2}
        │
        ▼
Pydantic 校验顺序：
    1) Field 基础约束（min_length 等）
    2) field_validator 逐字段（可改值，如 username→小写）
    3) model_validator(after) 跨字段（password == password2 ?）
        │
        ├─ 任一步抛 ValueError → 422（含错误信息）
        └─ 全过 → 干净对象进函数体

核心知识点 ★
============
★ field_validator 管单字段自定义逻辑，可校验也可转换（返回值替换原值）
★ model_validator(mode="after") 管跨字段校验（两次密码一致、时间先后等）
★ 校验失败统一 raise ValueError，FastAPI 自动包成 422，不用自己 try/except
★ 能用 Field() 表达的（长度/范围/正则）就别写校验器，保持简洁
★ 这是 Pydantic v2 写法（v1 是 @validator/@root_validator，已过时）
"""
