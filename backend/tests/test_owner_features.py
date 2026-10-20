from unittest.mock import Mock
import pytest
from conftest import submit
from app.db import SessionLocal
from app.models import Order
from app.sms import send_ready


def ready(client, payload):
    order = submit(client, payload).json()
    for status in ['preparing', 'ready']:
        result = client.patch(f"/api/orders/{order['id']}/status", json={'status': status, 'version': order['version']})
        assert result.status_code == 200
        order = result.json()
    return order


def test_phone_and_admin_revert(client, payload):
    payload['phone'] = '+91 (98765) 43210'
    order = ready(client, payload)
    assert order['phone'] == '+919876543210'
    assert order['ready_at']
    for role in ['cashier', 'kitchen']:
        client.post('/api/auth/login', json={'username': role, 'password': 'test-only-password-123'})
        assert client.patch(f"/api/orders/{order['id']}/status", json={'status': 'preparing', 'version': order['version']}).status_code == 403
    client.post('/api/auth/login', json={'username': 'admin', 'password': 'test-only-password-123'})
    changed = client.patch(f"/api/orders/{order['id']}/status", json={'status': 'preparing', 'version': order['version']}).json()
    assert changed['ready_at'] is None
    assert changed['status'] == 'preparing'
    assert 'Admin returned' in changed['history'][-1]['reason']
    assert changed['total'] == order['total']
    assert client.patch(f"/api/orders/{order['id']}/status", json={'status': 'ready', 'version': order['version']}).status_code == 409
    assert client.get('/api/orders?q=98765').json()[0]['id'] == order['id']


def test_phone_validation_and_sms_disabled(client, payload, monkeypatch):
    monkeypatch.delenv('SMS_PROVIDER', raising=False)
    assert submit(client, {**payload, 'phone': 'wrong'}).status_code == 422
    assert submit(client, {**payload, 'sms_opt_in': True}).status_code == 422
    order = ready(client, {**payload, 'phone': '+919876543210', 'sms_opt_in': True})
    assert order['sms_status'] == 'disabled'


@pytest.mark.parametrize('outcome,expected', [('accepted','accepted'), ('rejected','failed'), ('timeout','unknown')])
def test_sms_provider_outcomes_and_no_duplicate(client, payload, monkeypatch, outcome, expected):
    import httpx
    # Queue manually, so the worker and synchronous test cannot race.
    order = ready(client, payload)
    monkeypatch.setenv('SMS_PROVIDER', 'twilio')
    monkeypatch.setenv('TWILIO_ACCOUNT_SID', 'AC' + '0'*32)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'test-token')
    monkeypatch.setenv('TWILIO_FROM', '+15005550006')
    response = Mock(status_code=201 if outcome == 'accepted' else 400)
    response.json.return_value = {'sid': 'SMtest'}
    post = Mock(return_value=response)
    if outcome == 'timeout': post.side_effect = httpx.ReadTimeout('test')
    monkeypatch.setattr('app.sms.httpx.post', post)
    with SessionLocal() as db:
        record = db.get(Order, order['id'])
        record.phone, record.sms_opt_in, record.sms_status = '+919876543210', True, 'pending'
        db.commit()
        send_ready(order['id'])
    send_ready(order['id'])
    assert post.call_count == 1
    saved = client.get(f"/api/orders/{order['id']}").json()
    assert saved['sms_status'] == expected
    assert saved['status'] == 'ready'


def test_free_sauce_requires_style(client):
    from app.toss_menu import import_menu
    with SessionLocal() as db:
        import_menu(db); db.commit()
    item = next(i for i in client.get('/api/menu').json()['items'] if i['name'] == 'Cheese Fries')
    groups = {g['name']:g for g in item['groups']}
    sauce = groups['Free sauce']['options'][0]['id']
    base = {'menu_item_id':item['id'], 'quantity':1}
    assert submit(client, {'items':[{**base, 'option_ids':[sauce]}]}).status_code == 422
    for style in groups['Sauce preparation']['options']:
        result = submit(client, {'items':[{**base, 'option_ids':[sauce,style['id']]}]})
        assert result.status_code == 201
        assert result.json()['total'] == 9900


def test_ready_queues_once_and_revert_cancels_pending(client, payload, monkeypatch):
    monkeypatch.setattr('app.sms.pending_ids', lambda: [])
    monkeypatch.setattr('app.sms.configured', lambda: True)
    post = Mock()
    monkeypatch.setattr('app.sms.httpx.post', post)
    order = ready(client, {**payload, 'phone': '+919876543210', 'sms_opt_in': True})
    assert order['sms_status'] == 'pending'
    reverted = client.patch(f"/api/orders/{order['id']}/status", json={'status': 'preparing', 'version': order['version']}).json()
    assert reverted['sms_status'] == 'cancelled'
    send_ready(order['id'])
    post.assert_not_called()


def test_sms_acceptance_survives_revert_without_resend(client, payload, monkeypatch):
    monkeypatch.setattr('app.sms.pending_ids', lambda: [])
    order = ready(client, payload)
    with SessionLocal() as db:
        record = db.get(Order, order['id'])
        record.sms_opt_in = True
        record.phone = '+919876543210'
        record.sms_status = 'accepted'
        db.commit()
    order = client.get(f"/api/orders/{order['id']}").json()
    for status in ['preparing', 'ready']:
        order = client.patch(f"/api/orders/{order['id']}/status", json={'status': status, 'version': order['version']}).json()
        assert order['sms_status'] == 'accepted'
