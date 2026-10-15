from collections import Counter
from datetime import timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .auth import roles
from .models import Order, now
from .orders import INDIA

router = APIRouter(prefix='/api/analytics', dependencies=[Depends(roles('admin'))], tags=['Operations'])


@router.get('')
def analytics(db: Session = Depends(get_db)):
    today = now().astimezone(INDIA).date()
    orders = db.scalars(select(Order).where(Order.day >= today - timedelta(days=6))).all()
    daily = [o for o in orders if o.day == today]
    statuses = Counter(o.status for o in daily)
    popular = Counter()
    for order in daily:
        if order.status != 'cancelled':
            for item in order.items:
                popular[item.name] += item.quantity
    durations = [(o.ready_at.replace(tzinfo=timezone.utc) - o.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 60 for o in daily if o.ready_at and o.status != 'cancelled']
    hourly = Counter(o.created_at.replace(tzinfo=timezone.utc).astimezone(INDIA).hour for o in daily)
    return {'day': str(today), 'total_orders': len(daily), 'active_orders': sum(statuses[s] for s in ('new', 'preparing', 'ready')),
            'completed_orders': statuses['completed'], 'cancelled_orders': statuses['cancelled'],
            'created_order_value': sum(o.total for o in daily), 'completed_order_value': sum(o.total for o in daily if o.status == 'completed'),
            'average_preparation_minutes': round(sum(durations) / len(durations), 1) if durations else None,
            'popular_items': [{'name': name, 'quantity': count} for name, count in popular.most_common(8)],
            'hourly': [{'hour': h, 'orders': hourly[h]} for h in range(24)],
            'weekly': [{'day': str(today - timedelta(days=days)), 'orders': sum(o.day == today - timedelta(days=days) for o in orders)} for days in range(6, -1, -1)]}
