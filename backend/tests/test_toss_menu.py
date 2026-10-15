from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import MenuItem, Category
from app.toss_menu import import_menu
from conftest import submit


def install():
    with SessionLocal() as db:
        added = import_menu(db)
        db.commit()
        return added


def test_toss_import_preserves_orders_and_is_idempotent(client, payload):
    order = submit(client, payload).json()
    assert install() == 30
    assert install() == 0
    menu = client.get('/api/menu').json()
    assert len(menu['items']) == 30
    assert len(menu['categories']) == 11
    snapshot = client.get(f"/api/orders/{order['id']}").json()
    assert snapshot['total'] == 32000
    assert snapshot['items'][0]['name'] == 'Smoky Aloo Burger'
    with SessionLocal() as db:
        item = db.scalar(select(MenuItem).where(MenuItem.name == 'Chicken Cluck Burger'))
        item.price = 17500
        db.commit()
    install()
    with SessionLocal() as db:
        assert db.scalar(select(MenuItem).where(MenuItem.name == 'Chicken Cluck Burger')).price == 17500


def test_toss_confirmed_portion_prices_and_sauce(client):
    install()
    menu = client.get('/api/menu').json()
    for name, prices in [('Crispy Tenders', [149, 189, 259, 319]), ('Wings', [139, 179, 229, 289]), ('Fried Chicken Bucket', [119, 229, 319, 449])]:
        item = next(i for i in menu['items'] if i['name'] == name)
        portion = next(g for g in item['groups'] if g['min_select'] == 1)
        sauce = next(g for g in item['groups'] if g['name'] == 'Sauce tossed')
        assert submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1}]}).status_code == 422
        for option, price in zip(portion['options'], prices):
            response = submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1, 'option_ids': [option['id'], sauce['options'][0]['id']]}]})
            assert response.status_code == 201, response.text
            assert response.json()['total'] == (price + 30) * 100


def test_toss_extras_combos_and_category_specific_prices(client):
    install()
    menu = client.get('/api/menu').json()
    burger = next(i for i in menu['items'] if i['name'] == 'Chicken Cluck Burger')
    response = submit(client, {'items': [{'menu_item_id': burger['id'], 'quantity': 1, 'option_ids': [g['options'][0]['id'] for g in burger['groups']]}]})
    assert response.json()['total'] == (169 + 29 + 19) * 100
    for name, price in [('Combo 1', 329), ('Combo 2', 349), ('Combo 3', 379)]:
        item = next(i for i in menu['items'] if i['name'] == name)
        options = item['groups'][0]['options']
        assert len(options) == 3
        response = submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1, 'option_ids': [options[0]['id']]}]})
        assert response.json()['total'] == price * 100
    assert sorted(i['price'] for i in menu['items'] if i['name'] == 'Paneer Wrap') == [14900, 17900]
    assert sorted(i['price'] for i in menu['items'] if i['name'] == 'Peri Peri Fries') == [9900, 14900]


def test_import_keeps_custom_dishes(client):
    with SessionLocal() as db:
        category = db.scalar(select(Category).where(Category.name == 'Starters'))
        db.add(MenuItem(name='Staff Special', price=12500, category_id=category.id))
        db.commit()
    install()
    menu = client.get('/api/menu').json()
    assert any(i['name'] == 'Staff Special' for i in menu['items'])
    assert any(c['name'] == 'Starters' for c in menu['categories'])
