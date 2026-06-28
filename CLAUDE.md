# CLAUDE.md

给后续 Claude Code 会话的项目说明，打开即读。**先读完这份再动手。**

## 这是什么

FastAPI 的**中文教学项目**：一套循序渐进的代码课 + 一份网页图文笔记。
学习者是 **Java / SpringBoot 程序员**，同时在学 Python——讲解多用 SpringBoot 类比，代码注释 / 文档 / 讲解一律用中文。

> 姊妹项目：`../Langchain`、`../../LangGraph`（同一学习者的 LangChain / LangGraph 课程）。
> 那两套是「全新心智模型」，本项目可借用 Java Web 经验，**教学法刻意不同**（见下）。

## 权威版本（最重要）

- **`course_v2/` 是唯一在维护的学习版本，一切以它为准。**
- `archive_v1/`（旧版线性 14 课 + 旧 HTML 笔记）**已废弃**，只作回溯参考，**不要再改动它**。
- 课程的权威目录树和学习顺序见 **`course_v2/README.md`**（改了结构要同步更新它）。

## 课程结构

10 个「概念域」，**目录结构即学习路径**，从上往下学：

```
01 基础 → 02 请求参数 → 03 请求体与Pydantic → 04 响应 → 05 错误处理
→ 06 依赖注入 → 07 中间件与后台 → 08 安全认证 → 09 数据库SQLAlchemy → 10 工程化
```

前半「请求-响应原语轴」（01-05，一次 HTTP 来回怎么处理）→ 后半「能力轴」（06-10，依赖/认证/数据库/工程化）。

## 教学法（硬性原则）—— 与姊妹项目不同，注意

姊妹项目（Langchain/LangGraph）是「一文件一个新概念」，因为那是全新心智模型。
**本项目学习者有 SpringBoot 底子，规则改为：**

1. **简单点合并、难点细拆**：有 Java 类比、一看就懂的简单点 → 合并成一课多讲几个；和 Java 不一样、没有现成类比的难点 → 单独拆课、每课知识点少一点。
2. **必拆的真·难点**（Python/异步特有，Java 无对应）：`async/await`〔01/02〕、`yield` 依赖资源生命周期〔06/02〕、SQLAlchemy 关系与 N+1〔09/05〕、JWT 认证全链路（08 整域）。
3. **可合并的易点**（Java 老手秒懂）：路径+查询参数、请求体+Field+嵌套、response_model+状态码、HTTPException、middleware+CORS。
4. **多用 SpringBoot 类比**：DI≈@Autowired、Pydantic≈DTO+Bean Validation、SQLAlchemy≈JPA、APIRouter≈拆Controller、middleware≈Filter、settings≈@ConfigurationProperties。
5. **概念累积、不回退**：后面的课在前面的基础上加一层；标〔进阶〕的放各域末尾，第一遍可跳过。

## 文件内约定

每个 `.py` 顶部 docstring 固定结构：
1. 标题行 `【域名 / 序号】`
2. 与上一课的区别
3. 本课知识点（可多个）+ **对应的 SpringBoot 类比**
4. 为什么需要

文件末尾用多行字符串写「执行流程图 + ★核心规律」。跨课引用统一写 **`〔域文件夹名/序号〕`**，例如 `〔06_依赖注入/02〕`。

> ⚠️ 改了课程编号 / 顺序，必须同步更新所有 `【…】` 标题和 `〔…〕` 引用（`.py` 与 HTML 都有）。

## 三处必须同步

新增 / 调整一课时，以下三处都要改，保持一致：

1. **`.py`** —— docstring（标题/区别/知识点+类比/为什么）+ 代码 + 末尾流程图。
2. **`course_v2/fastapi_notes.html`** —— 侧边栏 nav 条目 + 正文 `<section>`，nav 顺序与正文严格一致。
3. **`course_v2/README.md`** —— 目录树（改结构必同步）。

## HTML 笔记说明（`course_v2/fastapi_notes.html`，待建）

沿用姊妹 LangGraph 的「手写追加式」：单文件、零依赖、浏览器直接打开、暗色护眼主题；
左侧 `<nav>` 手风琴折叠 + IntersectionObserver 滚动高亮，右侧 `<main>` 每课一个 `<section>`。
排版硬性要求见根目录 `LEARNING_SPEC.md` 第二节（字体 17px、侧栏 `height:100vh; overflow-y:auto` 等）。
> 旧笔记 `archive_v1/fastapi_notes.html` 是 14 课版，仅供抄排版，内容不要照搬。

## 运行与环境

- 用项目 `.venv` 运行。文件名以数字开头不是合法模块名，起服务时 `cd` 进课程目录：
  ```bash
  cd "course_v2/01_基础" && uvicorn 01_hello_fastapi:app --reload
  ```
- 启动后访问 `http://127.0.0.1:8000/docs`（Swagger UI）。
- 依赖：`fastapi`、`uvicorn[standard]`、`pydantic`、`pydantic-settings`、`sqlalchemy`、`python-jose[cryptography]`、`passlib[bcrypt]`、`python-multipart`（表单/上传）、`alembic`、`pytest`、`httpx`（TestClient）。
- **Windows 编码坑**：控制台默认 GBK，输出带 emoji 会 `UnicodeEncodeError`。运行前 `$env:PYTHONIOENCODING='utf-8'; chcp 65001`；PyCharm（UTF-8）里跑没问题。

## 新增 / 调整一课的步骤

1. 在对应域文件夹放 `NN_xxx.py`（序号紧接该域已有文件；插在中间则后续文件和所有 `〔…〕` 引用都要重编号）。
2. 写 docstring + 代码 + 末尾流程图，遵循「简单合并 / 难点细拆」原则。
3. 在 `fastapi_notes.html` 的 nav 和 `<main>` 对应位置插入 section。
4. 更新 `course_v2/README.md` 目录树。
5. 校验：`python -m py_compile` 全过；能跑的实跑一遍；HTML 标签开闭与 nav 顺序校验。
