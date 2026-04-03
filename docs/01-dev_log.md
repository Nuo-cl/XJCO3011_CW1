# Development Log

## 2026-04-03

### Project Setup
- Created GitHub repository: [XJCO3011_CW1](https://github.com/Nuo-cl/XJCO3011_CW1)
- Organized coursework PDF brief into `docs/coursework1_requirements.md`
- Set up Claude Code agent team (Architect, Developer, Reviewer)

### Technology Analysis
- Analyzed lecture slides (Unit 1-4) and coursework requirements
- Confirmed core tech stack: Python Flask + SQLite + SQLAlchemy + pytest
- Confirmed JWT for authentication, PythonAnywhere for deployment
- Identified advanced features for 70+ grade: HATEOAS, MCP Server, external dataset, input validation, Swagger docs
- Created `docs/tech_stack.md`

### Topic Selection
- Brainstormed with Architect agent (2 rounds: general topics → interactive/functional redesign)
- Confirmed topic: **ScholarTrack** — arXiv paper tracking & research notes platform
- Key design decisions:
  - No frontend/terminal UI — API-first, Swagger UI for testing, MCP for workflow demo
  - Local deployment + MCP preferred over PythonAnywhere
  - Single data source (arXiv API only), public paper pool with user-level collections
  - SQLite for core CRUD + ChromaDB for RAG semantic search

### Documentation
- Numbered all docs (00-07 series) for development workflow ordering
- Created `02-project_brief.md` with full project scope, architecture, and demo strategy
- Updated `03-tech_stack.md` with confirmed advanced features (JWT, HATEOAS, MCP, RAG)

### Documentation Completed
- `04-feature_spec.md` — 7 functional modules (F1-F7), 30 endpoints, 5 global requirements
- `05-data_models.md` — 8 SQLite models + 2 ChromaDB collections, with SQLAlchemy code
- `06-api_spec.md` — Full API spec with request/response examples for all 30 endpoints
- `07-dev_plan.md` — 5-phase plan (Apr 4 - Apr 28), milestones, risks, demo strategy

### Design Decisions
- Embedding: ChromaDB default (all-MiniLM-L6-v2), no separate model deployment needed
- No frontend/terminal UI: Swagger UI for testing, MCP for workflow demo
- Local deployment + MCP preferred; PythonAnywhere optional

### Pending
- Begin Phase 1: Project scaffolding
