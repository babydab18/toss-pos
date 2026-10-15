import io
import os
from pathlib import Path
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user, roles, hasher
from .models import Category, ModifierGroup, ModifierOption, MenuItem, User
from .schemas import CategoryInput, GroupInput, ItemInput, UserInput
from .realtime import hub

router = APIRouter(tags=['Menu'])
admin = APIRouter(prefix='/api/admin', dependencies=[Depends(roles('admin'))], tags=['Administration'])
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', './uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Image.MAX_IMAGE_PIXELS = 16000000


def group_json(group):
    return {'id': group.id, 'name': group.name, 'min_select': group.min_select, 'max_select': group.max_select,
            'options': [{'id': o.id, 'name': o.name, 'price': o.price} for o in group.options]}


def menu_data(db, all_items=False):
    categories = db.scalars(select(Category).where(Category.archived == False).order_by(Category.sort_order, Category.id)).all()
    query = select(MenuItem).where(MenuItem.archived == False, MenuItem.category_id.in_([c.id for c in categories])).order_by(MenuItem.sort_order, MenuItem.id)
    if not all_items:
        query = query.where(MenuItem.hidden == False)
    return {'categories': [{'id': c.id, 'name': c.name, 'sort_order': c.sort_order} for c in categories],
            'groups': [group_json(g) for g in db.scalars(select(ModifierGroup).where(ModifierGroup.archived == False).order_by(ModifierGroup.id))],
            'items': [{'id': i.id, 'category_id': i.category_id, 'name': i.name, 'description': i.description, 'price': i.price,
                       'image_url': i.image_url, 'available': i.available, 'hidden': i.hidden, 'is_combo': i.is_combo,
                       'vegetarian': i.vegetarian, 'sort_order': i.sort_order,
                       'groups': [group_json(g) for g in i.groups if not g.archived]} for i in db.scalars(query)]}


@router.get('/api/menu')
def menu(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return menu_data(db)


@admin.get('/menu')
def admin_menu(db: Session = Depends(get_db)):
    return menu_data(db, True)


def get_record(model, id, db):
    record = db.get(model, id)
    if not record or record.archived:
        raise HTTPException(404, 'Record not found')
    return record


async def save(db, record):
    db.add(record)
    db.commit()
    await hub.broadcast('menu.updated')
    return {'id': record.id}


@admin.post('/categories')
async def add_category(data: CategoryInput, db: Session = Depends(get_db)):
    return await save(db, Category(**data.model_dump()))


@admin.put('/categories/{id}')
async def update_category(id: int, data: CategoryInput, db: Session = Depends(get_db)):
    record = get_record(Category, id, db)
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    return await save(db, record)


@admin.post('/groups')
async def add_group(data: GroupInput, db: Session = Depends(get_db)):
    return await save(db, ModifierGroup(**data.model_dump(exclude={'options'}), options=[ModifierOption(**o.model_dump()) for o in data.options]))


@admin.put('/groups/{id}')
async def update_group(id: int, data: GroupInput, db: Session = Depends(get_db)):
    record = get_record(ModifierGroup, id, db)
    record.name, record.min_select, record.max_select = data.name, data.min_select, data.max_select
    # Preserve IDs for unchanged option names so existing drafts remain valid.
    old = {o.name.casefold(): o for o in record.options}
    options = []
    for entry in data.options:
        option = old.get(entry.name.casefold(), ModifierOption())
        option.name, option.price = entry.name, entry.price
        options.append(option)
    record.options = options
    return await save(db, record)


def assign_item(record, data, db):
    get_record(Category, data.category_id, db)
    groups = [get_record(ModifierGroup, id, db) for id in set(data.group_ids)]
    for key, value in data.model_dump(exclude={'group_ids'}).items():
        setattr(record, key, value)
    record.groups = groups
    return record


@admin.post('/items')
async def add_item(data: ItemInput, db: Session = Depends(get_db)):
    return await save(db, assign_item(MenuItem(), data, db))


@admin.put('/items/{id}')
async def update_item(id: int, data: ItemInput, db: Session = Depends(get_db)):
    return await save(db, assign_item(get_record(MenuItem, id, db), data, db))


@admin.delete('/{kind}/{id}')
async def archive(kind: str, id: int, db: Session = Depends(get_db)):
    model = {'items': MenuItem, 'groups': ModifierGroup, 'categories': Category}.get(kind)
    if model is None:
        raise HTTPException(404, 'Unknown resource')
    if kind == 'categories' and db.scalar(select(MenuItem.id).where(MenuItem.category_id == id, MenuItem.archived == False).limit(1)):
        raise HTTPException(409, 'Move or delete the items in this category first')
    record = get_record(model, id, db)
    record.archived = True
    return await save(db, record)


@admin.post('/images')
async def upload_image(file: UploadFile):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, 'Images must be under 5 MB')
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.format not in ('JPEG', 'PNG', 'WEBP') or img.width * img.height > 16000000:
                raise HTTPException(422, 'Use a JPEG, PNG or WebP image up to 16 megapixels')
            img.load()
            img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            filename = f'{uuid4().hex}.webp'
            img.save(UPLOAD_DIR / filename, 'WEBP', quality=85)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise HTTPException(422, 'Upload a valid JPEG, PNG, or WebP image')
    return {'url': f'/uploads/{filename}'}


@admin.get('/users')
def users(db: Session = Depends(get_db)):
    return [{'id': u.id, 'username': u.username, 'role': u.role} for u in db.scalars(select(User).order_by(User.id))]


@admin.post('/users', status_code=201)
def add_user(data: UserInput, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    user = User(username=data.username.lower(), password_hash=hasher.hash(data.password), role=data.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Username already exists')
    return {'id': user.id, 'username': user.username, 'role': user.role}
