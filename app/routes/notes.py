from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.paper import Paper
from app.models.note import Note, NOTE_MAX_LENGTH
from app.utils.errors import APIError
from app.utils.validators import validate_required_fields

notes_bp = Blueprint('notes', __name__, url_prefix='/api')


def _chromadb():
    return current_app.extensions.get('chromadb')


def _note_response(note):
    """Build a single note response dict with HATEOAS links."""
    data = note.to_dict()
    data['paper_title'] = note.paper.title
    links = {
        'self': f'/api/notes/{note.id}',
        'paper': f'/api/papers/{note.paper.arxiv_id}',
        'flashcards': f'/api/notes/{note.id}/flashcards',
    }
    data['_links'] = links
    return data


def _sync_note_to_chromadb(note, delete=False):
    """Sync note content to ChromaDB."""
    service = _chromadb()
    if not service:
        return
    try:
        if delete:
            service.delete_note(note.id)
        else:
            service.add_note(
                note_id=note.id,
                content=note.content,
                metadata={
                    'user_id': note.user_id,
                    'paper_id': note.paper.arxiv_id,
                    'created_at': note.created_at.isoformat(),
                },
            )
    except Exception:
        pass  # non-critical


def _validate_content(content):
    """Validate note content length."""
    if len(content) > NOTE_MAX_LENGTH:
        raise APIError(
            f'Content exceeds maximum length of {NOTE_MAX_LENGTH} characters.',
            400,
        )


@notes_bp.route('/notes', methods=['POST'])
@jwt_required()
def create_note():
    """Create a new insight note linked to a paper.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - paper_id
            - content
          properties:
            paper_id:
              type: string
              description: arXiv ID to link the note to (required)
              example: "2301.07041"
            content:
              type: string
              description: Insight content (max 1000 characters)
              example: The paper shows multi-head attention can be pruned without significant performance loss.
    responses:
      201:
        description: Note created successfully
      400:
        description: Missing required fields or content too long
      404:
        description: Linked paper not found
    """
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True)
    validate_required_fields(data, ['paper_id', 'content'])
    _validate_content(data['content'])

    arxiv_id = data['paper_id']
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        raise APIError(f"Paper with arxiv_id '{arxiv_id}' not found.", 404)

    note = Note(
        user_id=uid,
        paper_id=paper.id,
        content=data['content'],
    )
    db.session.add(note)
    db.session.commit()

    _sync_note_to_chromadb(note)

    return jsonify({
        'data': _note_response(note),
    }), 201


@notes_bp.route('/notes', methods=['GET'])
@jwt_required()
def list_notes():
    """List all notes for the authenticated user.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: query
        name: paper_id
        type: string
        required: false
        description: Filter by arXiv paper ID
        example: "2301.07041"
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 20
        description: Results per page (max 100)
    responses:
      200:
        description: Paginated list of notes
    """
    uid = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = Note.query.filter_by(user_id=uid)

    # Optional filter by paper arxiv_id
    paper_id_filter = request.args.get('paper_id')
    if paper_id_filter:
        paper = Paper.query.filter_by(arxiv_id=paper_id_filter).first()
        if paper:
            query = query.filter_by(paper_id=paper.id)
        else:
            query = query.filter(False)

    query = query.order_by(Note.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    data = [_note_response(n) for n in pagination.items]
    pages = pagination.pages or 1

    return jsonify({
        'data': data,
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
        },
        '_links': {
            'self': f'/api/notes?page={page}&per_page={per_page}',
            **(
                {'next': f'/api/notes?page={page+1}&per_page={per_page}'}
                if pagination.has_next else {}
            ),
            **(
                {'prev': f'/api/notes?page={page-1}&per_page={per_page}'}
                if pagination.has_prev else {}
            ),
        },
    }), 200


@notes_bp.route('/papers/<arxiv_id>/notes', methods=['GET'])
@jwt_required()
def list_paper_notes(arxiv_id):
    """List all notes for a specific paper.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 20
        description: Results per page (max 100)
    responses:
      200:
        description: Paginated list of notes for the paper
      404:
        description: Paper not found
    """
    uid = int(get_jwt_identity())
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        raise APIError(f"Paper with arxiv_id '{arxiv_id}' not found.", 404)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = Note.query.filter_by(user_id=uid, paper_id=paper.id).order_by(Note.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    data = [_note_response(n) for n in pagination.items]
    pages = pagination.pages or 1

    return jsonify({
        'data': data,
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
        },
        '_links': {
            'self': f'/api/papers/{arxiv_id}/notes?page={page}&per_page={per_page}',
        },
    }), 200


@notes_bp.route('/notes/<int:note_id>', methods=['GET'])
@jwt_required()
def get_note(note_id):
    """Get a specific note by ID.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: note_id
        type: integer
        required: true
        description: The note ID
        example: 1
    responses:
      200:
        description: Note details
      403:
        description: Access denied
      404:
        description: Note not found
    """
    uid = int(get_jwt_identity())
    note = db.session.get(Note, note_id)
    if not note:
        raise APIError('Note not found.', 404)

    if note.user_id != uid:
        raise APIError('Access denied.', 403)

    return jsonify({
        'data': _note_response(note),
    }), 200


@notes_bp.route('/notes/<int:note_id>', methods=['PUT'])
@jwt_required()
def update_note(note_id):
    """Update an existing note.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: note_id
        type: integer
        required: true
        description: The note ID
        example: 1
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            content:
              type: string
              description: Updated insight content (max 1000 characters)
              example: Revised findings after reading the supplementary material.
    responses:
      200:
        description: Note updated successfully
      400:
        description: Request body is required or content too long
      403:
        description: Access denied
      404:
        description: Note not found
    """
    uid = int(get_jwt_identity())
    note = db.session.get(Note, note_id)
    if not note:
        raise APIError('Note not found.', 404)

    if note.user_id != uid:
        raise APIError('Access denied.', 403)

    data = request.get_json(silent=True)
    if not data:
        raise APIError('Request body is required.', 400)

    if 'content' in data:
        _validate_content(data['content'])
        note.content = data['content']

    db.session.commit()
    _sync_note_to_chromadb(note)

    return jsonify({
        'data': _note_response(note),
    }), 200


@notes_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(note_id):
    """Delete a note.
    ---
    tags:
      - Notes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: note_id
        type: integer
        required: true
        description: The note ID
        example: 1
    responses:
      204:
        description: Note deleted
      403:
        description: Access denied
      404:
        description: Note not found
    """
    uid = int(get_jwt_identity())
    note = db.session.get(Note, note_id)
    if not note:
        raise APIError('Note not found.', 404)

    if note.user_id != uid:
        raise APIError('Access denied.', 403)

    _sync_note_to_chromadb(note, delete=True)
    db.session.delete(note)
    db.session.commit()
    return '', 204
