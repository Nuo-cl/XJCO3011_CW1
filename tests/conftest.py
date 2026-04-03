import json
import pytest
from datetime import date

from app import create_app, db as _db
from app.models.user import User
from app.models.paper import Paper


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    with app.app_context():
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Provide a clean database session."""
    return _db


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_user(app, db):
    """Create and return a test user."""
    user = User(
        username='testuser',
        email='test@example.com',
    )
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_paper(app, db):
    """Create and return a test paper with realistic arXiv data."""
    paper = Paper(
        arxiv_id='2401.12345',
        title='Attention Is All You Need Revisited',
        authors=json.dumps(['Alice Smith', 'Bob Jones']),
        abstract='We revisit the transformer architecture and propose improvements.',
        categories='cs.CL cs.AI',
        published_date=date(2024, 1, 15),
        arxiv_url='https://arxiv.org/abs/2401.12345',
        pdf_url='https://arxiv.org/pdf/2401.12345.pdf',
    )
    db.session.add(paper)
    db.session.commit()
    return paper


@pytest.fixture
def auth_headers(client, sample_user):
    """Log in the sample user and return JWT auth headers."""
    resp = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123',
    })
    token = resp.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}
