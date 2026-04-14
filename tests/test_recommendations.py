"""Tests for F5: Recommendations and random discovery."""
import json
from unittest.mock import patch, MagicMock
from datetime import date

from app.models.paper import Paper, UserPaper


def _make_paper(db, arxiv_id, title='Test Paper', category='cs.AI'):
    """Helper to create and persist a Paper."""
    p = Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=json.dumps(['Author']),
        abstract=f'Abstract for {arxiv_id}.',
        categories=category,
        published_date=date(2026, 4, 10),
        arxiv_url=f'https://arxiv.org/abs/{arxiv_id}',
        pdf_url=f'https://arxiv.org/pdf/{arxiv_id}.pdf',
    )
    db.session.add(p)
    db.session.flush()
    return p


# ---------------------------------------------------------------------------
# Daily Recommendations
# ---------------------------------------------------------------------------

def test_daily_recommendations_unauthorized(client):
    resp = client.get('/api/recommendations/daily')
    assert resp.status_code == 401


def test_daily_cold_start_no_categories(client, auth_headers):
    """Cold start with no preferred_categories should return 400."""
    resp = client.get('/api/recommendations/daily', headers=auth_headers)
    assert resp.status_code == 400


def test_daily_cold_start_with_categories(client, auth_headers, sample_user, db):
    """Cold start with preferred_categories returns papers."""
    sample_user.preferred_categories = ['cs.AI']
    db.session.commit()

    # Create papers that trending would return
    papers = [_make_paper(db, f'2604.0000{i}') for i in range(5)]
    db.session.commit()

    with patch('app.services.recommendation_service.ArxivService.trending', return_value=papers):
        resp = client.get('/api/recommendations/daily', headers=auth_headers)

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['strategy'] == 'cold_start'
    assert data['count'] > 0
    assert len(data['data']) == data['count']


def test_daily_cold_start_excludes_saved(client, auth_headers, sample_user, db):
    """Cold start should not recommend papers the user already saved."""
    sample_user.preferred_categories = ['cs.AI']
    db.session.commit()

    papers = [_make_paper(db, f'2604.1000{i}') for i in range(5)]
    db.session.commit()

    # Save the first paper
    up = UserPaper(user_id=sample_user.id, paper_id=papers[0].id)
    db.session.add(up)
    db.session.commit()

    with patch('app.services.recommendation_service.ArxivService.trending', return_value=papers):
        resp = client.get('/api/recommendations/daily', headers=auth_headers)

    data = resp.get_json()
    recommended_ids = [p['arxiv_id'] for p in data['data']]
    assert papers[0].arxiv_id not in recommended_ids


def test_daily_warm_start(client, auth_headers, sample_user, sample_paper, db):
    """With saved papers, strategy should be warm_start."""
    # Save a paper to trigger warm start
    up = UserPaper(user_id=sample_user.id, paper_id=sample_paper.id)
    db.session.add(up)
    db.session.commit()

    sample_user.preferred_categories = ['cs.AI']
    db.session.commit()

    # Create candidate papers for category recommendations
    cat_papers = [_make_paper(db, f'2604.2000{i}') for i in range(5)]
    db.session.commit()

    # Mock ChromaDB to return empty (so we test category fallback)
    mock_chromadb = MagicMock()
    mock_chromadb.search_papers.return_value = {'ids': [[]], 'distances': [[]], 'metadatas': [[]]}

    with patch('app.services.recommendation_service.ArxivService.trending', return_value=cat_papers):
        with patch('app.routes.recommendations._chromadb', return_value=mock_chromadb):
            resp = client.get('/api/recommendations/daily', headers=auth_headers)

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['strategy'] == 'warm_start'


# ---------------------------------------------------------------------------
# Random Discovery
# ---------------------------------------------------------------------------

def test_discover_missing_category(client):
    resp = client.get('/api/papers/discover')
    assert resp.status_code == 400


def test_discover_success(client, db):
    """Discover returns a random subset of papers."""
    papers = [_make_paper(db, f'2604.3000{i}') for i in range(10)]
    db.session.commit()

    with patch('app.services.recommendation_service.ArxivService.trending', return_value=papers):
        resp = client.get('/api/papers/discover?category=cs.AI&count=3')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 3
    assert len(data['data']) == 3
    assert data['category'] == 'cs.AI'


def test_discover_count_capped(client, db):
    """Count parameter should be capped at 10."""
    papers = [_make_paper(db, f'2604.4000{i}') for i in range(15)]
    db.session.commit()

    with patch('app.services.recommendation_service.ArxivService.trending', return_value=papers):
        resp = client.get('/api/papers/discover?category=cs.AI&count=50')

    data = resp.get_json()
    assert data['count'] <= 10
