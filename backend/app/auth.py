import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .models import User, Session, now
from .schemas import Login

router = APIRouter(prefix='/api/auth', tags=['Authentication'])
hasher = PasswordHasher()
COOKIE = 'streetside_session'
attempts = defaultdict(deque)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def session_user(token, db):
    session = db.get(Session, token_hash(token or ''))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= now():
        return None
    return db.get(User, session.user_id)


def current_user(request: Request, db: DBSession = Depends(get_db)):
    user = session_user(request.cookies.get(COOKIE), db)
    if not user:
        raise HTTPException(401, 'Please sign in again')
    return user


def roles(*allowed):
    def check(user: User = Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, 'Your role cannot perform this action')
        return user
    return check


@router.post('/login')
def login(data: Login, request: Request, response: Response, db: DBSession = Depends(get_db)):
    key = request.client.host if request.client else 'unknown'
    queue = attempts[key]
    stamp = time.monotonic()
    while queue and queue[0] < stamp - 60:
        queue.popleft()
    if len(queue) >= 15:
        raise HTTPException(429, 'Too many sign-in attempts. Wait one minute.')
    queue.append(stamp)
    user = db.scalar(select(User).where(User.username == data.username.lower()))
    try:
        valid = hasher.verify(user.password_hash if user else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not user:
        raise HTTPException(401, 'Incorrect username or password')
    db.execute(delete(Session).where(Session.expires_at < now()))
    token = secrets.token_urlsafe(48)
    db.add(Session(token_hash=token_hash(token), user_id=user.id, expires_at=now() + timedelta(hours=12)))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', samesite='strict', max_age=43200, path='/')
    return {'id': user.id, 'username': user.username, 'role': user.role}


@router.post('/logout')
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    db.execute(delete(Session).where(Session.token_hash == token_hash(request.cookies.get(COOKIE, ''))))
    db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


@router.get('/me')
def me(user: User = Depends(current_user)):
    return {'id': user.id, 'username': user.username, 'role': user.role}
