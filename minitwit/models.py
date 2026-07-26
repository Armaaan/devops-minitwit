# -*- coding: utf-8 -*-
"""
    models.py
    ~~~~~~~~~

    SQLAlchemy ORM models for MiniTwit.
    Introduced in session 05 task 3: DB abstraction layer — no raw SQL in app.py.
    Database: SQLite (migrated to PostgreSQL in session 06 task 2).
"""

import os
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/minitwit.db')

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}
                       if DATABASE_URL.startswith('sqlite') else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ─── ORM Models ───────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = 'user'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    pw_hash = Column(String, nullable=False)

    messages = relationship('Message', back_populates='author',
                            foreign_keys='Message.author_id')
    following = relationship('Follower', back_populates='who',
                             foreign_keys='Follower.who_id')
    followers = relationship('Follower', back_populates='whom',
                             foreign_keys='Follower.whom_id')


class Message(Base):
    __tablename__ = 'message'

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    text = Column(String, nullable=False)
    pub_date = Column(Integer)
    flagged = Column(Integer, default=0)

    author = relationship('User', back_populates='messages',
                          foreign_keys=[author_id])


class Follower(Base):
    __tablename__ = 'follower'

    who_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)
    whom_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)

    who = relationship('User', back_populates='following',
                       foreign_keys=[who_id])
    whom = relationship('User', back_populates='followers',
                        foreign_keys=[whom_id])


def init_db():
    """Create all tables. Idempotent — safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Return a new database session."""
    return SessionLocal()
