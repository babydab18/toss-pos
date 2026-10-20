from datetime import datetime, timezone, date
from uuid import uuid4
from sqlalchemy import String, Integer, BigInteger, Boolean, ForeignKey, DateTime, Date, Text, CheckConstraint, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    __table_args__ = (CheckConstraint("role IN ('admin','cashier','kitchen')"),)


class Session(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(default=0)
    archived: Mapped[bool] = mapped_column(default=False)


class ModifierGroup(Base):
    __tablename__ = 'modifier_groups'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    min_select: Mapped[int] = mapped_column(default=0)
    max_select: Mapped[int] = mapped_column(default=1)
    archived: Mapped[bool] = mapped_column(default=False)
    options: Mapped[list['ModifierOption']] = relationship(cascade='all, delete-orphan', order_by='ModifierOption.id', lazy='selectin')
    __table_args__ = (CheckConstraint('min_select >= 0 AND max_select >= 1 AND max_select >= min_select'),)


class ModifierOption(Base):
    __tablename__ = 'modifier_options'
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey('modifier_groups.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), default=0)
    __table_args__ = (CheckConstraint('price >= 0'),)


class ItemGroup(Base):
    __tablename__ = 'item_modifier_assignments'
    item_id: Mapped[int] = mapped_column(ForeignKey('menu_items.id', ondelete='CASCADE'), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey('modifier_groups.id'), primary_key=True)


class MenuItem(Base):
    __tablename__ = 'menu_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default='')
    price: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'))
    image_url: Mapped[str] = mapped_column(String(500), default='')
    available: Mapped[bool] = mapped_column(default=True)
    hidden: Mapped[bool] = mapped_column(default=False)
    archived: Mapped[bool] = mapped_column(default=False)
    is_combo: Mapped[bool] = mapped_column(default=False)
    vegetarian: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    groups: Mapped[list[ModifierGroup]] = relationship(secondary='item_modifier_assignments', lazy='selectin', order_by='ModifierGroup.id')
    __table_args__ = (CheckConstraint('price >= 0'),)


class DailyCounter(Base):
    __tablename__ = 'daily_counters'
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    number: Mapped[int] = mapped_column(default=0)


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    day: Mapped[date] = mapped_column(Date, index=True)
    number: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default='new', index=True)
    customer: Mapped[str] = mapped_column(String(100), default='')
    phone: Mapped[str] = mapped_column(String(20), default='')
    sms_opt_in: Mapped[bool] = mapped_column(default=False)
    sms_status: Mapped[str] = mapped_column(String(30), default='not_requested')
    sms_sid: Mapped[str] = mapped_column(String(100), default='')
    instructions: Mapped[str] = mapped_column(Text, default='')
    total: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), default=0)
    version: Mapped[int] = mapped_column(default=1)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    items: Mapped[list['OrderItem']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='OrderItem.id')
    history: Mapped[list['OrderHistory']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='OrderHistory.id')
    __mapper_args__ = {'version_id_col': version}
    __table_args__ = (UniqueConstraint('day', 'number'), CheckConstraint('total >= 0'), CheckConstraint("status IN ('new','preparing','ready','completed','cancelled')"))


class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'), index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey('menu_items.id'))
    name: Mapped[str] = mapped_column(String(150))
    base_price: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'))
    unit_price: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'))
    quantity: Mapped[int] = mapped_column()
    instructions: Mapped[str] = mapped_column(Text, default='')
    modifiers: Mapped[list['SelectedModifier']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='SelectedModifier.id')
    __table_args__ = (CheckConstraint('quantity > 0 AND quantity <= 99'), CheckConstraint('base_price >= 0 AND unit_price >= 0'))


class SelectedModifier(Base):
    __tablename__ = 'order_item_modifiers'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey('order_items.id', ondelete='CASCADE'), index=True)
    option_id: Mapped[int] = mapped_column()
    group_name: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'))


class OrderHistory(Base):
    __tablename__ = 'order_status_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text, default='')
    changes: Mapped[dict | None] = mapped_column(JSON)
