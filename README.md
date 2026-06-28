# FastAPI 学习项目

从零开始、循序渐进学 FastAPI 的代码 + 笔记。**面向 Java / SpringBoot 程序员**，全程用 SpringBoot 类比降低门槛。

> 姊妹项目：`../Langchain`、`../../LangGraph`（同一学习者的 LangChain / LangGraph 课程）。

---

## 🚀 换电脑 / 新电脑快速启动

> `.venv/`（虚拟环境）**不在仓库里**，新电脑必须重新创建。其余代码、笔记 git 一拉就全有。
> 本项目是纯本地 Web 框架，**不需要任何 API Key**。

```bash
# 1. 建虚拟环境（Python 3.11+）
python -m venv .venv

# 2. 激活
#   Windows PowerShell:
.venv\Scripts\Activate.ps1
#   macOS / Linux:
#   source .venv/bin/activate

# 3. 装依赖
pip install -r requirements.txt

# 4. 跑任意一课（文件名以数字开头，先 cd 进目录再启服务）
cd course_v2/01_基础
uvicorn 01_hello_fastapi:app --reload

# 5. 浏览器打开自动文档
#   http://127.0.0.1:8000/docs
```

> ⚠️ **Windows 控制台**默认 GBK，输出带 emoji 时可能报 `UnicodeEncodeError`。
> 跑前设一次：`$env:PYTHONIOENCODING='utf-8'; chcp 65001`（PyCharm 里默认 UTF-8，无此问题）。

---

## 📁 目录结构

| 目录 / 文件 | 说明 |
|------------|------|
| **`course_v2/`** | **← 当前学习版本，从这里开始** |
| `course_v2/README.md` | 课程指南：10 个概念域 + 学习顺序 + 设计哲学 + SpringBoot 类比表 |
| `course_v2/fastapi_notes.html` | 网页版图文笔记（暗色护眼，浏览器直接打开） |
| `course_v2/01_基础 … 10_工程化/` | 按概念域分组的 32 课 |
| `archive_v1/` | 旧版线性 14 课 + 旧 HTML 的完整留底（参考用，已废弃不动） |
| `CLAUDE.md` | 给 AI 协作者的项目说明（教学法、同步规则） |
| `LEARNING_SPEC.md` | 通用学习项目交付规范（HTML 排版要求等） |
| `requirements.txt` | Python 依赖（按域标注用途） |
| `.venv/` | 虚拟环境（需自建，不入库） |

---

## 📖 怎么学

课程组织方式：**按概念域分组（分类轴）+ 域内「简单点合并、难点细拆」**。
域与域之间已按前置依赖排好顺序，从上往下学即可：

```
前半「请求-响应原语轴」：01 基础 → 02 请求参数 → 03 请求体与Pydantic → 04 响应 → 05 错误处理
后半「能力轴」：06 依赖注入 → 07 中间件与后台 → 08 安全认证 → 09 数据库SQLAlchemy → 10 工程化
```

- **想看代码逐课跑**：进 `course_v2/`，按文件夹序号 + 文件内序号顺序看，每个 `.py` 顶部
  docstring 写了「本课知识点」「与上一课的区别」和「对应的 SpringBoot 类比」。
- **想看图文讲解**：浏览器打开 `course_v2/fastapi_notes.html`，侧边栏按域折叠导航 + 滚动高亮。
- **完整说明**：见 `course_v2/README.md`。

### 教学法（为什么和姊妹项目不同）

学习者有 SpringBoot 底子，FastAPI 与之高度同构（Pydantic≈DTO、Depends≈@Autowired、
SQLAlchemy≈JPA、APIRouter≈拆Controller、middleware≈Filter）。所以：

- **简单点合并**（一看类比就懂）：路径+查询参数、请求体+Field+嵌套、错误处理、中间件+CORS。
- **难点细拆**（和 Java 不一样、无现成类比）：`async/await`、`yield` 依赖、JWT 认证全链路（08 整域 5 课）、SQLAlchemy 的 N+1。

---

## ⚠️ 已知事项

- 标〔进阶〕的文件第一遍可跳过，不影响主线。
- 跑某些课需要额外的库（均在 `requirements.txt`）：表单/文件上传与 OAuth2 登录需 `python-multipart`；
  JWT 需 `python-jose`、密码哈希需 `passlib[bcrypt]`；测试课需 `pytest` + `httpx`。
- 课程会在各目录生成 `*.db`（SQLite）文件，已被 `.gitignore` 忽略，可随时删除重建。
- `10_工程化/06_final_project.py` 是综合实战：登录用 `alice` / `pwd123` 拿 token 后在 `/docs` 点 Authorize 测试。
