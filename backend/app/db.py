import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.engine import URL
from .config import normalize_database_url


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL and os.getenv('DATABASE_HOST'):
    DATABASE_URL = URL.create('postgresql+psycopg', username=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'], host=os.environ['DATABASE_HOST'], database=os.environ['POSTGRES_DB']).render_as_string(hide_password=False)
DATABASE_URL = normalize_database_url(DATABASE_URL or 'sqlite:///./street-side.db')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **(
    {'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else {}
))
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
