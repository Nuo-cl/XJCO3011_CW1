import json


def test_create_note(client, auth_headers, sample_paper):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
        'title': 'Test Note',
        'content': 'Some markdown content.',
    })
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['title'] == 'Test Note'
    assert data['paper_id'] == sample_paper.id


def test_create_note_standalone(client, auth_headers):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'title': 'Standalone Note',
        'content': 'No paper linked.',
    })
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['paper_id'] is None


def test_create_note_missing_fields(client, auth_headers):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'title': 'Only title',
    })
    assert resp.status_code == 400


def test_create_note_bad_paper(client, auth_headers):
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': 'nonexistent.99999',
        'title': 'Title',
        'content': 'Content',
    })
    assert resp.status_code == 404


def test_list_notes(client, auth_headers, sample_paper):
    client.post('/api/notes', headers=auth_headers, json={
        'title': 'Note 1', 'content': 'c1',
    })
    client.post('/api/notes', headers=auth_headers, json={
        'title': 'Note 2', 'content': 'c2',
    })
    resp = client.get('/api/notes', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['data']) == 2
    assert 'pagination' in data


def test_get_note(client, auth_headers):
    create = client.post('/api/notes', headers=auth_headers, json={
        'title': 'Get Me', 'content': 'content',
    })
    note_id = create.get_json()['data']['id']

    resp = client.get(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['data']['title'] == 'Get Me'


def test_get_note_forbidden(client, auth_headers, db):
    from app.models.user import User
    from app.models.note import Note

    user2 = User(username='other', email='other@test.com')
    user2.set_password('pass')
    db.session.add(user2)
    db.session.commit()

    note = Note(user_id=user2.id, title='Private', content='secret')
    db.session.add(note)
    db.session.commit()

    resp = client.get(f'/api/notes/{note.id}', headers=auth_headers)
    assert resp.status_code == 403


def test_update_note(client, auth_headers):
    create = client.post('/api/notes', headers=auth_headers, json={
        'title': 'Old Title', 'content': 'old',
    })
    note_id = create.get_json()['data']['id']

    resp = client.put(f'/api/notes/{note_id}', headers=auth_headers, json={
        'title': 'New Title',
    })
    assert resp.status_code == 200
    assert resp.get_json()['data']['title'] == 'New Title'


def test_delete_note(client, auth_headers):
    create = client.post('/api/notes', headers=auth_headers, json={
        'title': 'Delete Me', 'content': 'bye',
    })
    note_id = create.get_json()['data']['id']

    resp = client.delete(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f'/api/notes/{note_id}', headers=auth_headers)
    assert resp.status_code == 404


def test_list_paper_notes(client, auth_headers, sample_paper):
    client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
        'title': 'Paper Note', 'content': 'related',
    })
    resp = client.get(f'/api/papers/{sample_paper.arxiv_id}/notes', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 1


def test_notes_unauthorized(client):
    resp = client.get('/api/notes')
    assert resp.status_code == 401
