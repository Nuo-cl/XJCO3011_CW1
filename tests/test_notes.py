import json


def test_create_note(client, auth_headers, sample_paper):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
        'content': 'Key insight about attention mechanisms.',
    })
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['paper_id'] == sample_paper.id
    assert data['arxiv_id'] == sample_paper.arxiv_id
    assert 'preview' in data


def test_create_note_requires_paper(client, auth_headers):
    """Notes must be linked to a paper."""
    resp = client.post('/api/notes', headers=auth_headers, json={
        'content': 'No paper linked.',
    })
    assert resp.status_code == 400


def test_create_note_missing_content(client, auth_headers, sample_paper):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
    })
    assert resp.status_code == 400


def test_create_note_bad_paper(client, auth_headers):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': 'nonexistent.99999',
        'content': 'Content',
    })
    assert resp.status_code == 404


def test_create_note_too_long(client, auth_headers, sample_paper):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
        'content': 'x' * 1001,
    })
    assert resp.status_code == 400


def test_list_notes(client, auth_headers, sample_paper):
    client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'insight 1',
    })
    client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'insight 2',
    })
    resp = client.get('/api/notes', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['data']) == 2
    assert 'pagination' in data


def test_get_note(client, auth_headers, sample_paper):
    create = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'get this insight',
    })
    note_id = create.get_json()['data']['id']

    resp = client.get(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['data']['content'] == 'get this insight'


def test_get_note_forbidden(client, auth_headers, db, sample_paper):
    from app.models.user import User
    from app.models.note import Note

    user2 = User(username='other', email='other@test.com')
    user2.set_password('pass')
    db.session.add(user2)
    db.session.commit()

    note = Note(user_id=user2.id, paper_id=sample_paper.id, content='secret')
    db.session.add(note)
    db.session.commit()

    resp = client.get(f'/api/notes/{note.id}', headers=auth_headers)
    assert resp.status_code == 403


def test_update_note(client, auth_headers, sample_paper):
    create = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'old insight',
    })
    note_id = create.get_json()['data']['id']

    resp = client.put(f'/api/notes/{note_id}', headers=auth_headers, json={
        'content': 'updated insight',
    })
    assert resp.status_code == 200
    assert resp.get_json()['data']['content'] == 'updated insight'


def test_update_note_too_long(client, auth_headers, sample_paper):
    create = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'short',
    })
    note_id = create.get_json()['data']['id']

    resp = client.put(f'/api/notes/{note_id}', headers=auth_headers, json={
        'content': 'x' * 1001,
    })
    assert resp.status_code == 400


def test_delete_note(client, auth_headers, sample_paper):
    create = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'delete me',
    })
    note_id = create.get_json()['data']['id']

    resp = client.delete(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 404


def test_list_paper_notes(client, auth_headers, sample_paper):
    client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id, 'content': 'paper insight',
    })
    resp = client.get(f'/api/papers/{sample_paper.arxiv_id}/notes', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 1


def test_notes_unauthorized(client):
    resp = client.get('/api/notes')
    assert resp.status_code == 401
