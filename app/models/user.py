from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    preferred_categories = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    saved_papers = db.relationship('UserPaper', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    notes = db.relationship('Note', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    tags = db.relationship('Tag', backref='user', cascade='all, delete-orphan', lazy='dynamic')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'preferred_categories': self.preferred_categories or [],
            'created_at': self.created_at.isoformat(),
        }
