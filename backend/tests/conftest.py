import os
from pathlib import Path
from uuid import uuid4
import pytest

# TEST_DATABASE_URL must point at a disposable PostgreSQL database when set.
os.environ['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL', f'sqlite:///{Path(__file__).parent / "test.db"}')
os.environ['ADMIN_PASSWORD'] = 'test-only-password-123'
os.environ['MENU_PROFILE'] = 'demo'
os.environ['UPLOAD_DIR'] = str(Path(__file__).parent / 'uploads')

from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.main import app
from app.models import User
from app.seed import seed
from app.auth import attempts, hasher


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()
    seed()
    with SessionLocal() as db:
        for role in ['cashier', 'kitchen']:
            db.add(User(username=role, password_hash=hasher.hash('test-only-password-123'), role=role))
        db.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as client:
        assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'test-only-password-123'}).status_code == 200
        yield client


@pytest.fixture
def payload(client):
    menu = client.get('/api/menu').json()
    burger = next(i for i in menu['items'] if i['name'] == 'Smoky Aloo Burger')
    mild = burger['groups'][0]['options'][0]['id']
    cheese = burger['groups'][1]['options'][0]['id']
    return {'customer': 'Asha', 'instructions': 'Pickup by the side window', 'items': [
        {'menu_item_id': burger['id'], 'quantity': 2, 'option_ids': [mild, cheese], 'instructions': 'Less oil'}]}


def submit(client, payload, key=None):
    return client.post('/api/orders', json=payload, headers={'Idempotency-Key': key or str(uuid4())})
