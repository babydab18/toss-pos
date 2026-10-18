"""TOSS menu transcribed from the supplied printed menu. All prices are paise.

The importer only archives the original demo dishes; it does not delete orders,
staff, uploaded photos, or other dishes. Existing TOSS records are never reset.
"""
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Category, MenuItem, ModifierGroup, ModifierOption

DEMO_NAMES = {
    'Paneer Tikka', 'Crispy Corn', 'Smoky Aloo Burger', 'Chicken Tikka Wrap',
    'Street Hakka Noodles', 'Masala Fries', 'Mumbai Vada Pav', 'Loaded Nachos',
    'Fresh Lime Soda', 'Mango Lassi', 'Masala Chai', 'Burger Break Combo',
}
SAUCES = ['Cajun Mayo', 'Peri Peri Mayo', 'Chilli Garlic Mayo', 'Buffalo Sauce',
          'Hot Honey Glaze', 'BBQ Ranch', 'Nashville Hot Cheese', 'Honey Mustard', 'Garlic Blaze']
CATEGORIES = ['Burgers', 'Crispy Tenders', 'Wings', 'Fried Chicken Bucket', 'Loaded Fries',
              'Wraps', 'Mocktails', 'Veg Burgers', 'Veg Wraps', 'Veg Fries', 'Combo Deals']


def import_menu(db, archive_demo=True):
    existing_items = list(db.scalars(select(MenuItem)))
    if archive_demo:
        for item in existing_items:
            if item.name in DEMO_NAMES:
                item.archived = True
        db.flush()
        for category in db.scalars(select(Category).where(Category.archived == False)):
            # Retire only emptied demo categories, keeping any user-added content.
            if category.name in ['Starters', 'Main Course', 'Snacks', 'Beverages', 'Combos']:
                if not db.scalar(select(MenuItem.id).where(MenuItem.category_id == category.id, MenuItem.archived == False).limit(1)):
                    category.archived = True
    categories = {}
    for position, name in enumerate(CATEGORIES):
        category = db.scalar(select(Category).where(Category.name == name, Category.archived == False))
        if not category:
            category = Category(name=name, sort_order=position)
            db.add(category)
            db.flush()
        categories[name] = category

    def group(name, options, required=False, maximum=1):
        found = db.scalar(select(ModifierGroup).where(ModifierGroup.name == name, ModifierGroup.archived == False))
        if found:
            return found
        found = ModifierGroup(name=name, min_select=int(required), max_select=maximum,
            options=[ModifierOption(name=label, price=price * 100) for label, price in options])
        db.add(found)
        db.flush()
        return found

    toss = group('Sauce tossed', [(name, 30) for name in SAUCES])
    dip = group('Extra dip', [(name, 19) for name in SAUCES])
    cheese = group('Extra cheese', [('Add extra cheese', 29)])
    tenders = group('Tender portion', [('2 pieces', 0), ('4 pieces', 40), ('6 pieces', 110), ('8 pieces', 170)], True)
    wings = group('Wing portion', [('2 pieces', 0), ('4 pieces', 40), ('6 pieces', 90), ('8 pieces', 150)], True)
    bucket = group('Bucket portion', [('2 pieces', 0), ('4 pieces', 110), ('6 pieces', 200), ('8 pieces', 330)], True)
    drink = group('Combo mocktail', [(name, 0) for name in ['Blue Lagoon', 'Mint Mojito', 'Strawberry Mocktail']], True)

    # name, rupee price, category, description, vegetarian base, modifier groups
    dishes = [
        ('Chicken Cluck Burger', 169, 'Burgers', 'The TOSS chicken burger. Crispy, juicy, drippy.', False, [cheese, dip]),
        ('Nashville Cheese Burger', 189, 'Burgers', 'Nashville heat meets a cheesy chicken burger.', False, [cheese, dip]),
        ('Chicken Steak Burger', 199, 'Burgers', 'Chicken steak stacked in a burger bun.', False, [cheese, dip]),
        ('Smash Chicken Burger', 199, 'Burgers', 'Our smash-style chicken burger.', False, [cheese, dip]),
        ('Double Cheese Burger', 239, 'Burgers', 'A double hit of cheese. Full-on TOSS flavour.', False, [cheese, dip]),
        ('Triple Steak Stack', 299, 'Burgers', 'The towering triple-stack burger.', False, [cheese, dip]),
        ('Crispy Tenders', 149, 'Crispy Tenders', 'Golden chicken tenders. Choose 2, 4, 6 or 8 pieces.', False, [tenders, toss]),
        ('Wings', 139, 'Wings', 'Crispy chicken wings. Choose 2, 4, 6 or 8 pieces.', False, [wings, toss]),
        ('Fried Chicken Bucket', 119, 'Fried Chicken Bucket', 'Your fried chicken fix. Choose 2, 4, 6 or 8 pieces.', False, [bucket, toss]),
        ('Peri Peri Fries', 149, 'Loaded Fries', 'Peri peri fries from the loaded-fries menu.', True, [toss]),
        ('Chicken Loaded Fries', 169, 'Loaded Fries', 'Fries piled with chicken and TOSS flavour.', False, [toss]),
        ('Nashville Cheese Fries', 189, 'Loaded Fries', 'Loaded fries with Nashville cheese.', True, [toss]),
        ('Paneer Loaded Fries', 179, 'Loaded Fries', 'Paneer-topped fries from the loaded-fries menu.', True, [toss]),
        ('Chicken Loaded Wrap', 169, 'Wraps', 'Chicken, wrapped and ready to go.', False, []),
        ('Nashville Chicken Wrap', 189, 'Wraps', 'A chicken wrap with a Nashville kick.', False, []),
        ('Paneer Wrap', 179, 'Wraps', 'Paneer wrap from the main wraps menu.', True, []),
        ('Mushroom Wrap', 149, 'Wraps', 'Mushroom wrap from the main wraps menu.', True, []),
        ('Blue Lagoon', 119, 'Mocktails', 'The bright blue TOSS mocktail.', True, []),
        ('Mint Mojito', 119, 'Mocktails', 'A refreshing mint mocktail.', True, []),
        ('Strawberry Mocktail', 119, 'Mocktails', 'A fruity strawberry refresher.', True, []),
        ('Mushroom Burger', 159, 'Veg Burgers', 'Mushroom burger from the green menu.', True, [cheese, dip]),
        ('Paneer Burger', 179, 'Veg Burgers', 'Paneer burger from the green menu.', True, [cheese, dip]),
        ('Paneer Wrap', 149, 'Veg Wraps', 'Paneer wrap from the green menu.', True, []),
        ('Mushroom Wrap', 149, 'Veg Wraps', 'Mushroom wrap from the green menu.', True, []),
        ('Peri Peri Fries', 99, 'Veg Fries', 'Peri peri fries from the green menu.', True, []),
        ('Cheese Fries', 129, 'Veg Fries', 'Fries finished with cheese.', True, []),
        ('Paneer Loaded Fries', 169, 'Veg Fries', 'Paneer-topped fries from the green menu.', True, []),
        ('Combo 1', 329, 'Combo Deals', 'Chicken Cluck Burger + fries + mocktail.', False, [drink]),
        ('Combo 2', 349, 'Combo Deals', '4 wings + loaded fries + mocktail.', False, [drink]),
        ('Combo 3', 379, 'Combo Deals', 'Chicken Loaded Wrap + fries + mocktail.', False, [drink]),
    ]
    added = 0
    for position, (name, price, category_name, description, vegetarian, groups) in enumerate(dishes):
        category = categories[category_name]
        if db.scalar(select(MenuItem.id).where(MenuItem.name == name, MenuItem.category_id == category.id).limit(1)):
            continue
        db.add(MenuItem(name=name, price=price * 100, category_id=category.id, description=description,
            vegetarian=vegetarian, is_combo=category_name == 'Combo Deals', groups=groups, sort_order=position))
        added += 1
    db.flush()
    return added
