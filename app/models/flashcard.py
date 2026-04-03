from datetime import datetime

from app import db


class Flashcard(db.Model):
    __tablename__ = 'flashcard'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    ease_factor = db.Column(db.Float, nullable=False, default=2.5)
    interval = db.Column(db.Integer, nullable=False, default=1)
    repetitions = db.Column(db.Integer, nullable=False, default=0)
    next_review_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    reviews = db.relationship('ReviewLog', backref='flashcard', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'note_id': self.note_id,
            'question': self.question,
            'answer': self.answer,
            'ease_factor': self.ease_factor,
            'interval': self.interval,
            'repetitions': self.repetitions,
            'next_review_at': self.next_review_at.isoformat(),
            'created_at': self.created_at.isoformat(),
        }


class ReviewLog(db.Model):
    __tablename__ = 'review_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcard.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'flashcard_id': self.flashcard_id,
            'rating': self.rating,
            'reviewed_at': self.reviewed_at.isoformat(),
        }
