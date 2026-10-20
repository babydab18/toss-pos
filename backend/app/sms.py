"""Optional order-ready SMS. Never retry ambiguous provider outcomes automatically."""
import asyncio
import os
from pathlib import Path
import re
import httpx
from dotenv import load_dotenv
from sqlalchemy import select, update
from .db import SessionLocal
from .models import Order

load_dotenv(Path(__file__).resolve().parents[2] / '.env.sms', override=False)


def configured():
    return (os.getenv('SMS_PROVIDER') == 'twilio'
            and bool(re.fullmatch(r'AC[0-9a-fA-F]{32}', os.getenv('TWILIO_ACCOUNT_SID', '')))
            and bool(os.getenv('TWILIO_AUTH_TOKEN'))
            and bool(os.getenv('TWILIO_MESSAGING_SERVICE_SID') or os.getenv('TWILIO_FROM')))


def send_ready(order_id):
    with SessionLocal() as db:
        # Atomic claim prevents two workers from sending the same notification.
        claimed = db.execute(update(Order).where(Order.id == order_id, Order.sms_status == 'pending',
            Order.status == 'ready', Order.sms_opt_in == True).values(sms_status='sending', version=Order.version + 1))
        db.commit()
        if not claimed.rowcount:
            return
        order = db.get(Order, order_id)
        phone, number = order.phone, order.number
    state, sid = 'unknown', ''
    if not configured():
        state = 'disabled'
    else:
        account = os.environ['TWILIO_ACCOUNT_SID']
        data = {'To': phone, 'Body': f'TOSS: Your order #{number} is ready. Please collect it at the counter.'}
        if os.getenv('TWILIO_MESSAGING_SERVICE_SID'):
            data['MessagingServiceSid'] = os.environ['TWILIO_MESSAGING_SERVICE_SID']
        else:
            data['From'] = os.environ['TWILIO_FROM']
        try:
            response = httpx.post(f'https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json',
                auth=(account, os.environ['TWILIO_AUTH_TOKEN']), data=data, timeout=10)
            if response.status_code == 201:
                sid = str(response.json().get('sid', ''))[:100]
                state = 'accepted' if sid else 'unknown'
            elif 400 <= response.status_code < 500:
                state = 'failed'
            # A timeout/5xx might follow acceptance; do not risk duplicate texts.
        except (httpx.HTTPError, ValueError):
            pass
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.id == order_id, Order.sms_status == 'sending').values(sms_status=state, sms_sid=sid, version=Order.version + 1))
        db.commit()


def pending_ids():
    with SessionLocal() as db:
        return list(db.scalars(select(Order.id).where(Order.sms_status == 'pending', Order.status == 'ready').limit(20)))


def recover_interrupted():
    # Supported deployment uses one server worker. A crashed request may have sent.
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.sms_status == 'sending').values(sms_status='unknown', version=Order.version + 1))
        db.commit()


async def worker():
    import logging
    await asyncio.to_thread(recover_interrupted)
    while True:
        try:
            for order_id in await asyncio.to_thread(pending_ids):
                await asyncio.to_thread(send_ready, order_id)
        except Exception:
            logging.getLogger(__name__).warning('SMS worker could not process pending notifications; will check again.')
        await asyncio.sleep(2)
