"""Container bootstrap; migrations and seed must succeed before accepting requests."""
import os
import subprocess
import sys
from sqlalchemy.engine import URL

if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = URL.create(
        'postgresql+psycopg', username=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
        host=os.environ.get('DATABASE_HOST', 'db'), database=os.environ['POSTGRES_DB']
    ).render_as_string(hide_password=False)
subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
subprocess.run([sys.executable, '-m', 'app.seed'], check=True)
os.execvp(sys.executable, [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', os.getenv('PORT', '8000'), '--workers', '1'])
