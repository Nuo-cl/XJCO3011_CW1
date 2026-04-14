"""Tests for F5: Flashcards and spaced repetition (SM-2)."""
import json
import pytest
from datetime import datetime


@pytest.fixture
def sample_note(client, auth_headers, sample_paper):
    """Create a note for flashcard tests."""
    resp = client.post('/api/notes', headers=auth_headers, json={
        'paper_id': sample_paper.arxiv_id,
        'content': 'Content for flashcard tests.',
    })
    return resp.get_json()['data']


@pytest.fixture
def sample_flashcard(client, auth_headers, sample_note):
    """Create a flashcard for tests."""
    resp = client.post('/api/flashcards', headers=auth_headers, json={
        'note_id': sample_note['id'],
        'question': 'What is attention?',
        'answer': 'A mechanism for weighted aggregation.',
    })
    return resp.get_json()['data']


# --- SM-2 unit tests ---

def test_sm2_correct_response():
    from app.services.sm2_service import SM2Service

    class FakeCard:
        ease_factor = 2.5
        interval = 1
        repetitions = 0

    result = SM2Service.review(FakeCard(), rating=4)
    assert result['repetitions'] == 1
    assert result['interval'] == 1
    assert result['ease_factor'] >= 2.4


def test_sm2_second_correct():
    from app.services.sm2_service import SM2Service

    class FakeCard:
        ease_factor = 2.5
        interval = 1
        repetitions = 1

    result = SM2Service.review(FakeCard(), rating=4)
    assert result['repetitions'] == 2
    assert result['interval'] == 6


def test_sm2_incorrect_resets():
    from app.services.sm2_service import SM2Service

    class FakeCard:
        ease_factor = 2.5
        interval = 10
        repetitions = 5

    result = SM2Service.review(FakeCard(), rating=2)
    assert result['repetitions'] == 0
    assert result['interval'] == 1


def test_sm2_min_ease_factor():
    from app.services.sm2_service import SM2Service

    class FakeCard:
        ease_factor = 1.3
        interval = 1
        repetitions = 0

    result = SM2Service.review(FakeCard(), rating=3)
    assert result['ease_factor'] >= 1.3


# --- Flashcard CRUD ---

def test_create_flashcard(client, auth_headers, sample_note):
    resp = client.post('/api/flashcards', headers=auth_headers, json={
        'note_id': sample_note['id'],
        'question': 'What is Q in attention?',
        'answer': 'Query vector.',
    })
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['question'] == 'What is Q in attention?'
    assert data['ease_factor'] == 2.5
    assert data['interval'] == 1
    assert data['repetitions'] == 0


def test_create_flashcard_bad_note(client, auth_headers):
    resp = client.post('/api/flashcards', headers=auth_headers, json={
        'note_id': 9999,
        'question': 'Q',
        'answer': 'A',
    })
    assert resp.status_code == 404


def test_create_flashcard_missing_fields(client, auth_headers, sample_note):
    resp = client.post('/api/flashcards', headers=auth_headers, json={
        'note_id': sample_note['id'],
    })
    assert resp.status_code == 400


def test_list_flashcards(client, auth_headers, sample_flashcard):
    resp = client.get('/api/flashcards', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['data']) >= 1
    assert 'pagination' in data


def test_list_note_flashcards(client, auth_headers, sample_note, sample_flashcard):
    resp = client.get(f'/api/notes/{sample_note["id"]}/flashcards', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) >= 1


def test_update_flashcard(client, auth_headers, sample_flashcard):
    resp = client.put(f'/api/flashcards/{sample_flashcard["id"]}', headers=auth_headers, json={
        'question': 'Updated question?',
    })
    assert resp.status_code == 200
    assert resp.get_json()['data']['question'] == 'Updated question?'


def test_delete_flashcard(client, auth_headers, sample_flashcard):
    resp = client.delete(f'/api/flashcards/{sample_flashcard["id"]}', headers=auth_headers)
    assert resp.status_code == 204


# --- Review flow ---

def test_get_due_flashcards(client, auth_headers, sample_flashcard):
    resp = client.get('/api/flashcards/due', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total_due' in data
    assert isinstance(data['data'], list)


def test_review_flashcard(client, auth_headers, sample_flashcard):
    resp = client.post(f'/api/flashcards/{sample_flashcard["id"]}/review', headers=auth_headers, json={
        'rating': 4,
    })
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['rating'] == 4
    assert data['updated']['repetitions'] == 1
    assert 'reviewed_at' in data


def test_review_bad_rating(client, auth_headers, sample_flashcard):
    resp = client.post(f'/api/flashcards/{sample_flashcard["id"]}/review', headers=auth_headers, json={
        'rating': 6,
    })
    assert resp.status_code == 400


def test_review_stats(client, auth_headers, sample_flashcard):
    # Do a review first
    client.post(f'/api/flashcards/{sample_flashcard["id"]}/review', headers=auth_headers, json={
        'rating': 4,
    })
    resp = client.get('/api/review/stats', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['total_cards'] >= 1
    assert 'due_today' in data
    assert 'mastered' in data
    assert 'learning' in data
    assert 'reviews_in_period' in data
    assert 'daily_reviews' in data


def test_flashcards_unauthorized(client):
    resp = client.get('/api/flashcards')
    assert resp.status_code == 401
    resp = client.get('/api/flashcards/due')
    assert resp.status_code == 401
