import hashlib
import json
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.exc import StaleDataError
from .db import get_db
from .auth import current_user, roles
from .models import Order, OrderItem, SelectedModifier, OrderHistory, MenuItem, Category, DailyCounter, User, now
from .schemas import OrderInput, OrderEdit, StatusInput
from .realtime import hub

router = APIRouter(prefix='/api/orders', tags=['Orders'])
INDIA = ZoneInfo('Asia/Kolkata')


def iso(value):
    if value is None:
        return None
    from datetime import timezone
    return value.replace(tzinfo=timezone.utc).isoformat()


def serialize(order):
    return {'id': order.id, 'number': order.number, 'day': str(order.day), 'created_at': iso(order.created_at),
            'ready_at': iso(order.ready_at), 'customer': order.customer, 'phone': order.phone, 'sms_opt_in': order.sms_opt_in, 'sms_status': order.sms_status, 'instructions': order.instructions,
            'status': order.status, 'total': order.total, 'version': order.version,
            'items': [{'id': i.id, 'menu_item_id': i.menu_item_id, 'name': i.name, 'base_price': i.base_price,
                       'unit_price': i.unit_price, 'quantity': i.quantity, 'instructions': i.instructions,
                       'modifiers': [{'option_id': m.option_id, 'group_name': m.group_name, 'name': m.name, 'price': m.price} for m in i.modifiers]} for i in order.items],
            'history': [{'at': iso(h.at), 'status': h.status, 'reason': h.reason, 'changes': h.changes} for h in order.history]}


def build_lines(data, db):
    lines = []
    for entry in data.items:
        item = db.get(MenuItem, entry.menu_item_id)
        category = db.get(Category, item.category_id) if item else None
        if not item or item.archived or item.hidden or not item.available or not category or category.archived:
            raise HTTPException(409, 'An item is unavailable. Refresh the menu and update your order.')
        chosen = set(entry.option_ids)
        if len(chosen) != len(entry.option_ids):
            raise HTTPException(422, 'Duplicate modifier selection')
        known = set()
        modifiers = []
        for group in item.groups:
            if group.archived:
                continue
            selected = [option for option in group.options if option.id in chosen]
            if not group.min_select <= len(selected) <= group.max_select:
                raise HTTPException(422, f'{item.name}: choose {group.min_select}–{group.max_select} options for {group.name}')
            for option in selected:
                known.add(option.id)
                modifiers.append(SelectedModifier(option_id=option.id, group_name=group.name, name=option.name, price=option.price))
        sauce_groups = {g.name: g for g in item.groups if not g.archived}
        if 'Free sauce' in sauce_groups and 'Sauce preparation' in sauce_groups:
            has_sauce = any(o.id in chosen for o in sauce_groups['Free sauce'].options)
            has_style = any(o.id in chosen for o in sauce_groups['Sauce preparation'].options)
            if has_sauce != has_style:
                raise HTTPException(422, 'Choose both a free sauce and its preparation, or leave both blank for plain.')
        if chosen != known:
            raise HTTPException(422, 'A modifier is no longer valid. Customize the item again.')
        lines.append(OrderItem(menu_item_id=item.id, name=item.name, base_price=item.price,
                               unit_price=item.price + sum(m.price for m in modifiers), quantity=entry.quantity,
                               instructions=entry.instructions, modifiers=modifiers))
    return lines


def find_order(id, db):
    order = db.get(Order, id)
    if not order:
        raise HTTPException(404, 'Order not found')
    return order


def check_version(order, version):
    if order.version != version:
        raise HTTPException(409, 'This order changed on another device. Refresh and try again.')


def commit_update(db):
    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(409, 'This order changed on another device. Refresh and try again.')


@router.get('')
def list_orders(q: str = Query('', max_length=100), status: str = '', limit: int = Query(100, ge=1, le=300), offset: int = Query(0, ge=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Order)
    if status == 'active':
        query = query.where(Order.status.in_(['new', 'preparing', 'ready']))
    elif status:
        query = query.where(Order.status == status)
    if q:
        conditions = [Order.customer.ilike(f'%{q}%'), Order.phone.ilike(f'%{q}%'), Order.id == q]
        if q.lstrip('#').isdigit():
            conditions.append(Order.number == int(q.lstrip('#')))
        query = query.where(or_(*conditions))
    ordering = Order.created_at.asc() if status == 'active' else Order.created_at.desc()
    return [serialize(o) for o in db.scalars(query.order_by(ordering).offset(offset).limit(limit)).all()]


@router.get('/{id}')
def get_order(id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return serialize(find_order(id, db))


@router.post('', status_code=201)
async def create_order(data: OrderInput, idempotency_key: str = Header(min_length=16, max_length=100), user: User = Depends(roles('admin', 'cashier')), db: Session = Depends(get_db)):
    fingerprint_data = data.model_dump()
    if not data.phone and not data.sms_opt_in:
        fingerprint_data.pop('phone')
        fingerprint_data.pop('sms_opt_in')
    fingerprint = hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode()).hexdigest()
    def replay(existing):
        if existing.fingerprint != fingerprint or existing.created_by != user.id:
            raise HTTPException(409, 'Submission key already used for a different order')
        return serialize(existing)
    previous = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
    if previous:
        return replay(previous)
    lines = build_lines(data, db)
    day = now().astimezone(INDIA).date()
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(DailyCounter).values(day=day, number=1).on_conflict_do_update(index_elements=['day'], set_={'number': DailyCounter.number + 1}).returning(DailyCounter.number)
    number = db.scalar(statement)
    order = Order(day=day, number=number, customer=data.customer, phone=data.phone, sms_opt_in=data.sms_opt_in, instructions=data.instructions, items=lines,
                  total=sum(i.unit_price * i.quantity for i in lines), created_by=user.id,
                  idempotency_key=idempotency_key, fingerprint=fingerprint,
                  history=[OrderHistory(actor_id=user.id, status='new', reason='Sent to kitchen')])
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if previous:
            return replay(previous)
        raise
    await hub.broadcast('order.created', id=order.id)
    return serialize(order)


@router.put('/{id}')
async def edit_order(id: str, data: OrderEdit, user: User = Depends(roles('admin', 'cashier')), db: Session = Depends(get_db)):
    order = find_order(id, db)
    check_version(order, data.version)
    if order.status not in ('new', 'preparing'):
        raise HTTPException(409, 'Only new or preparing orders can be corrected')
    before = serialize(order)
    order.items = build_lines(data, db)
    order.customer, order.phone, order.instructions = data.customer, data.phone, data.instructions
    order.sms_opt_in = data.sms_opt_in
    order.total = sum(i.unit_price * i.quantity for i in order.items)
    order.version += 1  # Also version changes that only replace child records.
    order.history.append(OrderHistory(actor_id=user.id, status=order.status, reason=data.reason,
        changes={'before': {'items': before['items'], 'customer': before['customer'], 'phone': before['phone'], 'instructions': before['instructions'], 'total': before['total']},
                 'after': {'items': serialize(order)['items'], 'customer': order.customer, 'phone': order.phone, 'sms_opt_in': order.sms_opt_in, 'sms_status': order.sms_status, 'instructions': order.instructions, 'total': order.total}}))
    commit_update(db)
    await hub.broadcast('order.updated', id=order.id)
    return serialize(order)


@router.patch('/{id}/status')
async def change_status(id: str, data: StatusInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = find_order(id, db)
    check_version(order, data.version)
    allowed = {'new': ['preparing', 'cancelled'], 'preparing': ['ready', 'cancelled'], 'ready': ['completed', 'cancelled', 'preparing']}
    if data.status not in allowed.get(order.status, []):
        raise HTTPException(409, 'Invalid order status transition')
    reverting = order.status == 'ready' and data.status == 'preparing'
    if reverting and user.role != 'admin':
        raise HTTPException(403, 'Only an admin can return a ready order to preparing')
    if user.role == 'kitchen' and data.status not in ('preparing', 'ready'):
        raise HTTPException(403, 'Kitchen staff can only prepare or mark ready')
    if data.status == 'cancelled' and not data.reason.strip():
        raise HTTPException(422, 'A cancellation reason is required')
    if reverting:
        order.ready_at = None
        if order.sms_status == 'pending':
            order.sms_status = 'cancelled'
        data.reason = data.reason or 'Admin returned ready order to still preparing'
    order.status = data.status
    if data.status == 'ready':
        order.ready_at = now()
        if order.sms_opt_in and order.phone and order.sms_status in ('not_requested', 'disabled', 'cancelled'):
            from .sms import configured
            order.sms_status = 'pending' if configured() else 'disabled'
    order.history.append(OrderHistory(actor_id=user.id, status=data.status, reason=data.reason))
    commit_update(db)
    await hub.broadcast('order.updated', id=order.id)
    return serialize(order)
