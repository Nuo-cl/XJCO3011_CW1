from flask import jsonify


class APIError(Exception):
    """Custom API exception with HTTP status code and error type."""

    STATUS_MAP = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        500: 'internal_error',
    }

    def __init__(self, message, status_code=400, error_type=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type or self.STATUS_MAP.get(status_code, 'error')

    def to_dict(self):
        return {
            'error': self.error_type,
            'message': self.message,
        }


def register_error_handlers(app):
    """Register error handlers on the Flask app for consistent JSON error responses."""

    @app.errorhandler(APIError)
    def handle_api_error(e):
        return jsonify(e.to_dict()), e.status_code

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            'error': 'bad_request',
            'message': e.description if hasattr(e, 'description') else 'Bad request.',
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            'error': 'unauthorized',
            'message': e.description if hasattr(e, 'description') else 'Authentication required.',
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            'error': 'forbidden',
            'message': e.description if hasattr(e, 'description') else 'Access denied.',
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'error': 'not_found',
            'message': e.description if hasattr(e, 'description') else 'Resource not found.',
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            'error': 'method_not_allowed',
            'message': e.description if hasattr(e, 'description') else 'Method not allowed.',
        }), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({
            'error': 'conflict',
            'message': e.description if hasattr(e, 'description') else 'Resource conflict.',
        }), 409

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            'error': 'too_many_requests',
            'message': 'Rate limit exceeded. Please try again later.',
        }), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            'error': 'internal_error',
            'message': 'An unexpected error occurred.',
        }), 500

    # JWT error callbacks
    jwt = app.extensions.get('flask-jwt-extended', None)
    if jwt is None:
        return

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({
            'error': 'unauthorized',
            'message': 'Missing authorization token.',
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({
            'error': 'unauthorized',
            'message': 'Invalid authorization token.',
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'unauthorized',
            'message': 'Token has expired. Please log in again.',
        }), 401
