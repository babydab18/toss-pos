import io
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from PIL import Image
from app.main import app
from conftest import submit


@pytest.mark.parametrize('role', ['cashier', 'kitchen'])
def test_permissions(client, payload, role):
    client.post('/api/auth/logout')
    assert client.get('/api/menu').status_code == 401
    client.post('/api/auth/login', json={'username': role, 'password': 'test-only-password-123'})
    assert client.get('/api/admin/menu').status_code == 403
    assert client.get('/api/analytics').status_code == 403
    response = submit(client, payload)
    assert response.status_code == (201 if role == 'cashier' else 403)


def test_kitchen_status_permissions(client, payload):
    order = submit(client, payload).json()
    client.post('/api/auth/logout')
    client.post('/api/auth/login', json={'username': 'kitchen', 'password': 'test-only-password-123'})
    url = f"/api/orders/{order['id']}/status"
    assert client.patch(url, json={'status': 'cancelled', 'version': 1, 'reason': 'No'}).status_code == 403
    assert client.patch(url, json={'status': 'preparing', 'version': 1}).status_code == 200
    assert client.patch(url, json={'status': 'ready', 'version': 2}).status_code == 200
    assert client.patch(url, json={'status': 'completed', 'version': 3}).status_code == 403


def test_csrf_cookie_and_socket_auth(client):
    assert client.post('/api/auth/logout', headers={'origin': 'https://hostile.example'}).status_code == 403
    assert client.get('/api/auth/me').status_code == 200
    with TestClient(app) as stranger:
        assert stranger.get('/api/menu').status_code == 401
        with pytest.raises(WebSocketDisconnect):
            with stranger.websocket_connect('/api/ws', headers={'origin': 'http://localhost:5173'}):
                pass
    client.post('/api/auth/logout')
    assert client.get('/api/orders').status_code == 401


def test_configurable_modifiers_and_archival(client, payload):
    group = {'name': 'Toppings', 'min_select': 2, 'max_select': 1, 'options': [{'name': 'Herbs', 'price': 500}]}
    assert client.post('/api/admin/groups', json=group).status_code == 422
    group.update(min_select=0, max_select=1)
    result = client.post('/api/admin/groups', json=group)
    assert result.status_code == 200
    gid = result.json()['id']
    group['options'][0]['price'] = 1000
    assert client.put(f'/api/admin/groups/{gid}', json=group).status_code == 200
    order = submit(client, payload).json()
    iid = payload['items'][0]['menu_item_id']
    assert client.delete(f'/api/admin/items/{iid}').status_code == 200
    assert client.get(f"/api/orders/{order['id']}").json()['items'][0]['name'] == 'Smoky Aloo Burger'
    assert submit(client, payload).status_code == 409


def test_menu_broadcast_upload_and_users(client):
    with client.websocket_connect('/api/ws', headers={'origin': 'http://localhost:5173'}) as ws:
        ws.receive_json()
        assert client.post('/api/admin/categories', json={'name': 'Desserts', 'sort_order': 6}).status_code == 200
        assert ws.receive_json()['type'] == 'menu.updated'
    assert client.post('/api/admin/images', files={'file': ('bad.svg', b'<svg/>', 'image/svg+xml')}).status_code == 422
    file = io.BytesIO()
    Image.new('RGB', (10, 10), 'orange').save(file, 'PNG')
    uploaded = client.post('/api/admin/images', files={'file': ('food.png', file.getvalue(), 'image/png')})
    assert uploaded.status_code == 200
    assert client.get(uploaded.json()['url']).headers['content-type'] == 'image/webp'
    assert client.post('/api/admin/users', json={'username': 'newstaff', 'password': 'a-strong-test-password', 'role': 'cashier'}).status_code == 201
    assert client.post('/api/admin/users', json={'username': 'newstaff', 'password': 'a-strong-test-password', 'role': 'cashier'}).status_code == 409
