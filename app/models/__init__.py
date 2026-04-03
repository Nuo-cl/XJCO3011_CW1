from app import db
from app.models.user import User
from app.models.paper import Paper, UserPaper, Tag, UserPaperTag
from app.models.note import Note
from app.models.flashcard import Flashcard, ReviewLog

__all__ = [
    'db', 'User', 'Paper', 'UserPaper', 'Tag', 'UserPaperTag',
    'Note', 'Flashcard', 'ReviewLog',
]
