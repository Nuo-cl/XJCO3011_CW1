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

### MCP Prompt Examples

Below are example natural language prompts you can use with AI assistants (Claude Code, Claude Desktop) after connecting the MCP server. Each prompt maps to one or more MCP tools.

#### Account & Profile

| Prompt | Tool(s) Called |
|--------|---------------|
| "Register a new account with username alice, email alice@example.com, password test123456" | `register_user` |
| "Set my preferred arXiv categories to cs.AI, cs.CV, and cs.CL" | `update_profile` |
| "Change my email to newemail@example.com" | `update_profile` |

#### Paper Discovery

| Prompt | Tool(s) Called |
|--------|---------------|
| "Search for recent papers about vision transformers in the cs.CV category" | `search_papers` |
| "Find papers about large language models from the last 60 days" | `search_papers` |
| "What are the trending papers in cs.AI this week?" | `get_trending_papers` |
| "Show me some random papers in cs.CL for inspiration" | `discover_papers` |

#### Library Management

| Prompt | Tool(s) Called |
|--------|---------------|
| "Save paper 2403.12345 to my library with a note: great attention mechanism" | `save_paper` |
| "Show me all the papers in my library" | `list_library` |

#### Notes & Insights

| Prompt | Tool(s) Called |
|--------|---------------|
| "Create a note for paper 2403.12345: The pruning method reduces 40% parameters with only 1% accuracy drop" | `create_note` |
| "Search my notes for anything related to data augmentation" | `search_notes` |

#### Recommendations

| Prompt | Tool(s) Called |
|--------|---------------|
| "Give me today's paper recommendations" | `get_daily_recommendations` |
| "I'm a new user interested in NLP, what papers should I read?" | `update_profile` + `get_daily_recommendations` |

#### Knowledge Search

| Prompt | Tool(s) Called |
|--------|---------------|
| "Search across my papers and notes for anything about attention mechanisms" | `search_knowledge` |
| "What do I know about retrieval-augmented generation?" | `search_knowledge` |

#### Multi-step Workflow Example

A typical research workflow with the MCP server:

```
User: I just started using ScholarTrack. I'm interested in computer vision and NLP.

AI: I'll set up your profile first.
    → calls update_profile(preferred_categories="cs.CV,cs.CL")

User: What papers should I read today?

AI: Let me get your daily recommendations.
    → calls get_daily_recommendations()
    → returns cold_start results based on cs.CV and cs.CL

User: Paper 2604.05678 looks interesting, save it!

AI: Saving it to your library.
    → calls save_paper(arxiv_id="2604.05678")

User: I just read it — the key insight is they use a hierarchical attention mechanism
      that captures both local and global features efficiently.

AI: I'll record that as a note.
    → calls create_note(arxiv_id="2604.05678", content="...")

User: Now get me recommendations again.

AI: → calls get_daily_recommendations()
    → returns warm_start results (70% similarity-based + 30% fresh)
```

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

| Module | Method | Path | Auth |
|--------|--------|------|------|
| **F1: Auth** | POST | `/api/auth/register` | No |
| | POST | `/api/auth/login` | No |
| | GET | `/api/users/me` | Yes |
| | PUT | `/api/users/me` | Yes |
| **F2: Discovery** | GET | `/api/papers/search` | No |
| | GET | `/api/papers/trending` | No |
| | GET | `/api/papers/{arxiv_id}` | Optional |
| | GET | `/api/papers/discover` | No |
| **F3: Library** | POST | `/api/papers/{arxiv_id}/save` | Yes |
| | DELETE | `/api/papers/{arxiv_id}/save` | Yes |
| | GET | `/api/library` | Yes |
| | POST | `/api/library/{arxiv_id}/tags` | Yes |
| | DELETE | `/api/library/{arxiv_id}/tags/{tag_name}` | Yes |
| | GET | `/api/tags` | Yes |
| **F4: Notes** | POST | `/api/notes` | Yes |
| | GET | `/api/notes` | Yes |
| | GET | `/api/papers/{arxiv_id}/notes` | Yes |
| | GET | `/api/notes/{id}` | Yes |
| | PUT | `/api/notes/{id}` | Yes |
| | DELETE | `/api/notes/{id}` | Yes |
| **F5: Recommend** | GET | `/api/recommendations/daily` | Yes |
| **F6: Search** | POST | `/api/search/papers` | No |
| | POST | `/api/search/notes` | Yes |
| | POST | `/api/search/all` | Yes |

**Total: 24 endpoints** (7 public + 1 optional auth + 16 authenticated)

Interactive Swagger UI with full request/response examples is at `/apidocs` when the server is running. Detailed API documentation is available in [`docs/api_documentation.pdf`](docs/api_documentation.pdf).

### API Usage Examples (curl)

> **Windows note:** The examples below use PowerShell-compatible syntax. If using CMD, replace `\` line continuations with `^`. On Git Bash or WSL, the examples work as-is.

#### F1: Authentication

```bash
# Register a new account
curl -X POST http://localhost:5000/api/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"researcher1\", \"email\": \"r1@example.com\", \"password\": \"securepass123\"}"

# Login and get JWT token
curl -X POST http://localhost:5000/api/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"researcher1\", \"password\": \"securepass123\"}"
# -> returns { "data": { "access_token": "eyJhbGciOi..." } }

# View my profile (requires token)
curl http://localhost:5000/api/users/me ^
  -H "Authorization: Bearer <token>"

# Update profile — set preferred categories and email
curl -X PUT http://localhost:5000/api/users/me ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"preferred_categories\": [\"cs.AI\", \"cs.CV\", \"cs.CL\"], \"email\": \"new@example.com\"}"
```

#### F2: Paper Discovery

```bash
# Search papers by keyword (no auth required)
curl "http://localhost:5000/api/papers/search?q=vision+transformer&category=cs.CV&page=1"

# Search with date range
curl "http://localhost:5000/api/papers/search?q=LLM&date_from=2026-01-01&date_to=2026-04-01"

# Get trending papers in a category
curl "http://localhost:5000/api/papers/trending?category=cs.AI&days=7"

# Get a single paper by arXiv ID
curl http://localhost:5000/api/papers/2403.12345

# Discover random papers for serendipitous browsing (no auth required)
curl "http://localhost:5000/api/papers/discover?category=cs.CL&days=14&count=5"
```

#### F3: Paper Management

```bash
# Save a paper to your library (with optional memo)
curl -X POST http://localhost:5000/api/papers/2403.12345/save ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"memo\": \"Interesting multi-scale attention approach, read later\"}"

# List your saved papers (with optional tag filter)
curl "http://localhost:5000/api/library?tag=attention&page=1" ^
  -H "Authorization: Bearer <token>"

# Add tags to a saved paper
curl -X POST http://localhost:5000/api/library/2403.12345/tags ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"tags\": [\"attention\", \"to read\"]}"

# Remove a tag from a paper
curl -X DELETE http://localhost:5000/api/library/2403.12345/tags/attention ^
  -H "Authorization: Bearer <token>"

# List all your tags with usage counts
curl http://localhost:5000/api/tags ^
  -H "Authorization: Bearer <token>"

# Remove a paper from your library
curl -X DELETE http://localhost:5000/api/papers/2403.12345/save ^
  -H "Authorization: Bearer <token>"
```

#### F4: Insight Notes

```bash
# Create a note linked to a paper
curl -X POST http://localhost:5000/api/notes ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"paper_id\": \"2403.12345\", \"content\": \"Multi-head attention can be pruned without significant performance loss.\"}"

# List all your notes (with optional paper filter)
curl "http://localhost:5000/api/notes?paper_id=2403.12345" ^
  -H "Authorization: Bearer <token>"

# Get notes for a specific paper
curl http://localhost:5000/api/papers/2403.12345/notes ^
  -H "Authorization: Bearer <token>"

# Get a single note by ID
curl http://localhost:5000/api/notes/1 ^
  -H "Authorization: Bearer <token>"

# Update a note
curl -X PUT http://localhost:5000/api/notes/1 ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"content\": \"Updated findings after reading the supplementary material.\"}"

# Delete a note
curl -X DELETE http://localhost:5000/api/notes/1 ^
  -H "Authorization: Bearer <token>"
```

#### F5: Personalized Recommendations

```bash
# Get daily recommendations (cold_start or warm_start based on library size)
curl http://localhost:5000/api/recommendations/daily ^
  -H "Authorization: Bearer <token>"
```

#### F6: Semantic Search (RAG)

```bash
# Search paper abstracts by natural language (no auth required)
curl -X POST http://localhost:5000/api/search/papers ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"transformer attention mechanism optimization\", \"n_results\": 10}"

# Search your personal notes (requires auth)
curl -X POST http://localhost:5000/api/search/notes ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"query\": \"data augmentation techniques\", \"n_results\": 5}"

# Search across both papers and notes (requires auth)
curl -X POST http://localhost:5000/api/search/all ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <token>" ^
  -d "{\"query\": \"attention mechanism improvements\", \"n_results\": 10}"
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
