# Phase 1 Implementation Notes — Utils & ChromaDB Service

This document provides detailed implementation specs for Phase 1, Tasks #3 (utils module) and #4 (ChromaDB service). The Developer should follow these specs closely.

---

## 1. Utils Module (`app/utils/`)

Create `app/utils/__init__.py` that re-exports the public API from each submodule:

```python
from app.utils.errors import APIError, register_error_handlers
from app.utils.pagination import paginate_query
from app.utils.validators import validate_required_fields, validate_email, validate_pagination_params
```

---

### 1.1 errors.py

#### APIError Exception Class

```python
class APIError(Exception):
    """Custom API exception that carries HTTP status code and error type."""

    def __init__(self, message, status_code=400, error_type=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        # Default error_type derived from status code if not provided
        self.error_type = error_type or self._default_error_type()

    def _default_error_type(self):
        mapping = {
            400: 'bad_request',
            401: 'unauthorized',
            403: 'forbidden',
            404: 'not_found',
            409: 'conflict',
            500: 'internal_error',
        }
        return mapping.get(self.status_code, 'error')

    def to_dict(self):
        return {
            'error': self.error_type,
            'message': self.message,
        }
```

#### register_error_handlers(app)

Register Flask error handlers on the app instance. Must handle:

1. **APIError** — return `error.to_dict()` with `error.status_code`
2. **400 Bad Request** — catch Werkzeug `BadRequest`, return `{"error": "bad_request", "message": "..."}`
3. **401 Unauthorized** — for both Werkzeug and flask-jwt-extended failures
4. **403 Forbidden**
5. **404 Not Found** — catch Werkzeug `NotFound` (covers unknown routes)
6. **405 Method Not Allowed** — include in handlers for completeness
7. **409 Conflict**
8. **500 Internal Server Error** — catch generic `Exception`; log the traceback but return a safe message to the client (`"An unexpected error occurred"`)

Implementation detail: Use `@app.errorhandler(code)` for HTTP codes and `@app.errorhandler(APIError)` for the custom exception.

For JWT errors, flask-jwt-extended provides its own error callbacks. Register them in `register_error_handlers` or in the app factory. Key callbacks:
- `@jwt.unauthorized_loader` — missing token -> 401
- `@jwt.invalid_token_loader` — bad token -> 401
- `@jwt.expired_token_loader` — expired token -> 401

These should return the same `{"error": "unauthorized", "message": "..."}` format.

**Important:** All error responses must set `Content-Type: application/json`. Use `jsonify()` to ensure this.

---

### 1.2 pagination.py

#### paginate_query(query, page, per_page, max_per_page=100)

Takes a SQLAlchemy query object and returns a pagination result dict.

**Parameters:**
- `query` — SQLAlchemy `Query` object (not yet executed)
- `page` — int, current page (1-indexed)
- `per_page` — int, items per page
- `max_per_page` — int, hard cap (default 100)

**Logic:**
1. Clamp `per_page` to `max(1, min(per_page, max_per_page))`
2. Clamp `page` to `max(1, page)`
3. Use `query.paginate(page=page, per_page=per_page, error_out=False)` (Flask-SQLAlchemy's built-in paginator)
4. Build and return the result dict

**Return value:**

```python
{
    'data': [...],  # caller is responsible for serializing items
    'pagination': {
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
    },
    '_links': {
        'self': f'{base_url}?page={page}&per_page={per_page}',
        'next': f'{base_url}?page={page+1}&per_page={per_page}' if pagination.has_next else None,
        'prev': f'{base_url}?page={page-1}&per_page={per_page}' if pagination.has_prev else None,
    }
}
```

**Link generation:** Use `request.path` for the base path (not `request.url` which includes old query params). Preserve any non-pagination query params from the original request — this matters for filtered endpoints like `GET /api/library?tag=attention&page=2`.

**Design decision:** The function should NOT serialize items — it should return the raw `pagination.items` list in the `data` field, and the caller serializes them. This keeps pagination generic. Alternatively, accept an optional `serialize_fn` callback. Recommend the callback approach:

```python
def paginate_query(query, page, per_page, max_per_page=100, serialize_fn=None):
    # ...
    items = pagination.items
    data = [serialize_fn(item) for item in items] if serialize_fn else items
```

---

### 1.3 validators.py

#### validate_required_fields(data, fields)

```python
def validate_required_fields(data, fields):
    """
    Check that `data` (dict, typically from request.get_json()) contains all required fields.
    
    Returns: None if valid
    Raises: APIError(400) listing missing fields
    """
    if data is None:
        raise APIError('Request body must be JSON', status_code=400)
    missing = [f for f in fields if f not in data or data[f] is None]
    if missing:
        raise APIError(
            f'Missing required fields: {", ".join(missing)}',
            status_code=400
        )
```

Note: Check for both absence (`f not in data`) and explicit `None`. Do NOT check for empty strings here — that is context-dependent and should be validated at the route level if needed.

#### validate_email(email)

```python
import re

def validate_email(email):
    """
    Basic email format validation.
    
    Returns: None if valid
    Raises: APIError(400) if invalid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise APIError('Invalid email format', status_code=400)
```

This is intentionally simple — full RFC 5322 compliance is unnecessary for a coursework project. The regex covers all reasonable cases.

#### validate_pagination_params(args)

```python
def validate_pagination_params(args):
    """
    Extract and validate page/per_page from request args (werkzeug ImmutableMultiDict).
    
    Returns: (page: int, per_page: int) with defaults applied
    Raises: APIError(400) if values are not positive integers
    """
    try:
        page = int(args.get('page', 1))
        per_page = int(args.get('per_page', 20))
    except (ValueError, TypeError):
        raise APIError('page and per_page must be positive integers', status_code=400)

    if page < 1 or per_page < 1:
        raise APIError('page and per_page must be positive integers', status_code=400)

    return page, per_page
```

---

## 2. ChromaDB Service (`app/services/chromadb_service.py`)

### Design: Singleton Pattern

Use a module-level instance. ChromaDB's `PersistentClient` is designed to be long-lived.

```python
import chromadb

class ChromaDBService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, persist_directory='chroma_data'):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.paper_collection = self.client.get_or_create_collection(
            name='paper_abstracts',
            metadata={'hnsw:space': 'cosine'}
        )
        self.notes_collection = self.client.get_or_create_collection(
            name='user_notes',
            metadata={'hnsw:space': 'cosine'}
        )
```

### Configuration Integration

The `persist_directory` should come from Flask app config. In `app/__init__.py` (create_app), after `app` is created:

```python
app.config.setdefault('CHROMADB_DIR', 'chroma_data')
```

Then initialize in a lazy fashion — either:
- (A) Instantiate during `create_app` and store on `app.extensions['chromadb']`, or
- (B) Keep the singleton and pass the directory from config on first use

Recommend **(A)** for testability: the test config can use a temp directory or ephemeral client.

### Test Configuration

For tests, use `chromadb.EphemeralClient()` instead of `PersistentClient`. Add a config flag:

```python
# In TestConfig:
CHROMADB_PERSIST = False  # Use EphemeralClient
```

The service should check this flag:

```python
if app.config.get('CHROMADB_PERSIST', True):
    self.client = chromadb.PersistentClient(path=persist_dir)
else:
    self.client = chromadb.EphemeralClient()
```

### Phase 1 Scope

For Phase 1, only implement:
1. `__init__` — create client and both collections
2. `get_paper_collection()` — returns the paper_abstracts collection
3. `get_notes_collection()` — returns the user_notes collection

Stub the following methods with `pass` or `raise NotImplementedError` and a docstring:
- `add_paper(paper_id, abstract, metadata)` — Phase 2 (F2)
- `search_papers(query_text, n_results=10)` — Phase 3 (F6)
- `add_note(note_id, content, metadata)` — Phase 2 (F4)
- `update_note(note_id, content, metadata)` — Phase 2 (F4)
- `delete_note(note_id)` — Phase 2 (F4)
- `search_notes(query_text, user_id, n_results=5)` — Phase 3 (F6)
- `search_all(query_text, user_id, n_results=10)` — Phase 3 (F6)

### ChromaDB ID Conventions

Per the data model spec:
- Papers: `f"paper_{paper.id}"` (using the SQLite integer PK)
- Notes: `f"note_{note.id}"` (using the SQLite integer PK)

### Metadata Schemas

**paper_abstracts collection:**
```python
{
    'arxiv_id': str,      # e.g. '2403.12345'
    'title': str,
    'categories': str,    # e.g. 'cs.CV cs.AI'
    'published_date': str # ISO format date string
}
```

**user_notes collection:**
```python
{
    'user_id': int,       # for filtering — ChromaDB supports where clauses on metadata
    'title': str,
    'paper_id': int,      # nullable — 0 or omit if no paper
    'created_at': str     # ISO format datetime string
}
```

Note: ChromaDB metadata values must be str, int, float, or bool. No nested objects or lists. The `user_id` as int is fine.

---

## 3. Models — Implementation Watch Points

### 3.1 Cascade Delete Chains

The cascade chain is:

```
User delete
  -> UserPaper (cascade='all, delete-orphan')
       -> UserPaperTag (cascade='all, delete-orphan')
  -> Tag (cascade='all, delete-orphan')
  -> Note (cascade='all, delete-orphan')
       -> Flashcard (cascade='all, delete-orphan')
            -> ReviewLog (cascade='all, delete-orphan')
```

**Critical:** `cascade='all, delete-orphan'` must be set on the **parent's relationship**, not the child's ForeignKey. The spec exemplar is correct, but double-check that every level has it. Specifically:
- `User.saved_papers` -> `UserPaper` (has it)
- `UserPaper.tags` -> `UserPaperTag` (has it)
- `User.notes` -> `Note` (has it)
- `Note.flashcards` -> `Flashcard` (has it)
- `Flashcard.reviews` -> `ReviewLog` (has it)
- `User.tags` -> `Tag` (has it)

**Missing from spec exemplar:** User does not have a direct relationship to Flashcard or ReviewLog. This is fine — cascades chain through Note and Flashcard. But **queries** for "all user flashcards" need to join through Note, or we add a direct `User.flashcards` relationship. Since F5 endpoints query flashcards by `user_id` (which is a direct FK on Flashcard), the direct FK is sufficient for queries. No extra relationship needed.

### 3.2 Index Definitions

Add explicit `db.Index` or `index=True` on columns specified in the data model:

| Model | Indexed Columns |
|-------|----------------|
| User | `username` (unique implies index), `email` (unique implies index) |
| Paper | `arxiv_id` (unique implies index), `published_date`, `categories` |
| UserPaper | `user_id`, `paper_id` |
| Note | `user_id`, `paper_id`, `created_at` |
| Flashcard | `user_id`, `next_review_at` |
| ReviewLog | `user_id`, `reviewed_at` |

For non-unique indexes, use `index=True` on the column definition:

```python
published_date = db.Column(db.Date, nullable=False, index=True)
```

### 3.3 JSON Field Handling

**`User.preferred_categories`** — stored as `db.JSON`. SQLAlchemy's JSON type works with SQLite as of SA 2.0 (stores as TEXT, serialized). The `default=list` in the column definition means "call `list()` to produce `[]` for each new row" — this is correct (passing the callable, not a mutable default).

**`Paper.authors`** — stored as `db.Text`, containing a JSON-serialized array string (e.g., `'["Alice Smith", "Bob Johnson"]'`). This is **not** a JSON column; it is a plain text field. The route layer must:
- `json.loads(paper.authors)` when serializing for API response
- `json.dumps(authors_list)` when storing from arXiv API data

Why not `db.JSON`? The spec chose Text explicitly, and it works identically on SQLite. Either approach is acceptable, but follow the spec.

### 3.4 Timestamp Defaults

All `default=datetime.utcnow` — this must be the **callable** (no parentheses). If written as `default=datetime.utcnow()`, it evaluates once at class definition time and every row gets the same timestamp. The spec exemplar is correct.

For `Note.updated_at`, also set `onupdate=datetime.utcnow` (again, callable without parens). This auto-updates the timestamp on any `UPDATE` query via SQLAlchemy.

**Note on `utcnow` deprecation:** `datetime.utcnow()` is deprecated in Python 3.12+. For a coursework project targeting Python 3.10+, this is fine. If we want to be forward-compatible, use `lambda: datetime.now(timezone.utc)` instead. Recommend sticking with `datetime.utcnow` to match the spec exactly.

### 3.5 UniqueConstraint Handling

Several models use `__table_args__` for composite unique constraints:
- `UserPaper`: `(user_id, paper_id)` — prevents duplicate saves
- `Tag`: `(user_id, name)` — same tag name per user is one tag
- `UserPaperTag`: `(user_paper_id, tag_id)` — prevents duplicate tag assignments

When an `INSERT` violates these constraints, SQLAlchemy raises `IntegrityError`. The route layer should catch this and raise `APIError(409)` with a descriptive message. Example:

```python
from sqlalchemy.exc import IntegrityError

try:
    db.session.add(user_paper)
    db.session.commit()
except IntegrityError:
    db.session.rollback()
    raise APIError('Paper already saved to library', status_code=409)
```

### 3.6 Model `to_dict()` Methods

Each model should have a `to_dict()` method for serialization. These are not in the spec exemplar but are essential. The Developer should add them. Example for Paper:

```python
def to_dict(self):
    return {
        'arxiv_id': self.arxiv_id,
        'title': self.title,
        'authors': json.loads(self.authors),
        'abstract': self.abstract,
        'categories': self.categories,
        'published_date': self.published_date.isoformat(),
        'arxiv_url': self.arxiv_url,
        'pdf_url': self.pdf_url,
    }
```

Note: `_links` should NOT be generated in `to_dict()` — they depend on the request context and should be added in the route layer. Keep models context-free.

### 3.7 Backref vs back_populates

The spec uses `backref='user'` style. This is fine but creates implicit attributes. For clarity, the Developer may prefer explicit `back_populates` on both sides, but `backref` is acceptable and less verbose. Stay consistent — pick one style for the whole project.

---

## 4. File Checklist for Phase 1

After Tasks #3 and #4, these files should exist and be functional:

```
app/
├── utils/
│   ├── __init__.py          # Re-exports
│   ├── errors.py            # APIError + register_error_handlers
│   ├── pagination.py        # paginate_query
│   └── validators.py        # validate_required_fields, validate_email, validate_pagination_params
├── services/
│   ├── __init__.py          # (can be empty)
│   └── chromadb_service.py  # ChromaDBService singleton
└── models/
    ├── __init__.py          # Import all models, export db
    ├── user.py
    ├── paper.py
    ├── user_paper.py
    ├── tag.py
    ├── user_paper_tag.py
    ├── note.py
    ├── flashcard.py
    └── review_log.py
```

---

## 5. Integration with App Factory

In `create_app()`, after initializing extensions:

```python
# Error handlers
from app.utils.errors import register_error_handlers
register_error_handlers(app)

# ChromaDB (lazy — only if not testing with ephemeral)
from app.services.chromadb_service import ChromaDBService
chromadb_service = ChromaDBService(
    persist_directory=app.config.get('CHROMADB_DIR', 'chroma_data'),
    use_persistent=app.config.get('CHROMADB_PERSIST', True)
)
app.extensions['chromadb'] = chromadb_service
```

This ensures error handlers are active for all routes and ChromaDB is available via `current_app.extensions['chromadb']` in any request context.
