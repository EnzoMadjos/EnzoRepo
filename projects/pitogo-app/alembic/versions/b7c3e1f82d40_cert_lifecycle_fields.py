"""Add certificate lifecycle fields (finalized_at, voided_at, voided_by, void_reason)

Revision ID: b7c3e1f82d40
Revises: 441d398e2f58
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c3e1f82d40"
down_revision = "441d398e2f58"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("certificate_issues") as batch_op:
        batch_op.add_column(sa.Column("finalized_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("voided_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("voided_by", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("void_reason", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("certificate_issues") as batch_op:
        batch_op.drop_column("void_reason")
        batch_op.drop_column("voided_by")
        batch_op.drop_column("voided_at")
        batch_op.drop_column("finalized_at")
