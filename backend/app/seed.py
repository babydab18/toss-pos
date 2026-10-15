import os
from sqlalchemy import select
from .db import SessionLocal
from .models import User, Category, MenuItem, ModifierGroup, ModifierOption
from .auth import hasher


def seed_demo():
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            password = os.getenv('ADMIN_PASSWORD', '')
            if len(password) < 12:
                raise RuntimeError('Set ADMIN_PASSWORD to at least 12 characters before initializing')
            db.add(User(username=os.getenv('ADMIN_USERNAME', 'admin').lower(), password_hash=hasher.hash(password), role='admin'))
        if not db.scalar(select(Category.id).limit(1)):
            names = ['Starters', 'Main Course', 'Snacks', 'Beverages', 'Combos']
            categories = [Category(name=name, sort_order=index) for index, name in enumerate(names)]
            db.add_all(categories)
            spice = ModifierGroup(name='Spice level', min_select=1, max_select=1, options=[ModifierOption(name=s, price=0) for s in ['Mild', 'Medium', 'Spicy', 'Extra spicy']])
            burger = ModifierGroup(name='Make it yours', min_select=0, max_select=4, options=[ModifierOption(name=n, price=p) for n, p in [('Extra cheese', 2000), ('Extra patty', 5000), ('No onions', 0), ('No tomatoes', 0)]])
            noodles = ModifierGroup(name='Noodle extras', min_select=0, max_select=3, options=[ModifierOption(name=n, price=p) for n, p in [('Add egg', 1500), ('Extra vegetables', 2000), ('No garlic', 0)]])
            db.add_all([spice, burger, noodles])
            db.flush()
            samples = [
                ('Paneer Tikka', 'Charred paneer, peppers & mint chutney', 18000, 0, [spice], True),
                ('Crispy Corn', 'Golden corn tossed with chilli and lime', 12000, 0, [], True),
                ('Smoky Aloo Burger', 'Spiced potato patty, crunchy slaw & house sauce', 14000, 1, [spice, burger], True),
                ('Chicken Tikka Wrap', 'Tandoori chicken, pickled onion & soft roti', 19000, 1, [spice], False),
                ('Street Hakka Noodles', 'Wok-tossed noodles, fresh vegetables & soy', 16000, 1, [spice, noodles], True),
                ('Masala Fries', 'Crisp fries with our signature spice dust', 9000, 2, [], True),
                ('Mumbai Vada Pav', 'The classic potato fritter with garlic chutney', 7000, 2, [], True),
                ('Loaded Nachos', 'Corn chips, melted cheese & fresh salsa', 15000, 2, [], True),
                ('Fresh Lime Soda', 'Fresh lime, soda & a little street-side sparkle', 6000, 3, [], True),
                ('Mango Lassi', 'Chilled mango, creamy yogurt & cardamom', 9000, 3, [], True),
                ('Masala Chai', 'Slow-brewed tea with ginger and warming spices', 4000, 3, [], True),
                ('Burger Break Combo', 'Aloo burger + masala fries + fresh lime soda', 26000, 4, [spice, burger], True),
            ]
            for index, (name, description, price, category, groups, vegetarian) in enumerate(samples):
                db.add(MenuItem(name=name, description=description, price=price, category_id=categories[category].id, groups=groups, vegetarian=vegetarian, is_combo=category == 4, sort_order=index))
        db.commit()


def seed():
    if os.getenv('MENU_PROFILE') == 'demo':
        return seed_demo()
    from .toss_menu import import_menu
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            password = os.getenv('ADMIN_PASSWORD', '')
            if len(password) < 12:
                raise RuntimeError('Set ADMIN_PASSWORD to at least 12 characters before initializing')
            db.add(User(username=os.getenv('ADMIN_USERNAME', 'admin').lower(), password_hash=hasher.hash(password), role='admin'))
        if not db.scalar(select(Category.id).limit(1)):
            import_menu(db, archive_demo=False)
        db.commit()


if __name__ == '__main__':
    seed()
