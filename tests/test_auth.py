import json


def test_health_check(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_404_returns_json(client):
    resp = client.get('/api/nonexistent')
    assert resp.status_code == 404
    data = resp.get_json()
    assert data['error'] == 'not_found'


# --- Register ---

def test_register_success(client):
    resp = client.post('/api/auth/register', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'pass123',
    })
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['username'] == 'newuser'
    assert data['email'] == 'new@example.com'
    assert 'password' not in data
    assert 'password_hash' not in data


def test_register_missing_fields(client):
    resp = client.post('/api/auth/register', json={'username': 'x'})
    assert resp.status_code == 400


def test_register_duplicate_username(client, sample_user):
    resp = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'other@example.com',
        'password': 'pass123',
    })
    assert resp.status_code == 409


def test_register_duplicate_email(client, sample_user):
    resp = client.post('/api/auth/register', json={
        'username': 'other',
        'email': 'test@example.com',
        'password': 'pass123',
    })
    assert resp.status_code == 409


def test_register_invalid_email(client):
    resp = client.post('/api/auth/register', json={
        'username': 'user2',
        'email': 'not-an-email',
        'password': 'pass123',
    })
    assert resp.status_code == 400


# --- Login ---

def test_login_success(client, sample_user):
    resp = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123',
    })
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'


def test_login_wrong_password(client, sample_user):
    resp = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'wrongpass',
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post('/api/auth/login', json={
        'username': 'nobody',
        'password': 'pass',
    })
    assert resp.status_code == 401


# --- Profile ---

def test_get_profile(client, auth_headers):
    resp = client.get('/api/users/me', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['username'] == 'testuser'
    assert '_links' in resp.get_json()


def test_get_profile_unauthorized(client):
    resp = client.get('/api/users/me')
    assert resp.status_code == 401


def test_update_profile(client, auth_headers):
    resp = client.put('/api/users/me', headers=auth_headers, json={
        'preferred_categories': ['cs.CV', 'cs.AI'],
    })
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['preferred_categories'] == ['cs.CV', 'cs.AI']


def test_update_email_conflict(client, auth_headers, db):
    from app.models.user import User
    user2 = User(username='user2', email='taken@example.com')
    user2.set_password('pass')
    db.session.add(user2)
    db.session.commit()

    resp = client.put('/api/users/me', headers=auth_headers, json={
        'email': 'taken@example.com',
    })
    assert resp.status_code == 409
