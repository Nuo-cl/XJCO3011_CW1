from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.paper import Paper
from app.models.note import Note
from app.utils.errors import APIError

search_bp = Blueprint('search', __name__, url_prefix='/api')


def _chromadb():
    """Get the ChromaDB service from app extensions."""
    return current_app.extensions.get('chromadb')


def _clamp(value, lo=0.0, hi=1.0):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _build_paper_result(paper, distance):
    """Build a single paper search result dict."""
    relevance_score = round(_clamp(1.0 - distance), 4)
    return {
        'arxiv_id': paper.arxiv_id,
        'title': paper.title,
        'abstract': paper.abstract,
        'categories': paper.categories,
        'published_date': paper.published_date.isoformat(),
        'relevance_score': relevance_score,
        'type': 'paper',
        '_links': {
            'self': f'/api/papers/{paper.arxiv_id}',
            'save': f'/api/papers/{paper.arxiv_id}/save',
        },
    }


def _build_note_result(note, distance):
    """Build a single note search result dict."""
    relevance_score = round(_clamp(1.0 - distance), 4)
    result = {
        'id': note.id,
        'title': note.title,
        'content': note.content,
        'paper_id': note.paper.arxiv_id if note.paper else None,
        'relevance_score': relevance_score,
        'type': 'note',
        '_links': {
            'self': f'/api/notes/{note.id}',
        },
    }
    if note.paper:
        result['_links']['paper'] = f'/api/papers/{note.paper.arxiv_id}'
    return result


def _parse_search_body(default_n=10):
    """Parse and validate the search request body."""
    data = request.get_json(silent=True)
    if not data or not data.get('query'):
        raise APIError('Field "query" is required.', 400)
    query = data['query'].strip()
    if not query:
        raise APIError('Field "query" must not be empty.', 400)
    n_results = data.get('n_results', default_n)
    if not isinstance(n_results, int) or n_results < 1:
        raise APIError('"n_results" must be a positive integer.', 400)
    n_results = min(n_results, 50)
    return query, n_results


def _process_paper_results(results):
    """Convert ChromaDB paper results into response dicts."""
    items = []
    if not results or not results.get('ids') or not results['ids'][0]:
        return items

    ids = results['ids'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]

    for doc_id, distance, metadata in zip(ids, distances, metadatas):
        arxiv_id = metadata.get('arxiv_id', '')
        if not arxiv_id:
            # Fallback: strip "paper_" prefix from the ChromaDB document ID
            arxiv_id = doc_id.replace('paper_', '', 1) if doc_id.startswith('paper_') else doc_id

        paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
        if not paper:
            continue

        items.append(_build_paper_result(paper, distance))
    return items


def _process_note_results(results):
    """Convert ChromaDB note results into response dicts."""
    items = []
    if not results or not results.get('ids') or not results['ids'][0]:
        return items

    ids = results['ids'][0]
    distances = results['distances'][0]

    for doc_id, distance in zip(ids, distances):
        # ChromaDB note IDs are formatted as "note_{id}"
        try:
            note_id = int(doc_id.replace('note_', '', 1))
        except (ValueError, AttributeError):
            continue

        note = db.session.get(Note, note_id)
        if not note:
            continue

        items.append(_build_note_result(note, distance))
    return items


@search_bp.route('/search/papers', methods=['POST'])
def search_papers():
    """Semantic search over paper abstracts (public, no auth required)."""
    query, n_results = _parse_search_body(default_n=10)

    service = _chromadb()
    if not service:
        return jsonify({'data': [], 'query': query, 'source': 'paper_abstracts'}), 200

    try:
        results = service.search_papers(query, n_results=n_results)
    except Exception:
        return jsonify({'data': [], 'query': query, 'source': 'paper_abstracts'}), 200

    items = _process_paper_results(results)

    return jsonify({
        'data': items,
        'query': query,
        'source': 'paper_abstracts',
    }), 200


@search_bp.route('/search/notes', methods=['POST'])
@jwt_required()
def search_notes():
    """Semantic search over the current user's notes (auth required)."""
    uid = int(get_jwt_identity())
    query, n_results = _parse_search_body(default_n=5)

    service = _chromadb()
    if not service:
        return jsonify({'data': [], 'query': query, 'source': 'user_notes'}), 200

    try:
        results = service.search_notes(query, user_id=uid, n_results=n_results)
    except Exception:
        return jsonify({'data': [], 'query': query, 'source': 'user_notes'}), 200

    items = _process_note_results(results)

    return jsonify({
        'data': items,
        'query': query,
        'source': 'user_notes',
    }), 200


@search_bp.route('/search/all', methods=['POST'])
@jwt_required()
def search_all():
    """Search across both papers and notes, merged by relevance (auth required)."""
    uid = int(get_jwt_identity())
    query, n_results = _parse_search_body(default_n=10)

    service = _chromadb()
    if not service:
        return jsonify({'data': [], 'query': query, 'source': 'all'}), 200

    try:
        combined = service.search_all(query, user_id=uid, n_results=n_results)
    except Exception:
        return jsonify({'data': [], 'query': query, 'source': 'all'}), 200

    paper_items = _process_paper_results(combined.get('papers'))
    note_items = _process_note_results(combined.get('notes'))

    merged = paper_items + note_items
    merged.sort(key=lambda x: x['relevance_score'], reverse=True)

    return jsonify({
        'data': merged,
        'query': query,
        'source': 'all',
    }), 200
