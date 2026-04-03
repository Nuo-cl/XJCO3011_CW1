import re

from app.utils.errors import APIError


def validate_required_fields(data, fields):
    """Validate that all required fields are present and non-empty in data dict."""
    if not data:
        raise APIError('Request body is required.', 400)
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == '']
    if missing:
        raise APIError(f'Missing required fields: {", ".join(missing)}', 400)


def validate_email(email):
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise APIError('Invalid email format.', 400)


def validate_pagination_params(args):
    """Extract and validate pagination parameters from request args."""
    try:
        page = int(args.get('page', 1))
        per_page = int(args.get('per_page', 20))
    except (TypeError, ValueError):
        raise APIError('page and per_page must be integers.', 400)

    if page < 1:
        raise APIError('page must be >= 1.', 400)
    if per_page < 1 or per_page > 100:
        raise APIError('per_page must be between 1 and 100.', 400)

    return page, per_page
