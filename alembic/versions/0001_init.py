
"""Migração inicial: caixas de entrada/saída e estado."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "inbox_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("provider_message_id", sa.String(64), nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.TIMESTAMP(timezone=False)),
        sa.Column("trace_id", sa.String(64)),
        sa.UniqueConstraint("conversation_id","provider_message_id", name="uq_inbox_idem"),
    )
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False)),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.create_table(
        "conversation_state",
        sa.Column("conversation_id", sa.String(64), primary_key=True),
        sa.Column("memory_summary", sa.String(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_table(
        "conversation_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("ts", sa.BigInteger, nullable=False),
    )
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("sku", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("unit_price_cents", sa.Integer, nullable=False),
    )

def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("conversation_events")
    op.drop_table("conversation_state")
    op.drop_table("outbox_messages")
    op.drop_table("inbox_messages")
