from datetime import datetime

from app import db

# Maximum length for a single insight/note (characters)
NOTE_MAX_LENGTH = 1000


class Note(db.Model):
    __tablename__ = 'note'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper = db.relationship('Paper', lazy='joined')
    flashcards = db.relationship('Flashcard', backref='note', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'paper_id': self.paper_id,
            'arxiv_id': self.paper.arxiv_id if self.paper else None,
            'content': self.content,
            'preview': self.content[:100] + ('...' if len(self.content) > 100 else ''),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
