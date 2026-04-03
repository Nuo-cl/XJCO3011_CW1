from flask import request


def paginate_query(query, page=None, per_page=None, max_per_page=100, serialize_fn=None):
    """Paginate a SQLAlchemy query and return structured response data.

    Args:
        query: SQLAlchemy Query object (not yet executed).
        page: Current page (1-indexed). Defaults to request arg.
        per_page: Items per page. Defaults to request arg.
        max_per_page: Hard upper limit for per_page.
        serialize_fn: Optional callable to serialise each item.

    Returns:
        Dict with 'data', 'pagination', and '_links' keys.
    """
    if page is None:
        page = request.args.get('page', 1, type=int)
    if per_page is None:
        per_page = request.args.get('per_page', 20, type=int)

    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = pagination.items
    data = [serialize_fn(item) for item in items] if serialize_fn else items

    # Build relative links preserving non-pagination query params
    base_path = request.path
    extra_args = {k: v for k, v in request.args.items() if k not in ('page', 'per_page')}
    extra_qs = '&'.join(f'{k}={v}' for k, v in extra_args.items())
    if extra_qs:
        extra_qs = '&' + extra_qs

    def _page_url(p):
        return f'{base_path}?page={p}&per_page={per_page}{extra_qs}'

    links = {'self': _page_url(page)}
    if pagination.has_next:
        links['next'] = _page_url(page + 1)
    if pagination.has_prev:
        links['prev'] = _page_url(page - 1)

    return {
        'data': data,
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        },
        '_links': links,
    }
