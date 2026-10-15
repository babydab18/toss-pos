from copy import deepcopy
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal, engine
from app.models import MenuItem, Order, ModifierOption
from conftest import submit


def test_prices_required_modifiers_and_distinct_customizations(client, payload):
    invalid = deepcopy(payload)
    invalid['items'][0]['option_ids'] = []
    assert submit(client, invalid).status_code == 422
    second = deepcopy(payload['items'][0])
    second['option_ids'] = second['option_ids'][:1]
    second['quantity'] = 1
    payload['items'].append(second)
    response = submit(client, payload)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order['total'] == 46000  # 2 * (140 + 20), plus a separately customized 140 burger.
    assert len(order['items']) == 2
    assert order['items'][0]['instructions'] == 'Less oil'
    assert len(order['items'][0]['modifiers']) == 2


def test_duplicate_replay_and_payload_conflict(client, payload):
    key = str(uuid4())
    first = submit(client, payload, key).json()
    second = submit(client, payload, key)
    assert second.status_code == 201
    assert second.json()['id'] == first['id']
    payload['customer'] = 'Different customer'
    assert submit(client, payload, key).status_code == 409
    assert len(client.get('/api/orders').json()) == 1


def test_unavailable_and_invalid_modifier(client, payload):
    bad = deepcopy(payload)
    bad['items'][0]['option_ids'].append(999999)
    assert submit(client, bad).status_code == 422
    bad['items'][0]['option_ids'] = payload['items'][0]['option_ids'] * 2
    assert submit(client, bad).status_code == 422
    with SessionLocal() as db:
        item = db.get(MenuItem, payload['items'][0]['menu_item_id'])
        item.available = False
        db.commit()
    assert submit(client, payload).status_code == 409


def test_lifecycle_correction_and_stale_updates(client, payload):
    order = submit(client, payload).json()
    id = order['id']
    edited = client.put(f'/api/orders/{id}', json={**payload, 'version': 1, 'reason': 'Extra serving', 'items': [{**payload['items'][0], 'quantity': 3}]}).json()
    assert edited['total'] == 48000
    assert edited['version'] == 2
    assert edited['history'][-1]['changes']['before']['total'] == 32000
    assert client.patch(f'/api/orders/{id}/status', json={'status': 'preparing', 'version': 1}).status_code == 409
    version = 2
    for status in ['preparing', 'ready', 'completed']:
        result = client.patch(f'/api/orders/{id}/status', json={'status': status, 'version': version})
        assert result.status_code == 200, result.text
        version = result.json()['version']
    assert client.put(f'/api/orders/{id}', json={**payload, 'version': version, 'reason': 'Too late'}).status_code == 409


def test_cancel_reason_transition_and_metrics(client, payload):
    order = submit(client, payload).json()
    url = f"/api/orders/{order['id']}/status"
    assert client.patch(url, json={'status': 'ready', 'version': 1}).status_code == 409
    assert client.patch(url, json={'status': 'cancelled', 'version': 1}).status_code == 422
    assert client.patch(url, json={'status': 'cancelled', 'version': 1, 'reason': 'Customer left'}).status_code == 200
    data = client.get('/api/analytics').json()
    assert data['cancelled_orders'] == 1
    assert data['created_order_value'] == 32000
    assert data['completed_order_value'] == 0
    assert data['popular_items'] == []


def test_snapshots_and_database_reconnect(client, payload):
    original = submit(client, payload).json()
    with SessionLocal() as db:
        item = db.get(MenuItem, payload['items'][0]['menu_item_id'])
        item.name, item.price = 'New name', 99000
        modifier = db.get(ModifierOption, payload['items'][0]['option_ids'][1])
        modifier.name, modifier.price = 'New cheese', 7500
        db.commit()
    engine.dispose()
    with TestClient(app) as restarted:
        restarted.cookies.update(client.cookies)
        loaded = restarted.get(f"/api/orders/{original['id']}").json()
    assert loaded['total'] == original['total']
    assert loaded['items'][0]['name'] == 'Smoky Aloo Burger'
    assert loaded['items'][0]['modifiers'][1]['name'] == 'Extra cheese'


def test_websockets_two_devices_and_refresh(client, payload):
    headers = {'origin': 'http://localhost:5173'}
    with client.websocket_connect('/api/ws', headers=headers) as first, client.websocket_connect('/api/ws', headers=headers) as second:
        assert first.receive_json()['type'] == 'connected'
        assert second.receive_json()['type'] == 'connected'
        order = submit(client, payload).json()
        assert first.receive_json() == {'type': 'order.created', 'id': order['id']}
        assert second.receive_json()['id'] == order['id']
        client.patch(f"/api/orders/{order['id']}/status", json={'status': 'preparing', 'version': 1})
        assert first.receive_json()['type'] == 'order.updated'
        assert second.receive_json()['type'] == 'order.updated'
    with client.websocket_connect('/api/ws', headers=headers) as reconnected:
        assert reconnected.receive_json()['type'] == 'connected'
        assert client.get('/api/orders?status=active').json()[0]['status'] == 'preparing'


def test_daily_numbers_and_search(client, payload):
    first = submit(client, payload).json()
    second = submit(client, payload).json()
    assert second['number'] == first['number'] + 1
    assert len(client.get('/api/orders?q=Asha').json()) == 2
    assert client.get(f"/api/orders?q={second['id']}").json()[0]['id'] == second['id']


def test_transaction_rolls_back_invalid_order(client, payload):
    payload['items'].append({'menu_item_id': 999999, 'quantity': 1})
    assert submit(client, payload).status_code == 409
    with SessionLocal() as db:
        assert db.scalars(select(Order)).all() == []


def test_concurrent_retries_produce_one_ticket(client, payload):
    from concurrent.futures import ThreadPoolExecutor
    key = str(uuid4())
    cookies = dict(client.cookies)
    def request(_):
        with TestClient(app, cookies=cookies) as other:
            response = submit(other, payload, key)
            assert response.status_code == 201, response.text
            return response.json()['id']
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(request, range(4)))
    assert len(set(ids)) == 1
    assert len(client.get('/api/orders').json()) == 1


def test_modifier_maximum_and_quantity_bounds(client, payload):
    menu = client.get('/api/menu').json()
    item = next(i for i in menu['items'] if i['id'] == payload['items'][0]['menu_item_id'])
    payload['items'][0]['option_ids'].append(item['groups'][0]['options'][1]['id'])
    assert submit(client, payload).status_code == 422
    payload['items'][0]['option_ids'].pop()
    payload['items'][0]['quantity'] = 100
    assert submit(client, payload).status_code == 422


def test_hidden_items_and_nonempty_categories(client, payload):
    with SessionLocal() as db:
        item = db.get(MenuItem, payload['items'][0]['menu_item_id'])
        category_id = item.category_id
        item.hidden = True
        db.commit()
    assert submit(client, payload).status_code == 409
    assert not any(i['id'] == item.id for i in client.get('/api/menu').json()['items'])
    assert client.delete(f'/api/admin/categories/{category_id}').status_code == 409
