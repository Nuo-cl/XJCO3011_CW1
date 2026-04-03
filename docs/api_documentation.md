# ScholarTrack API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:5000/api`  
**Authentication:** JWT Bearer Token (`Authorization: Bearer <token>`)  
**Data Format:** JSON

---

## Table of Contents

1. [General Information](#1-general-information)
2. [F1: Authentication](#2-f1-authentication)
3. [F2: Paper Discovery](#3-f2-paper-discovery)
4. [F3: Paper Management](#4-f3-paper-management)
5. [F4: Notes](#5-f4-notes)
6. [F5: Flashcards & Spaced Repetition](#6-f5-flashcards--spaced-repetition)
7. [F6: Semantic Search](#7-f6-semantic-search)
8. [Endpoint Summary](#8-endpoint-summary)

---

## 1. General Information

### 1.1 Authentication

Authenticated endpoints require a JWT bearer token obtained via `POST /api/auth/login`. Include the token in the `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Tokens expire after **24 hours**.

### 1.2 Pagination

List endpoints support pagination via query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page (max 100) |

Paginated responses include:

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

### 1.3 Error Format

All errors follow a consistent format:

```json
{
  "error": "not_found",
  "message": "Paper with arxiv_id '2403.99999' not found"
}
```

### 1.4 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful read or update |
| 201 | Created | Resource created successfully |
| 204 | No Content | Resource deleted successfully |
| 400 | Bad Request | Input validation failed |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Access denied to another user's resource |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate operation (e.g. saving a paper twice) |
| 500 | Internal Server Error | Unexpected server error |

### 1.5 HATEOAS Links

All responses include a `_links` object with related resource URIs, enabling API navigation without hardcoded paths.

---

## 2. F1: Authentication

### 2.1 POST /api/auth/register

Register a new user account.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username |
| `email` | string | Yes | Valid email address |
| `password` | string | Yes | Account password |

**Example Request:**

```json
{
  "username": "researcher1",
  "email": "researcher1@example.com",
  "password": "securepass123"
}
```

**Success Response (201 Created):**

```json
{
  "data": {
    "id": 1,
    "username": "researcher1",
    "email": "researcher1@example.com",
    "preferred_categories": [],
    "created_at": "2026-04-03T10:00:00"
  },
  "_links": {
    "self": "/api/users/me",
    "login": "/api/auth/login"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing required fields or invalid email format |
| 409 | Username or email already exists |

---

### 2.2 POST /api/auth/login

Authenticate a user and obtain a JWT access token.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Account username |
| `password` | string | Yes | Account password |

**Example Request:**

```json
{
  "username": "researcher1",
  "password": "securepass123"
}
```

**Success Response (200 OK):**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Invalid username or password |

---

### 2.3 GET /api/users/me

Retrieve the current user's profile. **Requires authentication.**

**Success Response (200 OK):**

```json
{
  "data": {
    "id": 1,
    "username": "researcher1",
    "email": "researcher1@example.com",
    "preferred_categories": ["cs.CV", "cs.CL"],
    "created_at": "2026-04-03T10:00:00"
  },
  "_links": {
    "self": "/api/users/me",
    "library": "/api/library",
    "notes": "/api/notes"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

### 2.4 PUT /api/users/me

Update the current user's profile. **Requires authentication.**

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | New email address |
| `preferred_categories` | array of strings | Preferred arXiv categories |

**Example Request:**

```json
{
  "email": "new_email@example.com",
  "preferred_categories": ["cs.CV", "cs.CL", "cs.AI"]
}
```

**Success Response (200 OK):** Returns the updated user profile (same format as GET).

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Invalid email format or invalid field types |
| 401 | Missing or invalid JWT token |
| 409 | Email already in use by another account |

---

## 3. F2: Paper Discovery

### 3.1 GET /api/papers/search

Search arXiv papers by keyword. Results are fetched from the arXiv API and cached locally.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search keywords |
| `category` | string | No | arXiv category filter (e.g. `cs.CV`) |
| `date_from` | string | No | Start date (YYYY-MM-DD) |
| `date_to` | string | No | End date (YYYY-MM-DD) |
| `page` | integer | No | Page number (default 1) |
| `per_page` | integer | No | Items per page (default 20, max 100) |

**Example Request:**

```
GET /api/papers/search?q=vision+transformer&category=cs.CV&page=1
```

**Success Response (200 OK):**

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
  "pagination": {
    "total": 45,
    "page": 1,
    "per_page": 20,
    "pages": 3
  },
  "_links": {
    "self": "/api/papers/search?q=vision+transformer&page=1&per_page=20",
    "next": "/api/papers/search?q=vision+transformer&page=2&per_page=20"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing `q` parameter |

---

### 3.2 GET /api/papers/trending

Get recent papers in a specific arXiv category.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | Yes | arXiv category (e.g. `cs.CV`) |
| `days` | integer | No | Lookback period in days (default 7) |
| `page` | integer | No | Page number (default 1) |
| `per_page` | integer | No | Items per page (default 20, max 100) |

**Example Request:**

```
GET /api/papers/trending?category=cs.CV&days=7
```

**Success Response (200 OK):** Same format as paper search.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing `category` parameter |

---

### 3.3 GET /api/papers/{arxiv_id}

Retrieve details for a single paper. Checks local cache first, then fetches from arXiv API.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID (e.g. `2403.12345`) |

**Success Response (200 OK):**

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

Note: The `is_saved` field is only included when the request includes a valid JWT token.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 404 | Paper not found on arXiv |

---

## 4. F3: Paper Management

### 4.1 POST /api/papers/{arxiv_id}/save

Save a paper to the user's personal library. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID |

**Request Body (optional):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `memo` | string | No | Personal note about the paper |

**Example Request:**

```json
{
  "memo": "Interesting multi-scale attention approach, read later"
}
```

**Success Response (201 Created):**

```json
{
  "data": {
    "arxiv_id": "2403.12345",
    "title": "Efficient Vision Transformers with Multi-Scale Attention",
    "memo": "Interesting multi-scale attention approach, read later",
    "tags": [],
    "saved_at": "2026-04-03T14:30:00"
  },
  "_links": {
    "self": "/api/library",
    "paper": "/api/papers/2403.12345",
    "notes": "/api/papers/2403.12345/notes",
    "tags": "/api/library/2403.12345/tags"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 404 | Paper not found (locally or on arXiv) |
| 409 | Paper already saved to library |

---

### 4.2 DELETE /api/papers/{arxiv_id}/save

Remove a paper from the user's library. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID |

**Success Response (204 No Content):** Empty body.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 404 | Paper not in the user's library |

---

### 4.3 GET /api/library

List all papers in the user's personal library. **Requires authentication.**

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag` | string | No | Filter by tag name |
| `page` | integer | No | Page number (default 1) |
| `per_page` | integer | No | Items per page (default 20, max 100) |

**Example Request:**

```
GET /api/library?tag=attention&page=1
```

**Success Response (200 OK):**

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
      "saved_at": "2026-04-03T14:30:00",
      "_links": {
        "paper": "/api/papers/2403.12345",
        "notes": "/api/papers/2403.12345/notes",
        "tags": "/api/library/2403.12345/tags"
      }
    }
  ],
  "pagination": {
    "total": 12,
    "page": 1,
    "per_page": 20,
    "pages": 1
  },
  "_links": {
    "self": "/api/library?page=1&per_page=20"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

### 4.4 POST /api/library/{arxiv_id}/tags

Add tags to a saved paper. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tags` | array of strings | Yes | Tag names to add |

**Example Request:**

```json
{
  "tags": ["attention", "to read"]
}
```

**Success Response (200 OK):**

```json
{
  "data": {
    "arxiv_id": "2403.12345",
    "tags": ["attention", "to read"]
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | `tags` field is not a list |
| 401 | Missing or invalid JWT token |
| 404 | Paper not in the user's library |

---

### 4.5 DELETE /api/library/{arxiv_id}/tags/{tag_name}

Remove a tag from a saved paper. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID |
| `tag_name` | string | Tag name to remove |

**Success Response (204 No Content):** Empty body.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 404 | Tag not found or paper not in library |

---

### 4.6 GET /api/tags

List all of the current user's tags with usage counts. **Requires authentication.**

**Success Response (200 OK):**

```json
{
  "data": [
    { "name": "attention", "count": 5 },
    { "name": "to read", "count": 3 },
    { "name": "important", "count": 2 }
  ]
}
```

`count` is the number of papers tagged with this label.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

## 5. F4: Notes

### 5.1 POST /api/notes

Create a research note, optionally linked to a paper. **Requires authentication.**

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Note title |
| `content` | string | Yes | Note content (Markdown supported) |
| `paper_id` | string | No | arXiv ID to link the note to |

**Example Request:**

```json
{
  "paper_id": "2403.12345",
  "title": "Multi-Scale Attention Notes",
  "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism..."
}
```

**Success Response (201 Created):**

```json
{
  "data": {
    "id": 1,
    "paper_id": "2403.12345",
    "title": "Multi-Scale Attention Notes",
    "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism...",
    "created_at": "2026-04-03T15:00:00",
    "updated_at": "2026-04-03T15:00:00",
    "_links": {
      "self": "/api/notes/1",
      "paper": "/api/papers/2403.12345",
      "flashcards": "/api/notes/1/flashcards"
    }
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing `title` or `content` |
| 401 | Missing or invalid JWT token |
| 404 | Paper with given `paper_id` not found |

---

### 5.2 GET /api/notes

List all notes for the current user. **Requires authentication.**

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `paper_id` | string | No | Filter by arXiv paper ID |
| `page` | integer | No | Page number (default 1) |
| `per_page` | integer | No | Items per page (default 20, max 100) |

**Success Response (200 OK):**

```json
{
  "data": [
    {
      "id": 1,
      "paper_id": "2403.12345",
      "paper_title": "Efficient Vision Transformers...",
      "title": "Multi-Scale Attention Notes",
      "content": "## Key Ideas\n\n- ...",
      "created_at": "2026-04-03T15:00:00",
      "updated_at": "2026-04-03T15:00:00",
      "_links": {
        "self": "/api/notes/1",
        "paper": "/api/papers/2403.12345",
        "flashcards": "/api/notes/1/flashcards"
      }
    }
  ],
  "pagination": { "total": 8, "page": 1, "per_page": 20, "pages": 1 },
  "_links": { "self": "/api/notes?page=1&per_page=20" }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

### 5.3 GET /api/papers/{arxiv_id}/notes

List notes linked to a specific paper. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_id` | string | arXiv paper ID |

**Success Response (200 OK):** Same format as `GET /api/notes`, filtered by paper.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 404 | Paper not found |

---

### 5.4 GET /api/notes/{id}

Retrieve a single note. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Note ID |

**Success Response (200 OK):**

```json
{
  "data": {
    "id": 1,
    "paper_id": "2403.12345",
    "paper_title": "Efficient Vision Transformers...",
    "title": "Multi-Scale Attention Notes",
    "content": "## Key Ideas\n\n- Proposes a hierarchical attention mechanism...",
    "created_at": "2026-04-03T15:00:00",
    "updated_at": "2026-04-03T15:00:00",
    "_links": {
      "self": "/api/notes/1",
      "paper": "/api/papers/2403.12345",
      "flashcards": "/api/notes/1/flashcards"
    }
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 403 | Note belongs to another user |
| 404 | Note not found |

---

### 5.5 PUT /api/notes/{id}

Update a note. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Note ID |

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Updated title |
| `content` | string | Updated content |

**Example Request:**

```json
{
  "title": "Updated Title",
  "content": "Updated content with new insights..."
}
```

**Success Response (200 OK):** Returns the updated note (same format as GET).

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Empty request body |
| 401 | Missing or invalid JWT token |
| 403 | Note belongs to another user |
| 404 | Note not found |

---

### 5.6 DELETE /api/notes/{id}

Delete a note and its associated flashcards. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Note ID |

**Success Response (204 No Content):** Empty body.

Note: Deleting a note also cascade-deletes all linked flashcards and removes the note's vector from ChromaDB.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 403 | Note belongs to another user |
| 404 | Note not found |

---

## 6. F5: Flashcards & Spaced Repetition

### 6.1 POST /api/flashcards

Create a flashcard linked to a note. **Requires authentication.**

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `note_id` | integer | Yes | ID of the parent note |
| `question` | string | Yes | Flashcard question |
| `answer` | string | Yes | Flashcard answer |

**Example Request:**

```json
{
  "note_id": 1,
  "question": "What is Multi-Head Attention?",
  "answer": "A mechanism that runs multiple attention functions in parallel, allowing the model to attend to information from different representation subspaces."
}
```

**Success Response (201 Created):**

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
    "next_review_at": "2026-04-04T15:00:00",
    "created_at": "2026-04-03T15:00:00",
    "_links": {
      "self": "/api/flashcards/1",
      "note": "/api/notes/1",
      "review": "/api/flashcards/1/review"
    }
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing required fields |
| 401 | Missing or invalid JWT token |
| 403 | Note does not belong to the current user |
| 404 | Note not found |

---

### 6.2 GET /api/flashcards

List all flashcards for the current user. **Requires authentication.**

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `note_id` | integer | No | Filter by note ID |
| `page` | integer | No | Page number (default 1) |
| `per_page` | integer | No | Items per page (default 20, max 100) |

**Success Response (200 OK):** Paginated list of flashcards.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

### 6.3 GET /api/notes/{id}/flashcards

List flashcards for a specific note. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Note ID |

**Success Response (200 OK):** Paginated list of flashcards (same format as `GET /api/flashcards`).

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 403 | Note does not belong to the current user |
| 404 | Note not found |

---

### 6.4 PUT /api/flashcards/{id}

Update a flashcard's question or answer. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Flashcard ID |

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | Updated question |
| `answer` | string | Updated answer |

**Example Request:**

```json
{
  "question": "What are the components of Multi-Head Attention?",
  "answer": "Query, Key, and Value projections run through multiple parallel attention heads."
}
```

**Success Response (200 OK):** Returns the updated flashcard.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Empty request body |
| 401 | Missing or invalid JWT token |
| 403 | Flashcard does not belong to the current user |
| 404 | Flashcard not found |

---

### 6.5 DELETE /api/flashcards/{id}

Delete a flashcard. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Flashcard ID |

**Success Response (204 No Content):** Empty body.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |
| 403 | Flashcard does not belong to the current user |
| 404 | Flashcard not found |

---

### 6.6 GET /api/flashcards/due

Get flashcards due for review today. **Requires authentication.**

Returns all flashcards where `next_review_at` is in the past.

**Success Response (200 OK):**

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
      "next_review_at": "2026-04-04T15:00:00",
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

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

### 6.7 POST /api/flashcards/{id}/review

Submit a review rating for a flashcard. The SM-2 spaced repetition algorithm updates the card's scheduling parameters. **Requires authentication.**

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Flashcard ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rating` | integer | Yes | Score from 0 to 5 (0 = forgot completely, 5 = perfect recall) |

**SM-2 Rating Scale:**

| Rating | Meaning |
|--------|---------|
| 0 | Complete blackout |
| 1 | Incorrect, but recognised the answer |
| 2 | Incorrect, but the answer seemed easy to recall |
| 3 | Correct with significant difficulty |
| 4 | Correct with some hesitation |
| 5 | Perfect recall |

**Example Request:**

```json
{
  "rating": 4
}
```

**Success Response (200 OK):**

```json
{
  "data": {
    "flashcard_id": 1,
    "rating": 4,
    "updated": {
      "ease_factor": 2.5,
      "interval": 6,
      "repetitions": 2,
      "next_review_at": "2026-04-09T15:00:00"
    },
    "reviewed_at": "2026-04-03T20:00:00"
  }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Rating is not an integer between 0 and 5 |
| 401 | Missing or invalid JWT token |
| 403 | Flashcard does not belong to the current user |
| 404 | Flashcard not found |

---

### 6.8 GET /api/review/stats

Get spaced repetition review statistics. **Requires authentication.**

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Time period: `week` (default), `month`, or `all` |

**Success Response (200 OK):**

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

- `mastered`: Cards with `ease_factor >= 2.5` and `interval >= 21` days.
- `learning`: All other cards (`total_cards - mastered`).

**Error Responses:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid JWT token |

---

## 7. F6: Semantic Search

All search endpoints use ChromaDB for vector similarity search. Relevance scores range from 0 to 1 (higher = more relevant), calculated as `1 - cosine_distance`.

### 7.1 POST /api/search/papers

Semantic search over paper abstracts. **No authentication required.**

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language search query |
| `n_results` | integer | No | Number of results (default 10, max 50) |

**Example Request:**

```json
{
  "query": "transformer attention mechanism optimization",
  "n_results": 10
}
```

**Success Response (200 OK):**

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
      "type": "paper",
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

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing or empty `query` field |

---

### 7.2 POST /api/search/notes

Semantic search over the current user's notes. **Requires authentication.**

Notes are isolated by user — each user can only search their own notes.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language search query |
| `n_results` | integer | No | Number of results (default 5, max 50) |

**Example Request:**

```json
{
  "query": "data augmentation techniques",
  "n_results": 5
}
```

**Success Response (200 OK):**

```json
{
  "data": [
    {
      "id": 3,
      "title": "Data Augmentation Survey Notes",
      "content": "## Summary\n\n- ...",
      "paper_id": "2403.67890",
      "relevance_score": 0.92,
      "type": "note",
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

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing or empty `query` field |
| 401 | Missing or invalid JWT token |

---

### 7.3 POST /api/search/all

Combined semantic search across both papers and notes, merged and sorted by relevance. **Requires authentication.**

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language search query |
| `n_results` | integer | No | Results per source (default 10, max 50) |

**Example Request:**

```json
{
  "query": "attention mechanism improvements",
  "n_results": 10
}
```

**Success Response (200 OK):**

```json
{
  "data": [
    {
      "type": "note",
      "id": 1,
      "title": "Multi-Scale Attention Notes",
      "content": "Proposes a hierarchical attention mechanism...",
      "relevance_score": 0.94,
      "_links": { "self": "/api/notes/1" }
    },
    {
      "type": "paper",
      "arxiv_id": "2403.12345",
      "title": "Efficient Vision Transformers with Multi-Scale Attention",
      "abstract": "We propose a novel multi-scale attention...",
      "relevance_score": 0.89,
      "_links": { "self": "/api/papers/2403.12345" }
    }
  ],
  "query": "attention mechanism improvements",
  "source": "all"
}
```

Results are sorted by `relevance_score` in descending order. The `type` field indicates whether each result is a `paper` or `note`.

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing or empty `query` field |
| 401 | Missing or invalid JWT token |

---

## 8. Endpoint Summary

| Module | Method | Path | Auth |
|--------|--------|------|------|
| **F1** | POST | `/api/auth/register` | No |
| | POST | `/api/auth/login` | No |
| | GET | `/api/users/me` | Yes |
| | PUT | `/api/users/me` | Yes |
| **F2** | GET | `/api/papers/search` | No |
| | GET | `/api/papers/trending` | No |
| | GET | `/api/papers/{arxiv_id}` | Optional |
| **F3** | POST | `/api/papers/{arxiv_id}/save` | Yes |
| | DELETE | `/api/papers/{arxiv_id}/save` | Yes |
| | GET | `/api/library` | Yes |
| | POST | `/api/library/{arxiv_id}/tags` | Yes |
| | DELETE | `/api/library/{arxiv_id}/tags/{tag_name}` | Yes |
| | GET | `/api/tags` | Yes |
| **F4** | POST | `/api/notes` | Yes |
| | GET | `/api/notes` | Yes |
| | GET | `/api/papers/{arxiv_id}/notes` | Yes |
| | GET | `/api/notes/{id}` | Yes |
| | PUT | `/api/notes/{id}` | Yes |
| | DELETE | `/api/notes/{id}` | Yes |
| **F5** | POST | `/api/flashcards` | Yes |
| | GET | `/api/flashcards` | Yes |
| | GET | `/api/notes/{id}/flashcards` | Yes |
| | PUT | `/api/flashcards/{id}` | Yes |
| | DELETE | `/api/flashcards/{id}` | Yes |
| | GET | `/api/flashcards/due` | Yes |
| | POST | `/api/flashcards/{id}/review` | Yes |
| | GET | `/api/review/stats` | Yes |
| **F6** | POST | `/api/search/papers` | No |
| | POST | `/api/search/notes` | Yes |
| | POST | `/api/search/all` | Yes |

**Total: 30 endpoints** (7 public + 1 optional auth + 22 authenticated)
