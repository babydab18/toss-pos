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
    assert install() == 27
    assert install() == 0
    menu = client.get('/api/menu').json()
    assert len(menu['items']) == 27
    assert len(menu['categories']) == 11
    snapshot = client.get(f"/api/orders/{order['id']}").json()
    assert snapshot['total'] == 32000
    assert snapshot['items'][0]['name'] == 'Smoky Aloo Burger'
    with SessionLocal() as db:
        item = db.scalar(select(MenuItem).where(MenuItem.name == 'Crispy Chick'))
        item.price = 17500
        db.commit()
    install()
    with SessionLocal() as db:
        assert db.scalar(select(MenuItem).where(MenuItem.name == 'Crispy Chick')).price == 17500


def test_toss_confirmed_portion_prices_and_sauce(client):
    install()
    menu = client.get('/api/menu').json()
    for name, prices in [('Crispy Tenders', [149, 199, 259]), ('Wings', [139, 179, 229]), ('Fried Chicken Drumsticks', [119, 149, 219])]:
        item = next(i for i in menu['items'] if i['name'] == name)
        portion = next(g for g in item['groups'] if g['min_select'] == 1)
        sauce = next(g for g in item['groups'] if g['name'] == 'Free sauce')
        style = next(g for g in item['groups'] if g['name'] == 'Sauce preparation')
        assert submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1}]}).status_code == 422
        assert len(portion['options']) == len(prices) == 3
        assert len(sauce['options']) == 8
        for option, price in zip(portion['options'], prices):
            response = submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1, 'option_ids': [option['id'], sauce['options'][0]['id'], style['options'][0]['id']]}]})
            assert response.status_code == 201, response.text
            assert response.json()['total'] == price * 100


def test_toss_extras_combos_and_category_specific_prices(client):
    install()
    menu = client.get('/api/menu').json()
    burger = next(i for i in menu['items'] if i['name'] == 'Crispy Chick')
    response = submit(client, {'items': [{'menu_item_id': burger['id'], 'quantity': 1, 'option_ids': [g['options'][0]['id'] for g in burger['groups']]}]})
    assert response.json()['total'] == (169 + 29 + 19) * 100
    for name, price in [('Toss Bite - Combo 1', 329), ('Toss Wings - Combo 2', 349), ('Toss Wrap - Combo 3', 379)]:
        item = next(i for i in menu['items'] if i['name'] == name)
        options = item['groups'][0]['options']
        assert len(options) == 3
        response = submit(client, {'items': [{'menu_item_id': item['id'], 'quantity': 1, 'option_ids': [options[0]['id']]}]})
        assert response.json()['total'] == price * 100
    assert sorted(i['price'] for i in menu['items'] if i['name'] == 'Paneer Wrap') == [10900, 11900]
    assert sorted(i['price'] for i in menu['items'] if i['name'] == 'Peri Peri Fries') == [7900]


def test_import_keeps_custom_dishes(client):
    with SessionLocal() as db:
        category = db.scalar(select(Category).where(Category.name == 'Starters'))
        db.add(MenuItem(name='Staff Special', price=12500, category_id=category.id))
        db.commit()
    install()
    menu = client.get('/api/menu').json()
    assert any(i['name'] == 'Staff Special' for i in menu['items'])
    assert any(c['name'] == 'Starters' for c in menu['categories'])


def test_revision_updates_legacy_records_without_rewriting_orders(client):
    from fixtures.legacy_toss_menu import import_menu as legacy_import
    with SessionLocal() as db:
        legacy_import(db)
        db.commit()
    old_menu = client.get('/api/menu').json()
    tender = next(i for i in old_menu['items'] if i['name'] == 'Crispy Tenders')
    portion = next(g for g in tender['groups'] if g['name'] == 'Tender portion')
    sauce = next(g for g in tender['groups'] if g['name'] == 'Sauce tossed')
    eight_pieces = portion['options'][3]['id']
    retired = next(i for i in old_menu['items'] if i['name'] == 'Double Cheese Burger')
    old_order = submit(client, {'items': [
        {'menu_item_id': tender['id'], 'quantity': 1, 'option_ids': [portion['options'][1]['id'], sauce['options'][0]['id']]},
        {'menu_item_id': retired['id'], 'quantity': 1},
    ]}).json()
    assert old_order['total'] == (189 + 30 + 239) * 100
    old_burger = next(i for i in old_menu['items'] if i['name'] == 'Chicken Cluck Burger')
    with SessionLocal() as db:
        burger = db.get(MenuItem, old_burger['id'])
        burger.image_url = '/uploads/owner-photo.webp'
        burger.available = False
        db.add(MenuItem(name='Owner Special', category_id=burger.category_id, price=15100))
        assert import_menu(db, update_existing=True) == 0
        db.commit()
    current = client.get('/api/menu').json()
    assert len(current['items']) == 28  # 27 poster items plus the custom special
    renamed = next(i for i in current['items'] if i['name'] == 'Crispy Chick')
    assert renamed['id'] == old_burger['id']
    assert renamed['image_url'] == '/uploads/owner-photo.webp'
    assert renamed['available'] is False
    assert client.get(f"/api/orders/{old_order['id']}").json() == old_order
    assert submit(client, {'items': [{'menu_item_id': retired['id'], 'quantity': 1}]}).status_code == 409
    assert submit(client, {'items': [{'menu_item_id': tender['id'], 'quantity': 1, 'option_ids': [eight_pieces]}]}).status_code == 422
    before = client.get('/api/menu').json()
    with SessionLocal() as db:
        assert import_menu(db, update_existing=True) == 0
        db.commit()
    assert client.get('/api/menu').json() == before


def test_every_revised_poster_price_and_sauce_assignment(client):
    install()
    menu = client.get('/api/menu').json()
    categories = {c['id']: c['name'] for c in menu['categories']}
    expected = {
        'Burgers': {'Crispy Chick':169, 'Nash Cheese':189, 'Steak Bite':199, 'Smash Chick':199, 'Triple Stack':299},
        'Crispy Tenders': {'Crispy Tenders':149}, 'Wings': {'Wings':139},
        'Fried Chicken Drumsticks': {'Fried Chicken Drumsticks':119},
        'Loaded Fries': {'Chicken Loaded Fries':169, 'Nashville Cheese Fries':189, 'Paneer Chick Loaded Fries':179},
        'Wraps': {'Chicken Loaded Wrap':129, 'Nashville Chicken Wrap':129, 'Paneer Wrap':119, 'Mushroom Wrap':109},
        'Mocktails': {'Tossy Blue':79, 'Cool Toss':79, 'Pink Venom':79},
        'Veg Burgers': {'Mushroom Burger':109, 'Paneer Burger':129},
        'Veg Wraps': {'Paneer Wrap':109, 'Mushroom Wrap':109},
        'Veg Fries': {'Peri Peri Fries':79, 'Cheese Fries':99},
        'Combo Deals': {'Toss Bite - Combo 1':329, 'Toss Wings - Combo 2':349, 'Toss Wrap - Combo 3':379},
    }
    actual = {category: {} for category in categories.values()}
    for item in menu['items']:
        category = categories[item['category_id']]
        actual[category][item['name']] = item['price'] // 100
        if category not in ('Burgers', 'Mocktails', 'Combo Deals'):
            sauce = next(g for g in item['groups'] if g['name'] == 'Free sauce')
            assert {o['price'] for o in sauce['options']} == {0}
            assert {o['name'] for o in sauce['options']} == {'Cajun Mayo', 'Peri Peri Mayo', 'Chilli Garlic Mayo', 'Buffalo Sauce', 'Nashville Hot Cheese', 'Fiery Glaze', 'Honey Mustard', 'Garlic Blaze'}
        if category == 'Combo Deals':
            assert {o['name'] for o in item['groups'][0]['options']} == {'Tossy Blue', 'Cool Toss', 'Pink Venom'}
    assert actual == expected
    assert next(i for i in menu['items'] if i['name'] == 'Paneer Chick Loaded Fries')['vegetarian'] is False
