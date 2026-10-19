"""Initialize the local SQLite install without saving a plaintext password."""
from datetime import datetime
from getpass import getpass
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def initialize(root):
    backend = root / "backend"
    database = backend / "street-side.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    os.environ["UPLOAD_DIR"] = str(backend / "uploads")
    os.environ.pop("MENU_PROFILE", None)
    os.environ.pop("ADMIN_PASSWORD", None)
    os.environ["ADMIN_USERNAME"] = "admin"
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    if database.exists():
        backups = root / "backups"
        backups.mkdir(exist_ok=True)
        target = backups / ("before-setup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".db")
        with sqlite3.connect(database) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        print("Existing database backed up to", target)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import select
    from app.seed import seed
    with SessionLocal() as db:
        existing_user = db.scalar(select(User.id).limit(1))
    if not existing_user:
        print("Create the owner's admin password (12-200 characters). Typing is hidden.")
        while True:
            password = getpass("New admin password: ")
            if not 12 <= len(password) <= 200 or password != password.strip():
                print("Use 12-200 characters without leading/trailing spaces.")
                continue
            if password != getpass("Confirm password: "):
                print("Passwords did not match. Try again.")
                continue
            os.environ["ADMIN_PASSWORD"] = password
            break
    try:
        seed()
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    print("Database ready. Existing users and menu edits were preserved." if existing_user else "Database ready. Sign in as admin with the password you just created.")


if __name__ == "__main__":
    initialize(Path(__file__).resolve().parents[1])
