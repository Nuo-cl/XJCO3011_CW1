# Technology Stack

## Core Architecture
- **RESTful API** - Module mandated architectural style
- **HTTP Protocol** - GET, POST, PUT, DELETE methods
- **JSON** - Response data format
- **Stateless Design** - REST core constraint

## Language & Framework
- **Python 3** + **Flask** - Lightweight, fast development, PythonAnywhere friendly

## Database
- **SQLite** - SQL database, zero-config, portable
- **SQLAlchemy** - ORM for clean database operations

## Authentication
- **JWT** (`flask-jwt-extended`) - User registration, login, token-based access control

## Testing
- **pytest** - Unit and integration tests

## Deployment
- **PythonAnywhere** - Free hosting, coursework recommended

## Advanced Features (for 70+ grade)

### HATEOAS / Hypermedia
- API responses include relevant links to related resources (e.g., `_links` field)
- Aligns with REST Uniform Interface constraint (Lecture Unit 4)

### MCP Server Compatibility
- Expose API as an MCP-compatible server for AI tool integration
- Advanced feature explicitly mentioned in coursework brief

### External Dataset Integration
- Integrate a public dataset to enrich API data (specific dataset TBD with project topic)

### Input Validation
- Request data validation with clear error messages
- Unified error response format across all endpoints

### API Documentation
- **Swagger/OpenAPI** for interactive docs, export to PDF for submission

## To Be Decided

| Item | Notes |
|------|-------|
| Project topic | To be discussed with Architect agent |
| External dataset | Depends on project topic |
| Specific data models | Depends on project topic |
