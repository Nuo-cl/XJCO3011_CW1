# ScholarTrack: Technical Report

**Module:** XJCO3011 Web Services and Web Data  
**Author:** [Student Name]  
**Date:** April 2026  
**Repository:** [GitHub URL]

---

## 1. Introduction

ScholarTrack is a RESTful Web API designed for researchers to discover arXiv papers, manage a personal research library, take structured notes, and reinforce learning through spaced repetition flashcards. The system also provides AI-powered semantic search across papers and notes using Retrieval-Augmented Generation (RAG) techniques, and exposes its functionality to AI assistants via the Model Context Protocol (MCP).

The API comprises 30 endpoints across seven feature modules, supporting the full research workflow from paper discovery to knowledge retention.

---

## 2. Design and Architecture

### 2.1 Overall Architecture

ScholarTrack follows a **layered architecture** with clear separation of concerns:

- **Routes Layer** — Flask Blueprints handling HTTP request/response, input validation, and HATEOAS link generation.
- **Service Layer** — Business logic encapsulated in service classes (ArxivService, ChromaDBService, SM2Service), decoupled from HTTP concerns.
- **Data Layer** — SQLAlchemy ORM models with SQLite for persistent storage, ChromaDB for vector embeddings.

This separation allows the MCP server to reuse the service layer directly without duplicating business logic, and makes each layer independently testable.

### 2.2 Application Factory Pattern

The application uses Flask's **app factory pattern** (`create_app`), which provides several advantages (Pallets Projects, 2010):

- Multiple configurations (development, testing, production) can coexist without code changes.
- The testing suite creates isolated application instances with in-memory databases.
- Circular import issues are avoided by deferring extension initialisation.

### 2.3 RESTful API Design

The API adheres to REST principles (Fielding, 2000):

- **Resource-oriented URLs** — nouns represent resources (e.g., `/api/papers`, `/api/notes`), HTTP methods represent actions.
- **Stateless communication** — each request carries its own authentication token (JWT).
- **HATEOAS** — every response includes `_links` with related resource URIs, enabling clients to navigate the API without hardcoded paths.
- **Consistent error format** — all errors return `{"error": "snake_case_type", "message": "..."}` with appropriate HTTP status codes.

### 2.4 Data Model

The database schema consists of eight tables:

| Model | Purpose |
|-------|---------|
| User | Account credentials and preferences |
| Paper | Cached arXiv paper metadata |
| UserPaper | Many-to-many join for user collections |
| Tag | User-defined labels |
| UserPaperTag | Tag assignments to saved papers |
| Note | Research notes, optionally linked to papers |
| Flashcard | SM-2 spaced repetition cards linked to notes |
| ReviewLog | Flashcard review history |

Key design decisions:

- **Papers are read-only from arXiv** — the system caches paper metadata locally on first access but does not allow user uploads. This keeps the data model clean and avoids content moderation concerns.
- **Tags attach to UserPaper, not Paper** — different users can tag the same paper differently without interference.
- **Notes cascade-delete flashcards** — deleting a note automatically removes its associated flashcards and ChromaDB vectors, maintaining referential integrity.

---

## 3. Technology Stack Justification

### 3.1 Programming Language: Python

Python was chosen for its mature web framework ecosystem, strong library support for scientific computing and machine learning, and the availability of first-party clients for both the arXiv API and ChromaDB (Python Software Foundation, 2024). The arXiv Python client (`arxiv==2.2.0`) and ChromaDB SDK are Python-native, making integration straightforward compared to alternatives like Node.js or Go, which would require custom HTTP wrappers.

### 3.2 Framework: Flask

Flask was selected over Django and FastAPI for the following reasons:

- **Minimalism** — Flask provides routing, request handling, and extension hooks without imposing an ORM, admin panel, or template engine (Pallets Projects, 2010). This allows precise control over each architectural layer.
- **Extension ecosystem** — flask-jwt-extended, Flask-SQLAlchemy, Flask-CORS, and Flasgger integrate cleanly without conflicts.
- **Learning curve** — Flask's explicit wiring (blueprints, app factory) makes the application structure transparent, which is valuable for demonstrating architectural understanding in a coursework context.

Django was considered but rejected due to its monolithic design — its built-in ORM, admin, and authentication system add unnecessary complexity for a pure API project. FastAPI was considered for its automatic OpenAPI generation, but Flasgger provides equivalent functionality for Flask, and Flask's maturity ensures broader community support for troubleshooting.

### 3.3 Database: SQLite + SQLAlchemy

SQLite was chosen as the relational database because:

- **Zero configuration** — no separate database server to install or manage, ideal for local development and coursework deployment.
- **File-based portability** — the entire database is a single file, simplifying backup and transfer.
- **Sufficient for the use case** — ScholarTrack is a single-user or low-concurrency application where SQLite's write-locking is not a bottleneck.

SQLAlchemy 2.0 provides the ORM layer, offering type-safe queries, relationship management, and database-agnostic migration support should the project scale to PostgreSQL in future (Bayer, 2012).

### 3.4 Vector Search: ChromaDB

ChromaDB was selected for RAG semantic search over paper abstracts and user notes:

- **Built-in embeddings** — ChromaDB uses the `all-MiniLM-L6-v2` sentence transformer model by default, eliminating the need for external model deployment or API calls (Chroma, 2024).
- **Dual storage modes** — `PersistentClient` for production (data survives restarts) and `EphemeralClient` for testing (in-memory, no file locks).
- **Cosine distance** — configured for cosine similarity, which is standard for semantic text similarity tasks.

Alternatives considered:
- **FAISS** — lower-level, requires manual embedding generation and lacks built-in metadata filtering.
- **Pinecone/Weaviate** — cloud-hosted, adding external dependencies and costs inappropriate for a coursework project.

### 3.5 Authentication: JWT

JSON Web Tokens via flask-jwt-extended provide stateless authentication (Jones, Bradley and Sakimura, 2015):

- Tokens expire after 24 hours, balancing security with user convenience.
- The server does not need to maintain session state, aligning with REST's stateless constraint.
- Token-based auth integrates cleanly with both browser clients and the MCP server.

---

## 4. Core Feature Implementation

### 4.1 arXiv Integration (F2)

The ArxivService wraps the `arxiv` Python client to search and retrieve papers. Results are cached in the local SQLite database on first access, with the arXiv ID as the deduplication key (version suffixes like `v1`, `v2` are stripped). Paper abstracts are simultaneously indexed in ChromaDB for semantic search.

The query builder (`_build_query`) constructs arXiv API queries by combining category filters, keyword terms, and date ranges into a single query string. Date constraints are embedded directly using arXiv's `submittedDate` field (e.g., `submittedDate:[202604020000 TO 202604042359]`), ensuring the API server handles filtering rather than fetching excess results and filtering locally. This approach was adopted after discovering that wildcard queries (`all:*`) combined with category-only filters caused intermittent HTTP 500 errors from the arXiv API.

### 4.2 Spaced Repetition — SM-2 Algorithm (F5)

The SM2Service implements the SuperMemo 2 algorithm (Wozniak, 1990):

- **Rating >= 3** (correct recall): increment repetitions, calculate new interval (`interval * ease_factor`), adjust ease factor.
- **Rating < 3** (incorrect): reset repetitions to 0 and interval to 1.
- **Ease factor minimum**: clamped at 1.3 to prevent intervals from shrinking too aggressively.

The review statistics endpoint provides daily breakdowns and mastery metrics (cards with `ease_factor >= 2.5` and `interval >= 21` days are considered "mastered").

### 4.3 RAG Semantic Search (F6)

The search system operates across two ChromaDB collections:

- `paper_abstracts` — indexed when papers are first fetched from arXiv.
- `user_notes` — indexed when notes are created or updated, with `user_id` metadata for access isolation.

The `/api/search/all` endpoint merges results from both collections, sorted by relevance score (`1 - cosine_distance`), enabling researchers to find connections between their notes and the broader literature.

### 4.4 MCP Server (F7)

The MCP server uses the FastMCP SDK to expose nine tools that AI assistants (e.g., Claude) can invoke directly. It bootstraps a Flask application context and calls the service layer, bypassing HTTP routing. This design avoids the overhead of HTTP round-trips and ensures consistency with the web API's business logic.

---

## 5. Testing

### 5.1 Approach

The test suite uses **pytest** with the following strategy:

- **Unit tests** — SM-2 algorithm logic tested with mock flashcard objects, isolated from the database.
- **Integration tests** — API endpoints tested via Flask's test client with an in-memory SQLite database and ephemeral ChromaDB instance.
- **Fixture-based setup** — `conftest.py` provides reusable fixtures (app, client, authenticated headers, sample data) to reduce test duplication.

### 5.2 Coverage

| Component | Coverage |
|-----------|----------|
| Models | 95-100% |
| Routes | 75-91% |
| Services | 41-95% |
| **Overall** | **81%** |

The 66 tests cover all critical paths: authentication flows, CRUD operations, access control (403 for cross-user access), input validation (400 for missing fields), conflict handling (409 for duplicates), and the SM-2 algorithm's mathematical correctness.

The lower coverage in `arxiv_service.py` (41%) reflects the difficulty of testing external API calls without network access; the service is tested indirectly through the paper endpoints using pre-cached data.

---

## 6. Challenges and Solutions

### 6.1 ChromaDB File Locking on Windows

**Problem:** ChromaDB's `PersistentClient` holds a file lock on `chroma.sqlite3`, causing `PermissionError` during test teardown on Windows.

**Solution:** Configured the testing environment to use `EphemeralClient` (in-memory mode) via a `CHROMADB_PERSIST=False` flag, eliminating file system dependencies in tests entirely.

### 6.2 JWT Identity Type Mismatch

**Problem:** The login endpoint stored the user ID as a string (`identity=str(user.id)`), but test fixtures created tokens with integer identities, causing 401 errors in tests.

**Solution:** Standardised the test fixture to obtain tokens via the actual login endpoint rather than manually creating them, ensuring the token format matches production behaviour exactly.

### 6.3 arXiv API Rate Limiting

**Problem:** The arXiv API has strict rate limits (approximately 1 request per 3 seconds), which can cause timeouts during rapid development and testing.

**Solution:** Implemented a local caching strategy — papers are stored in SQLite on first fetch and served from cache on subsequent requests. The `fetch_by_id` method checks the local database before making an API call, reducing external dependencies.

### 6.4 arXiv Trending Query Instability

**Problem:** The initial implementation of the trending papers feature used a wildcard query (`all:*`) with a category filter, relying on post-fetch Python-side date filtering. This caused intermittent HTTP 500 errors from the arXiv API, as the server struggled to process unbounded wildcard queries.

**Solution:** Refactored the query builder to embed date constraints directly into the arXiv API query using the `submittedDate` field range syntax, and removed the wildcard term entirely. The trending endpoint now sends a precise, bounded query (e.g., `cat:cs.AI AND submittedDate:[202604020000 TO 202604042359]`), which the arXiv API handles reliably.

---

## 7. Limitations

- **Single-user focus** — while the API supports multiple user accounts, it has not been stress-tested for concurrent write operations, which could expose SQLite's single-writer limitation.
- **No paper content indexing** — only abstracts are indexed in ChromaDB; full-text PDF content is not processed due to the complexity of PDF extraction and the associated computational cost.
- **Embedding model fixed** — ChromaDB's default `all-MiniLM-L6-v2` model is lightweight but may underperform on domain-specific scientific vocabulary compared to specialised models like SciBERT.
- **No real-time sync** — paper metadata cached locally may become stale if arXiv updates the record (e.g., new versions).

---

## 8. Future Improvements

- **PostgreSQL migration** — replace SQLite with PostgreSQL for concurrent access support and production deployment.
- **Full-text PDF indexing** — extract and index paper content using tools like PyMuPDF, significantly improving search quality.
- **Domain-specific embeddings** — fine-tune or swap the embedding model to a science-focused model (e.g., SPECTER2) for better semantic understanding of academic text.
- **Collaborative features** — shared reading lists, annotation sharing, and group study sessions.
- **Deployment** — containerise with Docker and deploy to a cloud platform (e.g., PythonAnywhere, Railway) with CI/CD pipelines.

---

## 9. GenAI Declaration

This project was developed with the assistance of **Claude Code** (Anthropic, 2025), an AI-powered coding assistant. Claude Code was used for:

- **Architecture planning** — brainstorming feature decomposition and endpoint design.
- **Code implementation** — generating route handlers, service classes, and database models following the planned specifications.
- **Test writing** — creating pytest test suites for each feature module.
- **Documentation** — generating API docstrings, README, and this technical report draft.
- **Debugging** — diagnosing issues such as the ChromaDB file lock problem and JWT identity type mismatch.

The development workflow used Claude Code's agent team feature, with a team lead coordinating developer and reviewer agents. Sample conversation logs are provided in Appendix A.

All AI-generated code was reviewed, tested, and validated before inclusion. The architectural decisions and technology choices reflect the author's understanding and judgement, informed by AI suggestions.

---

## References

Anthropic (2025) *Claude Code*. Available at: https://claude.ai/code (Accessed: 3 April 2026).

Bayer, M. (2012) *SQLAlchemy*. Available at: https://www.sqlalchemy.org/ (Accessed: 3 April 2026).

Chroma (2024) *ChromaDB: The AI-native open-source embedding database*. Available at: https://www.trychroma.com/ (Accessed: 3 April 2026).

Fielding, R.T. (2000) *Architectural styles and the design of network-based software architectures*. PhD thesis. University of California, Irvine.

Jones, M., Bradley, J. and Sakimura, N. (2015) 'JSON Web Token (JWT)', *RFC 7519*. Internet Engineering Task Force. Available at: https://datatracker.ietf.org/doc/html/rfc7519 (Accessed: 3 April 2026).

Pallets Projects (2010) *Flask: A Python Microframework*. Available at: https://flask.palletsprojects.com/ (Accessed: 3 April 2026).

Python Software Foundation (2024) *Python 3.11 Documentation*. Available at: https://docs.python.org/3.11/ (Accessed: 3 April 2026).

Wozniak, P.A. (1990) *Optimization of repetition spacing in the practice of learning*. Master's thesis. University of Technology in Poznan.
