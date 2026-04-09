import json
import logging
from datetime import date, datetime, timedelta
from itertools import islice

import arxiv

from app import db
from app.models.paper import Paper

logger = logging.getLogger(__name__)


class ArxivService:
    """Wrapper for arXiv API: search, fetch, cache, and ChromaDB sync."""

    # Reuse a single client to avoid repeated handshake overhead.
    # delay_seconds is the polite wait between paged requests; 1.0s is within
    # arXiv's fair-use guidelines while being faster than the 3.0s default.
    _client = arxiv.Client(page_size=20, delay_seconds=1.0, num_retries=3)

    @staticmethod
    def _paper_from_result(result):
        """Convert an arxiv.Result to a Paper model (or return existing cached one)."""
        arxiv_id = result.entry_id.split('/abs/')[-1]
        # Strip version suffix (e.g. "2401.12345v2" -> "2401.12345")
        if 'v' in arxiv_id:
            arxiv_id = arxiv_id.rsplit('v', 1)[0]

        existing = Paper.query.filter_by(arxiv_id=arxiv_id).first()
        if existing:
            return existing

        paper = Paper(
            arxiv_id=arxiv_id,
            title=result.title.replace('\n', ' ').strip(),
            authors=json.dumps([a.name for a in result.authors]),
            abstract=result.summary.replace('\n', ' ').strip(),
            categories=' '.join(result.categories),
            published_date=result.published.date() if result.published else date.today(),
            arxiv_url=result.entry_id,
            pdf_url=result.pdf_url or '',
        )
        db.session.add(paper)
        return paper

    @staticmethod
    def _sync_to_chromadb(paper, chromadb_service):
        """Sync a paper's abstract to ChromaDB for semantic search."""
        if chromadb_service and paper.abstract:
            try:
                chromadb_service.add_paper(
                    paper_id=paper.id,
                    abstract=paper.abstract,
                    metadata={
                        'arxiv_id': paper.arxiv_id,
                        'title': paper.title,
                        'categories': paper.categories,
                        'published_date': paper.published_date.isoformat(),
                    },
                )
            except Exception as e:
                logger.warning('ChromaDB sync failed for paper %s: %s', paper.arxiv_id, e)

    @staticmethod
    def _build_query(query, category=None, date_from=None, date_to=None):
        """Build an arXiv API query string with optional category and date filters."""
        parts = []

        if category:
            parts.append(f'cat:{category}')

        if query and query != '*':
            parts.append(f'all:{query}')

        # Embed date range directly in the arXiv query using submittedDate
        if date_from or date_to:
            start = date_from.replace('-', '') if date_from else '190001010000'
            end = date_to.replace('-', '') + '2359' if date_to else '209912312359'
            if len(start) == 8:
                start += '0000'
            parts.append(f'submittedDate:[{start} TO {end}]')

        if not parts:
            # Wrap bare query consistently with all: prefix
            return f'all:{query}' if query else 'all:*'

        return ' AND '.join(parts)

    # Maximum number of results to fetch from arXiv in a single request
    MAX_ARXIV_FETCH = 100

    @classmethod
    def search(cls, query, category=None, date_from=None, date_to=None,
               max_results=20, offset=0, chromadb_service=None):
        """Search arXiv and cache results locally.

        Args:
            offset: Number of results to skip (for pagination).
            max_results: Number of results to return (after skipping).
        """
        search_query = cls._build_query(query, category, date_from, date_to)

        # Cap total fetch to avoid over-requesting from arXiv
        fetch_count = min(offset + max_results, cls.MAX_ARXIV_FETCH)

        search = arxiv.Search(
            query=search_query,
            max_results=fetch_count,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        for result in islice(cls._client.results(search), offset, offset + max_results):
            paper = cls._paper_from_result(result)
            papers.append(paper)

        db.session.commit()

        # Sync to ChromaDB
        for paper in papers:
            cls._sync_to_chromadb(paper, chromadb_service)

        return papers

    @classmethod
    def fetch_by_id(cls, arxiv_id, chromadb_service=None):
        """Fetch a single paper by arXiv ID. Returns cached version if available."""
        existing = Paper.query.filter_by(arxiv_id=arxiv_id).first()
        if existing:
            return existing

        search = arxiv.Search(id_list=[arxiv_id])
        results = list(cls._client.results(search))
        if not results:
            return None

        paper = cls._paper_from_result(results[0])
        db.session.commit()
        cls._sync_to_chromadb(paper, chromadb_service)
        return paper

    @classmethod
    def trending(cls, category, days=7, max_results=20, offset=0, chromadb_service=None):
        """Get recent papers in a category using date-range query."""
        date_from = (date.today() - timedelta(days=days)).isoformat()
        date_to = date.today().isoformat()
        return cls.search(
            query=None,
            category=category,
            date_from=date_from,
            date_to=date_to,
            max_results=max_results,
            offset=offset,
            chromadb_service=chromadb_service,
        )
