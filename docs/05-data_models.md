# 数据模型设计：ScholarTrack

## 模型关系总览

```
User
 ├── 1:N ── UserPaper ── N:1 ── Paper
 │            └── M:N ── Tag (通过 UserPaperTag)
 ├── 1:N ── Note ── N:1 ── Paper (可选关联)
 │            └── 1:N ── Flashcard
 │                        └── 1:N ── ReviewLog
 └── preferences (JSON 字段)
```

---

## 模型定义

### User

用户账户，认证与身份信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 用户 ID |
| username | String(80) | UNIQUE, NOT NULL | 用户名 |
| email | String(120) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | String(256) | NOT NULL | bcrypt 哈希密码 |
| preferred_categories | JSON | DEFAULT '[]' | 关注的 arXiv 分类列表，如 ["cs.CV", "cs.CL"] |
| created_at | DateTime | NOT NULL, DEFAULT now | 注册时间 |

索引：`username`、`email`

---

### Paper

论文元数据，公共论文池。所有数据来自 arXiv API，只读（用户不直接创建或修改）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 内部 ID |
| arxiv_id | String(50) | UNIQUE, NOT NULL | arXiv 论文 ID，如 "2403.12345" |
| title | Text | NOT NULL | 论文标题 |
| authors | Text | NOT NULL | 作者列表（JSON 数组的字符串形式） |
| abstract | Text | NOT NULL | 论文摘要 |
| categories | String(200) | NOT NULL | arXiv 分类，如 "cs.CV cs.AI" |
| published_date | Date | NOT NULL | 发表日期 |
| arxiv_url | String(300) | NOT NULL | arXiv 页面链接 |
| pdf_url | String(300) | NOT NULL | PDF 下载链接 |
| fetched_at | DateTime | NOT NULL, DEFAULT now | 本地缓存时间 |

索引：`arxiv_id`、`published_date`、`categories`

说明：
- 论文通过 arXiv API 获取后自动缓存到此表
- 通过 `arxiv_id` 去重，已存在的论文不重复插入
- `abstract` 同步向量化写入 ChromaDB（collection: `paper_abstracts`）

---

### UserPaper

用户与论文的收藏关系（多对多）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 关系 ID |
| user_id | Integer | FK(User.id), NOT NULL | 用户 |
| paper_id | Integer | FK(Paper.id), NOT NULL | 论文 |
| memo | Text | DEFAULT NULL | 收藏时的个人备注 |
| saved_at | DateTime | NOT NULL, DEFAULT now | 收藏时间 |

约束：UNIQUE(user_id, paper_id) — 同一用户不能重复收藏同一论文

索引：`user_id`、`paper_id`

---

### Tag

用户自定义标签。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 标签 ID |
| user_id | Integer | FK(User.id), NOT NULL | 所属用户 |
| name | String(50) | NOT NULL | 标签名称，如 "attention mechanism"、"to read" |

约束：UNIQUE(user_id, name) — 同一用户标签名不重复

---

### UserPaperTag

收藏论文与标签的关联（多对多）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 关系 ID |
| user_paper_id | Integer | FK(UserPaper.id), NOT NULL | 收藏关系 |
| tag_id | Integer | FK(Tag.id), NOT NULL | 标签 |

约束：UNIQUE(user_paper_id, tag_id)

---

### Note

用户的阅读笔记。项目核心 CRUD 模型。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 笔记 ID |
| user_id | Integer | FK(User.id), NOT NULL | 作者 |
| paper_id | Integer | FK(Paper.id), DEFAULT NULL | 关联论文（可选） |
| title | String(200) | NOT NULL | 笔记标题 |
| content | Text | NOT NULL | 笔记内容（Markdown） |
| created_at | DateTime | NOT NULL, DEFAULT now | 创建时间 |
| updated_at | DateTime | NOT NULL, DEFAULT now | 最后更新时间 |

索引：`user_id`、`paper_id`、`created_at`

说明：
- `paper_id` 可选：笔记可以关联到论文，也可以独立存在
- `content` 同步向量化写入 ChromaDB（collection: `user_notes`，metadata 含 user_id）
- 更新/删除时同步维护 ChromaDB

---

### Flashcard

复习闪卡，关联到笔记。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 闪卡 ID |
| user_id | Integer | FK(User.id), NOT NULL | 所属用户 |
| note_id | Integer | FK(Note.id), NOT NULL | 关联笔记 |
| question | Text | NOT NULL | 问题 |
| answer | Text | NOT NULL | 答案 |
| ease_factor | Float | NOT NULL, DEFAULT 2.5 | SM-2 难度因子 |
| interval | Integer | NOT NULL, DEFAULT 1 | 当前复习间隔（天） |
| repetitions | Integer | NOT NULL, DEFAULT 0 | 连续正确次数 |
| next_review_at | DateTime | NOT NULL, DEFAULT now | 下次复习时间 |
| created_at | DateTime | NOT NULL, DEFAULT now | 创建时间 |

索引：`user_id`、`next_review_at`

说明：
- `ease_factor` 最小值 1.3
- `interval` 单位为天
- `repetitions` 用于 SM-2 算法前两次的特殊处理（第 1 次 interval=1，第 2 次 interval=6）

---

### ReviewLog

每次复习的记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, auto-increment | 记录 ID |
| user_id | Integer | FK(User.id), NOT NULL | 用户 |
| flashcard_id | Integer | FK(Flashcard.id), NOT NULL | 闪卡 |
| rating | Integer | NOT NULL | SM-2 评分（0-5） |
| reviewed_at | DateTime | NOT NULL, DEFAULT now | 复习时间 |

索引：`user_id`、`reviewed_at`

说明：
- 每次提交复习结果时插入一条记录
- 用于统计复习历史和正确率趋势

---

## ChromaDB Collections

ChromaDB 不替代 SQLite，仅作为语义搜索的向量索引。

### paper_abstracts

| 字段 | 说明 |
|------|------|
| id | 格式：`paper_{Paper.id}` |
| document | Paper.abstract |
| metadata | `{arxiv_id, title, categories, published_date}` |

- 写入时机：Paper 缓存到 SQLite 时同步写入
- 使用 ChromaDB 默认 embedding（all-MiniLM-L6-v2）

### user_notes

| 字段 | 说明 |
|------|------|
| id | 格式：`note_{Note.id}` |
| document | Note.content |
| metadata | `{user_id, title, paper_id, created_at}` |

- 写入时机：Note 创建/更新时写入，删除时移除
- 查询时通过 `metadata.user_id` 过滤，确保只搜索当前用户的笔记

---

## 级联删除策略

| 触发 | 级联效果 |
|------|----------|
| 删除 User | 删除其所有 UserPaper、Tag、Note、Flashcard、ReviewLog |
| 删除 UserPaper | 删除关联的 UserPaperTag |
| 删除 Note | 删除关联的 Flashcard → 其 ReviewLog；移除 ChromaDB 向量 |
| 删除 Flashcard | 删除关联的 ReviewLog |
| Paper 不会被用户删除 | 公共池数据，只读 |

---

## SQLAlchemy 模型示意

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    preferred_categories = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_papers = db.relationship('UserPaper', backref='user', cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='user', cascade='all, delete-orphan')
    tags = db.relationship('Tag', backref='user', cascade='all, delete-orphan')

class Paper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text, nullable=False)
    categories = db.Column(db.String(200), nullable=False)
    published_date = db.Column(db.Date, nullable=False)
    arxiv_url = db.Column(db.String(300), nullable=False)
    pdf_url = db.Column(db.String(300), nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    memo = db.Column(db.Text)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'paper_id'),)
    paper = db.relationship('Paper')
    tags = db.relationship('UserPaperTag', backref='user_paper', cascade='all, delete-orphan')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'name'),)

class UserPaperTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_paper_id = db.Column(db.Integer, db.ForeignKey('user_paper.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_paper_id', 'tag_id'),)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper = db.relationship('Paper')
    flashcards = db.relationship('Flashcard', backref='note', cascade='all, delete-orphan')

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    ease_factor = db.Column(db.Float, nullable=False, default=2.5)
    interval = db.Column(db.Integer, nullable=False, default=1)
    repetitions = db.Column(db.Integer, nullable=False, default=0)
    next_review_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship('ReviewLog', backref='flashcard', cascade='all, delete-orphan')

class ReviewLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcard.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)
```
