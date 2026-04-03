# API 接口文档：ScholarTrack

## 基本信息

- **Base URL**: `http://localhost:5000/api`
- **数据格式**: JSON
- **认证方式**: JWT Bearer Token（`Authorization: Bearer <token>`）
- **分页参数**: `page`（默认 1）、`per_page`（默认 20，最大 100）

## 通用响应格式

### 成功响应

```json
{
  "data": { ... },
  "_links": {
    "self": "/api/..."
  }
}
```

### 列表响应（含分页）

```json
{
  "data": [ ... ],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  },
  "_links": {
    "self": "/api/...?page=1",
    "next": "/api/...?page=2",
    "prev": null
  }
}
```

### 错误响应

```json
{
  "error": "not_found",
  "message": "Paper with arxiv_id '2403.99999' not found"
}
```

### 状态码规范

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 查询、更新成功 |
| 201 | Created | 创建成功 |
| 204 | No Content | 删除成功 |
| 400 | Bad Request | 输入验证失败 |
| 401 | Unauthorized | 未认证或 token 过期 |
| 403 | Forbidden | 无权操作他人资源 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 重复操作（如重复收藏） |
| 500 | Internal Server Error | 服务端异常 |

---

## F1 用户认证

### POST /api/auth/register

注册新用户。

**请求：**
```json
{
  "username": "researcher1",
  "email": "researcher1@example.com",
  "password": "securepass123"
}
```

**成功响应（201）：**
```json
{
  "data": {
    "id": 1,
    "username": "researcher1",
    "email": "researcher1@example.com",
    "preferred_categories": [],
    "created_at": "2026-04-03T10:00:00Z"
  },
  "_links": {
    "self": "/api/users/me",
    "login": "/api/auth/login"
  }
}
```

**错误响应：**
- 400：缺少必填字段或格式不合法
- 409：用户名或邮箱已存在

---

### POST /api/auth/login

用户登录，获取 JWT token。

**请求：**
```json
{
  "username": "researcher1",
  "password": "securepass123"
}
```

**成功响应（200）：**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**错误响应：**
- 401：用户名或密码错误

---

### GET /api/users/me

获取当前用户信息。**需要认证。**

**成功响应（200）：**
```json
{
  "data": {
    "id": 1,
    "username": "researcher1",
    "email": "researcher1@example.com",
    "preferred_categories": ["cs.CV", "cs.CL"],
    "created_at": "2026-04-03T10:00:00Z"
  },
  "_links": {
    "self": "/api/users/me",
    "library": "/api/library",
    "notes": "/api/notes"
  }
}
```

---

### PUT /api/users/me

更新当前用户信息。**需要认证。**

**请求：**
```json
{
  "email": "new_email@example.com",
  "preferred_categories": ["cs.CV", "cs.CL", "cs.AI"]
}
```

**成功响应（200）：** 返回更新后的用户信息（格式同 GET）。

**错误响应：**
- 400：字段格式不合法
- 409：邮箱已被占用

---

## F2 论文发现

### GET /api/papers/search

搜索 arXiv 论文。从 arXiv API 实时查询，结果缓存到本地。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 是 | 搜索关键词 |
| category | string | 否 | arXiv 分类过滤，如 "cs.CV" |
| date_from | string | 否 | 起始日期（YYYY-MM-DD） |
| date_to | string | 否 | 结束日期（YYYY-MM-DD） |
| page | int | 否 | 页码，默认 1 |
| per_page | int | 否 | 每页数量，默认 20 |

**成功响应（200）：**
```json
{
  "data": [
    {
      "arxiv_id": "2403.12345",
      "title": "Efficient Vision Transformers with Multi-Scale Attention",
      "authors": ["Alice Smith", "Bob Johnson"],
      "abstract": "We propose a novel multi-scale attention mechanism...",
      "categories": "cs.CV cs.AI",
      "published_date": "2026-03-28",
      "arxiv_url": "https://arxiv.org/abs/2403.12345",
      "pdf_url": "https://arxiv.org/pdf/2403.12345",
      "_links": {
        "self": "/api/papers/2403.12345",
        "save": "/api/papers/2403.12345/save",
        "notes": "/api/papers/2403.12345/notes"
      }
    }
  ],
  "pagination": { "total": 45, "page": 1, "per_page": 20, "pages": 3 },
  "_links": {
    "self": "/api/papers/search?q=vision+transformer&page=1",
    "next": "/api/papers/search?q=vision+transformer&page=2"
  }
}
```

**错误响应：**
- 400：缺少 q 参数

---

### GET /api/papers/trending

获取指定领域的近期论文。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 是 | arXiv 分类，如 "cs.CV" |
| days | int | 否 | 时间范围，默认 7 天 |
| page | int | 否 | 页码 |
| per_page | int | 否 | 每页数量 |

**成功响应（200）：** 格式同 `/api/papers/search`。

**错误响应：**
- 400：缺少 category 参数

---

### GET /api/papers/{arxiv_id}

获取单篇论文详情。优先查本地缓存，未命中则从 arXiv API 获取。

**成功响应（200）：**
```json
{
  "data": {
    "arxiv_id": "2403.12345",
    "title": "Efficient Vision Transformers with Multi-Scale Attention",
    "authors": ["Alice Smith", "Bob Johnson"],
    "abstract": "We propose a novel multi-scale attention mechanism...",
    "categories": "cs.CV cs.AI",
    "published_date": "2026-03-28",
    "arxiv_url": "https://arxiv.org/abs/2403.12345",
    "pdf_url": "https://arxiv.org/pdf/2403.12345",
    "is_saved": true,
    "_links": {
      "self": "/api/papers/2403.12345",
      "save": "/api/papers/2403.12345/save",
      "notes": "/api/papers/2403.12345/notes"
    }
  }
}
```

**错误响应：**
- 404：arXiv 上不存在该论文

说明：`is_saved` 字段需要认证才会返回（未认证时不包含此字段）。

---

## F3 论文管理

### POST /api/papers/{arxiv_id}/save

收藏论文到个人库。**需要认证。**

**请求：**
```json
{
  "memo": "Interesting multi-scale attention approach, read later"
}
```

`memo` 为可选字段。

**成功响应（201）：**
```json
{
  "data": {
    "arxiv_id": "2403.12345",
    "title": "Efficient Vision Transformers with Multi-Scale Attention",
    "memo": "Interesting multi-scale attention approach, read later",
    "tags": [],
    "saved_at": "2026-04-03T14:30:00Z"
  },
  "_links": {
    "self": "/api/library",
    "paper": "/api/papers/2403.12345",
    "notes": "/api/papers/2403.12345/notes",
    "tags": "/api/library/2403.12345/tags"
  }
}
```

**错误响应：**
- 404：论文不存在（本地和 arXiv 均未找到）
- 409：已收藏该论文

---

### DELETE /api/papers/{arxiv_id}/save

取消收藏论文。**需要认证。**

**成功响应（204）：** 无响应体。

**错误响应：**
- 404：未收藏该论文

---

### GET /api/library

查看当前用户的收藏列表。**需要认证。**

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tag | string | 否 | 按标签过滤 |
| page | int | 否 | 页码 |
| per_page | int | 否 | 每页数量 |

**成功响应（200）：**
```json
{
  "data": [
    {
      "arxiv_id": "2403.12345",
      "title": "Efficient Vision Transformers with Multi-Scale Attention",
      "authors": ["Alice Smith", "Bob Johnson"],
      "categories": "cs.CV cs.AI",
      "published_date": "2026-03-28",
      "memo": "Interesting multi-scale attention approach",
      "tags": ["attention", "to read"],
      "saved_at": "2026-04-03T14:30:00Z",
      "_links": {
        "paper": "/api/papers/2403.12345",
        "notes": "/api/papers/2403.12345/notes",
        "tags": "/api/library/2403.12345/tags"
      }
    }
  ],
  "pagination": { "total": 12, "page": 1, "per_page": 20, "pages": 1 },
  "_links": { "self": "/api/library?page=1" }
}
```

---

### POST /api/library/{arxiv_id}/tags

为收藏的论文添加标签。**需要认证。**

**请求：**
```json
{
  "tags": ["attention", "to read"]
}
```

**成功响应（200）：**
```json
{
  "data": {
    "arxiv_id": "2403.12345",
    "tags": ["attention", "to read"]
  }
}
```

**错误响应：**
- 404：未收藏该论文

---

### DELETE /api/library/{arxiv_id}/tags/{tag_name}

移除收藏论文上的标签。**需要认证。**

**成功响应（204）：** 无响应体。

**错误响应：**
- 404：标签不存在或未收藏该论文

---

### GET /api/tags

查看当前用户的所有标签。**需要认证。**

**成功响应（200）：**
```json
{
  "data": [
    { "name": "attention", "count": 5 },
    { "name": "to read", "count": 3 },
    { "name": "important", "count": 2 }
  ]
}
```

`count` 为使用该标签的论文数量。

---

## F4 笔记系统

### POST /api/notes

创建笔记。**需要认证。**

**请求：**
```json
{
  "paper_id": "2403.12345",
  "title": "Multi-Scale Attention Notes",
  "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism..."
}
```

`paper_id`（arXiv ID）为可选字段，不传则创建独立笔记。

**成功响应（201）：**
```json
{
  "data": {
    "id": 1,
    "paper_id": "2403.12345",
    "title": "Multi-Scale Attention Notes",
    "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism...",
    "created_at": "2026-04-03T15:00:00Z",
    "updated_at": "2026-04-03T15:00:00Z"
  },
  "_links": {
    "self": "/api/notes/1",
    "paper": "/api/papers/2403.12345",
    "flashcards": "/api/notes/1/flashcards"
  }
}
```

**错误响应：**
- 400：缺少 title 或 content
- 404：paper_id 对应的论文不存在

---

### GET /api/notes

查看当前用户的所有笔记。**需要认证。**

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| paper_id | string | 否 | 按论文 arXiv ID 过滤 |
| page | int | 否 | 页码 |
| per_page | int | 否 | 每页数量 |

**成功响应（200）：**
```json
{
  "data": [
    {
      "id": 1,
      "paper_id": "2403.12345",
      "paper_title": "Efficient Vision Transformers...",
      "title": "Multi-Scale Attention Notes",
      "content": "## Key Ideas\n\n- ...",
      "created_at": "2026-04-03T15:00:00Z",
      "updated_at": "2026-04-03T15:00:00Z",
      "_links": {
        "self": "/api/notes/1",
        "paper": "/api/papers/2403.12345",
        "flashcards": "/api/notes/1/flashcards"
      }
    }
  ],
  "pagination": { "total": 8, "page": 1, "per_page": 20, "pages": 1 },
  "_links": { "self": "/api/notes?page=1" }
}
```

---

### GET /api/papers/{arxiv_id}/notes

查看指定论文的笔记。**需要认证。**

**成功响应（200）：** 格式同 `GET /api/notes`，自动按 paper_id 过滤。

---

### GET /api/notes/{id}

查看单条笔记。**需要认证。**

**成功响应（200）：**
```json
{
  "data": {
    "id": 1,
    "paper_id": "2403.12345",
    "paper_title": "Efficient Vision Transformers...",
    "title": "Multi-Scale Attention Notes",
    "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism...",
    "created_at": "2026-04-03T15:00:00Z",
    "updated_at": "2026-04-03T15:00:00Z"
  },
  "_links": {
    "self": "/api/notes/1",
    "paper": "/api/papers/2403.12345",
    "flashcards": "/api/notes/1/flashcards"
  }
}
```

**错误响应：**
- 403：笔记不属于当前用户
- 404：笔记不存在

---

### PUT /api/notes/{id}

更新笔记。**需要认证。**

**请求：**
```json
{
  "title": "Updated Title",
  "content": "Updated content..."
}
```

所有字段可选，仅更新提供的字段。

**成功响应（200）：** 返回更新后的笔记（格式同 GET）。

**错误响应：**
- 403：笔记不属于当前用户
- 404：笔记不存在

---

### DELETE /api/notes/{id}

删除笔记。**需要认证。** 同时级联删除关联的闪卡和 ChromaDB 向量。

**成功响应（204）：** 无响应体。

**错误响应：**
- 403：笔记不属于当前用户
- 404：笔记不存在

---

## F5 闪卡与间隔重复

### POST /api/flashcards

创建闪卡。**需要认证。**

**请求：**
```json
{
  "note_id": 1,
  "question": "What is Multi-Head Attention?",
  "answer": "A mechanism that runs multiple attention functions in parallel..."
}
```

**成功响应（201）：**
```json
{
  "data": {
    "id": 1,
    "note_id": 1,
    "question": "What is Multi-Head Attention?",
    "answer": "A mechanism that runs multiple attention functions in parallel...",
    "ease_factor": 2.5,
    "interval": 1,
    "repetitions": 0,
    "next_review_at": "2026-04-04T15:00:00Z",
    "created_at": "2026-04-03T15:00:00Z"
  },
  "_links": {
    "self": "/api/flashcards/1",
    "note": "/api/notes/1",
    "review": "/api/flashcards/1/review"
  }
}
```

**错误响应：**
- 400：缺少必填字段
- 403：笔记不属于当前用户
- 404：笔记不存在

---

### GET /api/flashcards

查看当前用户的所有闪卡。**需要认证。**

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| note_id | int | 否 | 按笔记过滤 |
| page | int | 否 | 页码 |
| per_page | int | 否 | 每页数量 |

**成功响应（200）：** 闪卡列表，分页格式。

---

### GET /api/notes/{id}/flashcards

查看某条笔记下的闪卡。**需要认证。**

**成功响应（200）：** 格式同 `GET /api/flashcards`。

---

### PUT /api/flashcards/{id}

编辑闪卡。**需要认证。**

**请求：**
```json
{
  "question": "Updated question?",
  "answer": "Updated answer."
}
```

**成功响应（200）：** 返回更新后的闪卡。

**错误响应：**
- 403：闪卡不属于当前用户
- 404：闪卡不存在

---

### DELETE /api/flashcards/{id}

删除闪卡。**需要认证。**

**成功响应（204）：** 无响应体。

---

### GET /api/flashcards/due

获取今日待复习的闪卡。**需要认证。**

**成功响应（200）：**
```json
{
  "data": [
    {
      "id": 1,
      "question": "What is Multi-Head Attention?",
      "answer": "A mechanism that...",
      "note_id": 1,
      "ease_factor": 2.5,
      "interval": 1,
      "repetitions": 0,
      "next_review_at": "2026-04-04T15:00:00Z",
      "_links": {
        "self": "/api/flashcards/1",
        "review": "/api/flashcards/1/review",
        "note": "/api/notes/1"
      }
    }
  ],
  "total_due": 5
}
```

---

### POST /api/flashcards/{id}/review

提交复习结果，系统根据 SM-2 算法更新闪卡参数。**需要认证。**

**请求：**
```json
{
  "rating": 4
}
```

`rating` 范围 0-5（SM-2 标准：0=完全忘记，5=轻松记住）。

**成功响应（200）：**
```json
{
  "data": {
    "flashcard_id": 1,
    "rating": 4,
    "updated": {
      "ease_factor": 2.5,
      "interval": 6,
      "repetitions": 2,
      "next_review_at": "2026-04-09T15:00:00Z"
    },
    "reviewed_at": "2026-04-03T20:00:00Z"
  }
}
```

**错误响应：**
- 400：rating 不在 0-5 范围内

---

### GET /api/review/stats

查看复习统计。**需要认证。**

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | string | 否 | 统计周期："week"（默认）、"month"、"all" |

**成功响应（200）：**
```json
{
  "data": {
    "total_cards": 25,
    "due_today": 5,
    "mastered": 12,
    "learning": 13,
    "reviews_in_period": 42,
    "average_rating": 3.8,
    "daily_reviews": [
      { "date": "2026-04-01", "count": 8, "avg_rating": 3.5 },
      { "date": "2026-04-02", "count": 12, "avg_rating": 4.0 },
      { "date": "2026-04-03", "count": 22, "avg_rating": 3.9 }
    ]
  }
}
```

`mastered`：ease_factor >= 2.5 且 interval >= 21 的闪卡数。

---

## F6 RAG 语义搜索

### POST /api/search/papers

在论文摘要中进行语义搜索。

**请求：**
```json
{
  "query": "transformer attention mechanism optimization",
  "n_results": 10
}
```

**成功响应（200）：**
```json
{
  "data": [
    {
      "arxiv_id": "2403.12345",
      "title": "Efficient Vision Transformers with Multi-Scale Attention",
      "abstract": "We propose a novel...",
      "categories": "cs.CV cs.AI",
      "published_date": "2026-03-28",
      "relevance_score": 0.89,
      "_links": {
        "self": "/api/papers/2403.12345",
        "save": "/api/papers/2403.12345/save"
      }
    }
  ],
  "query": "transformer attention mechanism optimization",
  "source": "paper_abstracts"
}
```

`relevance_score` 为 ChromaDB 返回的相似度分数（0-1，越高越相关）。

---

### POST /api/search/notes

在当前用户的笔记中进行语义搜索。**需要认证。**

**请求：**
```json
{
  "query": "data augmentation techniques",
  "n_results": 5
}
```

**成功响应（200）：**
```json
{
  "data": [
    {
      "id": 3,
      "title": "Data Augmentation Survey Notes",
      "content": "## Summary\n\n- ...",
      "paper_id": "2403.67890",
      "relevance_score": 0.92,
      "_links": {
        "self": "/api/notes/3",
        "paper": "/api/papers/2403.67890"
      }
    }
  ],
  "query": "data augmentation techniques",
  "source": "user_notes"
}
```

---

### POST /api/search/all

跨库联合搜索（论文 + 笔记）。**需要认证。**

**请求：**
```json
{
  "query": "attention mechanism improvements",
  "n_results": 10
}
```

**成功响应（200）：**
```json
{
  "data": [
    {
      "type": "note",
      "id": 1,
      "title": "Multi-Scale Attention Notes",
      "snippet": "Proposes a hierarchical attention mechanism...",
      "relevance_score": 0.94,
      "_links": { "self": "/api/notes/1" }
    },
    {
      "type": "paper",
      "arxiv_id": "2403.12345",
      "title": "Efficient Vision Transformers with Multi-Scale Attention",
      "snippet": "We propose a novel multi-scale attention...",
      "relevance_score": 0.89,
      "_links": { "self": "/api/papers/2403.12345" }
    }
  ],
  "query": "attention mechanism improvements",
  "source": "all"
}
```

结果按 `relevance_score` 降序排列，`type` 标注来源。

---

## 端点汇总

| 模块 | 方法 | 路径 | 认证 |
|------|------|------|------|
| **F1** | POST | `/api/auth/register` | 否 |
| | POST | `/api/auth/login` | 否 |
| | GET | `/api/users/me` | 是 |
| | PUT | `/api/users/me` | 是 |
| **F2** | GET | `/api/papers/search` | 否 |
| | GET | `/api/papers/trending` | 否 |
| | GET | `/api/papers/{arxiv_id}` | 否 |
| **F3** | POST | `/api/papers/{arxiv_id}/save` | 是 |
| | DELETE | `/api/papers/{arxiv_id}/save` | 是 |
| | GET | `/api/library` | 是 |
| | POST | `/api/library/{arxiv_id}/tags` | 是 |
| | DELETE | `/api/library/{arxiv_id}/tags/{tag_name}` | 是 |
| | GET | `/api/tags` | 是 |
| **F4** | POST | `/api/notes` | 是 |
| | GET | `/api/notes` | 是 |
| | GET | `/api/papers/{arxiv_id}/notes` | 是 |
| | GET | `/api/notes/{id}` | 是 |
| | PUT | `/api/notes/{id}` | 是 |
| | DELETE | `/api/notes/{id}` | 是 |
| **F5** | POST | `/api/flashcards` | 是 |
| | GET | `/api/flashcards` | 是 |
| | GET | `/api/notes/{id}/flashcards` | 是 |
| | PUT | `/api/flashcards/{id}` | 是 |
| | DELETE | `/api/flashcards/{id}` | 是 |
| | GET | `/api/flashcards/due` | 是 |
| | POST | `/api/flashcards/{id}/review` | 是 |
| | GET | `/api/review/stats` | 是 |
| **F6** | POST | `/api/search/papers` | 否 |
| | POST | `/api/search/notes` | 是 |
| | POST | `/api/search/all` | 是 |

**共计 30 个端点**（7 个公开 + 23 个需认证）。
