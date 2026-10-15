"""Use 64-bit paise amounts to avoid overflow on large customized orders."""
from alembic import op
import sqlalchemy as sa

revision = 'f8fbb5123170'
down_revision = 'e0cb6517b969'
branch_labels = None
depends_on = None

MONEY = {'menu_items': ['price'], 'modifier_options': ['price'], 'orders': ['total'], 'order_items': ['base_price', 'unit_price'], 'order_item_modifiers': ['price']}


def upgrade():
    # SQLite uses a signed 64-bit integer for INTEGER already and has no ALTER TYPE.
    if op.get_bind().dialect.name == 'postgresql':
        for table, columns in MONEY.items():
            for column in columns:
                op.alter_column(table, column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        for table, columns in MONEY.items():
            for column in columns:
                op.alter_column(table, column, existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
