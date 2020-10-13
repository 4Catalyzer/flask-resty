# example/models.py

import datetime as dt
from flask_sqlalchemy import SQLAlchemy

from . import app

db = SQLAlchemy(app)


class Author(db.Model):
    __tablename__ = "example_authors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, default=dt.datetime.utcnow, nullable=False
    )


class Book(db.Model):
    __tablename__ = "example_books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey(Author.id), nullable=False)
    author = db.relationship(Author, backref=db.backref("books"))
    published_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(
        db.DateTime, default=dt.datetime.utcnow, nullable=False
    )
