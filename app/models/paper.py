from datetime import datetime

from app import db


class Paper(db.Model):
    __tablename__ = 'paper'

    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text, nullable=False)  # JSON array as string
    abstract = db.Column(db.Text, nullable=False)
    categories = db.Column(db.String(200), nullable=False)
    published_date = db.Column(db.Date, nullable=False, index=True)
    arxiv_url = db.Column(db.String(300), nullable=False)
    pdf_url = db.Column(db.String(300), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'authors': json.loads(self.authors) if self.authors else [],
            'abstract': self.abstract,
            'categories': self.categories,
            'published_date': self.published_date.isoformat(),
            'arxiv_url': self.arxiv_url,
            'pdf_url': self.pdf_url,
            'fetched_at': self.fetched_at.isoformat(),
        }


class UserPaper(db.Model):
    __tablename__ = 'user_paper'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'paper_id', name='uq_user_paper'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False, index=True)
    memo = db.Column(db.Text)
    saved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    paper = db.relationship('Paper', lazy='joined')
    tags = db.relationship('UserPaperTag', backref='user_paper', cascade='all, delete-orphan', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'paper': self.paper.to_dict(),
            'memo': self.memo,
            'tags': [upt.tag.name for upt in self.tags],
            'saved_at': self.saved_at.isoformat(),
        }


class Tag(db.Model):
    __tablename__ = 'tag'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_user_tag'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }


class UserPaperTag(db.Model):
    __tablename__ = 'user_paper_tag'
    __table_args__ = (
        db.UniqueConstraint('user_paper_id', 'tag_id', name='uq_user_paper_tag'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_paper_id = db.Column(db.Integer, db.ForeignKey('user_paper.id'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False, index=True)

    tag = db.relationship('Tag', lazy='joined')
