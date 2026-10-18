"""TOSS menu transcribed from the supplied printed menu. All prices are paise.

The importer only archives the original demo dishes; it does not delete orders,
staff, uploaded photos, or other dishes. Existing TOSS records change only with the explicit update_existing option.
Source: owner-supplied poster dated 2026-10-18.
"""
from sqlalchemy import select
from .db import SessionLocal
from .models import Category, MenuItem, ModifierGroup, ModifierOption

DEMO_NAMES = {
    'Paneer Tikka', 'Crispy Corn', 'Smoky Aloo Burger', 'Chicken Tikka Wrap',
    'Street Hakka Noodles', 'Masala Fries', 'Mumbai Vada Pav', 'Loaded Nachos',
    'Fresh Lime Soda', 'Mango Lassi', 'Masala Chai', 'Burger Break Combo',
}
SAUCES = ['Cajun Mayo', 'Peri Peri Mayo', 'Chilli Garlic Mayo', 'Buffalo Sauce',
          'Fiery Glaze', 'Nashville Hot Cheese', 'Honey Mustard', 'Garlic Blaze']
CATEGORIES = ['Burgers', 'Crispy Tenders', 'Wings', 'Fried Chicken Joints', 'Loaded Fries',
              'Wraps', 'Mocktails', 'Veg Burgers', 'Veg Wraps', 'Veg Fries', 'Combo Deals']


def import_menu(db, archive_demo=True, update_existing=False):
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
    if update_existing:
        # Archive only the three retired entries from the previous poster.
        retired = {('Burgers', 'Double Cheese Burger'), ('Loaded Fries', 'Peri Peri Fries'), ('Veg Fries', 'Paneer Loaded Fries')}
        for item, category in db.execute(select(MenuItem, Category).join(Category, MenuItem.category_id == Category.id)):
            if (category.name, item.name) in retired:
                item.archived = True
    categories = {}
    for position, name in enumerate(CATEGORIES):
        category = db.scalar(select(Category).where(Category.name == name, Category.archived == False))
        if not category and update_existing and name == 'Fried Chicken Joints':
            category = db.scalar(select(Category).where(Category.name == 'Fried Chicken Bucket', Category.archived == False))
            if category:
                category.name = name
        if not category:
            category = Category(name=name, sort_order=position)
            db.add(category)
            db.flush()
        categories[name] = category

    def group(name, options, required=False, maximum=1):
        found = db.scalar(select(ModifierGroup).where(ModifierGroup.name == name, ModifierGroup.archived == False))
        if not found and update_existing and name == 'Joint portion':
            found = db.scalar(select(ModifierGroup).where(ModifierGroup.name == 'Bucket portion', ModifierGroup.archived == False))
            if found:
                found.name = name
        if found:
            if update_existing:
                found.min_select, found.max_select = int(required), maximum
                by_name = {option.name: option for option in found.options}
                replacement = []
                for label, price in options:
                    option = by_name.get(label) or ModifierOption(name=label)
                    option.price = price * 100
                    replacement.append(option)
                found.options = replacement
            return found
        found = ModifierGroup(name=name, min_select=int(required), max_select=maximum,
            options=[ModifierOption(name=label, price=price * 100) for label, price in options])
        db.add(found)
        db.flush()
        return found

    toss = group('Sauce tossed', [(name, 29) for name in SAUCES])
    dip = group('Extra dip', [(name, 19) for name in SAUCES])
    cheese = group('Extra cheese', [('Add extra cheese', 29)])
    tenders = group('Tender portion', [('2 pieces', 0), ('4 pieces', 50), ('6 pieces', 110)], True)
    wings = group('Wing portion', [('2 pieces', 0), ('4 pieces', 40), ('6 pieces', 90)], True)
    bucket = group('Joint portion', [('2 pieces', 0), ('4 pieces', 30), ('6 pieces', 100)], True)
    drink = group('Combo mocktail', [(name, 0) for name in ['Tossy Blue', 'Cool Toss', 'Pink Venom']], True)

    # name, rupee price, category, description, vegetarian base, modifier groups
    dishes = [
        ('Crispy Chick', 169, 'Burgers', 'The crispy chicken burger from the TOSS menu.', False, [cheese, dip]),
        ('Nash Cheese', 189, 'Burgers', 'The Nashville cheese burger.', False, [cheese, dip]),
        ('Steak Bite', 199, 'Burgers', 'The TOSS chicken steak burger.', False, [cheese, dip]),
        ('Smash Chick', 199, 'Burgers', 'The TOSS smash chicken burger.', False, [cheese, dip]),
        ('Triple Stack', 299, 'Burgers', 'The TOSS triple-stack burger.', False, [cheese, dip]),
        ('Crispy Tenders', 149, 'Crispy Tenders', 'Crispy chicken tenders. Choose 2, 4 or 6 pieces.', False, [tenders, toss]),
        ('Wings', 139, 'Wings', 'Chicken wings. Choose 2, 4 or 6 pieces.', False, [wings, toss]),
        ('Fried Chicken Joints', 119, 'Fried Chicken Joints', 'Fried chicken joints. Choose 2, 4 or 6 pieces.', False, [bucket, toss]),
        ('Chicken Loaded Fries', 169, 'Loaded Fries', 'Chicken loaded fries from the TOSS menu.', False, [toss]),
        ('Nashville Cheese Fries', 189, 'Loaded Fries', 'Nashville cheese fries from the TOSS menu.', True, [toss]),
        ('Paneer Chick Loaded Fries', 179, 'Loaded Fries', 'Paneer Chick Loaded Fries, as named on the printed menu.', False, [toss]),
        ('Chicken Loaded Wrap', 129, 'Wraps', 'Chicken loaded wrap from the main wraps menu.', False, [toss]),
        ('Nashville Chicken Wrap', 129, 'Wraps', 'Nashville chicken wrap from the main wraps menu.', False, [toss]),
        ('Paneer Wrap', 119, 'Wraps', 'Paneer wrap from the main wraps menu.', True, [toss]),
        ('Mushroom Wrap', 109, 'Wraps', 'Mushroom wrap from the main wraps menu.', True, [toss]),
        ('Tossy Blue', 79, 'Mocktails', 'The blue TOSS mocktail.', True, []),
        ('Cool Toss', 79, 'Mocktails', 'The green TOSS mocktail.', True, []),
        ('Pink Venom', 79, 'Mocktails', 'The pink TOSS mocktail.', True, []),
        ('Mushroom Burger', 109, 'Veg Burgers', 'Mushroom burger from the veg menu.', True, [toss]),
        ('Paneer Burger', 129, 'Veg Burgers', 'Paneer burger from the veg menu.', True, [toss]),
        ('Paneer Wrap', 109, 'Veg Wraps', 'Paneer wrap from the veg wraps menu.', True, [toss]),
        ('Mushroom Wrap', 109, 'Veg Wraps', 'Mushroom wrap from the veg wraps menu.', True, [toss]),
        ('Peri Peri Fries', 79, 'Veg Fries', 'Peri peri fries from the veg fries menu.', True, [toss]),
        ('Cheese Fries', 99, 'Veg Fries', 'Cheese fries from the veg fries menu.', True, [toss]),
        ('Toss Bite - Combo 1', 329, 'Combo Deals', 'Crispy Chick Burger + fries + mocktail.', False, [drink]),
        ('Toss Wings - Combo 2', 349, 'Combo Deals', '4 wings + loaded fries + mocktail.', False, [drink]),
        ('Toss Wrap - Combo 3', 379, 'Combo Deals', 'Chicken Loaded Wrap + peri peri fries + mocktail.', False, [drink]),
    ]
    previous_names = {
        'Crispy Chick': 'Chicken Cluck Burger', 'Nash Cheese': 'Nashville Cheese Burger',
        'Steak Bite': 'Chicken Steak Burger', 'Smash Chick': 'Smash Chicken Burger',
        'Triple Stack': 'Triple Steak Stack', 'Fried Chicken Joints': 'Fried Chicken Bucket',
        'Paneer Chick Loaded Fries': 'Paneer Loaded Fries',
        'Tossy Blue': 'Blue Lagoon', 'Cool Toss': 'Mint Mojito', 'Pink Venom': 'Strawberry Mocktail',
        'Toss Bite - Combo 1': 'Combo 1', 'Toss Wings - Combo 2': 'Combo 2', 'Toss Wrap - Combo 3': 'Combo 3',
    }
    added = 0
    for position, (name, price, category_name, description, vegetarian, groups) in enumerate(dishes):
        category = categories[category_name]
        item = db.scalar(select(MenuItem).where(MenuItem.name == name, MenuItem.category_id == category.id).limit(1))
        if not item and update_existing and name in previous_names:
            item = db.scalar(select(MenuItem).where(MenuItem.name == previous_names[name], MenuItem.category_id == category.id).limit(1))
        if item and not update_existing:
            continue
        if not item:
            item = MenuItem(category_id=category.id)
            db.add(item)
            added += 1
        # Keep identity, uploaded photo, manual visibility and availability.
        item.name, item.price, item.description = name, price * 100, description
        item.vegetarian, item.is_combo = vegetarian, category_name == 'Combo Deals'
        item.groups, item.sort_order = groups, position
    db.flush()
    return added


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import the 2026-10-18 TOSS poster menu.')
    parser.add_argument('--update-existing', action='store_true', help='Apply revised poster prices/names/options and archive retired dishes. Back up the database first.')
    args = parser.parse_args()
    with SessionLocal() as db:
        added = import_menu(db, update_existing=args.update_existing)
        db.commit()
        print(f'TOSS menu imported: {added} items added; update_existing={args.update_existing}. Orders, staff and uploaded photos retained.')
