"""Staff password rotation without exposing passwords in command-line arguments."""
import argparse
from getpass import getpass
from sqlalchemy import select, delete
from .db import SessionLocal
from .models import User, Session
from .auth import hasher


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['reset-password'])
    parser.add_argument('username')
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username.lower()))
        if not user:
            raise SystemExit('User not found')
        password = getpass('New password (12+ characters): ')
        if len(password) < 12 or len(password) > 200 or password != password.strip():
            raise SystemExit('Use 12–200 characters without leading or trailing whitespace')
        if password != getpass('Confirm password: '):
            raise SystemExit('Passwords did not match')
        user.password_hash = hasher.hash(password)
        db.execute(delete(Session).where(Session.user_id == user.id))
        db.commit()
    print('Password updated and existing sessions revoked.')


if __name__ == '__main__':
    main()
