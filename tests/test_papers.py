"""Tests for F2 (paper discovery) and F3 (paper management) endpoints.

arXiv API calls are tested via pre-cached papers in the DB to avoid
external network dependency. Integration with real arXiv is optional.
"""
import json


def test_get_paper_cached(client, sample_paper):
    """GET /api/papers/{arxiv_id} returns cached paper."""
    resp = client.get(f'/api/papers/{sample_paper.arxiv_id}')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['arxiv_id'] == sample_paper.arxiv_id
    assert '_links' in data


def test_get_paper_not_found(client):
    resp = client.get('/api/papers/9999.99999')
    assert resp.status_code == 404


def test_search_missing_query(client):
    resp = client.get('/api/papers/search')
    assert resp.status_code == 400


def test_trending_missing_category(client):
    resp = client.get('/api/papers/trending')
    assert resp.status_code == 400


# --- F3: Paper Management ---

def test_save_paper(client, auth_headers, sample_paper):
    resp = client.post(
        f'/api/papers/{sample_paper.arxiv_id}/save',
        headers=auth_headers,
        json={'memo': 'Read later'},
    )
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['arxiv_id'] == sample_paper.arxiv_id
    assert data['memo'] == 'Read later'
    assert data['tags'] == []


def test_save_paper_duplicate(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    resp = client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    assert resp.status_code == 409


def test_unsave_paper(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    resp = client.delete(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    assert resp.status_code == 204


def test_unsave_paper_not_saved(client, auth_headers, sample_paper):
    resp = client.delete(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    assert resp.status_code == 404


def test_get_library(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    resp = client.get('/api/library', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['data']) == 1
    assert data['data'][0]['arxiv_id'] == sample_paper.arxiv_id
    assert 'pagination' in data


def test_library_empty(client, auth_headers):
    resp = client.get('/api/library', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 0


def test_add_tags(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    resp = client.post(
        f'/api/library/{sample_paper.arxiv_id}/tags',
        headers=auth_headers,
        json={'tags': ['attention', 'important']},
    )
    assert resp.status_code == 200
    tags = resp.get_json()['data']['tags']
    assert 'attention' in tags
    assert 'important' in tags


def test_add_tags_not_saved(client, auth_headers, sample_paper):
    resp = client.post(
        f'/api/library/{sample_paper.arxiv_id}/tags',
        headers=auth_headers,
        json={'tags': ['x']},
    )
    assert resp.status_code == 404


def test_remove_tag(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    client.post(
        f'/api/library/{sample_paper.arxiv_id}/tags',
        headers=auth_headers,
        json={'tags': ['remove-me']},
    )
    resp = client.delete(
        f'/api/library/{sample_paper.arxiv_id}/tags/remove-me',
        headers=auth_headers,
    )
    assert resp.status_code == 204


def test_remove_tag_not_found(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    resp = client.delete(
        f'/api/library/{sample_paper.arxiv_id}/tags/nonexistent',
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_get_tags(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    client.post(
        f'/api/library/{sample_paper.arxiv_id}/tags',
        headers=auth_headers,
        json={'tags': ['tag1', 'tag2']},
    )
    resp = client.get('/api/tags', headers=auth_headers)
    assert resp.status_code == 200
    names = [t['name'] for t in resp.get_json()['data']]
    assert 'tag1' in names
    assert 'tag2' in names


def test_library_filter_by_tag(client, auth_headers, sample_paper):
    client.post(f'/api/papers/{sample_paper.arxiv_id}/save', headers=auth_headers)
    client.post(
        f'/api/library/{sample_paper.arxiv_id}/tags',
        headers=auth_headers,
        json={'tags': ['filter-me']},
    )
    resp = client.get('/api/library?tag=filter-me', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 1

    resp = client.get('/api/library?tag=nonexistent', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 0


def test_paper_management_unauthorized(client, sample_paper):
    resp = client.post(f'/api/papers/{sample_paper.arxiv_id}/save')
    assert resp.status_code == 401
    resp = client.get('/api/library')
    assert resp.status_code == 401
