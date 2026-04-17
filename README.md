<p align="center">
  <img src="resources/logo.png" alt="ScholarTrack Logo" width="180" />
</p>

<h1 align="center">ScholarTrack</h1>

<p align="center">
  A RESTful Web API for researchers to discover and track arXiv papers, record insights, and get personalized recommendations.<br/>
  Built with Flask for the XJCO3011 Web Services and Web Data coursework.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/flask-3.1.1-lightgrey?logo=flask" alt="Flask 3.1.1" />
  <img src="https://img.shields.io/badge/tests-60%20passed-brightgreen" alt="Tests" />
  <img src="https://img.shields.io/badge/coverage-80%25-green" alt="Coverage" />
</p>

## Features

### Authentication (F1)
Register an account, log in with JWT tokens, and manage your researcher profile including preferred arXiv categories (e.g., `cs.AI`, `cs.CV`). Preferred categories drive the recommendation engine.

### Paper Discovery (F2)
Search arXiv papers by keyword, category, and date range. Browse trending papers in any arXiv category, or use the **discover** endpoint for serendipitous browsing — random papers from a chosen field to spark new research directions.

### Paper Management (F3)
Save interesting papers to your personal library with optional memos. Organize them using **user-scoped tags** — each user can tag the same paper differently. Filter your library by tag, and manage tags independently.

### Insight Notes (F4)
Record short insight annotations (max 1000 characters) linked to specific papers. Notes capture key takeaways, critiques, or ideas as you read. Each paper can have multiple notes, and notes are searchable via semantic search.

### Personalized Recommendations (F5)
Get daily paper recommendations tailored to your interests. New users receive **trending papers** from preferred categories (cold start). As you save papers, the engine switches to a **hybrid model**: 70% semantic similarity to your library + 30% fresh papers from active categories, with already-saved papers excluded.

### RAG Semantic Search (F6)
Search across paper abstracts and your personal notes using natural language queries. The system uses **ChromaDB** with all-MiniLM-L6-v2 embeddings for vector similarity. Search papers globally, search notes privately (user-isolated), or search both simultaneously with merged relevance ranking.

### MCP Server (F7)
Integrate ScholarTrack with AI assistants (e.g., Claude) via the **Model Context Protocol**. The MCP server exposes 11 tools that let AI assistants search papers, manage your library, create notes, and get recommendations — all through natural conversation.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Flask 3.1.1 |
| Database | SQLite + SQLAlchemy 2.0 |
| Authentication | JWT (flask-jwt-extended) |
| Rate Limiting | Flask-Limiter |
| Vector Search | ChromaDB 1.0.7 |
| External API | arXiv Python client |
| API Documentation | Flasgger (Swagger/OpenAPI) |
| Testing | pytest + pytest-cov |

## Quick Start

### Prerequisites

- Python 3.11+
- Conda (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/Nuo-cl/ScholarTrack.git
cd ScholarTrack

# Create conda environment
conda create -n scholartrack python=3.11
conda activate scholartrack

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
pytest                        # Run all tests
pytest --cov=app tests/       # Run with coverage report
pytest tests/test_auth.py -v  # Run a specific test module
```

## MCP Server

ScholarTrack includes an MCP (Model Context Protocol) server that exposes core functionality as tools for AI assistants such as Claude. The MCP server calls the service layer directly (not via HTTP), so the Flask web server does not need to be running.

### Available Tools

| Tool | Description |
|------|-------------|
| `register_user` | Register a new account and switch to it |
| `update_profile` | Update preferred categories or email |
| `search_papers` | Search arXiv by keyword, category, and time range |
| `get_trending_papers` | Get recent trending papers in an arXiv category |
| `get_daily_recommendations` | Personalized daily paper recommendations |
| `discover_papers` | Random paper discovery for serendipitous browsing |
| `save_paper` | Save a paper to the user's library |
| `list_library` | List all saved papers |
| `create_note` | Record a short insight note linked to a paper |
| `search_notes` | Semantic search across personal notes |
| `search_knowledge` | Search across both papers and notes |

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

After restarting Claude Code, the AI assistant can directly invoke tools like `search_papers`, `get_daily_recommendations`, etc.

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

## REST API

All endpoints are under the `/api` prefix. Authenticated endpoints require a JWT bearer token:

```
Authorization: Bearer <access_token>
```

### Endpoint Summary

| Module | Key Endpoints | Auth |
|--------|--------------|------|
| Authentication (F1) | `POST /auth/register`, `POST /auth/login`, `GET /users/me`, `PUT /users/me` | Partial |
| Paper Discovery (F2) | `GET /papers/search`, `GET /papers/trending`, `GET /papers/discover`, `GET /papers/<id>` | No |
| Paper Management (F3) | `POST /papers/<id>/save`, `GET /library`, `POST /library/<id>/tags` | Yes |
| Notes (F4) | `POST /notes`, `GET /notes`, `GET /papers/<id>/notes`, `PUT /notes/<id>` | Yes |
| Recommendations (F5) | `GET /recommendations/daily` | Yes |
| Semantic Search (F6) | `POST /search/papers`, `POST /search/notes`, `POST /search/all` | Partial |

Interactive Swagger UI with full request/response examples is at `/apidocs` when the server is running. Detailed API documentation is available in [`docs/api_documentation.pdf`](docs/api_documentation.pdf).

### Quick Example

```bash
# Register and login
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "researcher1", "email": "r1@example.com", "password": "securepass123"}'

curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "researcher1", "password": "securepass123"}'
# -> returns { "data": { "access_token": "eyJ..." } }

# Search papers (no auth required)
curl "http://localhost:5000/api/papers/search?q=vision+transformer&category=cs.CV"

# Get daily recommendations (auth required)
curl http://localhost:5000/api/recommendations/daily \
  -H "Authorization: Bearer <token>"
```

## Project Structure

```
app/
├── __init__.py          # Flask app factory
├── config.py            # Configuration (dev/test/prod)
├── models/              # SQLAlchemy models (6 tables)
├── routes/              # API endpoints (5 Blueprint modules)
├── services/            # Business logic (arXiv, ChromaDB, recommendations)
└── utils/               # Error handling, validation
tests/                   # pytest test suite
docs/                    # Design specs and API documentation
mcp_server.py            # MCP server for AI assistants
```

## License

This project is coursework for XJCO3011 at the University of Leeds.
