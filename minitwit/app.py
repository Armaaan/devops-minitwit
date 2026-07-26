# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application rewritten with FastAPI + SQLAlchemy + SQLite.

    Session 02: Refactored from Flask/Python2 to FastAPI/Python3.
    Session 05: DB abstraction layer introduced via SQLAlchemy ORM (no raw SQL).
    Session 06: Database migrated to PostgreSQL via DATABASE_URL env var.
"""

import os
import time
from hashlib import md5
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, Response, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, Message, Follower, get_db, init_db

# ─── Configuration ────────────────────────────────────────────────────────────
PER_PAGE = 30
SECRET_KEY = os.environ.get('SECRET_KEY', 'development key')
LATEST_FILE = os.environ.get('LATEST_FILE', '/data/latest_processed_sim_action_id.txt')
SIMULATOR_AUTH = "Basic c2ltdWxhdG9yOnN1cGVyX3NhZmUh"

# ─── App & Templates ──────────────────────────────────────────────────────────
app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')
serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE = 'mt_session'


# ─── Template filters ─────────────────────────────────────────────────────────

def format_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


templates.env.filters['datetimeformat'] = format_datetime
templates.env.filters['gravatar'] = gravatar_url


# ─── Session helpers ──────────────────────────────────────────────────────────

def get_session(request: Request) -> dict:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        try:
            return dict(serializer.loads(cookie, max_age=86400 * 7))
        except Exception:
            pass
    return {}


def set_session(response: Response, data: dict):
    response.set_cookie(SESSION_COOKIE, serializer.dumps(data),
                        httponly=True, samesite='lax')


def get_flashes(session_data: dict) -> list:
    return session_data.pop('_flashes', [])


def add_flash(session_data: dict, message: str):
    session_data.setdefault('_flashes', []).append(message)


# ─── Template helper ──────────────────────────────────────────────────────────

def render(template_name: str, request: Request, **ctx) -> HTMLResponse:
    tmpl = templates.env.get_template(template_name)
    ctx['request'] = request
    content = tmpl.render(**ctx)
    return HTMLResponse(content=content)


# ─── Message helper ───────────────────────────────────────────────────────────

def message_to_dict(msg: Message) -> dict:
    """Convert an ORM Message + its author to a template-compatible dict."""
    return {
        'message_id': msg.message_id,
        'author_id': msg.author_id,
        'text': msg.text,
        'pub_date': msg.pub_date,
        'flagged': msg.flagged,
        'username': msg.author.username,
        'email': msg.author.email,
        'user_id': msg.author.user_id,
    }


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event('startup')
def startup():
    init_db()


# ─── Web Routes ───────────────────────────────────────────────────────────────

@app.get('/public', response_class=HTMLResponse)
async def public_timeline(request: Request):
    session_data = get_session(request)
    db = get_db()
    user = db.get(User, session_data.get('user_id')) if 'user_id' in session_data else None
    messages = (db.query(Message)
                  .filter(Message.flagged == 0)
                  .order_by(Message.pub_date.desc())
                  .limit(PER_PAGE)
                  .all())
    msgs = [message_to_dict(m) for m in messages]
    flashes = get_flashes(session_data)
    db.close()
    response = render('timeline.html', request,
                      messages=msgs, user=user, flashes=flashes)
    set_session(response, session_data)
    return response


@app.get('/', response_class=HTMLResponse)
async def timeline(request: Request):
    session_data = get_session(request)
    db = get_db()
    user = db.get(User, session_data.get('user_id')) if 'user_id' in session_data else None
    if not user:
        db.close()
        return RedirectResponse(url='/public', status_code=302)
    followed_ids = [f.whom_id for f in user.following]
    messages = (db.query(Message)
                  .filter(Message.flagged == 0,
                          Message.author_id.in_([user.user_id] + followed_ids))
                  .order_by(Message.pub_date.desc())
                  .limit(PER_PAGE)
                  .all())
    msgs = [message_to_dict(m) for m in messages]
    flashes = get_flashes(session_data)
    db.close()
    user_dict = {'user_id': user.user_id, 'username': user.username, 'email': user.email}
    response = render('timeline.html', request,
                      messages=msgs, user=user_dict, flashes=flashes)
    set_session(response, session_data)
    return response


@app.get('/login', response_class=HTMLResponse)
async def login_get(request: Request):
    session_data = get_session(request)
    if 'user_id' in session_data:
        return RedirectResponse(url='/', status_code=302)
    flashes = get_flashes(session_data)
    response = render('login.html', request, error=None, flashes=flashes)
    set_session(response, session_data)
    return response


@app.post('/login', response_class=HTMLResponse)
async def login_post(request: Request,
                     username: str = Form(default=''),
                     password: str = Form(default='')):
    session_data = get_session(request)
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    error = None
    if user is None:
        error = 'Invalid username'
    elif not check_password_hash(user.pw_hash, password):
        error = 'Invalid password'
    else:
        add_flash(session_data, 'You were logged in')
        session_data['user_id'] = user.user_id
        response = RedirectResponse(url='/', status_code=302)
        set_session(response, session_data)
        return response
    response = render('login.html', request, error=error, flashes=[])
    set_session(response, session_data)
    return response


@app.get('/logout')
async def logout(request: Request):
    session_data = get_session(request)
    add_flash(session_data, 'You were logged out')
    session_data.pop('user_id', None)
    response = RedirectResponse(url='/public', status_code=302)
    set_session(response, session_data)
    return response


@app.get('/register', response_class=HTMLResponse)
async def register_get(request: Request):
    session_data = get_session(request)
    if 'user_id' in session_data:
        return RedirectResponse(url='/', status_code=302)
    flashes = get_flashes(session_data)
    response = render('register.html', request, error=None, flashes=flashes)
    set_session(response, session_data)
    return response


@app.post('/register')
async def register_post(request: Request, latest: int = -1):
    content_type = request.headers.get('content-type', '')

    # Simulator sends JSON
    if 'application/json' in content_type:
        update_latest(latest)
        body = await request.json()
        db = get_db()
        error = None
        if not body.get('username'):
            error = 'You have to enter a username'
        elif not body.get('email') or '@' not in body.get('email', ''):
            error = 'You have to enter a valid email address'
        elif not body.get('pwd'):
            error = 'You have to enter a password'
        elif db.query(User).filter(User.username == body['username']).first() is not None:
            error = 'The username is already taken'
        else:
            db.add(User(username=body['username'], email=body['email'],
                        pw_hash=generate_password_hash(body['pwd'])))
            db.commit()
            db.close()
            return Response(status_code=204)
        db.close()
        return JSONResponse(status_code=400, content={"status": 400, "error_msg": error})

    # Web browser sends form data
    form = await request.form()
    username = form.get('username', '')
    email = form.get('email', '')
    password = form.get('password', '')
    password2 = form.get('password2', '')
    session_data = get_session(request)
    db = get_db()
    error = None
    if not username:
        error = 'You have to enter a username'
    elif not email or '@' not in email:
        error = 'You have to enter a valid email address'
    elif not password:
        error = 'You have to enter a password'
    elif password != password2:
        error = 'The two passwords do not match'
    elif db.query(User).filter(User.username == username).first() is not None:
        error = 'The username is already taken'
    else:
        db.add(User(username=username, email=email,
                    pw_hash=generate_password_hash(password)))
        db.commit()
        db.close()
        add_flash(session_data, 'You were successfully registered and can login now')
        response = RedirectResponse(url='/login', status_code=302)
        set_session(response, session_data)
        return response
    db.close()
    response = render('register.html', request, error=error, flashes=[])
    set_session(response, session_data)
    return response


@app.post('/add_message')
async def add_message(request: Request, text: str = Form(default='')):
    session_data = get_session(request)
    if 'user_id' not in session_data:
        return Response(status_code=401)
    if text:
        db = get_db()
        db.add(Message(author_id=session_data['user_id'],
                       text=text,
                       pub_date=int(time.time()),
                       flagged=0))
        db.commit()
        db.close()
        add_flash(session_data, 'Your message was recorded')
    response = RedirectResponse(url='/', status_code=302)
    set_session(response, session_data)
    return response


# ─── Simulator API (Session 03) ───────────────────────────────────────────────

def update_latest(latest: int = -1):
    if latest != -1:
        with open(LATEST_FILE, 'w') as fp:
            fp.write(str(latest))


def check_sim_auth(authorization: Optional[str]) -> Optional[JSONResponse]:
    if authorization != SIMULATOR_AUTH:
        return JSONResponse(status_code=403,
                            content={"status": 403,
                                     "error_msg": "You are not authorized to use this resource!"})
    return None


@app.get('/latest')
async def get_latest():
    try:
        with open(LATEST_FILE) as fp:
            latest = int(fp.read().strip())
    except Exception:
        latest = -1
    return {"latest": latest}


@app.post('/msgs/{username}')
async def sim_messages_post(request: Request, username: str, latest: int = -1,
                            authorization: Optional[str] = Header(default=None)):
    update_latest(latest)
    err = check_sim_auth(authorization)
    if err:
        return err
    body = await request.json()
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        db.close()
        return Response(status_code=404)
    db.add(Message(author_id=user.user_id, text=body['content'],
                   pub_date=int(time.time()), flagged=0))
    db.commit()
    db.close()
    return Response(status_code=204)


@app.get('/msgs/{username}')
async def sim_messages_get(request: Request, username: str, no: int = 100,
                           latest: int = -1,
                           authorization: Optional[str] = Header(default=None)):
    update_latest(latest)
    err = check_sim_auth(authorization)
    if err:
        return err
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        db.close()
        return Response(status_code=404)
    messages = (db.query(Message)
                  .filter(Message.flagged == 0, Message.author_id == user.user_id)
                  .order_by(Message.pub_date.desc())
                  .limit(no).all())
    result = [{"content": m.text, "pub_date": m.pub_date,
               "user": m.author.username} for m in messages]
    db.close()
    return result


@app.get('/msgs')
async def sim_messages(request: Request, no: int = 100, latest: int = -1,
                       authorization: Optional[str] = Header(default=None)):
    update_latest(latest)
    err = check_sim_auth(authorization)
    if err:
        return err
    db = get_db()
    messages = (db.query(Message)
                  .filter(Message.flagged == 0)
                  .order_by(Message.pub_date.desc())
                  .limit(no).all())
    result = [{"content": m.text, "pub_date": m.pub_date,
               "user": m.author.username} for m in messages]
    db.close()
    return result


@app.get('/fllws/{username}')
async def sim_follow_get(request: Request, username: str, no: int = 100,
                         latest: int = -1,
                         authorization: Optional[str] = Header(default=None)):
    update_latest(latest)
    err = check_sim_auth(authorization)
    if err:
        return err
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        db.close()
        return Response(status_code=404)
    follows = (db.query(User)
                 .join(Follower, Follower.whom_id == User.user_id)
                 .filter(Follower.who_id == user.user_id)
                 .limit(no).all())
    result = {"follows": [u.username for u in follows]}
    db.close()
    return result


@app.post('/fllws/{username}')
async def sim_follow_post(request: Request, username: str, latest: int = -1,
                          authorization: Optional[str] = Header(default=None)):
    update_latest(latest)
    err = check_sim_auth(authorization)
    if err:
        return err
    body = await request.json()
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        db.close()
        return Response(status_code=404)
    if 'follow' in body:
        target = db.query(User).filter(User.username == body['follow']).first()
        if not target:
            db.close()
            return Response(status_code=404)
        db.add(Follower(who_id=user.user_id, whom_id=target.user_id))
        db.commit()
    elif 'unfollow' in body:
        target = db.query(User).filter(User.username == body['unfollow']).first()
        if not target:
            db.close()
            return Response(status_code=404)
        db.query(Follower).filter(
            Follower.who_id == user.user_id,
            Follower.whom_id == target.user_id
        ).delete()
        db.commit()
    db.close()
    return Response(status_code=204)


# ─── User routes — MUST be after all specific routes ──────────────────────────

@app.get('/{username}/follow')
async def follow_user(request: Request, username: str):
    session_data = get_session(request)
    if 'user_id' not in session_data:
        return Response(status_code=401)
    db = get_db()
    target = db.query(User).filter(User.username == username).first()
    if not target:
        db.close()
        return Response(status_code=404)
    db.add(Follower(who_id=session_data['user_id'], whom_id=target.user_id))
    db.commit()
    add_flash(session_data, 'You are now following "%s"' % username)
    db.close()
    response = RedirectResponse(url='/%s' % username, status_code=302)
    set_session(response, session_data)
    return response


@app.get('/{username}/unfollow')
async def unfollow_user(request: Request, username: str):
    session_data = get_session(request)
    if 'user_id' not in session_data:
        return Response(status_code=401)
    db = get_db()
    target = db.query(User).filter(User.username == username).first()
    if not target:
        db.close()
        return Response(status_code=404)
    db.query(Follower).filter(
        Follower.who_id == session_data['user_id'],
        Follower.whom_id == target.user_id
    ).delete()
    db.commit()
    add_flash(session_data, 'You are no longer following "%s"' % username)
    db.close()
    response = RedirectResponse(url='/%s' % username, status_code=302)
    set_session(response, session_data)
    return response


@app.get('/{username}', response_class=HTMLResponse)
async def user_timeline(request: Request, username: str):
    session_data = get_session(request)
    db = get_db()
    profile_user = db.query(User).filter(User.username == username).first()
    if not profile_user:
        db.close()
        return Response(status_code=404)
    user = db.get(User, session_data.get('user_id')) if 'user_id' in session_data else None
    followed = False
    if user:
        followed = db.query(Follower).filter(
            Follower.who_id == user.user_id,
            Follower.whom_id == profile_user.user_id
        ).first() is not None
    messages = (db.query(Message)
                  .filter(Message.flagged == 0,
                          Message.author_id == profile_user.user_id)
                  .order_by(Message.pub_date.desc())
                  .limit(PER_PAGE).all())
    msgs = [message_to_dict(m) for m in messages]
    flashes = get_flashes(session_data)
    profile_dict = {'user_id': profile_user.user_id,
                    'username': profile_user.username,
                    'email': profile_user.email}
    user_dict = {'user_id': user.user_id, 'username': user.username,
                 'email': user.email} if user else None
    db.close()
    response = render('timeline.html', request,
                      messages=msgs, user=user_dict,
                      profile_user=profile_dict, followed=followed, flashes=flashes)
    set_session(response, session_data)
    return response