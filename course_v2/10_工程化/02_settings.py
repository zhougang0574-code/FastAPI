"""
【工程化 / 02】配置管理：pydantic-settings 读环境变量

与上一课的区别：
    前面 SECRET_KEY、数据库 URL 都硬编码在代码里（〔08/03〕就埋了雷）。本课把配置
    集中到一个 Settings 类，从环境变量/.env 读取——就是 Spring 的 @ConfigurationProperties。

本课知识点：
    1. BaseSettings：字段自动从环境变量读取               —— ≈ @ConfigurationProperties
    2. 类型注解即类型转换（int/bool 自动转）+ 校验
    3. .env 文件 + env_file 配置本地开发默认值
    4. 用依赖注入提供 Settings（可缓存）

为什么需要：
    密钥、连接串绝不能硬编码进代码或提交 git。配置应按环境（开发/生产）注入。
    pydantic-settings 让配置「有类型、有校验、来源统一」，比散落的 os.getenv 强得多。
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict


# BaseSettings 子类：每个字段自动从同名环境变量读取（大小写不敏感）
# ≈ @ConfigurationProperties，字段类型即转换规则
class Settings(BaseSettings):
    app_name: str = "FastAPI 学习项目"        # 环境变量 APP_NAME
    secret_key: str = "dev-secret-change-me"   # 环境变量 SECRET_KEY（生产必须由环境提供）
    database_url: str = "sqlite:///./app.db"   # 环境变量 DATABASE_URL
    debug: bool = False                        # DEBUG=1/true → True（自动类型转换）

    # 本地开发时从 .env 读；生产用真正的环境变量覆盖
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# lru_cache：Settings 只构建一次（读环境/文件有成本），后续复用同一实例
@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

app = FastAPI(title="配置管理")


@app.get("/config")
def show_config(settings: SettingsDep):
    # 注意：绝不要把 secret_key 这类敏感配置真的返回出去，这里仅演示读取
    return {"app_name": settings.app_name, "debug": settings.debug,
            "db": settings.database_url}


"""
执行流程图
==========

配置来源优先级（高 → 低）：
    真实环境变量  >  .env 文件  >  代码里的默认值
        │
        ▼
Settings() 实例化时自动读取 + 按字段类型转换/校验
        │
        ▼
get_settings()（lru_cache 只建一次）──Depends──▶ 注入路由

硬编码 vs Settings：
    硬编码 SECRET_KEY="..."  → 泄露风险、改配置要改代码、不能分环境  ✗
    Settings 从环境读        → 不进 git、按环境注入、有类型校验      ✓

核心知识点 ★
============
★ BaseSettings 字段自动从环境变量读取（≈ @ConfigurationProperties），类型注解即转换
★ 优先级：真实环境变量 > .env > 默认值；.env 只放本地开发，必须 .gitignore
★ 敏感配置（SECRET_KEY、DB 密码）一律走环境，绝不硬编码、不提交 git
★ 用 @lru_cache 包 get_settings，避免每次请求都重读环境/文件
★ 回去把 〔08/03〕硬编码的 SECRET_KEY 改成从 Settings 读，就是生产做法
"""
