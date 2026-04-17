from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app import db, limiter
from app.models.user import User
from app.utils.errors import APIError
from app.utils.validators import validate_required_fields, validate_email

auth_bp = Blueprint('auth', __name__, url_prefix='/api')


@auth_bp.route('/auth/register', methods=['POST'])
@limiter.limit('5 per minute')
def register():
    """Register a new user account.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              example: researcher1
            email:
              type: string
              example: researcher1@example.com
            password:
              type: string
              example: securepass123
    responses:
      201:
        description: User registered successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                email:
                  type: string
                preferred_categories:
                  type: array
                  items:
                    type: string
                created_at:
                  type: string
            _links:
              type: object
              properties:
                self:
                  type: string
                login:
                  type: string
      400:
        description: Missing required fields or invalid email format
      409:
        description: Username or email already exists
    """
    data = request.get_json(silent=True)
    validate_required_fields(data, ['username', 'email', 'password'])
    validate_email(data['email'])

    if User.query.filter_by(username=data['username']).first():
        raise APIError('Username already exists.', 409)
    if User.query.filter_by(email=data['email']).first():
        raise APIError('Email already exists.', 409)

    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'data': user.to_dict(),
        '_links': {
            'self': '/api/users/me',
            'login': '/api/auth/login',
        },
    }), 201


@auth_bp.route('/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def login():
    """Authenticate user and obtain JWT token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: researcher1
            password:
              type: string
              example: securepass123
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                access_token:
                  type: string
                token_type:
                  type: string
                  example: bearer
                expires_in:
                  type: integer
                  example: 86400
      401:
        description: Invalid username or password
    """
    data = request.get_json(silent=True)
    validate_required_fields(data, ['username', 'password'])

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        raise APIError('Invalid username or password.', 401)

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'data': {
            'access_token': token,
            'token_type': 'bearer',
            'expires_in': 86400,
        },
    }), 200


@auth_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: User profile retrieved
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                email:
                  type: string
                preferred_categories:
                  type: array
                  items:
                    type: string
                created_at:
                  type: string
            _links:
              type: object
      401:
        description: Missing or invalid JWT token
    """
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        raise APIError('User not found.', 404)
    return jsonify({
        'data': user.to_dict(),
        '_links': {
            'self': '/api/users/me',
            'library': '/api/library',
            'notes': '/api/notes',
        },
    }), 200


@auth_bp.route('/users/me', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: newemail@example.com
            preferred_categories:
              type: array
              items:
                type: string
              example: ["cs.CV", "cs.CL"]
    responses:
      200:
        description: Profile updated successfully
      400:
        description: Invalid email format or invalid field types
      401:
        description: Missing or invalid JWT token
      409:
        description: Email already in use by another account
    """
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        raise APIError('User not found.', 404)
    data = request.get_json(silent=True)
    if not data:
        raise APIError('Request body is required.', 400)

    if 'email' in data:
        validate_email(data['email'])
        existing = User.query.filter(User.email == data['email'], User.id != user.id).first()
        if existing:
            raise APIError('Email already in use.', 409)
        user.email = data['email']

    if 'preferred_categories' in data:
        if not isinstance(data['preferred_categories'], list):
            raise APIError('preferred_categories must be a list.', 400)
        user.preferred_categories = data['preferred_categories']

    db.session.commit()
    return jsonify({
        'data': user.to_dict(),
        '_links': {
            'self': '/api/users/me',
            'library': '/api/library',
            'notes': '/api/notes',
        },
    }), 200
