"""ScholarTrack MCP Server — exposes core API functionality as tools for AI assistants.

Calls the service/database layer directly (not via HTTP).
Configure in Claude Desktop or Claude Code as a local MCP server.

Usage:
    python mcp_server.py [--user-id USER_ID]
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta

from mcp.server.fastmcp import FastMCP

# Bootstrap Flask app for database access
from app import create_app, db
from app.models.user import User
from app.models.paper import Paper, UserPaper
from app.models.note import Note
from app.models.flashcard import Flashcard, ReviewLog
from app.services.arxiv_service import ArxivService
from app.services.sm2_service import SM2Service

mcp = FastMCP("ScholarTrack")

# Global Flask app and default user
_app = None
_user_id = 1


def _get_app():
    global _app
    if _app is None:
        _app = create_app('development')
    return _app


def _chromadb():
    return _get_app().extensions.get('chromadb')


@mcp.tool()
def search_papers(query: str, category: str = None, days: int = 30) -> str:
    """Search arXiv for papers by keyword and optional category.

    Args:
        query: Search keywords (e.g. "vision transformer").
        category: arXiv category filter (e.g. "cs.CV"). Optional.
        days: Only return papers from the last N days. Default 30.
    """
    with _get_app().app_context():
        date_from = (date.today() - timedelta(days=days)).isoformat()
        date_to = date.today().isoformat()
        papers = ArxivService.search(
            query=query,
            category=category,
            date_from=date_from,
            date_to=date_to,
            max_results=10,
            chromadb_service=_chromadb(),
        )
        results = [p.to_dict() for p in papers]
        return json.dumps(results, indent=2)


@mcp.tool()
def get_trending_papers(category: str, days: int = 7) -> str:
    """Get recent trending papers in a specific arXiv category.

    Args:
        category: arXiv category (e.g. "cs.CV", "cs.CL", "cs.AI").
        days: Number of days to look back. Default 7.
    """
    with _get_app().app_context():
        papers = ArxivService.trending(
            category=category,
            days=days,
            max_results=10,
            chromadb_service=_chromadb(),
        )
        results = [p.to_dict() for p in papers]
        return json.dumps(results, indent=2)


@mcp.tool()
def save_paper(arxiv_id: str, memo: str = None) -> str:
    """Save a paper to the user's personal library.

    Args:
        arxiv_id: The arXiv paper ID (e.g. "2401.12345").
        memo: Optional personal note about why you're saving this paper.
    """
    with _get_app().app_context():
        paper = ArxivService.fetch_by_id(arxiv_id, chromadb_service=_chromadb())
        if not paper:
            return json.dumps({'error': f'Paper {arxiv_id} not found on arXiv.'})

        existing = UserPaper.query.filter_by(user_id=_user_id, paper_id=paper.id).first()
        if existing:
            return json.dumps({'message': 'Paper already saved.', 'arxiv_id': arxiv_id})

        up = UserPaper(user_id=_user_id, paper_id=paper.id, memo=memo)
        db.session.add(up)
        db.session.commit()
        return json.dumps({'message': 'Paper saved.', 'arxiv_id': arxiv_id, 'title': paper.title})


@mcp.tool()
def list_library() -> str:
    """List all papers in the user's personal library."""
    with _get_app().app_context():
        user_papers = UserPaper.query.filter_by(user_id=_user_id).order_by(
            UserPaper.saved_at.desc()
        ).limit(20).all()

        results = []
        for up in user_papers:
            results.append({
                'arxiv_id': up.paper.arxiv_id,
                'title': up.paper.title,
                'memo': up.memo,
                'tags': [upt.tag.name for upt in up.tags],
                'saved_at': up.saved_at.isoformat(),
            })
        return json.dumps(results, indent=2)


@mcp.tool()
def create_note(arxiv_id: str, content: str) -> str:
    """Create a short insight note linked to a paper (max 1000 characters).

    Args:
        arxiv_id: arXiv paper ID to link the note to (required).
        content: Insight content (max 1000 characters).
    """
    with _get_app().app_context():
        from app.models.note import NOTE_MAX_LENGTH
        if len(content) > NOTE_MAX_LENGTH:
            return json.dumps({'error': f'Content exceeds {NOTE_MAX_LENGTH} characters.'})

        paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
        if not paper:
            return json.dumps({'error': f'Paper {arxiv_id} not found.'})

        note = Note(user_id=_user_id, paper_id=paper.id, content=content)
        db.session.add(note)
        db.session.commit()

        # Sync to ChromaDB
        service = _chromadb()
        if service:
            try:
                service.add_note(
                    note_id=note.id,
                    content=content,
                    metadata={
                        'user_id': _user_id,
                        'paper_id': arxiv_id,
                        'created_at': note.created_at.isoformat(),
                    },
                )
            except Exception:
                pass

        return json.dumps({
            'message': 'Note created.',
            'id': note.id,
            'arxiv_id': arxiv_id,
            'preview': content[:100],
        })


@mcp.tool()
def search_notes(query: str) -> str:
    """Semantic search across your personal research notes.

    Args:
        query: Natural language search query.
    """
    with _get_app().app_context():
        service = _chromadb()
        if not service:
            return json.dumps([])

        try:
            results = service.search_notes(query, user_id=_user_id, n_results=5)
        except Exception:
            return json.dumps([])

        items = []
        if results and results.get('ids') and results['ids'][0]:
            for doc_id, distance in zip(results['ids'][0], results['distances'][0]):
                try:
                    note_id = int(doc_id.replace('note_', ''))
                    note = db.session.get(Note, note_id)
                    if note:
                        items.append({
                            'id': note.id,
                            'preview': note.content[:100],
                            'arxiv_id': note.paper.arxiv_id if note.paper else None,
                            'relevance_score': round(max(0, 1 - distance), 4),
                        })
                except (ValueError, AttributeError):
                    continue
        return json.dumps(items, indent=2)


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Search across both papers and personal notes for relevant knowledge.

    Args:
        query: Natural language search query.
    """
    with _get_app().app_context():
        service = _chromadb()
        if not service:
            return json.dumps([])

        try:
            combined = service.search_all(query, user_id=_user_id, n_results=5)
        except Exception:
            return json.dumps([])

        items = []
        # Process papers
        paper_results = combined.get('papers')
        if paper_results and paper_results.get('ids') and paper_results['ids'][0]:
            for doc_id, distance, meta in zip(
                paper_results['ids'][0],
                paper_results['distances'][0],
                paper_results['metadatas'][0],
            ):
                items.append({
                    'type': 'paper',
                    'arxiv_id': meta.get('arxiv_id', ''),
                    'title': meta.get('title', ''),
                    'relevance_score': round(max(0, 1 - distance), 4),
                })

        # Process notes
        note_results = combined.get('notes')
        if note_results and note_results.get('ids') and note_results['ids'][0]:
            for doc_id, distance in zip(note_results['ids'][0], note_results['distances'][0]):
                try:
                    note_id = int(doc_id.replace('note_', ''))
                    note = db.session.get(Note, note_id)
                    if note:
                        items.append({
                            'type': 'note',
                            'id': note.id,
                            'preview': note.content[:100],
                            'arxiv_id': note.paper.arxiv_id if note.paper else None,
                            'relevance_score': round(max(0, 1 - distance), 4),
                        })
                except (ValueError, AttributeError):
                    continue

        items.sort(key=lambda x: x['relevance_score'], reverse=True)
        return json.dumps(items, indent=2)


@mcp.tool()
def get_due_flashcards() -> str:
    """Get flashcards that are due for review today."""
    with _get_app().app_context():
        now = datetime.utcnow()
        cards = Flashcard.query.filter(
            Flashcard.user_id == _user_id,
            Flashcard.next_review_at <= now,
        ).order_by(Flashcard.next_review_at.asc()).limit(20).all()

        results = []
        for card in cards:
            results.append({
                'id': card.id,
                'question': card.question,
                'answer': card.answer,
                'ease_factor': card.ease_factor,
                'interval': card.interval,
            })
        return json.dumps(results, indent=2)


@mcp.tool()
def review_flashcard(flashcard_id: int, rating: int) -> str:
    """Submit a review rating for a flashcard (SM-2 spaced repetition).

    Args:
        flashcard_id: The ID of the flashcard to review.
        rating: Score from 0-5 (0=forgot completely, 5=perfect recall).
    """
    with _get_app().app_context():
        card = db.session.get(Flashcard, flashcard_id)
        if not card or card.user_id != _user_id:
            return json.dumps({'error': 'Flashcard not found.'})

        if rating < 0 or rating > 5:
            return json.dumps({'error': 'Rating must be 0-5.'})

        updated = SM2Service.review(card, rating)
        card.ease_factor = updated['ease_factor']
        card.interval = updated['interval']
        card.repetitions = updated['repetitions']
        card.next_review_at = updated['next_review_at']

        log = ReviewLog(user_id=_user_id, flashcard_id=card.id, rating=rating)
        db.session.add(log)
        db.session.commit()

        return json.dumps({
            'message': 'Review recorded.',
            'next_review_at': card.next_review_at.isoformat(),
            'interval': card.interval,
            'ease_factor': card.ease_factor,
        })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ScholarTrack MCP Server')
    parser.add_argument('--user-id', type=int, default=1, help='Default user ID')
    args = parser.parse_args()
    _user_id = args.user_id
    mcp.run()
