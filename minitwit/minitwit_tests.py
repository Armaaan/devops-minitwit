# -*- coding: utf-8 -*-
"""
    MiniTwit Integration Tests
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the MiniTwit FastAPI application.
    Adapted from the original Flask tests (session 02).
    Session 05: Updated to use ORM for DB reset instead of raw SQL.
    Session 07: Serves as quality gate in CI chain.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use a temporary database for tests
_db_fd, _db_path = tempfile.mkstemp(suffix='.db')
os.close(_db_fd)
os.environ['DATABASE_URL'] = f'sqlite:///{_db_path}'

import models
import app as minitwit_app
from app import app
from models import init_db, get_db, User, Message, Follower, Base, engine

client = TestClient(app, follow_redirects=True)


@pytest.fixture(autouse=True)
def reset_db():
    """Before each test, drop and recreate all tables via ORM."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def register(username, password, password2=None, email=None):
    if password2 is None:
        password2 = password
    if email is None:
        email = username + '@example.com'
    return client.post('/register', data={
        'username': username, 'password': password,
        'password2': password2, 'email': email,
    })


def login(username, password):
    return client.post('/login', data={'username': username, 'password': password})


def register_and_login(username, password):
    register(username, password)
    return login(username, password)


def logout():
    return client.get('/logout')


def add_message(text):
    rv = client.post('/add_message', data={'text': text})
    if text:
        assert 'Your message was recorded' in rv.text
    return rv


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_register():
    rv = register('user1', 'default')
    assert 'You were successfully registered' in rv.text
    rv = register('user1', 'default')
    assert 'The username is already taken' in rv.text
    rv = register('', 'default')
    assert 'You have to enter a username' in rv.text
    rv = register('meh', '')
    assert 'You have to enter a password' in rv.text
    rv = register('meh', 'x', 'y')
    assert 'The two passwords do not match' in rv.text
    rv = register('meh', 'foo', email='broken')
    assert 'You have to enter a valid email address' in rv.text


def test_login_logout():
    register_and_login('user1', 'default')
    rv = login('user1', 'default')
    assert 'You were logged in' in rv.text
    rv = logout()
    assert 'You were logged out' in rv.text
    rv = login('user1', 'wrongpassword')
    assert 'Invalid password' in rv.text
    rv = login('user2', 'wrongpassword')
    assert 'Invalid username' in rv.text


def test_message_recording():
    register_and_login('foo', 'default')
    add_message('test message 1')
    add_message('<test message 2>')
    rv = client.get('/')
    assert 'test message 1' in rv.text
    assert '&lt;test message 2&gt;' in rv.text


def test_timelines():
    register_and_login('foo', 'default')
    add_message('the message by foo')
    logout()
    register_and_login('bar', 'default')
    add_message('the message by bar')
    rv = client.get('/public')
    assert 'the message by foo' in rv.text
    assert 'the message by bar' in rv.text

    rv = client.get('/')
    assert 'the message by foo' not in rv.text
    assert 'the message by bar' in rv.text

    rv = client.get('/foo/follow')
    assert 'You are now following' in rv.text

    rv = client.get('/')
    assert 'the message by foo' in rv.text
    assert 'the message by bar' in rv.text

    rv = client.get('/bar')
    assert 'the message by foo' not in rv.text
    assert 'the message by bar' in rv.text
    rv = client.get('/foo')
    assert 'the message by foo' in rv.text
    assert 'the message by bar' not in rv.text

    rv = client.get('/foo/unfollow')
    assert 'You are no longer following' in rv.text
    rv = client.get('/')
    assert 'the message by foo' not in rv.text
    assert 'the message by bar' in rv.text
