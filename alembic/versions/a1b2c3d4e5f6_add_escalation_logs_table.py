"""add_escalation_logs_table

Revision ID: a1b2c3d4e5f6
Revises: 7adb30e94476
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7adb30e94476"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escalation_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_escalation_logs_complaint_id"),
        "escalation_logs",
        ["complaint_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_escalation_logs_complaint_id"), table_name="escalation_logs")
    op.drop_table("escalation_logs")
