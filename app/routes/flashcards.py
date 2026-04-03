from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app import db
from app.models.note import Note
from app.models.flashcard import Flashcard, ReviewLog
from app.services.sm2_service import SM2Service
from app.utils.errors import APIError
from app.utils.validators import validate_required_fields

flashcards_bp = Blueprint('flashcards', __name__, url_prefix='/api')


def _flashcard_response(card):
    data = card.to_dict()
    data['_links'] = {
        'self': f'/api/flashcards/{card.id}',
        'note': f'/api/notes/{card.note_id}',
        'review': f'/api/flashcards/{card.id}/review',
    }
    return data


@flashcards_bp.route('/flashcards', methods=['POST'])
@jwt_required()
def create_flashcard():
    """Create a new flashcard linked to a note.
    ---
    tags:
      - Flashcards
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - note_id
            - question
            - answer
          properties:
            note_id:
              type: integer
              example: 1
            question:
              type: string
              example: "What is Multi-Head Attention?"
            answer:
              type: string
              example: "A mechanism that runs multiple attention functions in parallel."
    responses:
      201:
        description: Flashcard created successfully
      400:
        description: Missing required fields
      401:
        description: Missing or invalid JWT token
      403:
        description: Note does not belong to current user
      404:
        description: Note not found
    """
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True)
    validate_required_fields(data, ['note_id', 'question', 'answer'])

    note = db.session.get(Note, data['note_id'])
    if not note:
        raise APIError('Note not found.', 404)
    if note.user_id != uid:
        raise APIError('Access denied.', 403)

    card = Flashcard(
        user_id=uid,
        note_id=note.id,
        question=data['question'],
        answer=data['answer'],
    )
    db.session.add(card)
    db.session.commit()

    return jsonify({
        'data': _flashcard_response(card),
    }), 201


@flashcards_bp.route('/flashcards', methods=['GET'])
@jwt_required()
def list_flashcards():
    """List all flashcards for the current user.
    ---
    tags:
      - Flashcards
    security:
      - Bearer: []
    parameters:
      - name: note_id
        in: query
        type: integer
        required: false
        description: Filter by note ID
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated list of flashcards
      401:
        description: Missing or invalid JWT token
    """
    uid = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = Flashcard.query.filter_by(user_id=uid)

    note_id = request.args.get('note_id', type=int)
    if note_id:
        query = query.filter_by(note_id=note_id)

    query = query.order_by(Flashcard.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pages = pagination.pages or 1

    return jsonify({
        'data': [_flashcard_response(c) for c in pagination.items],
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
        },
        '_links': {
            'self': f'/api/flashcards?page={page}&per_page={per_page}',
        },
    }), 200


@flashcards_bp.route('/notes/<int:note_id>/flashcards', methods=['GET'])
@jwt_required()
def list_note_flashcards(note_id):
    """List flashcards for a specific note.
    ---
    tags:
      - Flashcards
    security:
      - Bearer: []
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated list of flashcards for the note
      401:
        description: Missing or invalid JWT token
      403:
        description: Note does not belong to current user
      404:
        description: Note not found
    """
    uid = int(get_jwt_identity())
    note = db.session.get(Note, note_id)
    if not note:
        raise APIError('Note not found.', 404)
    if note.user_id != uid:
        raise APIError('Access denied.', 403)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = Flashcard.query.filter_by(user_id=uid, note_id=note_id).order_by(Flashcard.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pages = pagination.pages or 1

    return jsonify({
        'data': [_flashcard_response(c) for c in pagination.items],
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
        },
        '_links': {
            'self': f'/api/notes/{note_id}/flashcards?page={page}&per_page={per_page}',
        },
    }), 200


@flashcards_bp.route('/flashcards/<int:card_id>', methods=['PUT'])
@jwt_required()
def update_flashcard(card_id):
    """Update a flashcard's question or answer.
    ---
    tags:
      - Flashcards
    security:
      - Bearer: []
    parameters:
      - name: card_id
        in: path
        type: integer
        required: true
        description: Flashcard ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            question:
              type: string
              example: "Updated question?"
            answer:
              type: string
              example: "Updated answer."
    responses:
      200:
        description: Flashcard updated successfully
      400:
        description: Request body is required
      401:
        description: Missing or invalid JWT token
      403:
        description: Flashcard does not belong to current user
      404:
        description: Flashcard not found
    """
    uid = int(get_jwt_identity())
    card = db.session.get(Flashcard, card_id)
    if not card:
        raise APIError('Flashcard not found.', 404)
    if card.user_id != uid:
        raise APIError('Access denied.', 403)

    data = request.get_json(silent=True)
    if not data:
        raise APIError('Request body is required.', 400)

    if 'question' in data:
        card.question = data['question']
    if 'answer' in data:
        card.answer = data['answer']

    db.session.commit()

    return jsonify({
        'data': _flashcard_response(card),
    }), 200


@flashcards_bp.route('/flashcards/<int:card_id>', methods=['DELETE'])
@jwt_required()
def delete_flashcard(card_id):
    """Delete a flashcard.
    ---
    tags:
      - Flashcards
    security:
      - Bearer: []
    parameters:
      - name: card_id
        in: path
        type: integer
        required: true
        description: Flashcard ID
    responses:
      204:
        description: Flashcard deleted successfully
      401:
        description: Missing or invalid JWT token
      403:
        description: Flashcard does not belong to current user
      404:
        description: Flashcard not found
    """
    uid = int(get_jwt_identity())
    card = db.session.get(Flashcard, card_id)
    if not card:
        raise APIError('Flashcard not found.', 404)
    if card.user_id != uid:
        raise APIError('Access denied.', 403)

    db.session.delete(card)
    db.session.commit()
    return '', 204


@flashcards_bp.route('/flashcards/due', methods=['GET'])
@jwt_required()
def get_due_flashcards():
    """Get flashcards due for review today.
    ---
    tags:
      - Spaced Repetition
    security:
      - Bearer: []
    responses:
      200:
        description: List of due flashcards with total count
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
            total_due:
              type: integer
      401:
        description: Missing or invalid JWT token
    """
    uid = int(get_jwt_identity())
    now = datetime.utcnow()

    cards = Flashcard.query.filter(
        Flashcard.user_id == uid,
        Flashcard.next_review_at <= now,
    ).order_by(Flashcard.next_review_at.asc()).all()

    return jsonify({
        'data': [_flashcard_response(c) for c in cards],
        'total_due': len(cards),
    }), 200


@flashcards_bp.route('/flashcards/<int:card_id>/review', methods=['POST'])
@jwt_required()
def review_flashcard(card_id):
    """Submit a review rating for a flashcard (SM-2 spaced repetition).
    ---
    tags:
      - Spaced Repetition
    security:
      - Bearer: []
    parameters:
      - name: card_id
        in: path
        type: integer
        required: true
        description: Flashcard ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rating
          properties:
            rating:
              type: integer
              minimum: 0
              maximum: 5
              example: 4
              description: "SM-2 rating: 0=forgot completely, 5=perfect recall"
    responses:
      200:
        description: Review recorded, returns updated SM-2 parameters
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                flashcard_id:
                  type: integer
                rating:
                  type: integer
                updated:
                  type: object
                  properties:
                    ease_factor:
                      type: number
                    interval:
                      type: integer
                    repetitions:
                      type: integer
                    next_review_at:
                      type: string
                reviewed_at:
                  type: string
      400:
        description: Rating must be an integer between 0 and 5
      401:
        description: Missing or invalid JWT token
      403:
        description: Flashcard does not belong to current user
      404:
        description: Flashcard not found
    """
    uid = int(get_jwt_identity())
    card = db.session.get(Flashcard, card_id)
    if not card:
        raise APIError('Flashcard not found.', 404)
    if card.user_id != uid:
        raise APIError('Access denied.', 403)

    data = request.get_json(silent=True)
    validate_required_fields(data, ['rating'])

    rating = data['rating']
    if not isinstance(rating, int) or rating < 0 or rating > 5:
        raise APIError('Rating must be an integer between 0 and 5.', 400)

    # Apply SM-2 algorithm
    updated = SM2Service.review(card, rating)
    card.ease_factor = updated['ease_factor']
    card.interval = updated['interval']
    card.repetitions = updated['repetitions']
    card.next_review_at = updated['next_review_at']

    # Log the review
    log = ReviewLog(
        user_id=uid,
        flashcard_id=card.id,
        rating=rating,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'data': {
            'flashcard_id': card.id,
            'rating': rating,
            'updated': {
                'ease_factor': card.ease_factor,
                'interval': card.interval,
                'repetitions': card.repetitions,
                'next_review_at': card.next_review_at.isoformat(),
            },
            'reviewed_at': log.reviewed_at.isoformat(),
        },
    }), 200


@flashcards_bp.route('/review/stats', methods=['GET'])
@jwt_required()
def review_stats():
    """Get spaced repetition review statistics.
    ---
    tags:
      - Spaced Repetition
    security:
      - Bearer: []
    parameters:
      - name: period
        in: query
        type: string
        enum: [week, month, all]
        default: week
        description: Statistics time period
    responses:
      200:
        description: Review statistics
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                total_cards:
                  type: integer
                due_today:
                  type: integer
                mastered:
                  type: integer
                  description: "Cards with ease_factor >= 2.5 and interval >= 21"
                learning:
                  type: integer
                reviews_in_period:
                  type: integer
                average_rating:
                  type: number
                daily_reviews:
                  type: array
                  items:
                    type: object
                    properties:
                      date:
                        type: string
                      count:
                        type: integer
                      avg_rating:
                        type: number
      401:
        description: Missing or invalid JWT token
    """
    uid = int(get_jwt_identity())
    period = request.args.get('period', 'week')

    total_cards = Flashcard.query.filter_by(user_id=uid).count()
    due_today = Flashcard.query.filter(
        Flashcard.user_id == uid,
        Flashcard.next_review_at <= datetime.utcnow(),
    ).count()

    # Mastered: ease_factor >= 2.5 and interval >= 21
    mastered = Flashcard.query.filter(
        Flashcard.user_id == uid,
        Flashcard.ease_factor >= 2.5,
        Flashcard.interval >= 21,
    ).count()

    learning = total_cards - mastered

    # Period filter for review logs
    if period == 'month':
        since = datetime.utcnow() - timedelta(days=30)
    elif period == 'all':
        since = datetime(2000, 1, 1)
    else:
        since = datetime.utcnow() - timedelta(days=7)

    reviews_query = ReviewLog.query.filter(
        ReviewLog.user_id == uid,
        ReviewLog.reviewed_at >= since,
    )

    reviews_in_period = reviews_query.count()
    avg_rating_result = db.session.query(func.avg(ReviewLog.rating)).filter(
        ReviewLog.user_id == uid,
        ReviewLog.reviewed_at >= since,
    ).scalar()
    average_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0.0

    # Daily breakdown
    daily_data = db.session.query(
        func.date(ReviewLog.reviewed_at).label('date'),
        func.count(ReviewLog.id).label('count'),
        func.avg(ReviewLog.rating).label('avg_rating'),
    ).filter(
        ReviewLog.user_id == uid,
        ReviewLog.reviewed_at >= since,
    ).group_by(func.date(ReviewLog.reviewed_at)).order_by('date').all()

    daily_reviews = [
        {
            'date': str(row.date),
            'count': row.count,
            'avg_rating': round(float(row.avg_rating), 1) if row.avg_rating else 0.0,
        }
        for row in daily_data
    ]

    return jsonify({
        'data': {
            'total_cards': total_cards,
            'due_today': due_today,
            'mastered': mastered,
            'learning': learning,
            'reviews_in_period': reviews_in_period,
            'average_rating': average_rating,
            'daily_reviews': daily_reviews,
        },
    }), 200
