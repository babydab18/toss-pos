"""Optional customer phone number."""
from alembic import op
import sqlalchemy as sa
revision = 'a19_phone'
down_revision = 'f8fbb5123170'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('phone', sa.String(20), nullable=False, server_default=''))

    op.add_column('orders', sa.Column('sms_opt_in', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('orders', sa.Column('sms_status', sa.String(30), nullable=False, server_default='not_requested'))
    op.add_column('orders', sa.Column('sms_sid', sa.String(100), nullable=False, server_default=''))


def downgrade():
    op.drop_column('orders', 'sms_sid')
    op.drop_column('orders', 'sms_status')
    op.drop_column('orders', 'sms_opt_in')
    op.drop_column('orders', 'phone')
