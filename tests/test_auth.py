def test_health_check(client):
    """Health check endpoint returns 200 with expected JSON."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'ScholarTrack' in data['message']


def test_404_returns_json(client):
    """Non-existent endpoint returns JSON 404 error."""
    response = client.get('/api/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'not_found'
