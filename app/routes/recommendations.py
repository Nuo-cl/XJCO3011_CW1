from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.user import User
from app.services.recommendation_service import RecommendationService

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api')


def _chromadb():
    return current_app.extensions.get('chromadb')


def _paper_links(arxiv_id):
    return {
        'self': f'/api/papers/{arxiv_id}',
        'save': f'/api/papers/{arxiv_id}/save',
        'notes': f'/api/papers/{arxiv_id}/notes',
    }


@recommendations_bp.route('/recommendations/daily', methods=['GET'])
@jwt_required()
def daily_recommendations():
    """Get personalized daily paper recommendations.
    ---
    tags:
      - Recommendations
    security:
      - Bearer: []
    responses:
      200:
        description: List of recommended papers
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
            strategy:
              type: string
              enum: [cold_start, warm_start]
              description: Which recommendation strategy was used
            count:
              type: integer
      400:
        description: No preferred categories set (cold start)
      401:
        description: Missing or invalid JWT token
    """
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    papers, strategy, _meta = RecommendationService.daily_recommendations(
        user=user,
        chromadb_service=_chromadb(),
    )

    data = []
    for p in papers:
        d = p.to_dict()
        d['_links'] = _paper_links(p.arxiv_id)
        data.append(d)

    return jsonify({
        'data': data,
        'strategy': strategy,
        'count': len(data),
        '_links': {
            'self': '/api/recommendations/daily',
            'profile': '/api/users/me',
        },
    }), 200
