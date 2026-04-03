import json
import logging
from datetime import date, datetime, timedelta

import arxiv

from app import db
from app.models.paper import Paper

logger = logging.getLogger(__name__)


class ArxivService:
    """Wrapper for arXiv API: search, fetch, cache, and ChromaDB sync."""

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

    @classmethod
    def search(cls, query, category=None, date_from=None, date_to=None,
               max_results=20, chromadb_service=None):
        """Search arXiv and cache results locally."""
        search_query = query
        if category:
            search_query = f'cat:{category} AND all:{query}'

        client = arxiv.Client()
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        for result in client.results(search):
            paper = cls._paper_from_result(result)
            papers.append(paper)

        db.session.commit()

        # Filter by date range after caching
        if date_from:
            d = date.fromisoformat(date_from)
            papers = [p for p in papers if p.published_date >= d]
        if date_to:
            d = date.fromisoformat(date_to)
            papers = [p for p in papers if p.published_date <= d]

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

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        if not results:
            return None

        paper = cls._paper_from_result(results[0])
        db.session.commit()
        cls._sync_to_chromadb(paper, chromadb_service)
        return paper

    @classmethod
    def trending(cls, category, days=7, max_results=20, chromadb_service=None):
        """Get recent papers in a category."""
        return cls.search(
            query='*',
            category=category,
            date_from=(date.today() - timedelta(days=days)).isoformat(),
            max_results=max_results,
            chromadb_service=chromadb_service,
        )
