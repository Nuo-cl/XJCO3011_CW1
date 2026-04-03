from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request

from app import db
from app.models.paper import Paper, UserPaper, Tag, UserPaperTag
from app.services.arxiv_service import ArxivService
from app.utils.errors import APIError
from app.utils.validators import validate_required_fields

papers_bp = Blueprint('papers', __name__, url_prefix='/api')


def _paper_links(arxiv_id):
    return {
        'self': f'/api/papers/{arxiv_id}',
        'save': f'/api/papers/{arxiv_id}/save',
        'notes': f'/api/papers/{arxiv_id}/notes',
    }


def _chromadb():
    return current_app.extensions.get('chromadb')


# ---------------------------------------------------------------------------
# F2: Paper Discovery
# ---------------------------------------------------------------------------

@papers_bp.route('/papers/search', methods=['GET'])
def search_papers():
    """Search for papers on arXiv.
    ---
    tags:
      - Paper Discovery
    parameters:
      - in: query
        name: q
        type: string
        required: true
        description: Search query string
        example: transformer attention mechanism
      - in: query
        name: category
        type: string
        required: false
        description: arXiv category filter
        example: cs.AI
      - in: query
        name: date_from
        type: string
        required: false
        description: Start date filter (YYYY-MM-DD)
        example: "2025-01-01"
      - in: query
        name: date_to
        type: string
        required: false
        description: End date filter (YYYY-MM-DD)
        example: "2025-12-31"
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
        description: List of matching papers with pagination
      400:
        description: Missing required query parameter "q"
    """
    q = request.args.get('q')
    if not q:
        raise APIError('Query parameter "q" is required.', 400)

    category = request.args.get('category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    papers = ArxivService.search(
        query=q,
        category=category,
        date_from=date_from,
        date_to=date_to,
        max_results=page * per_page,
        chromadb_service=_chromadb(),
    )

    # Manual pagination over the list
    total = len(papers)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = papers[start:end]
    pages = (total + per_page - 1) // per_page if total else 1

    data = []
    for p in page_items:
        d = p.to_dict()
        d['_links'] = _paper_links(p.arxiv_id)
        data.append(d)

    return jsonify({
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page, 'pages': pages},
        '_links': {
            'self': f'/api/papers/search?q={q}&page={page}&per_page={per_page}',
            **(
                {'next': f'/api/papers/search?q={q}&page={page+1}&per_page={per_page}'}
                if page < pages else {}
            ),
            **(
                {'prev': f'/api/papers/search?q={q}&page={page-1}&per_page={per_page}'}
                if page > 1 else {}
            ),
        },
    }), 200


@papers_bp.route('/papers/trending', methods=['GET'])
def trending_papers():
    """Get trending papers in an arXiv category.
    ---
    tags:
      - Paper Discovery
    parameters:
      - in: query
        name: category
        type: string
        required: true
        description: arXiv category
        example: cs.LG
      - in: query
        name: days
        type: integer
        required: false
        default: 7
        description: Number of days to look back
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
        description: List of trending papers with pagination
      400:
        description: Missing required query parameter "category"
    """
    category = request.args.get('category')
    if not category:
        raise APIError('Query parameter "category" is required.', 400)

    days = request.args.get('days', 7, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    papers = ArxivService.trending(
        category=category,
        days=days,
        max_results=page * per_page,
        chromadb_service=_chromadb(),
    )

    total = len(papers)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = papers[start:end]
    pages = (total + per_page - 1) // per_page if total else 1

    data = []
    for p in page_items:
        d = p.to_dict()
        d['_links'] = _paper_links(p.arxiv_id)
        data.append(d)

    return jsonify({
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page, 'pages': pages},
        '_links': {
            'self': f'/api/papers/trending?category={category}&page={page}&per_page={per_page}',
        },
    }), 200


@papers_bp.route('/papers/<arxiv_id>', methods=['GET'])
def get_paper(arxiv_id):
    """Get details of a specific paper by arXiv ID.
    ---
    tags:
      - Paper Discovery
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
    responses:
      200:
        description: Paper details (includes is_saved field if authenticated)
      404:
        description: Paper not found
    """
    paper = ArxivService.fetch_by_id(arxiv_id, chromadb_service=_chromadb())
    if not paper:
        raise APIError(f"Paper with arxiv_id '{arxiv_id}' not found.", 404)

    data = paper.to_dict()
    data['_links'] = _paper_links(arxiv_id)

    # Add is_saved if user is authenticated
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            up = UserPaper.query.filter_by(user_id=int(uid), paper_id=paper.id).first()
            data['is_saved'] = up is not None
    except Exception:
        pass

    return jsonify({'data': data}), 200


# ---------------------------------------------------------------------------
# F3: Paper Management
# ---------------------------------------------------------------------------

@papers_bp.route('/papers/<arxiv_id>/save', methods=['POST'])
@jwt_required()
def save_paper(arxiv_id):
    """Save a paper to the user's library.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            memo:
              type: string
              example: Interesting approach to multi-head attention
    responses:
      201:
        description: Paper saved successfully
      404:
        description: Paper not found
      409:
        description: Paper already saved
    """
    uid = int(get_jwt_identity())

    paper = ArxivService.fetch_by_id(arxiv_id, chromadb_service=_chromadb())
    if not paper:
        raise APIError(f"Paper with arxiv_id '{arxiv_id}' not found.", 404)

    existing = UserPaper.query.filter_by(user_id=uid, paper_id=paper.id).first()
    if existing:
        raise APIError('Paper already saved.', 409)

    data = request.get_json(silent=True) or {}
    up = UserPaper(user_id=uid, paper_id=paper.id, memo=data.get('memo'))
    db.session.add(up)
    db.session.commit()

    return jsonify({
        'data': {
            'arxiv_id': paper.arxiv_id,
            'title': paper.title,
            'memo': up.memo,
            'tags': [],
            'saved_at': up.saved_at.isoformat(),
        },
        '_links': {
            'self': '/api/library',
            'paper': f'/api/papers/{arxiv_id}',
            'notes': f'/api/papers/{arxiv_id}/notes',
            'tags': f'/api/library/{arxiv_id}/tags',
        },
    }), 201


@papers_bp.route('/papers/<arxiv_id>/save', methods=['DELETE'])
@jwt_required()
def unsave_paper(arxiv_id):
    """Remove a paper from the user's library.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
    responses:
      204:
        description: Paper removed from library
      404:
        description: Paper not found in library
    """
    uid = int(get_jwt_identity())
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        raise APIError('Paper not found in your library.', 404)

    up = UserPaper.query.filter_by(user_id=uid, paper_id=paper.id).first()
    if not up:
        raise APIError('Paper not found in your library.', 404)

    db.session.delete(up)
    db.session.commit()
    return '', 204


@papers_bp.route('/library', methods=['GET'])
@jwt_required()
def get_library():
    """List all papers in the user's library.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    parameters:
      - in: query
        name: tag
        type: string
        required: false
        description: Filter by tag name
        example: deep-learning
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
        description: Paginated list of saved papers
    """
    uid = int(get_jwt_identity())
    tag_filter = request.args.get('tag')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = UserPaper.query.filter_by(user_id=uid)

    if tag_filter:
        tag = Tag.query.filter_by(user_id=uid, name=tag_filter).first()
        if tag:
            query = query.join(UserPaperTag).filter(UserPaperTag.tag_id == tag.id)
        else:
            query = query.filter(False)  # no results

    query = query.order_by(UserPaper.saved_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    import json
    data = []
    for up in pagination.items:
        paper = up.paper
        d = {
            'arxiv_id': paper.arxiv_id,
            'title': paper.title,
            'authors': json.loads(paper.authors) if paper.authors else [],
            'categories': paper.categories,
            'published_date': paper.published_date.isoformat(),
            'memo': up.memo,
            'tags': [upt.tag.name for upt in up.tags],
            'saved_at': up.saved_at.isoformat(),
            '_links': {
                'paper': f'/api/papers/{paper.arxiv_id}',
                'notes': f'/api/papers/{paper.arxiv_id}/notes',
                'tags': f'/api/library/{paper.arxiv_id}/tags',
            },
        }
        data.append(d)

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
            'self': f'/api/library?page={page}&per_page={per_page}',
            **(
                {'next': f'/api/library?page={page+1}&per_page={per_page}'}
                if pagination.has_next else {}
            ),
            **(
                {'prev': f'/api/library?page={page-1}&per_page={per_page}'}
                if pagination.has_prev else {}
            ),
        },
    }), 200


@papers_bp.route('/library/<arxiv_id>/tags', methods=['POST'])
@jwt_required()
def add_tags(arxiv_id):
    """Add tags to a saved paper.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - tags
          properties:
            tags:
              type: array
              items:
                type: string
              example: ["deep-learning", "transformers"]
    responses:
      200:
        description: Updated list of tags on the paper
      400:
        description: Invalid request body or tags not a list
      404:
        description: Paper not found or not in library
    """
    uid = int(get_jwt_identity())
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        raise APIError('Paper not found.', 404)

    up = UserPaper.query.filter_by(user_id=uid, paper_id=paper.id).first()
    if not up:
        raise APIError('Paper not in your library.', 404)

    data = request.get_json(silent=True)
    validate_required_fields(data, ['tags'])
    if not isinstance(data['tags'], list):
        raise APIError('"tags" must be a list.', 400)

    for tag_name in data['tags']:
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        tag = Tag.query.filter_by(user_id=uid, name=tag_name).first()
        if not tag:
            tag = Tag(user_id=uid, name=tag_name)
            db.session.add(tag)
            db.session.flush()

        exists = UserPaperTag.query.filter_by(user_paper_id=up.id, tag_id=tag.id).first()
        if not exists:
            db.session.add(UserPaperTag(user_paper_id=up.id, tag_id=tag.id))

    db.session.commit()

    current_tags = [upt.tag.name for upt in up.tags]
    return jsonify({
        'data': {
            'arxiv_id': arxiv_id,
            'tags': current_tags,
        },
    }), 200


@papers_bp.route('/library/<arxiv_id>/tags/<tag_name>', methods=['DELETE'])
@jwt_required()
def remove_tag(arxiv_id, tag_name):
    """Remove a tag from a saved paper.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    parameters:
      - in: path
        name: arxiv_id
        type: string
        required: true
        description: The arXiv paper identifier
        example: "2301.07041"
      - in: path
        name: tag_name
        type: string
        required: true
        description: Name of the tag to remove
        example: deep-learning
    responses:
      204:
        description: Tag removed from paper
      404:
        description: Paper, library entry, or tag not found
    """
    uid = int(get_jwt_identity())
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        raise APIError('Paper not found.', 404)

    up = UserPaper.query.filter_by(user_id=uid, paper_id=paper.id).first()
    if not up:
        raise APIError('Paper not in your library.', 404)

    tag = Tag.query.filter_by(user_id=uid, name=tag_name).first()
    if not tag:
        raise APIError('Tag not found.', 404)

    upt = UserPaperTag.query.filter_by(user_paper_id=up.id, tag_id=tag.id).first()
    if not upt:
        raise APIError('Tag not found on this paper.', 404)

    db.session.delete(upt)
    db.session.commit()
    return '', 204


@papers_bp.route('/tags', methods=['GET'])
@jwt_required()
def get_tags():
    """List all tags created by the user.
    ---
    tags:
      - Paper Management
    security:
      - Bearer: []
    responses:
      200:
        description: List of tags with paper counts
    """
    uid = int(get_jwt_identity())
    tags = Tag.query.filter_by(user_id=uid).all()

    data = []
    for tag in tags:
        count = UserPaperTag.query.filter_by(tag_id=tag.id).count()
        data.append({'name': tag.name, 'count': count})

    return jsonify({'data': data}), 200
