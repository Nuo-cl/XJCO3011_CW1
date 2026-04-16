import logging
import random

from app import db
from app.models.paper import Paper, UserPaper
from app.services.arxiv_service import ArxivService

logger = logging.getLogger(__name__)


class RecommendationService:
    """Personalized paper recommendations and random discovery."""

    # Target counts for warm-start mixing strategy
    SIMILARITY_COUNT = 7
    CATEGORY_COUNT = 3
    TOTAL_TARGET = 10

    @classmethod
    def daily_recommendations(cls, user, chromadb_service=None):
        """Generate daily paper recommendations for a user.

        Returns:
            Tuple of (list[Paper], strategy_name, metadata_dict).
            metadata_dict contains extra context such as saved_count.
        """
        saved_count = UserPaper.query.filter_by(user_id=user.id).count()
        meta = {'saved_count': saved_count}

        if saved_count == 0:
            papers, strategy = cls._cold_start(user, chromadb_service)
        else:
            papers, strategy = cls._warm_start(user, chromadb_service)

        return papers, strategy, meta

    @classmethod
    def _cold_start(cls, user, chromadb_service):
        """Recommend based on preferred categories only."""
        categories = user.preferred_categories or []
        if not categories:
            from app.utils.errors import APIError
            raise APIError(
                'Set preferred_categories in your profile first '
                '(PUT /api/users/me).',
                400,
            )

        saved_ids = cls._get_saved_arxiv_ids(user.id)
        seen = set()
        papers = []

        for cat in categories[:3]:
            try:
                batch = ArxivService.trending(
                    category=cat,
                    days=7,
                    max_results=10,
                    chromadb_service=chromadb_service,
                )
                for p in batch:
                    if p.arxiv_id not in seen and p.arxiv_id not in saved_ids:
                        seen.add(p.arxiv_id)
                        papers.append(p)
            except Exception as e:
                logger.warning('Cold start trending fetch failed for %s: %s', cat, e)

        return papers[:cls.TOTAL_TARGET], 'cold_start'

    @classmethod
    def _warm_start(cls, user, chromadb_service):
        """Recommend via similarity + fresh category papers."""
        saved_ids = cls._get_saved_arxiv_ids(user.id)
        seen = set(saved_ids)
        papers = []

        # --- Similarity-based portion ---
        sim_papers = cls._similarity_recommendations(
            user, chromadb_service, saved_ids, seen,
        )
        papers.extend(sim_papers)

        # --- Category-based freshness portion ---
        cat_papers = cls._category_recommendations(
            user, chromadb_service, seen,
        )
        papers.extend(cat_papers)

        return papers[:cls.TOTAL_TARGET], 'warm_start'

    @classmethod
    def _similarity_recommendations(cls, user, chromadb_service, saved_ids, seen):
        """Find papers similar to user's saved papers via ChromaDB."""
        if not chromadb_service:
            return []

        recent_saved = (
            UserPaper.query
            .filter_by(user_id=user.id)
            .order_by(UserPaper.saved_at.desc())
            .limit(10)
            .all()
        )
        if not recent_saved:
            return []

        seed = random.choice(recent_saved)
        query_text = seed.paper.abstract
        if not query_text:
            return []

        try:
            # Fetch extra results to allow filtering
            results = chromadb_service.search_papers(
                query=query_text,
                n_results=30,
            )
        except Exception as e:
            logger.warning('ChromaDB similarity search failed: %s', e)
            return []

        papers = []
        if results and results.get('ids') and results['ids'][0]:
            metadatas = results.get('metadatas', [[]])[0]
            for meta in metadatas:
                arxiv_id = meta.get('arxiv_id', '')
                if arxiv_id and arxiv_id not in seen:
                    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
                    if paper:
                        seen.add(arxiv_id)
                        papers.append(paper)
                        if len(papers) >= cls.SIMILARITY_COUNT:
                            break

        return papers

    @classmethod
    def _category_recommendations(cls, user, chromadb_service, seen):
        """Fetch fresh papers from a preferred or inferred category."""
        categories = user.preferred_categories or []

        # Fallback: infer categories from saved papers
        if not categories:
            recent = (
                UserPaper.query
                .filter_by(user_id=user.id)
                .order_by(UserPaper.saved_at.desc())
                .limit(5)
                .all()
            )
            for up in recent:
                if up.paper.categories:
                    categories.extend(up.paper.categories.split())
            categories = list(set(categories))

        if not categories:
            return []

        cat = random.choice(categories)
        papers = []
        try:
            batch = ArxivService.trending(
                category=cat,
                days=7,
                max_results=15,
                chromadb_service=chromadb_service,
            )
            for p in batch:
                if p.arxiv_id not in seen:
                    seen.add(p.arxiv_id)
                    papers.append(p)
                    if len(papers) >= cls.CATEGORY_COUNT:
                        break
        except Exception as e:
            logger.warning('Category trending fetch failed for %s: %s', cat, e)

        return papers

    @staticmethod
    def _get_saved_arxiv_ids(user_id):
        """Return a set of arxiv_ids for papers saved by the user."""
        rows = (
            db.session.query(Paper.arxiv_id)
            .join(UserPaper, UserPaper.paper_id == Paper.id)
            .filter(UserPaper.user_id == user_id)
            .all()
        )
        return {r[0] for r in rows}

    @staticmethod
    def discover_random(category, days=7, count=5, chromadb_service=None):
        """Return a random subset of recent papers in a category."""
        papers = ArxivService.trending(
            category=category,
            days=days,
            max_results=max(count * 4, 20),
            chromadb_service=chromadb_service,
        )
        if len(papers) <= count:
            return papers
        return random.sample(papers, count)
