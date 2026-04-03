"""Tests for F6: RAG semantic search."""


def test_chromadb_service_init():
    """ChromaDB service can be instantiated with ephemeral client."""
    from app.services.chromadb_service import ChromaDBService
    service = ChromaDBService(use_persistent=False)
    assert service.paper_collection is not None
    assert service.notes_collection is not None


def test_search_papers_empty(client):
    """Search papers with no data returns empty list."""
    resp = client.post('/api/search/papers', json={
        'query': 'transformer',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['data'] == []
    assert data['source'] == 'paper_abstracts'


def test_search_papers_missing_query(client):
    resp = client.post('/api/search/papers', json={})
    assert resp.status_code == 400


def test_search_notes_unauthorized(client):
    resp = client.post('/api/search/notes', json={'query': 'test'})
    assert resp.status_code == 401


def test_search_notes_empty(client, auth_headers):
    resp = client.post('/api/search/notes', headers=auth_headers, json={
        'query': 'some query',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['data'] == []
    assert data['source'] == 'user_notes'


def test_search_all_empty(client, auth_headers):
    resp = client.post('/api/search/all', headers=auth_headers, json={
        'query': 'attention mechanism',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['source'] == 'all'
    assert isinstance(data['data'], list)


def test_search_all_unauthorized(client):
    resp = client.post('/api/search/all', json={'query': 'test'})
    assert resp.status_code == 401


def test_search_papers_with_data(client, app, sample_paper):
    """Search papers after adding data to ChromaDB."""
    chromadb = app.extensions.get('chromadb')
    if chromadb:
        chromadb.add_paper(
            paper_id=sample_paper.id,
            abstract=sample_paper.abstract,
            metadata={
                'arxiv_id': sample_paper.arxiv_id,
                'title': sample_paper.title,
                'categories': sample_paper.categories,
                'published_date': sample_paper.published_date.isoformat(),
            },
        )

    resp = client.post('/api/search/papers', json={
        'query': 'transformer architecture',
        'n_results': 5,
    })
    assert resp.status_code == 200
    data = resp.get_json()['data']
    if chromadb:
        assert len(data) >= 1
        assert 'relevance_score' in data[0]
        assert 'arxiv_id' in data[0]
