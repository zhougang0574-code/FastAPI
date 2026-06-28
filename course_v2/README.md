# FastAPI 课程 v2 —— 分类轴 + 难点细拆（SpringBoot 类比驱动）

本版把课程从「纯线性 14 课」重排为「**按概念域分组**（分类轴），域内 **简单点合并、难点细拆**」。

- 旧版（原始线性 14 课 + 旧 HTML 笔记）完整留底在 `../archive_v1/`，**已废弃，不再改动**。
- 本目录是当前学习版本，**目录结构即学习路径**，从上往下学。

---

## 一、设计哲学（为什么这样分，和姊妹项目不一样）

学习者是 **Java / SpringBoot 程序员**，同时在学 Python。FastAPI 的心智模型与 SpringBoot 高度同构：

| FastAPI | SpringBoot 对应 |
|---|---|
| `@app.get` / 路径操作函数 | `@GetMapping` / Controller 方法 |
| Pydantic `BaseModel` | DTO + Bean Validation（`@Valid`/`@NotNull`） |
| `Depends()` 依赖注入 | `@Autowired` / 构造器注入 |
| `APIRouter` | 拆分多个 `@RestController` |
| middleware | `Filter` / `HandlerInterceptor` |
| SQLAlchemy ORM | JPA / Hibernate |
| `HTTPException` | `@ResponseStatus` / `@ExceptionHandler` |

**所以本课程的教学法刻意区别于 Langchain / LangGraph 那套「一文件一个新概念」**：

> **有 Java 类比、一看就懂的简单点 → 合并成一课多讲几个；
> 和 Java 不一样、没有现成类比的难点 → 单独拆课、每课知识点少一点。**

需要**细拆**的「真·难点」（Python/异步特有，Java 无对应）：
`async/await`、`yield` 依赖的资源生命周期、SQLAlchemy 的关系与 N+1、JWT 认证全链路。

可以**合并**的「易点」（Java 老手秒懂）：
路径/查询参数、请求体+校验、response_model+状态码、HTTPException、middleware+CORS。

设计轴：**前半「请求-响应原语轴」**（一次 HTTP 来回怎么处理）→ **后半「能力轴」**（依赖/认证/数据库/工程化）。
标〔进阶〕的第一遍可跳过，不影响主线。

---

## 二、目录结构（即学习顺序）

```
01_基础/
  01_hello_fastapi.py      FastAPI() / 路由装饰器 / 自动 JSON / uvicorn 启动 / docs   〔合并·易〕
  02_async_vs_sync.py      async def vs def，为什么异步是 FastAPI 的核心             ★难点·细拆

02_请求参数/
  01_path_and_query.py     路径参数 + 查询参数 + 类型提示自动校验                     〔合并·易〕
  02_params_advanced.py    Enum 取值 / 路由顺序陷阱 / Query() 约束 / 多参数共存       〔进阶·合并〕

03_请求体与Pydantic/
  01_request_body.py       BaseModel + Field 约束 + 嵌套模型（≈ DTO + Bean Validation） 〔合并·易〕
  02_form_and_file.py      Form 表单 + File / UploadFile 文件上传
  03_validators.py         field_validator / model_validator 自定义校验               〔进阶〕

04_响应/
  01_response_model.py     response_model 过滤字段 + status_code + exclude_unset       〔合并·易〕
  02_custom_and_stream.py  JSONResponse / 自定义 headers / Union / StreamingResponse   〔进阶·合并〕

05_错误处理/
  01_error_handling.py     HTTPException + @exception_handler + 覆盖 422 校验错误      〔合并·易〕

06_依赖注入/
  01_depends_basic.py      Depends 函数依赖 + 类依赖 + 嵌套依赖（≈ @Autowired）       〔合并·易〕
  02_yield_depends.py      yield 依赖：打开→使用→关闭，资源生命周期                  ★难点·细拆
  03_global_depends.py     路由组依赖 / 全局依赖                                       〔进阶〕

07_中间件与后台/
  01_middleware_cors.py    @app.middleware + 洋葱模型 + CORSMiddleware（≈ Filter）      〔合并·易〕
  02_background_tasks.py   BackgroundTasks 响应后异步执行

08_安全认证/                                                       ★整域细拆（无 Java 类比）
  01_oauth2_password.py    OAuth2PasswordBearer + /token 登录端点
  02_password_hash.py      bcrypt 哈希存储 + verify_password
  03_jwt_token.py          JWT 签发 / 解码 / 过期
  04_current_user_dep.py   get_current_user 依赖保护路由
  05_scopes.py             权限作用域 Scopes                                           〔进阶〕

09_数据库SQLAlchemy/                                               ★关系/N+1 细拆（ORM 细节与 JPA 有别）
  01_db_setup.py           engine / SessionLocal / get_db / Model vs Schema 分离
  02_crud.py               完整 CRUD + get_or_404 + 软删除 + 分页过滤                  〔合并〕
  03_one_to_many.py        一对多：ForeignKey + relationship + back_populates
  04_many_to_many.py       多对多：中间关联表
  05_n_plus_1.py           N+1 问题与 joinedload 急加载                               ★难点·细拆
  06_alembic_migration.py  Alembic 数据库迁移（≈ Flyway）                             〔进阶〕

10_工程化/
  01_apirouter.py          APIRouter 把大项目拆成多文件（≈ 多 Controller）           ★重要
  02_settings.py           pydantic-settings 读环境变量管理配置（≈ @ConfigurationProperties）
  03_lifespan.py           lifespan 启动/关闭钩子（≈ @PostConstruct/@PreDestroy）
  04_testing.py            TestClient / pytest 测试 API（≈ MockMvc）
  05_websocket.py          WebSocket 双向通信                                          〔进阶〕
  06_final_project.py      综合：Todo API（认证 + 关系 + APIRouter 拆分 + 测试）
```

### 域间排序的依据（前置依赖）
- **01-05 是请求-响应原语**：先把「一次 HTTP 来回」拆开（入门→参数→请求体→响应→错误），后面每个能力都复用它们。
- **06 依赖注入**是 FastAPI 的粘合层（认证、数据库会话都靠它注入），所以排在能力域之前。
- **07 中间件/后台**是横切关注点；
- **08 认证**依赖 06 的 `Depends`；**09 数据库**依赖 06 的 `yield` 会话；
- **10 工程化**（拆分/配置/生命周期/测试）综合前面所有积木，放最后，并以综合项目收尾。

---

## 三、相对 archive_v1（旧 14 课）的优化

| 优化 | 说明 |
|---|---|
| 补 async/await | 旧版 14 课全是 `def`，没讲 FastAPI 的立身之本——异步；新增 `01/02` 专课，I/O 课改用 `async def` |
| 难点细拆 | 旧第 9 课把 OAuth2+JWT+bcrypt+依赖塞一课 → 拆成 08 域 4 课；yield 依赖、N+1 各自单独成课 |
| 易点合并 | 路径+查询参数合一课、请求体+Field+嵌套合一课、错误处理合一课（Java 老手不需要拆） |
| 补工程化 | 新增 APIRouter 拆项目、pydantic-settings 配置、lifespan、Alembic 迁移、WebSocket |
| 补能力 | 文件上传、后台任务、流式响应 |
| 固定模板 | 每个 `.py`：docstring（标题/与上一课区别/本课知识点/SpringBoot 类比）+ 分段代码 + 末尾流程图 + ★核心规律 |

---

## 四、运行方式

```bash
# 在仓库根目录用项目 .venv 启动任意一课（模块名即文件名去掉 .py）
uvicorn "course_v2.01_基础.01_hello_fastapi:app" --reload
# 文件名以数字开头不是合法模块名时，cd 进目录再起：
#   cd course_v2/01_基础 && uvicorn 01_hello_fastapi:app --reload
```

启动后访问交互文档：`http://127.0.0.1:8000/docs`（Swagger UI）。

> ⚠️ **Windows 用户**：控制台默认 GBK，输出带 emoji 时可能 `UnicodeEncodeError`。运行前设一次：
> ```powershell
> $env:PYTHONIOENCODING='utf-8'; chcp 65001
> ```
