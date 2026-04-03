# ScholarTrack

A RESTful Web API for researchers to track arXiv papers, manage research notes, and use spaced repetition learning. Built with Flask for the XJCO3011 Web Services and Web Data coursework.

## Features

- **Paper Discovery (F2)** — Search and browse arXiv papers with category filtering
- **Paper Management (F3)** — Save papers to a personal library with tags and memos
- **Research Notes (F4)** — Full CRUD note-taking linked to papers, with Markdown support
- **Flashcards & SM-2 (F5)** — Spaced repetition flashcards using the SM-2 algorithm
- **RAG Semantic Search (F6)** — Vector search over paper abstracts and notes via ChromaDB
- **MCP Server (F7)** — AI assistant integration through the Model Context Protocol

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Flask 3.1.1 |
| Database | SQLite + SQLAlchemy 2.0 |
| Authentication | JWT (flask-jwt-extended) |
| Vector Search | ChromaDB 1.0.7 |
| External API | arXiv Python client |
| API Documentation | Flasgger (Swagger/OpenAPI) |
| Testing | pytest + pytest-cov |

## Quick Start

### Prerequisites

- Python 3.11+
- pip or conda

### Installation

```bash
# Clone the repository
git clone https://github.com/Nuo-cl/ScholarTrack.git
cd ScholarTrack

# Create and activate a virtual environment (or use conda)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
python run.py
```

The API server starts at `http://localhost:5000`. Swagger UI is available at `http://localhost:5000/apidocs`.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app tests/

# Run a specific test module
pytest tests/test_auth.py -v
```

## API Overview

**30 endpoints** across 7 feature modules. Base URL: `/api`

| Module | Endpoints | Auth Required |
|--------|-----------|---------------|
| Authentication (F1) | 4 | Partial |
| Paper Discovery (F2) | 3 | No |
| Paper Management (F3) | 6 | Yes |
| Notes (F4) | 6 | Yes |
| Flashcards (F5) | 5 | Yes |
| Spaced Repetition (F5) | 3 | Yes |
| Semantic Search (F6) | 3 | Partial |

Full API documentation is available in [`docs/api_documentation.pdf`](docs/api_documentation.pdf).
Interactive Swagger UI is at `/apidocs` when the server is running.

### Authentication

All authenticated endpoints require a JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens expire after 24 hours.

### Common API Usage Examples

**Register a new account:**

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "researcher1", "email": "researcher1@example.com", "password": "securepass123"}'
```

**Login and obtain a token:**

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "researcher1", "password": "securepass123"}'
```

Response:

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**Search arXiv papers (no auth required):**

```bash
curl "http://localhost:5000/api/papers/search?q=vision+transformer&category=cs.CV"
```

**Save a paper to your library:**

```bash
curl -X POST http://localhost:5000/api/papers/2403.12345/save \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"memo": "Interesting attention approach"}'
```

**Create a research note linked to a paper:**

```bash
curl -X POST http://localhost:5000/api/notes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "2403.12345", "title": "Key Ideas", "content": "## Summary\n\nNovel multi-scale attention mechanism..."}'
```

**Create a flashcard from a note:**

```bash
curl -X POST http://localhost:5000/api/flashcards \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"note_id": 1, "question": "What is Multi-Head Attention?", "answer": "A mechanism that runs multiple attention functions in parallel."}'
```

**Review a flashcard (SM-2 spaced repetition):**

```bash
curl -X POST http://localhost:5000/api/flashcards/1/review \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"rating": 4}'
```

Rating scale: 0 (forgot completely) to 5 (perfect recall). The SM-2 algorithm adjusts the review interval accordingly.

**Semantic search across papers and notes:**

```bash
curl -X POST http://localhost:5000/api/search/all \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "attention mechanism improvements", "n_results": 10}'
```

For the complete list of all 30 endpoints with request/response examples, see the [API Documentation](docs/api_documentation.pdf).

## MCP Server

ScholarTrack includes an MCP (Model Context Protocol) server that exposes core functionality as tools for AI assistants such as Claude. The MCP server calls the service layer directly (not via HTTP), so the Flask web server does not need to be running.

### Available Tools

| Tool | Description |
|------|-------------|
| `search_papers` | Search arXiv for papers by keyword and optional category |
| `get_trending_papers` | Get recent trending papers in an arXiv category |
| `save_paper` | Save a paper to the user's personal library |
| `list_library` | List all papers in the user's library |
| `create_note` | Create a research note, optionally linked to a paper |
| `search_notes` | Semantic search across personal research notes |
| `search_knowledge` | Search across both papers and notes |
| `get_due_flashcards` | Get flashcards due for review today |
| `review_flashcard` | Submit a review rating for a flashcard (SM-2) |

### Running Standalone

```bash
python mcp_server.py [--user-id USER_ID]
```

The `--user-id` flag specifies which user's data to operate on (default: 1). The MCP server bypasses JWT authentication and accesses the database directly.

### Configuring with Claude Code

Create a `.mcp.json` file in the project root:

```json
{
  "mcpServers": {
    "scholartrack": {
      "command": "python",
      "args": ["mcp_server.py", "--user-id", "1"],
      "cwd": "/path/to/ScholarTrack"
    }
  }
}
```

After restarting Claude Code, the AI assistant can directly invoke tools like `search_papers`, `save_paper`, `create_note`, etc. For example, you can ask Claude to "search for recent papers on vision transformers" and it will call the `search_papers` tool automatically.

### Configuring with Claude Desktop

Add the following to your Claude Desktop MCP settings (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "scholartrack": {
      "command": "python",
      "args": ["mcp_server.py", "--user-id", "1"],
      "cwd": "/path/to/ScholarTrack"
    }
  }
}
```

## Project Structure

```
app/
├── __init__.py          # Flask app factory
├── config.py            # Configuration (dev/test/prod)
├── models/              # SQLAlchemy models (8 tables)
├── routes/              # API endpoints (5 Blueprint modules)
├── services/            # Business logic (arXiv, ChromaDB, SM-2)
└── utils/               # Error handling, pagination, validation
tests/                   # pytest test suite (66 tests)
docs/                    # Design specs and API documentation
mcp_server.py            # MCP server for AI assistants
```

## License

This project is coursework for XJCO3011 at the University of Leeds.
