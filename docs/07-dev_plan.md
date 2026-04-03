# 开发计划：ScholarTrack

## 总览

- **开发周期**：2026-04-04 ~ 2026-04-21（18 天）
- **答辩准备**：2026-04-22 ~ 2026-04-28
- **答辩时间**：2026-04-28 ~ 2026-05-07
- **开发方式**：Claude Code Agent Team（Architect + Developer + Reviewer）

---

## Phase 1：项目脚手架（Apr 4 - Apr 5，2 天）

### 目标
搭建项目骨架，确保基础环境可运行。

### 任务

| ID | 任务 | 说明 |
|----|------|------|
| 1.1 | 初始化项目结构 | Flask app 工厂模式、目录结构、配置文件 |
| 1.2 | 数据库配置 | SQLite + SQLAlchemy 初始化、migration 设置 |
| 1.3 | 创建所有数据模型 | 按 05-data_models.md 实现 8 个模型 |
| 1.4 | ChromaDB 初始化 | 创建 paper_abstracts 和 user_notes 两个 collection |
| 1.5 | 依赖管理 | requirements.txt / pyproject.toml |
| 1.6 | 基础测试框架 | pytest 配置、测试数据库 fixture |

### 项目目录结构

```
cw1/
├── docs/                     # 文档（已有）
├── app/
│   ├── __init__.py           # Flask app 工厂
│   ├── config.py             # 配置（开发/测试/生产）
│   ├── models/               # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── paper.py
│   │   ├── note.py
│   │   └── flashcard.py
│   ├── routes/               # API 路由（Blueprint）
│   │   ├── __init__.py
│   │   ├── auth.py           # F1
│   │   ├── papers.py         # F2 + F3
│   │   ├── notes.py          # F4
│   │   ├── flashcards.py     # F5
│   │   └── search.py         # F6
│   ├── services/             # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── arxiv_service.py  # arXiv API 调用
│   │   ├── chromadb_service.py  # ChromaDB 操作
│   │   └── sm2_service.py    # SM-2 算法
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── errors.py         # 统一错误处理
│       ├── pagination.py     # 分页辅助
│       └── validators.py     # 输入验证
├── tests/
│   ├── conftest.py           # pytest fixtures
│   ├── test_auth.py
│   ├── test_papers.py
│   ├── test_notes.py
│   ├── test_flashcards.py
│   └── test_search.py
├── mcp_server.py             # MCP Server 入口
├── run.py                    # Flask 启动入口
├── requirements.txt
└── README.md
```

### 交付标准
- `flask run` 可启动，返回健康检查端点
- 所有模型建表成功
- pytest 可运行（即使还没有测试用例）

---

## Phase 2：核心 CRUD（Apr 6 - Apr 10，5 天）

### 目标
实现 F1-F4，完成所有必须功能模块。这是满足作业最低要求的关键阶段。

### 任务

| ID | 任务 | 天数 | 依赖 |
|----|------|------|------|
| 2.1 | F1 用户认证（register, login, JWT, /users/me） | 1 天 | Phase 1 |
| 2.2 | F2 论文发现（arXiv API 集成、搜索、缓存） | 1.5 天 | 2.1 |
| 2.3 | F3 论文管理（收藏、取消收藏、标签、个人库） | 1 天 | 2.2 |
| 2.4 | F4 笔记系统（完整 CRUD + ChromaDB 同步） | 1 天 | 2.2 |
| 2.5 | 全局功能：错误处理、分页、HATEOAS、输入验证 | 0.5 天 | 与 2.1-2.4 并行 |

### 详细说明

**2.1 用户认证**
- 实现 flask-jwt-extended 集成
- 4 个端点：register、login、get me、update me
- 密码用 werkzeug.security 哈希
- 编写测试：注册成功/重复、登录成功/失败、token 验证

**2.2 论文发现**
- 封装 arxiv_service.py：调用 arXiv API、解析 Atom XML 响应
- 实现搜索、热门、详情 3 个端点
- 缓存逻辑：查询结果自动存入 Paper 表（arxiv_id 去重）
- 论文摘要写入 ChromaDB paper_abstracts collection
- 编写测试：搜索参数验证、缓存命中、arXiv API mock

**2.3 论文管理**
- 收藏/取消收藏、标签 CRUD
- 个人库列表（支持标签过滤、分页）
- 编写测试：收藏/重复收藏、标签操作、权限验证

**2.4 笔记系统**
- 完整 CRUD：创建、列表、详情、更新、删除
- ChromaDB 同步：创建时写入、更新时覆盖、删除时移除
- 权限校验：只能操作自己的笔记
- 编写测试：CRUD 全流程、权限 403、ChromaDB 同步

### 交付标准
- 20 个端点全部可用（F1: 4 + F2: 3 + F3: 6 + F4: 6 + 健康检查: 1）
- 每个模块有对应的测试文件
- 所有测试通过

---

## Phase 3：高级特性（Apr 11 - Apr 15，5 天）

### 目标
实现 F5-F7，达到 70+ 分数段要求。

### 任务

| ID | 任务 | 天数 | 依赖 |
|----|------|------|------|
| 3.1 | F5 闪卡与间隔重复 | 2 天 | Phase 2 |
| 3.2 | F6 RAG 语义搜索 | 1.5 天 | Phase 2（ChromaDB 已有数据） |
| 3.3 | F7 MCP Server | 1.5 天 | 3.1 + 3.2 |

### 详细说明

**3.1 闪卡与间隔重复**
- SM-2 算法实现（sm2_service.py）
- 闪卡 CRUD：创建、列表、编辑、删除
- 复习流程：获取待复习卡片、提交评分、更新参数
- 复习统计端点
- 编写测试：SM-2 计算、复习流程、统计聚合

**3.2 RAG 语义搜索**
- 3 个搜索端点：论文搜索、笔记搜索、联合搜索
- ChromaDB 查询封装（chromadb_service.py）
- 笔记搜索按 user_id 过滤
- 联合搜索结果合并与排序
- 编写测试：搜索结果验证、用户隔离

**3.3 MCP Server**
- 使用 mcp Python SDK
- 实现 9 个 tools（见 04-feature_spec.md F7.1）
- 工具内部直接调用 service 层（不走 HTTP）
- 本地测试：通过 Claude Desktop / Claude Code 配置并验证
- 编写 MCP server 启动说明

### 交付标准
- 30 个端点全部可用
- MCP Server 可通过 Claude 调用
- 所有测试通过

---

## Phase 4：文档与质量（Apr 16 - Apr 19，4 天）

### 目标
完成所有交付文档，代码质量达标。

### 任务

| ID | 任务 | 天数 | 说明 |
|----|------|------|------|
| 4.1 | API 文档（PDF） | 1 天 | Swagger/OpenAPI → 导出 PDF，含所有端点、示例、错误码 |
| 4.2 | 技术报告 | 1.5 天 | 最多 5 页：设计选择、技术栈论证、挑战、反思、GenAI 声明 |
| 4.3 | README.md | 0.5 天 | 项目概述、安装步骤、运行方式、API 文档引用、MCP 配置说明 |
| 4.4 | Reviewer 审查 | 0.5 天 | 启动 Reviewer agent 全面审查代码、文档、评分标准对齐 |
| 4.5 | 问题修复 | 0.5 天 | 根据 Reviewer 反馈修复问题 |

### 文档要求对照

| 交付物 | 要求 | 对应任务 |
|--------|------|----------|
| 代码仓库 | 公开 GitHub，可运行，有提交历史 | 全程维护 |
| API 文档 | PDF，描述端点/参数/响应/示例/错误码 | 4.1 |
| 技术报告 | ≤5 页，含 GenAI 声明 | 4.2 |
| README.md | 设置说明、项目概述 | 4.3 |
| 演示幻灯片 | PowerPoint，用于口试 | Phase 5 |

### 交付标准
- API 文档 PDF 生成完毕
- 技术报告完成且 ≤ 5 页
- README.md 可引导他人成功运行项目
- Reviewer 审查无阻塞性问题

---

## Phase 5：提交与答辩准备（Apr 20 - Apr 28，9 天）

### 任务

| ID | 任务 | 时间 | 说明 |
|----|------|------|------|
| 5.1 | 最终测试 | Apr 20 | 全部端点手动验证 + 自动化测试通过 |
| 5.2 | 部署（可选） | Apr 20 | PythonAnywhere 部署（如有时间） |
| 5.3 | 提交 | Apr 21 | GitHub 最终 push + Minerva 提交 |
| 5.4 | 演示幻灯片 | Apr 22-24 | 5 分钟展示内容：项目概述、架构、演示、亮点 |
| 5.5 | 演示排练 | Apr 25-27 | 练习 demo 流程（Swagger UI + MCP 工作流） |
| 5.6 | Q&A 准备 | Apr 25-27 | 准备常见问题：设计选择、挑战、GenAI 使用、技术细节 |

### 演示流程设计（5 分钟）

```
[0:00-0:30]  项目介绍：ScholarTrack 是什么、解决什么问题
[0:30-1:30]  架构概览：技术栈、数据流（幻灯片）
[1:30-3:00]  API 演示（Swagger UI）：注册→登录→搜索论文→收藏→写笔记
[3:00-4:30]  MCP 演示（Claude 对话）：语义搜索→笔记→闪卡复习
[4:30-5:00]  总结亮点：RAG、SM-2、arXiv 集成、GenAI 使用
```

### Q&A 准备要点

- 为什么选 Flask 而不是 Django/FastAPI？
- 为什么选 SQLite 而不是 PostgreSQL？
- JWT 的优缺点？为什么不用 session？
- SM-2 算法怎么工作的？参数怎么调？
- ChromaDB 的 embedding 模型选择理由？
- arXiv API 的限制和你的应对策略？
- GenAI 在开发中具体怎么使用的？哪些是 AI 生成的？
- 项目的局限性和改进方向？

---

## 里程碑检查点

| 日期 | 里程碑 | 验证方式 |
|------|--------|----------|
| Apr 5 | 项目骨架可运行 | `flask run` 启动，模型建表成功 |
| Apr 10 | 核心 CRUD 完成 | 20 个端点可用，测试通过 |
| Apr 15 | 高级特性完成 | 30 个端点 + MCP 可用，测试通过 |
| Apr 19 | 文档完成 | API 文档 PDF + 技术报告 + README |
| Apr 21 | 提交 | GitHub + Minerva |
| Apr 28 | 答辩就绪 | 幻灯片 + 演示排练完成 |

---

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| arXiv API 不稳定/被限流 | F2 无法正常工作 | 实现重试机制 + 本地缓存优先；测试中 mock arXiv 响应 |
| ChromaDB 在 PythonAnywhere 不可用 | F6 部署失败 | 优先保证本地运行；部署为可选项 |
| SM-2 算法实现有误 | F5 复习间隔异常 | 编写详细单元测试覆盖各种评分场景 |
| MCP SDK 学习成本 | F7 延期 | 提前 Apr 11 开始研究 SDK 文档 |
| 时间不足 | 高级特性未完成 | Phase 2（核心 CRUD）优先保证；Phase 3 按 F5→F6→F7 优先级裁剪 |

---

## Git 提交策略

- 每个功能模块完成后至少一次有意义的 commit
- commit message 格式：`feat(module): description` / `fix(module): description` / `docs: description` / `test: description`
- 不提交 secrets、.env、数据库文件、ChromaDB 持久化目录
- .gitignore 包含：`*.db`、`.env`、`__pycache__/`、`chroma_data/`、`*.pyc`
