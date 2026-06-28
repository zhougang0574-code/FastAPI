"""
【数据库SQLAlchemy / 06】Alembic 数据库迁移（进阶·说明课）

与上一课的区别：
    前面都用 Base.metadata.create_all() 建表——它只能「建新表」，无法处理「表已存在、
    要加一列」的演进。本课介绍 Alembic：版本化管理表结构变更（≈ Flyway / Liquibase）。

本课知识点（本课是流程说明，命令在终端跑，不是 uvicorn 启动）：
    1. create_all 的局限：不会改已存在的表结构
    2. Alembic：用版本脚本记录每次结构变更，可升级/回滚      —— ≈ Flyway migration
    3. autogenerate 对比 Model 与数据库，自动生成迁移脚本

为什么需要：
    生产数据库不能删表重建。表结构演进必须版本化、可回滚、可在团队间同步——
    这正是 Java 世界的 Flyway/Liquibase 做的事，Python 这边是 Alembic。
"""

# 本课没有可启动的 app——Alembic 是命令行工具。下面是标准工作流（在项目根、装好 alembic 后执行）。

WORKFLOW = r"""
1) 初始化（生成 alembic/ 目录和 alembic.ini，一次性）：
   alembic init alembic

2) 配置（编辑两处）：
   - alembic.ini → sqlalchemy.url = sqlite:///./app.db
   - alembic/env.py → 把你的 Base.metadata 赋给 target_metadata：
         from your_models import Base
         target_metadata = Base.metadata     # autogenerate 据此对比

3) 自动生成迁移脚本（对比 Model 与当前数据库的差异）：
   alembic revision --autogenerate -m "add price column"
   → 在 alembic/versions/ 下生成一个带 upgrade()/downgrade() 的脚本

4) 应用迁移（升级到最新）：
   alembic upgrade head

5) 回滚一步 / 看历史：
   alembic downgrade -1
   alembic history
"""

print(WORKFLOW)


"""
执行流程图
==========

改了 ORM Model（比如给 Item 加一列 price）
        │
        ▼
alembic revision --autogenerate -m "..."
        │   （对比 Model vs 数据库，生成 versions/xxxx.py）
        ▼
检查生成的 upgrade()/downgrade() 脚本（autogenerate 不是 100% 准，要人审）
        │
        ▼
alembic upgrade head    → 把变更应用到数据库
        │
        ▼（出问题）
alembic downgrade -1    → 回滚

create_all  vs  Alembic：
    create_all：只建不存在的表，改结构无能为力（仅适合学习/原型）
    Alembic   ：版本化、可升级/回滚、团队同步（生产标配）≈ Flyway

核心知识点 ★
============
★ create_all 不会修改已存在的表结构，生产环境靠 Alembic 做版本化迁移（≈ Flyway/Liquibase）
★ env.py 里 target_metadata = Base.metadata 是 autogenerate 的关键
★ 标准节奏：改 Model → revision --autogenerate → 人审脚本 → upgrade head
★ autogenerate 生成的脚本要人工复核（重命名列、数据迁移它识别不准）
★ 迁移脚本应随代码一起提交 git，保证团队/各环境结构一致
"""
